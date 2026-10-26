import logging
from abc import ABC
from dataclasses import dataclass

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.errors.ralph_error import RalphError
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.domain.interfaces.settings_interface import ISettings
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.domain.interfaces.thinking_phase_interface import IThinkingPhase

_CORRECTION_TEMPLATE = (
    "A saída anterior não pôde ser interpretada: {reason}\n"
    "Reescreva a resposta como um único objeto JSON válido, no formato exigido acima, "
    "sem texto antes ou depois e sem cerca de código."
)
_INVALID_OUTPUT_AUDIT_TEMPLATE = (
    "Saída inválida descartada na fase {phase}: {reason}\n\n"
    "Saída bruta do modelo:\n\n{raw_output}"
)
_NO_TOKENS = 0
_NO_ELAPSED_MS = 0
_NO_RETRIES_LEFT = 0
# Temperatura de toda chamada de retentativa. Repetir um pedido que falhou com a temperatura do usuário
# — em geral baixa — tende a reproduzir a mesma saída e a mesma falha até esgotar as tentativas.
_RETRY_TEMPERATURE = 1.0


@dataclass
class _PhaseAccounting:
    """Consumo agregado das chamadas de uma execução de fase, para exibição.

    Os totais da sessão não vêm daqui: vêm de cada invocação registrada. Esta agregação
    só alimenta o `PhaseOutcome`, que descreve a fase como um todo.
    """

    tokens_input: int = _NO_TOKENS
    tokens_output: int = _NO_TOKENS
    inference_time_ms: int = _NO_ELAPSED_MS
    input_known: bool = True
    output_known: bool = True

    def add(self, tokens_input: int | None, tokens_output: int | None, elapsed_ms: int) -> None:
        """Soma o que se sabe de uma chamada concluída.

        Args:
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            elapsed_ms: Duração da chamada, em milissegundos.
        """
        self.tokens_input += tokens_input or _NO_TOKENS
        self.tokens_output += tokens_output or _NO_TOKENS
        self.inference_time_ms += elapsed_ms
        self.input_known = self.input_known and tokens_input is not None
        self.output_known = self.output_known and tokens_output is not None


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
        session_recorder: ISessionRecorder,
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
            session_recorder: Registro da sessão, fonte única das invocações ao modelo.
            clock: Fonte de tempo do domínio.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.llm_completions: ILLMCompletions = llm_completions
        self.template_provider: IPromptTemplateProvider = template_provider
        self.parser: IStructuredResponseParser = parser
        self.cost_guard: ICostGuard = cost_guard
        self.session_recorder: ISessionRecorder = session_recorder
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger
        self.model_name: str | None = None
        self.max_tokens: int | None = None
        self.temperature: float | None = None
        self.provider: ModelProviderEnum | None = None

    def configure(
        self,
        model_name: str,
        max_tokens: int,
        temperature: float,
        provider: ModelProviderEnum,
    ) -> None:
        """Fixa os parâmetros do modelo usados por todas as execuções da fase.

        Args:
            model_name: Nome do modelo a ser usado nas chamadas da fase.
            max_tokens: Limite de tokens de saída das chamadas da fase.
            temperature: Temperatura de geração das chamadas da fase.
            provider: Provedor que atende as chamadas da fase.
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.provider = provider

    async def execute(
        self,
        context: ContextWindow,
        variables: dict[str, str],
        validation: ValidationContext | None = None,
        is_retry: bool = False,
    ) -> PhaseOutcome:
        """Executa a fase sobre a janela de contexto informada.

        O prompt entra na janela, o modelo responde, o custo é contabilizado e a
        saída é parseada. Duas falhas são retentáveis até o limite configurado, porque
        ambas são não determinísticas: o modelo devolver algo que não é o JSON da fase
        (ou um JSON que contradiz o contexto de validação), caso em que a janela recebe uma
        mensagem de correção, e o provedor devolver uma resposta sem conteúdo nenhum, caso em
        que não há o que corrigir, só o que repetir. Cada retentativa é uma nova invocação,
        autorizada e registrada como as demais: o custo de uma chamada não se perde por ela ter
        sido recusada, e uma recusa do parser não consome tentativas de resolução da tarefa.

        Cada saída recusada pelo parser fica registrada na sessão no momento da recusa, inclusive a
        última, que encerra a fase com erro: a auditoria independe de a fase terminar bem.

        Toda chamada de retentativa sai com a temperatura de retentativa (1), e não com a do usuário:
        tanto as correções de saída inválida ou vazia quanto, quando `is_retry` é verdadeiro, todas as
        chamadas da execução. A temperatura configurada não muda; a próxima execução volta a usá-la.

        Args:
            context: Janela de contexto em que a fase é executada.
            variables: Placeholders a substituir no template da fase.
            validation: Dados esperados pela chamada, repassados ao parser.
            is_retry: Indica que a execução inteira repete um pedido reprovado.

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
        accounting = _PhaseAccounting()
        invalid_outputs: list[InvalidOutput] = []
        temperature = _RETRY_TEMPERATURE if is_retry else self.temperature

        while True:
            # A janela é a conversa enviada nesta chamada; a resposta só entra nela depois do envio.
            prompt_input = tuple(context.messages)
            try:
                llm_message = await self.__call_model(context=context, accounting=accounting, temperature=temperature)
            except EmptyCompletionError as error:
                # Sem conteúdo não há mensagem a acrescentar à janela: a única correção possível
                # é pedir de novo, com o mesmo contexto. O custo da chamada já foi registrado.
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                temperature = _RETRY_TEMPERATURE
                continue

            raw_output = llm_message.output_message.text

            try:
                parsed = self.parser.parse(
                    raw_output=raw_output,
                    phase=self.phase,
                    validation=validation,
                    finish_reason=llm_message.finish_reason,
                )
            except PhaseParsingError as error:
                invalid_output = InvalidOutput(raw_output=raw_output, reason=error.reason)
                invalid_outputs.append(invalid_output)
                # A auditoria não pode depender de a fase terminar bem: é justamente quando as correções
                # se esgotam que o intercâmbio com o modelo precisa ter ficado na sessão.
                await self.__audit_invalid_output(
                    context=context, invalid_output=invalid_output, prompt_input=prompt_input
                )
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                context.append(
                    message=Message(
                        creation_timestamp=self.clock.now(),
                        text=_CORRECTION_TEMPLATE.format(reason=error.reason),
                        source=MessageSourceEnum.USER,
                    )
                )
                temperature = _RETRY_TEMPERATURE
                continue

            return PhaseOutcome(
                raw_output=raw_output,
                parsed=parsed,
                tokens=TokensUsage(
                    tokens_input=accounting.tokens_input,
                    tokens_output=accounting.tokens_output,
                    llm_model=llm_message.tokens.llm_model,
                    input_known=accounting.input_known,
                    output_known=accounting.output_known,
                ),
                inference_time_ms=accounting.inference_time_ms,
                context_id=context.context_id,
                invalid_outputs=tuple(invalid_outputs),
                prompt_input=prompt_input,
            )

    async def __audit_invalid_output(
        self, context: ContextWindow, invalid_output: InvalidOutput, prompt_input: tuple[Message, ...]
    ) -> None:
        """Registra na sessão uma saída recusada pelo parser, com o motivo da recusa.

        O registro é uma etapa programática, sem consumo: o custo da chamada que a produziu já
        consta na invocação correspondente.

        Args:
            context: Janela de contexto em que a fase roda.
            invalid_output: Saída recusada e motivo.
            prompt_input: Conversa enviada ao modelo na chamada que produziu a saída recusada.
        """
        await self.session_recorder.record_programmatic_step(
            phase=self.phase,
            content=_INVALID_OUTPUT_AUDIT_TEMPLATE.format(
                phase=self.phase.value, reason=invalid_output.reason, raw_output=invalid_output.raw_output
            ),
            task_id=context.task_id,
            context_id=context.context_id,
            prompt_input=prompt_input,
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

    async def __call_model(
        self, context: ContextWindow, accounting: _PhaseAccounting, temperature: float | None
    ) -> LLMMessage:
        """Valida, autoriza, registra, chama o modelo cronometrando e contabiliza o consumo.

        A requisição é validada localmente primeiro: uma recusa anterior ao envio não é uma chamada,
        não consome orçamento e não gera invocação. Só depois da validação e da autorização a
        invocação é registrada, imediatamente antes do envio, e concluída qualquer que seja o
        desfecho: resposta, completion vazia ou erro do provedor. Assim nenhuma chamada enviada some
        da contagem, e o consumo que o provedor informou é preservado mesmo quando o conteúdo é
        inutilizável.

        Args:
            context: Janela de contexto enviada integralmente ao modelo.
            accounting: Agregação do consumo da fase, atualizada com esta chamada.
            temperature: Temperatura desta chamada: a configurada ou, numa retentativa, a de retentativa.

        Returns:
            LLMMessage: Resultado da chamada.

        Raises:
            ValueError: Quando a requisição é recusada localmente, antes de qualquer envio.
            BudgetExceededError: Quando o guardião de custo nega a chamada.
            EmptyCompletionError: Quando o provedor responde sem conteúdo utilizável.
        """
        self.llm_completions.validate_conversation(
            conversation=context.messages,
            model_name=self.model_name,
            max_tokens=self.max_tokens,
            temperature=temperature,
            provider=self.provider,
        )
        verdict = self.cost_guard.begin_call(
            phase=self.phase, reserved_output_tokens=self.max_tokens or self.settings.llm_max_tokens
        )
        if not verdict.authorized:
            raise BudgetExceededError(limit=verdict.limit, phase=self.phase, reason=verdict.reason)

        invocation_id = await self.session_recorder.start_invocation(
            phase=self.phase,
            task_id=context.task_id,
            context_id=context.context_id,
            model_name=self.model_name or self.settings.llm_model,
            provider=self.provider or self.settings.llm_provider,
            temperature=self.settings.llm_temperature if temperature is None else temperature,
        )

        started_at_ms = self.clock.monotonic_ms()
        try:
            llm_message = await self.llm_completions.send_conversation(
                conversation=context.messages,
                model_name=self.model_name,
                max_tokens=self.max_tokens,
                temperature=temperature,
                provider=self.provider,
            )
        except EmptyCompletionError as error:
            elapsed_ms = self.clock.monotonic_ms() - started_at_ms
            self.cost_guard.register_usage(
                tokens_input=error.tokens_input or _NO_TOKENS, tokens_output=error.tokens_output or _NO_TOKENS
            )
            accounting.add(tokens_input=error.tokens_input, tokens_output=error.tokens_output, elapsed_ms=elapsed_ms)
            await self.session_recorder.complete_invocation(
                invocation_id=invocation_id,
                outcome=InvocationOutcomeEnum.EMPTY_COMPLETION,
                duration_ms=elapsed_ms,
                tokens_input=error.tokens_input,
                tokens_output=error.tokens_output,
                finish_reason=error.finish_reason,
                provider_response_id=error.response_id,
            )
            raise
        except Exception:
            await self.session_recorder.complete_invocation(
                invocation_id=invocation_id,
                outcome=InvocationOutcomeEnum.PROVIDER_ERROR,
                duration_ms=self.clock.monotonic_ms() - started_at_ms,
                tokens_input=None,
                tokens_output=None,
            )
            raise
        elapsed_ms = self.clock.monotonic_ms() - started_at_ms

        tokens = llm_message.tokens
        context.append(message=llm_message.output_message)
        context.register_usage(tokens=tokens)
        self.cost_guard.register_usage(tokens_input=tokens.tokens_input, tokens_output=tokens.tokens_output)

        known_input = tokens.known_input
        known_output = tokens.known_output
        accounting.add(tokens_input=known_input, tokens_output=known_output, elapsed_ms=elapsed_ms)
        await self.session_recorder.complete_invocation(
            invocation_id=invocation_id,
            outcome=InvocationOutcomeEnum.SUCCESS,
            duration_ms=elapsed_ms,
            tokens_input=known_input,
            tokens_output=known_output,
            finish_reason=llm_message.finish_reason,
            provider_response_id=llm_message.provider_response_id,
        )
        return llm_message
