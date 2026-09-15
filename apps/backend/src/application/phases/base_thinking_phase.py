import logging
from abc import ABC

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.errors.ralph_error import RalphError
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.settings_interface import ISettings
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.domain.interfaces.thinking_phase_interface import IThinkingPhase

_CORRECTION_TEMPLATE = (
    "A saída anterior não pôde ser interpretada: {reason}\n"
    "Reescreva a resposta como um único objeto JSON válido, no formato exigido acima, "
    "sem texto antes ou depois e sem cerca de código."
)
_NO_TOKENS = 0
_NO_ELAPSED_MS = 0
_NO_RETRIES_LEFT = 0


class BaseThinkingPhase(IThinkingPhase, ABC):
    """Template Method comum às etapas do fluxo de thinking.

    O esqueleto "montar prompt → chamar LLM → registrar custo → parsear JSON" é
    idêntico para todas as fases; as subclasses variam apenas o template e o
    schema esperado.
    """

    def __init__(
        self,
        llm_completions: ILLMCompletions,
        template_provider: IPromptTemplateProvider,
        parser: IStructuredResponseParser,
        cost_guard: ICostGuard,
        clock: IClock,
        settings: ISettings,
        logger: logging.Logger,
    ) -> None:
        """Inicializa a fase.

        Args:
            llm_completions: Porta de completions do domínio.
            template_provider: Provedor dos templates de prompt.
            parser: Parser da saída estruturada do modelo.
            cost_guard: Ponto único de decisão sobre limites de custo.
            clock: Fonte de tempo do domínio.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.llm_completions: ILLMCompletions = llm_completions
        self.template_provider: IPromptTemplateProvider = template_provider
        self.parser: IStructuredResponseParser = parser
        self.cost_guard: ICostGuard = cost_guard
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger
        self.model_name: str | None = None
        self.max_tokens: int | None = None
        self.temperature: float | None = None

    def configure(self, model_name: str, max_tokens: int, temperature: float) -> None:
        """Fixa os parâmetros do modelo usados por todas as execuções da fase.

        Args:
            model_name: Nome do modelo a ser usado nas chamadas da fase.
            max_tokens: Limite de tokens de saída das chamadas da fase.
            temperature: Temperatura de geração das chamadas da fase.
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def execute(self, context: ContextWindow, variables: dict[str, str]) -> PhaseOutcome:
        """Executa a fase sobre a janela de contexto informada.

        O prompt entra na janela, o modelo responde, o custo é contabilizado e a
        saída é parseada. Duas falhas são retentáveis até o limite configurado, porque
        ambas são não determinísticas: o modelo devolver algo que não é o JSON da fase
        (aí a janela recebe uma mensagem de correção) e o provedor devolver uma resposta
        sem conteúdo nenhum (aí não há o que corrigir, só o que repetir). O custo de cada
        retentativa é somado ao resultado, porque é custo real.

        Args:
            context: Janela de contexto em que a fase é executada.
            variables: Placeholders a substituir no template da fase.

        Returns:
            PhaseOutcome: Resultado da execução da fase.

        Raises:
            BudgetExceededError: Quando o guardião de custo nega a chamada.
            PhaseParsingError: Quando o limite de retentativas de parsing se esgota.
            EmptyCompletionError: Quando o provedor insiste em responder sem conteúdo.
        """
        context.append(
            message=Message(
                creation_timestamp=self.clock.now(),
                text=self.template_provider.render(phase=self.phase, variables=variables),
                source=MessageSourceEnum.USER,
            )
        )

        retries_left = self.settings.ralph_json_parse_max_retries
        tokens_input = _NO_TOKENS
        tokens_output = _NO_TOKENS
        inference_time_ms = _NO_ELAPSED_MS

        while True:
            try:
                llm_message, elapsed_ms = await self.__call_model(context=context)
            except EmptyCompletionError as error:
                # Sem conteúdo não há tokens a somar nem mensagem a acrescentar à janela: a
                # única correção possível é pedir de novo, com o mesmo contexto.
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                continue

            tokens = llm_message.tokens
            tokens_input += tokens.tokens_input
            tokens_output += tokens.tokens_output
            inference_time_ms += elapsed_ms
            raw_output = llm_message.output_message.text

            try:
                parsed = self.parser.parse(raw_output=raw_output, phase=self.phase)
            except PhaseParsingError as error:
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                context.append(
                    message=Message(
                        creation_timestamp=self.clock.now(),
                        text=_CORRECTION_TEMPLATE.format(reason=error.reason),
                        source=MessageSourceEnum.USER,
                    )
                )
                continue

            return PhaseOutcome(
                raw_output=raw_output,
                parsed=parsed,
                tokens=TokensUsage(
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    llm_model=tokens.llm_model,
                ),
                inference_time_ms=inference_time_ms,
                context_id=context.context_id,
            )

    def __consume_retry(self, retries_left: int, error: RalphError) -> int:
        """Gasta uma retentativa de saída inválida, ou deixa a falha subir.

        Args:
            retries_left: Retentativas ainda disponíveis nesta execução da fase.
            error: Falha que motivou a retentativa.

        Returns:
            int: Retentativas restantes depois de gastar uma.

        Raises:
            RalphError: A própria falha recebida, quando não há mais retentativa.
        """
        if retries_left <= _NO_RETRIES_LEFT:
            self.logger.warning("Fase '%s' esgotou as retentativas de saída inválida", self.phase.value)
            raise error
        return retries_left - 1

    async def __call_model(self, context: ContextWindow) -> tuple[LLMMessage, int]:
        """Autoriza, chama o modelo cronometrando e contabiliza o consumo.

        Args:
            context: Janela de contexto enviada integralmente ao modelo.

        Returns:
            tuple[LLMMessage, int]: Resultado da chamada e sua duração em milissegundos.

        Raises:
            BudgetExceededError: Quando o guardião de custo nega a chamada.
        """
        verdict = self.cost_guard.authorize(phase=self.phase)
        if not verdict.authorized:
            raise BudgetExceededError(limit=verdict.limit)

        started_at_ms = self.clock.monotonic_ms()
        llm_message = await self.llm_completions.send_conversation(
            conversation=context.messages,
            model_name=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        elapsed_ms = self.clock.monotonic_ms() - started_at_ms

        context.append(message=llm_message.output_message)
        context.register_usage(tokens=llm_message.tokens)
        self.cost_guard.register_call(tokens=llm_message.tokens)

        return llm_message, elapsed_ms
