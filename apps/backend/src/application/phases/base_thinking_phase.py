import logging
from abc import ABC
from asyncio import CancelledError
from dataclasses import dataclass, field

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.entities.thinking.parsed_output import ParsedOutput
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.output_defect_enum import OutputDefectEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
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

# Correção pedida ao modelo, por defeito da saída recusada. Nenhuma repete o template da fase: ele
# já está na janela, e instruções e aprendizados não mudam dentro de uma mesma execução.
_CORRECTION_BY_DEFECT: dict[OutputDefectEnum, str] = {
    OutputDefectEnum.SYNTAX: (
        "## JSON syntax correction\n\n"
        "The previous output is not valid JSON: {reason}\n"
        "Do not redo the resolution and do not change the content: return the same content as the previous "
        "output, serialized as a single valid JSON object in the format already requested, with no text "
        "before or after it and no code fence."
    ),
    OutputDefectEnum.CONTRACT: (
        "## Phase contract correction\n\n"
        "The previous output is readable JSON, but it does not fulfill the contract of this stage: {reason}\n"
        "Check your own output — in a verification report, your report — against the instructions "
        "and fix whatever is inconsistent: every decision must be yours and consistent with your "
        "evaluations, and nothing will be adjusted automatically. Preserve all unaffected content. "
        "Do not remove necessary tasks or steps merely to satisfy the parser. "
        "Return the complete corrected output, "
        "as a single valid JSON object, with no text before or after it and no code fence."
    ),
    OutputDefectEnum.TRUNCATED: (
        "## Length interruption recovery\n\n"
        "The previous output was cut off by the length limit and is incomplete: {reason}\n"
        "Do not continue the previous output: it was discarded as a phase result and will not be joined "
        "to the next one. "
        "Produce a new, complete and more concise output that fits within the limit, as a single valid "
        "JSON object in the format already requested, with no text before or after it and no code fence."
    ),
}
_PLANNING_PHASES = frozenset({ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING})
_PLANNING_RECOVERY_INSTRUCTIONS = (
    "\n\n### Planning coverage\n\n"
    "The complete corrected plan must still cover the requested determination, including the final steps "
    "needed to obtain it. In additional planning, cover the remaining gaps using the supplied approved results. "
    "A missing title does not authorize dropping other necessary tasks. Preserve unaffected content; "
    "change the batch, task IDs or content when the reported defect requires it, such as a task limit "
    "or duplicate IDs, while preserving the necessary coverage."
)
_INVALID_OUTPUT_AUDIT_TEMPLATE = (
    "Saída inválida descartada na fase {phase} ({defect}): {reason}\n"
    "Diagnóstico: invocação {invocation_id}; problema {code}; sintaxe {syntax}; contrato {contract}; "
    "término {finish_reason}; interrupção por comprimento {length}.\n\n"
    "Saída bruta do modelo:\n\n{raw_output}"
)
_UNKNOWN_VALUE = "desconhecido"
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


@dataclass
class _RecoveryChain:
    """Saídas recusadas da execução corrente da fase, à espera do resultado da recuperação.

    A primeira recusa é a invocação original: toda chamada seguinte da mesma execução a aponta.
    Cada recusa guarda a estratégia aplicada a ela — correção, quando ainda havia retentativa, ou
    nenhuma, quando a recusa esgotou as retentativas.
    """

    rejected: list[tuple[str, RecoveryStrategyEnum]] = field(default_factory=list)

    @property
    def origin_invocation_id(self) -> str | None:
        """Invocação original da cadeia, ou `None` quando nenhuma saída foi recusada."""
        if not self.rejected:
            return None
        return self.rejected[0][0]


@dataclass(frozen=True)
class _AcceptedCall:
    """Chamada cuja saída o parser aceitou, com o que a fase precisa para montar o resultado."""

    llm_message: LLMMessage
    invocation_id: str
    parsed_output: ParsedOutput
    prompt_input: tuple[Message, ...]


class BaseThinkingPhase(IThinkingPhase, ABC):
    """Template Method comum às etapas do fluxo de thinking.

    O esqueleto "montar prompt → chamar LLM → registrar custo → parsear JSON" é
    idêntico para todas as fases; as subclasses variam apenas o template e o
    schema esperado.

    Cada execução roda numa janela nova, da própria fase: é a regra de isolamento de contexto
    do fluxo. A janela só é reaproveitada pelas correções de saída dessa mesma execução.
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
            max_tokens: Limite de tokens da sessão; nenhuma chamada da fase pede mais que ele.
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

        A janela tem de ser nova e da própria fase: uma tarefa diferente ou uma mudança de fase
        nunca herda a conversa de outra execução. O prompt entra na janela, o modelo responde, o
        custo é contabilizado e a saída é parseada. Duas falhas são retentáveis até o limite
        configurado, porque ambas são não determinísticas: o modelo devolver algo que não é o JSON
        da fase (ou um JSON que contradiz o contexto de validação), caso em que a janela recebe uma
        mensagem de correção, e o provedor devolver uma resposta sem conteúdo nenhum, caso em
        que não há o que corrigir, só o que repetir. Cada retentativa é uma nova invocação,
        autorizada e registrada como as demais: o custo de uma chamada não se perde por ela ter
        sido recusada, e uma recusa do parser não consome tentativas de resolução da tarefa.

        A correção reaproveita a janela da execução: as respostas recusadas e as mensagens de
        correção permanecem integralmente, e o template não é acrescentado de novo, porque instruções e
        aprendizados não mudam dentro de uma execução. A mensagem de correção depende do defeito
        (`OutputDefectEnum`): um erro de sintaxe pede o mesmo conteúdo em JSON válido, sem nova
        resolução; uma violação de contrato pede ao modelo que confira e corrija a própria saída;
        uma interrupção por comprimento pede uma nova saída completa e concisa, nunca a continuação
        da anterior — a saída aceita é sempre uma única resposta do modelo, sem emendas.
        A recuperação de A.2/C.2 orienta preservar a cobertura da determinação solicitada, inclusive
        seus passos finais; isso é instrução ao modelo, não uma validação semântica programática.

        Cada saída recusada pelo parser fica registrada na sessão no momento da recusa, inclusive a
        última, que encerra a fase com erro: a auditoria independe de a fase terminar bem.

        Cada saída avaliada pelo parser recebe um diagnóstico na invocação que a produziu, aceita ou
        não. Uma recusa abre a recuperação: as chamadas seguintes da execução apontam a invocação
        original, e cada recusa termina marcada como recuperada (pela invocação cuja saída foi aceita)
        ou como falha, qualquer que seja o erro que encerre a execução. Esse registro é operacional:
        não muda as retentativas, o orçamento nem o que o fluxo faz com a saída.

        Um cancelamento controlado também encerra as recuperações pendentes como falha antes de
        ser propagado; não é convertido em resposta, erro de parsing ou nova tentativa.

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
            ValueError: Quando a janela não é nova ou pertence a outra fase, antes de qualquer chamada.
            BudgetExceededError: Quando o guardião de custo nega a chamada.
            PhaseParsingError: Quando o limite de retentativas de parsing se esgota.
            EmptyCompletionError: Quando o provedor insiste em responder sem conteúdo.
        """
        self.__ensure_fresh_window(context=context)
        context.append(
            message=Message(
                creation_timestamp=self.clock.now(),
                text=self.template_provider.render(phase=self.phase, variables=variables),
                source=MessageSourceEnum.USER,
            )
        )

        accounting = _PhaseAccounting()
        invalid_outputs: list[InvalidOutput] = []
        chain = _RecoveryChain()
        try:
            accepted = await self.__run_until_accepted(
                context=context,
                validation=validation,
                temperature=_RETRY_TEMPERATURE if is_retry else self.temperature,
                accounting=accounting,
                invalid_outputs=invalid_outputs,
                chain=chain,
            )
        except (Exception, CancelledError):
            await self.__close_failed_recovery(chain=chain)
            raise
        await self.__close_recovery(
            chain=chain, result=RecoveryResultEnum.RECOVERED, resolved_by_invocation_id=accepted.invocation_id
        )

        return PhaseOutcome(
            raw_output=accepted.llm_message.output_message.text,
            parsed=accepted.parsed_output.parsed,
            tokens=TokensUsage(
                tokens_input=accounting.tokens_input,
                tokens_output=accounting.tokens_output,
                llm_model=accepted.llm_message.tokens.llm_model,
                input_known=accounting.input_known,
                output_known=accounting.output_known,
            ),
            inference_time_ms=accounting.inference_time_ms,
            context_id=context.context_id,
            invalid_outputs=tuple(invalid_outputs),
            prompt_input=accepted.prompt_input,
        )

    async def __run_until_accepted(
        self,
        context: ContextWindow,
        validation: ValidationContext | None,
        temperature: float | None,
        accounting: _PhaseAccounting,
        invalid_outputs: list[InvalidOutput],
        chain: _RecoveryChain,
    ) -> _AcceptedCall:
        """Chama o modelo até o parser aceitar a saída ou as retentativas se esgotarem.

        Cada saída avaliada ganha um diagnóstico na invocação que a produziu; cada saída recusada
        entra na cadeia de recuperação, e as chamadas seguintes apontam a invocação original.

        Args:
            context: Janela de contexto em que a fase é executada.
            validation: Dados esperados pela chamada, repassados ao parser.
            temperature: Temperatura da primeira chamada; as retentativas usam a de retentativa.
            accounting: Agregação do consumo da fase.
            invalid_outputs: Saídas recusadas da execução, acrescentadas à medida que surgem.
            chain: Cadeia de recuperação da execução.

        Returns:
            _AcceptedCall: Chamada cuja saída foi aceita.

        Raises:
            BudgetExceededError: Quando o guardião de custo nega a chamada.
            PhaseParsingError: Quando o limite de retentativas de parsing se esgota.
            EmptyCompletionError: Quando o provedor insiste em responder sem conteúdo.
        """
        retries_left = self.settings.ralph_json_parse_max_retries

        while True:
            # A janela é a conversa enviada nesta chamada; a resposta só entra nela depois do envio.
            prompt_input = tuple(context.messages)
            try:
                llm_message, invocation_id = await self.__call_model(
                    context=context,
                    accounting=accounting,
                    temperature=temperature,
                    recovers_invocation_id=chain.origin_invocation_id,
                )
            except EmptyCompletionError as error:
                # Sem conteúdo não há mensagem a acrescentar à janela: a única correção possível
                # é pedir de novo, com o mesmo contexto. O custo da chamada já foi registrado.
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                temperature = _RETRY_TEMPERATURE
                continue

            raw_output = llm_message.output_message.text

            try:
                parsed_output = self.parser.parse_output(
                    raw_output=raw_output,
                    phase=self.phase,
                    validation=validation,
                    finish_reason=llm_message.finish_reason,
                )
            except PhaseParsingError as error:
                # Um parser que não classifica a recusa não autoriza presumir nada sobre ela.
                diagnostic = error.diagnostic or OutputDiagnostic.unclassified(
                    reason=error.reason, finish_reason=llm_message.finish_reason
                )
                await self.session_recorder.record_output_diagnostic(
                    invocation_id=invocation_id, diagnostic=diagnostic
                )
                invalid_output = InvalidOutput(
                    raw_output=raw_output, reason=error.reason, defect=error.defect,
                    invocation_id=invocation_id, diagnostic=diagnostic
                )
                invalid_outputs.append(invalid_output)
                # A auditoria não pode depender de a fase terminar bem: é justamente quando as correções
                # se esgotam que o intercâmbio com o modelo precisa ter ficado na sessão.
                await self.__audit_invalid_output(
                    context=context, invalid_output=invalid_output, prompt_input=prompt_input
                )
                await self.__open_recovery(
                    chain=chain, invocation_id=invocation_id, has_retry=retries_left > _NO_RETRIES_LEFT
                )
                retries_left = self.__consume_retry(retries_left=retries_left, error=error)
                context.append(
                    message=Message(
                        creation_timestamp=self.clock.now(),
                        text=self.__correction_message(error=error),
                        source=MessageSourceEnum.USER,
                    )
                )
                temperature = _RETRY_TEMPERATURE
                continue

            await self.session_recorder.record_output_diagnostic(
                invocation_id=invocation_id, diagnostic=parsed_output.diagnostic
            )
            return _AcceptedCall(
                llm_message=llm_message,
                invocation_id=invocation_id,
                parsed_output=parsed_output,
                prompt_input=prompt_input,
            )

    def __ensure_fresh_window(self, context: ContextWindow) -> None:
        """Exige uma janela nova, criada para esta fase.

        Reaproveitar a janela de outra fase ou de outra execução faria o modelo herdar uma conversa
        que não é dele; as entradas de que a fase precisa chegam explicitamente pelas variáveis.

        Args:
            context: Janela de contexto recebida pela execução.

        Raises:
            ValueError: Quando a janela pertence a outra fase ou já recebeu mensagens.
        """
        if context.phase is not self.phase:
            raise ValueError(
                f"A fase '{self.phase.value}' não pode rodar na janela da fase '{context.phase.value}': "
                "toda mudança de fase exige uma janela nova."
            )
        if not context.is_empty():
            raise ValueError(
                f"A fase '{self.phase.value}' exige uma janela nova; a janela '{context.context_id}' já foi usada."
            )

    async def __open_recovery(self, chain: _RecoveryChain, invocation_id: str, has_retry: bool) -> None:
        """Acrescenta uma saída recusada à cadeia, com a estratégia que será aplicada a ela.

        Com retentativa disponível, a correção é pedida e a recuperação fica pendente até a execução
        terminar; sem retentativa, não há estratégia e o resultado será registrado como falha.

        Args:
            chain: Cadeia de recuperação da execução.
            invocation_id: Invocação que produziu a saída recusada.
            has_retry: Indica se ainda há retentativa de saída inválida na execução.
        """
        if not has_retry:
            chain.rejected.append((invocation_id, RecoveryStrategyEnum.NONE))
            return

        chain.rejected.append((invocation_id, RecoveryStrategyEnum.CORRECTION_PROMPT))
        await self.session_recorder.record_output_recovery(
            invocation_id=invocation_id,
            recovery=OutputRecovery(
                strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.PENDING
            ),
        )

    async def __close_recovery(
        self,
        chain: _RecoveryChain,
        result: RecoveryResultEnum,
        resolved_by_invocation_id: str | None = None,
    ) -> None:
        """Registra o resultado final da recuperação em cada saída recusada da execução.

        Args:
            chain: Cadeia de recuperação da execução.
            result: Resultado final: recuperada ou falha.
            resolved_by_invocation_id: Invocação cuja saída foi aceita, quando houve recuperação.
        """
        for invocation_id, strategy in chain.rejected:
            await self.session_recorder.record_output_recovery(
                invocation_id=invocation_id,
                recovery=OutputRecovery(
                    strategy=strategy, result=result, resolved_by_invocation_id=resolved_by_invocation_id
                ),
            )

    async def __close_failed_recovery(self, chain: _RecoveryChain) -> None:
        """Registra a falha da recuperação sem encobrir o erro que encerrou a execução.

        Args:
            chain: Cadeia de recuperação da execução.
        """
        try:
            await self.__close_recovery(chain=chain, result=RecoveryResultEnum.FAILED)
        except Exception:
            self.logger.exception(
                "Fase '%s' não conseguiu registrar a falha da recuperação de saída inválida", self.phase.value
            )

    async def __audit_invalid_output(
        self, context: ContextWindow, invalid_output: InvalidOutput, prompt_input: tuple[Message, ...]
    ) -> None:
        """Registra na sessão uma saída recusada pelo parser, com o motivo e o diagnóstico da recusa.

        O registro é uma etapa programática, sem consumo, ligada à invocação que produziu a saída: o
        custo da chamada já consta nessa invocação, que também guarda o diagnóstico estruturado.

        Args:
            context: Janela de contexto em que a fase roda.
            invalid_output: Saída recusada e motivo.
            prompt_input: Conversa enviada ao modelo na chamada que produziu a saída recusada.
        """
        await self.session_recorder.record_programmatic_step(
            phase=self.phase,
            content=self.__render_audit(invalid_output=invalid_output),
            task_id=context.task_id,
            context_id=context.context_id,
            prompt_input=prompt_input,
            invocation_id=invalid_output.invocation_id,
        )

    def __render_audit(self, invalid_output: InvalidOutput) -> str:
        """Monta o texto da auditoria: motivo legível, diagnóstico estruturado e saída bruta.

        Args:
            invalid_output: Saída recusada, com a invocação de origem e o diagnóstico.

        Returns:
            str: Texto da etapa programática de auditoria.
        """
        diagnostic = invalid_output.diagnostic
        return _INVALID_OUTPUT_AUDIT_TEMPLATE.format(
            phase=self.phase.value,
            defect=invalid_output.defect.label,
            reason=invalid_output.reason,
            invocation_id=invalid_output.invocation_id,
            code=diagnostic.problem.code.value,
            syntax=diagnostic.syntax_status.value if diagnostic.syntax_status is not None else _UNKNOWN_VALUE,
            contract=diagnostic.contract_status.value,
            finish_reason=diagnostic.finish_reason or _UNKNOWN_VALUE,
            length=diagnostic.length_interruption.value,
            raw_output=invalid_output.raw_output,
        )

    def __correction_message(self, error: PhaseParsingError) -> str:
        """Pede correção pelo defeito, com orientação de cobertura nas fases de planejamento.

        O conteúdo recusado já está integralmente na janela. A orientação não congela o lote:
        corrigir um teto ou identificadores duplicados pode exigir alterar tarefas.

        Args:
            error: Recusa do parser com o defeito e o motivo específico.

        Returns:
            str: Instruções em inglês e Markdown, sem repetir o template da fase.
        """
        correction = _CORRECTION_BY_DEFECT[error.defect].format(reason=error.reason)
        if self.phase in _PLANNING_PHASES:
            return correction + _PLANNING_RECOVERY_INSTRUCTIONS
        return correction

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
        self,
        context: ContextWindow,
        accounting: _PhaseAccounting,
        temperature: float | None,
        recovers_invocation_id: str | None,
    ) -> tuple[LLMMessage, str]:
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
            recovers_invocation_id: Invocação original cuja saída recusada esta chamada tenta recuperar.

        Returns:
            tuple[LLMMessage, str]: Resultado da chamada e identificador da invocação registrada.

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
        call_max_tokens = self.__call_max_tokens()
        verdict = self.cost_guard.begin_call(phase=self.phase, reserved_output_tokens=call_max_tokens)
        if not verdict.authorized:
            raise BudgetExceededError(limit=verdict.limit, phase=self.phase, reason=verdict.reason)

        invocation_id = await self.session_recorder.start_invocation(
            phase=self.phase,
            task_id=context.task_id,
            context_id=context.context_id,
            model_name=self.model_name or self.settings.llm_model,
            provider=self.provider or self.settings.llm_provider,
            temperature=self.settings.llm_temperature if temperature is None else temperature,
            recovers_invocation_id=recovers_invocation_id,
        )

        started_at_ms = self.clock.monotonic_ms()
        try:
            llm_message = await self.llm_completions.send_conversation(
                conversation=context.messages,
                model_name=self.model_name,
                max_tokens=call_max_tokens,
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
        return llm_message, invocation_id

    def __call_max_tokens(self) -> int:
        """Teto de saída da próxima chamada: o saldo de tokens da sessão, nunca acima do limite pedido.

        O limite de tokens vale para a sessão inteira; cada chamada pede só o que ainda resta dele
        para a fase (C.3 enxerga a reserva da resposta final). Com o saldo zerado o teto é zero, e o
        guardião de custo nega a chamada.

        Returns:
            int: Tokens de saída que a chamada pode pedir ao modelo.
        """
        session_limit = self.max_tokens or self.settings.llm_max_tokens
        return min(session_limit, self.cost_guard.available_output_tokens(phase=self.phase))
