import logging
from typing import Any, AsyncGenerator, Sequence

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.message import Message
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.global_approval import GlobalApproval
from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.entities.thinking.learning import Learning
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.errors.ralph_error import RalphError
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.context_window_factory_interface import IContextWindowFactory
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.learnings_memory_interface import ILearningsMemory
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.domain.interfaces.settings_interface import ISettings
from src.domain.interfaces.task_queue_interface import ITaskQueue
from src.domain.interfaces.thinking_phase_interface import IThinkingPhase

_RALPH_FLOW = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_SETUP_TASK_LABEL = "setup"
_SYNTHESIS_TASK_LABEL = "synthesis"
_NO_INFERENCE_TIME_MS = 0
_FIRST_TASK_NUMBER = 1
_FIRST_ATTEMPT = 1

_CRITERIA_HEADING = "## Critérios de aceite gerais"
_TASKS_HEADING = "## Tarefas planejadas"
_LEARNINGS_HEADING = "## Aprendizados extraídos"
_NO_LEARNINGS_CONTENT = "Nenhum aprendizado foi extraído desta tarefa."
_NO_PLANNING_LEARNINGS_CONTENT = "Nenhum aprendizado foi extraído do enunciado."
_RESET_CONTENT = "Contexto reinicializado para a tarefa `{task_id}`. Nova janela: `{context_id}`."
_TASK_CONTENT = (
    "### {task_id} — {title}\n\n{description}\n\n"
    "**Critérios de aceite:**\n{criteria}"
)
_STORE_CONTENT = "Resultado da tarefa `{task_id}` armazenado."
_REPORT_CONTENT = "**Decisão:** `{decision}`\n\n{evaluations}"
_EVALUATION_ITEM = "- `{criterion_id}` — {status}: {justification}"
_MET_LABEL = "atendido"
_UNMET_LABEL = "não atendido"
_VALIDATOR_REPORT_CONTENT = "## Veredito do validador (tentativa {attempt})\n\n{report}"
_INVALID_VERIFIER_OUTPUT_CONTENT = (
    "O validador devolveu uma saída inválida e foi instruído a corrigi-la.\n\n"
    "**Saída inválida:**\n\n{raw_output}\n\n**Motivo da recusa:** {reason}"
)
_RETRY_INSTRUCTION_CONTENT = (
    "A tentativa anterior foi reprovada. Critérios não satisfeitos: {unmet}.\n\n"
    "Refaça a resolução da tarefa corrigindo exatamente esses pontos."
)
_RESULT_BLOCK = "## {task_id} — {title}\n\n{content}"
_ERROR_CONTENT = "**Erro:** {reason}"
_CONSUMPTION_DETAIL = "Consumo conhecido: {tokens} tokens em {calls} chamadas ao modelo."
_DISCARDED_DETAIL = "Tarefas descartadas: {tasks}."
_PENDING_CRITERIA_DETAIL = "Critérios gerais pendentes: {criteria}."
_ATTEMPTS_DETAIL = (
    "A tarefa `{task_id}` foi reprovada nas {attempts} tentativas permitidas; nenhum resultado foi "
    "armazenado e a execução foi encerrada sem resposta final."
)
_PLANNING_DETAIL = "{reason} Critérios gerais ainda não atendidos: {criteria}."
_ITEM_SEPARATOR = "\n"
_BLOCK_SEPARATOR = "\n\n"
_SENTENCE_SEPARATOR = " "
_LIST_SEPARATOR = ", "
_CRITERION_ITEM = "- `{criterion_id}`: {description}"


class RalphThinkingUseCase:
    """Orquestra o fluxo completo do Ralph Loop adaptado.

    Executa Planejamento → Execução em Loop → Criação da Resposta Final,
    conforme o pseudocódigo canônico do orquestrador descrito no paper.

    A única saída com resposta é a síntese (C.3) depois de uma aprovação global (C.1)
    sobre resultados aprovados individualmente (B.2/B.3). Quando um limite operacional
    impede o fluxo de continuar sem violar essas condições, a sessão termina sem conclusão
    (`failed`, sem resposta final, com o motivo estruturado). O paper não define limites de
    recursos nem esse encerramento: ele é um tratamento operacional adicional.
    """

    def __init__(
        self,
        general_criteria_phase: IThinkingPhase,
        task_decomposition_phase: IThinkingPhase,
        planning_learnings_phase: IThinkingPhase,
        task_resolution_phase: IThinkingPhase,
        task_verification_phase: IThinkingPhase,
        learnings_extraction_phase: IThinkingPhase,
        global_verification_phase: IThinkingPhase,
        additional_planning_phase: IThinkingPhase,
        final_answer_phase: IThinkingPhase,
        task_queue: ITaskQueue,
        learnings_memory: ILearningsMemory,
        context_window_factory: IContextWindowFactory,
        cost_guard: ICostGuard,
        session_recorder: ISessionRecorder,
        clock: IClock,
        settings: ISettings,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso.

        Args:
            general_criteria_phase: Fase A.1.
            task_decomposition_phase: Fase A.2.
            planning_learnings_phase: Fase A.3.
            task_resolution_phase: Fase B.1.
            task_verification_phase: Fase B.2.
            learnings_extraction_phase: Fase B.4.
            global_verification_phase: Fase C.1.
            additional_planning_phase: Fase C.2.
            final_answer_phase: Fase C.3.
            task_queue: Fila de tarefas do loop de execução.
            learnings_memory: Armazenamento dos aprendizados pontuais.
            context_window_factory: Fábrica de janelas de contexto novas.
            cost_guard: Ponto único de decisão sobre limites de custo.
            session_recorder: Rastreador e persistidor do histórico da sessão.
            clock: Fonte de tempo do domínio.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.general_criteria_phase: IThinkingPhase = general_criteria_phase
        self.task_decomposition_phase: IThinkingPhase = task_decomposition_phase
        self.planning_learnings_phase: IThinkingPhase = planning_learnings_phase
        self.task_resolution_phase: IThinkingPhase = task_resolution_phase
        self.task_verification_phase: IThinkingPhase = task_verification_phase
        self.learnings_extraction_phase: IThinkingPhase = learnings_extraction_phase
        self.global_verification_phase: IThinkingPhase = global_verification_phase
        self.additional_planning_phase: IThinkingPhase = additional_planning_phase
        self.final_answer_phase: IThinkingPhase = final_answer_phase
        self.task_queue: ITaskQueue = task_queue
        self.learnings_memory: ILearningsMemory = learnings_memory
        self.context_window_factory: IContextWindowFactory = context_window_factory
        self.cost_guard: ICostGuard = cost_guard
        self.session_recorder: ISessionRecorder = session_recorder
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger
        self.__user_question: str = ""
        self.__max_tokens: int = 0
        self.__general_criteria: tuple[AcceptanceCriterion, ...] = ()
        self.__results: dict[str, TaskResult] = {}
        self.__active_task_id: str | None = None
        self.__pending_criteria_ids: tuple[str, ...] = ()
        self.__context: ContextWindow = ContextWindow(context_id="", phase=_RALPH_FLOW)
        self.__running_phase: ThinkingPhaseEnum = _RALPH_FLOW

    async def execute(self, input_dto: RalphThinkingInputDTO) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o fluxo completo de thinking, emitindo um evento por etapa.

        Args:
            input_dto: Pergunta do usuário e parâmetros do modelo.

        Yields:
            ThinkingEvent: Evento correspondente a cada etapa do fluxo.

        Raises:
            Exception: Toda falha ou interrupção depois da criação da sessão, inclusive na gravação
                da pergunta do usuário, é registrada, emitida como um único evento `error`, encerra a
                sessão como `failed` e é repropagada ao chamador.
        """
        self.__user_question = input_dto.user_input
        self.__max_tokens = input_dto.max_tokens
        await self.session_recorder.start(
            user_question=input_dto.user_input,
            flow=_RALPH_FLOW,
            model_name=input_dto.model_name,
            max_tokens=input_dto.max_tokens,
            temperature=input_dto.temperature,
            provider=input_dto.provider,
        )

        try:
            await self.session_recorder.record_user_input(content=input_dto.user_input)
            self.__configure_phases(input_dto=input_dto)
            async for event in self.__run_planning():
                yield event
            async for event in self.__run_synthesis():
                yield event
        except Exception as error:
            async for event in self.__fail(error=error):
                yield event
            raise

    async def __run_planning(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa A.1, A.2 e A.3, produzindo os critérios gerais, a fila inicial e as anotações do enunciado.

        O plano inicial é validado contra o espaço de tarefas da sessão antes de tocar a
        fila: um lote acima do teto é devolvido ao planejador para correção, e nunca truncado.

        Yields:
            ThinkingEvent: Eventos `setup` (A.1), `tasks` (A.2) e `learn` (A.3).
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA)
        outcome = await self.__execute_phase(
            runner=self.general_criteria_phase, context=context, variables={"user_question": self.__user_question}
        )
        self.__general_criteria = self.__to_criteria(parsed=outcome.parsed)
        content = f"{_CRITERIA_HEADING}\n\n{self.__render_criteria(criteria=self.__general_criteria)}"
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.SETUP,
            phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
            task=_SETUP_TASK_LABEL,
            content=content,
            context=context,
            outcome=outcome,
            task_id=None,
        )

        context = self.__new_context(phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION)
        outcome = await self.__execute_phase(
            runner=self.task_decomposition_phase,
            context=context,
            variables={"user_question": self.__user_question, **self.__planning_limits()},
            validation=self.__planning_validation(),
        )
        tasks = self.__to_tasks(parsed=outcome.parsed, origin_phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION)
        self.task_queue.push_back(tasks=tasks)
        self.cost_guard.register_task_created(quantity=len(tasks))
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.TASKS,
            phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
            task=_SETUP_TASK_LABEL,
            content=f"{_TASKS_HEADING}\n\n{self.__render_tasks(tasks=tasks)}",
            context=context,
            outcome=outcome,
            task_id=None,
        )

        async for event in self.__extract_planning_learnings():
            yield event

    async def __extract_planning_learnings(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Extrai os aprendizados pontuais do enunciado (A.3).

        São as anotações dos pontos que chamam a atenção na pergunta — valores com unidades,
        alternativas, fórmulas, condições. A fase enxerga só o enunciado, numa janela própria, e o
        que ela extrai entra na memória antes de qualquer tarefa: assim as alternativas e os dados
        fornecidos chegam ao contexto novo de todas as tarefas, mesmo àquelas cuja descrição não os
        repetiu. Como os demais aprendizados, chegam à área "Aprendizados Pontuais" de todo prompt das
        fases B e C.

        Yields:
            ThinkingEvent: Evento `learn`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS)
        outcome = await self.__execute_phase(
            runner=self.planning_learnings_phase, context=context, variables={"user_question": self.__user_question}
        )
        learnings = self.__to_learnings(parsed=outcome.parsed, task_id=None)
        self.learnings_memory.append(learnings=learnings)
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.LEARN,
            phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS,
            task=_SETUP_TASK_LABEL,
            content=self.__render_learnings(learnings=learnings, empty_content=_NO_PLANNING_LEARNINGS_CONTENT),
            context=context,
            outcome=outcome,
            task_id=None,
        )

    async def __run_loop(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o loop de execução até a fila de tarefas se esvaziar.

        Yields:
            ThinkingEvent: Eventos de cada tarefa executada.

        Raises:
            ExecutionInterruptedError: Quando um limite impede de iniciar a próxima tarefa.
        """
        while not self.task_queue.is_empty():
            self.__ensure_next_task_can_start()
            async for event in self.__run_task(task=self.task_queue.pop_next()):
                yield event

    async def __run_task(self, task: Task) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa uma tarefa completa: B.1, B.2, B.3 e B.4.

        Args:
            task: Tarefa retirada da fila, já em andamento.

        Yields:
            ThinkingEvent: Eventos `reset`, `execute`, `reasoning`, `verify_*`,
            `store` e `learn` daquela tarefa.
        """
        self.__active_task_id = task.id
        context = self.__new_context(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, task_id=task.id)
        reset_content = _RESET_CONTENT.format(task_id=task.id, context_id=context.context_id)
        await self.session_recorder.record_programmatic_step(
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
            content=reset_content,
            task_id=task.id,
            context_id=context.context_id,
        )
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.THINKING,
            subtype=ThinkingEventSubtypeEnum.RESET,
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
            task=task.id,
            content=reset_content,
            context=context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

        # A janela nova não recebe um bloco avulso de aprendizados: eles chegam pela área
        # "Aprendizados Pontuais" do próprio template de B.1, como em todo prompt das fases B e C.
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.THINKING,
            subtype=ThinkingEventSubtypeEnum.EXECUTE,
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
            task=task.id,
            content=self.__render_task(task=task),
            context=context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

        async for event in self.__resolve_task(task=task, context=context):
            yield event
        async for event in self.__store_result(task=task, context=context):
            yield event
        async for event in self.__extract_learnings(task=task, context=context):
            yield event
        self.__active_task_id = None

    async def __resolve_task(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o ciclo de tentativas de B.1 e B.2 para uma tarefa.

        A janela da tarefa é a mesma em toda retentativa: a tentativa reprovada e o veredito do
        validador permanecem no contexto e guiam a correção. Cada veredito é anexado a essa
        janela assim que existe, antes de qualquer decisão — inclusive o da aprovação e o da
        última reprovação —, porque B.4 recebe o contexto completo da tarefa. A janela do
        validador continua isolada: só o seu relatório volta para cá.

        Toda tentativa depois de uma reprovação é uma retentativa: B.1 é chamada com a temperatura de
        retentativa, e a verificação dessa tentativa volta à temperatura do usuário.

        A função só retorna quando a última tentativa foi aprovada. Se as tentativas se esgotam,
        a tarefa não é aprovada, nada é armazenado e a execução é interrompida.

        Args:
            task: Tarefa em execução.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Eventos `reasoning` e `verify_pass`/`verify_fail`.

        Raises:
            ExecutionInterruptedError: Quando as tentativas se esgotam sem aprovação.
        """
        while True:
            attempt = self.cost_guard.register_task_attempt(task_id=task.id)
            outcome = await self.__execute_phase(
                runner=self.task_resolution_phase,
                context=context,
                variables=self.__resolution_variables(task=task),
                is_retry=attempt > _FIRST_ATTEMPT,
            )
            preliminary = outcome.parsed["result"]
            yield await self.__record_and_build(
                subtype=ThinkingEventSubtypeEnum.REASONING,
                phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
                task=task.id,
                content=preliminary,
                context=context,
                outcome=outcome,
                task_id=task.id,
            )

            verification_context = self.context_window_factory.create(
                phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION, task_id=task.id
            )
            outcome = await self.__execute_phase(
                runner=self.task_verification_phase,
                context=verification_context,
                variables=self.__verification_variables(task=task, preliminary=preliminary),
                validation=ValidationContext(
                    expected_criteria_ids=tuple(criterion.id for criterion in task.acceptance_criteria)
                ),
            )
            report = self.__to_report(parsed=outcome.parsed)
            task.attempts.append(TaskAttempt(number=attempt, output=preliminary, report=report))
            self.__record_verification_in_task_context(
                context=context, attempt=attempt, report=report, invalid_outputs=outcome.invalid_outputs
            )
            yield await self.__record_and_build(
                subtype=(
                    ThinkingEventSubtypeEnum.VERIFY_PASS if report.approved else ThinkingEventSubtypeEnum.VERIFY_FAIL
                ),
                phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                task=task.id,
                content=self.__render_report(report=report),
                context=verification_context,
                outcome=outcome,
                task_id=task.id,
            )

            if report.approved:
                task.status = TaskStatusEnum.APPROVED
                return

            if not self.cost_guard.can_retry_task(task_id=task.id):
                task.status = TaskStatusEnum.FAILED
                raise ExecutionInterruptedError(
                    limit=BudgetLimitEnum.TASK_ATTEMPTS,
                    phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                    detail=_ATTEMPTS_DETAIL.format(task_id=task.id, attempts=attempt),
                    task_id=task.id,
                )

            context.append(
                message=Message(
                    creation_timestamp=self.clock.now(),
                    text=_RETRY_INSTRUCTION_CONTENT.format(unmet=self.__render_ids(ids=report.unmet_criteria_ids)),
                    source=MessageSourceEnum.USER,
                )
            )

    def __record_verification_in_task_context(
        self,
        context: ContextWindow,
        attempt: int,
        report: VerificationReport,
        invalid_outputs: Sequence[InvalidOutput],
    ) -> None:
        """Acrescenta ao histórico da tarefa a interação com o validador.

        Primeiro as saídas inválidas que o validador teve de corrigir, claramente identificadas
        como tais; depois o relatório validado, o único com efeito de controle.

        Args:
            context: Janela de contexto da tarefa.
            attempt: Número da tentativa verificada.
            report: Relatório validado da verificação.
            invalid_outputs: Saídas recusadas pelo parser e corrigidas pelo validador.
        """
        for invalid_output in invalid_outputs:
            context.append(
                message=Message(
                    creation_timestamp=self.clock.now(),
                    text=_INVALID_VERIFIER_OUTPUT_CONTENT.format(
                        raw_output=invalid_output.raw_output, reason=invalid_output.reason
                    ),
                    source=MessageSourceEnum.USER,
                )
            )
        context.append(
            message=Message(
                creation_timestamp=self.clock.now(),
                text=_VALIDATOR_REPORT_CONTENT.format(attempt=attempt, report=self.__render_report(report=report)),
                source=MessageSourceEnum.USER,
            )
        )

    async def __store_result(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Armazena o resultado aprovado de uma tarefa (B.3), sem chamar o modelo.

        Só uma tarefa aprovada, cuja última tentativa tem relatório aprovado, tem resultado a
        armazenar; a própria tarefa garante isso ao entregá-lo.

        Args:
            task: Tarefa recém-aprovada.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Evento `store`, sempre com tempo de inferência zero.
        """
        self.__running_phase = ThinkingPhaseEnum.B3_RESULT_STORAGE
        self.__results[task.id] = task.approved_result()
        content = _STORE_CONTENT.format(task_id=task.id)
        await self.session_recorder.record_programmatic_step(
            phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
            content=content,
            task_id=task.id,
            context_id=context.context_id,
        )
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.THINKING,
            subtype=ThinkingEventSubtypeEnum.STORE,
            phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
            task=task.id,
            content=content,
            context=context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

    async def __extract_learnings(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Extrai os aprendizados pontuais de uma tarefa (B.4).

        Usa a janela completa da tarefa, que contém todas as tentativas e todos os vereditos do
        validador — é lá que fatos úteis podem ter emergido. O template recebe os aprendizados já
        registrados, para que a extração não os repita.

        Args:
            task: Tarefa recém-concluída.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Evento `learn`.
        """
        outcome = await self.__execute_phase(
            runner=self.learnings_extraction_phase, context=context, variables=self.__learnings_variables()
        )
        learnings = self.__to_learnings(parsed=outcome.parsed, task_id=task.id)
        self.learnings_memory.append(learnings=learnings)
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.LEARN,
            phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION,
            task=task.id,
            content=self.__render_learnings(learnings=learnings),
            context=context,
            outcome=outcome,
            task_id=task.id,
        )

    async def __run_synthesis(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o loop de tarefas, C.1, C.2 (quando necessário) e C.3.

        C.3 só é alcançada com uma aprovação global em mãos. Enquanto C.1 reprova, o fluxo
        volta ao loop pela C.2; se C.2 não puder rodar, a execução é interrompida.

        Yields:
            ThinkingEvent: Eventos do loop, `compile` (C.1), `replan` (C.2),
            `compile` (C.3) e, por último, o evento `result`.

        Raises:
            ExecutionInterruptedError: Quando C.1 reprova e não há como planejar mais.
        """
        approval: GlobalApproval | None = None
        while approval is None:
            async for event in self.__run_loop():
                yield event

            context = self.__new_context(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)
            stored_results = self.__render_results()
            outcome = await self.__execute_phase(
                runner=self.global_verification_phase,
                context=context,
                variables=self.__synthesis_variables(stored_results=stored_results),
                validation=ValidationContext(
                    expected_criteria_ids=tuple(criterion.id for criterion in self.__general_criteria)
                ),
            )
            report = self.__to_report(parsed=outcome.parsed)
            self.__pending_criteria_ids = report.unmet_criteria_ids
            yield await self.__record_and_build(
                subtype=ThinkingEventSubtypeEnum.COMPILE,
                phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
                task=_SYNTHESIS_TASK_LABEL,
                content=self.__render_report(report=report),
                context=context,
                outcome=outcome,
                task_id=None,
            )

            if report.approved:
                approval = GlobalApproval(
                    report=report, stored_results=stored_results, task_ids=tuple(self.__results)
                )
                continue

            verdict = self.cost_guard.authorize_additional_planning(reserved_output_tokens=self.__max_tokens)
            if not verdict.authorized:
                raise ExecutionInterruptedError(
                    limit=verdict.limit,
                    phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
                    detail=_PLANNING_DETAIL.format(
                        reason=verdict.reason, criteria=self.__render_ids(ids=report.unmet_criteria_ids)
                    ),
                )

            async for event in self.__run_additional_planning(report=report):
                yield event

        async for event in self.__run_final_answer(approval=approval):
            yield event

    async def __run_additional_planning(self, report: VerificationReport) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa C.2, inserindo as novas tarefas no topo da fila.

        O lote é validado contra os espaços que a sessão ainda tem antes de entrar na fila; um
        lote acima do teto volta ao planejador para correção, e nunca é truncado.

        Args:
            report: Relatório de C.1 com os critérios gerais não atendidos.

        Yields:
            ThinkingEvent: Evento `replan`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)
        outcome = await self.__execute_phase(
            runner=self.additional_planning_phase,
            context=context,
            variables={
                **self.__planning_variables(report=report),
                **self.__planning_limits(),
                **self.__learnings_variables(),
            },
            validation=self.__planning_validation(),
        )
        tasks = self.__to_tasks(parsed=outcome.parsed, origin_phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)
        self.task_queue.push_front(tasks=tasks)
        self.cost_guard.register_task_created(quantity=len(tasks))
        self.cost_guard.register_additional_planning_round()
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.REPLAN,
            phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
            task=_SYNTHESIS_TASK_LABEL,
            content=f"{_TASKS_HEADING}\n\n{self.__render_tasks(tasks=tasks)}",
            context=context,
            outcome=outcome,
            task_id=None,
        )

    async def __run_final_answer(self, approval: GlobalApproval) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa C.3 sobre o conjunto de resultados que C.1 aprovou e encerra a sessão.

        A sessão só é concluída depois que a síntese válida foi produzida e persistida; o evento
        terminal é emitido por último.

        Args:
            approval: Aprovação global, de onde vêm os resultados que C.3 pode usar.

        Yields:
            ThinkingEvent: Evento `compile` de C.3 e o evento final `result`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER)
        outcome = await self.__execute_phase(
            runner=self.final_answer_phase,
            context=context,
            variables=self.__synthesis_variables(stored_results=approval.stored_results),
        )
        final_answer = outcome.parsed["final_answer"]
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.COMPILE,
            phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
            task=_SYNTHESIS_TASK_LABEL,
            content=final_answer,
            context=context,
            outcome=outcome,
            task_id=None,
        )

        await self.session_recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer=final_answer)
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.RESULT,
            subtype=ThinkingEventSubtypeEnum.COMPILE,
            phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
            task=_SYNTHESIS_TASK_LABEL,
            content=final_answer,
            context=context,
            inference_time_ms=outcome.inference_time_ms,
        )

    async def __fail(self, error: Exception) -> AsyncGenerator[ThinkingEvent, None]:
        """Encerra a sessão sem conclusão e só então emite o único evento terminal de erro.

        Uma interrupção por limite de recursos e um erro técnico terminam do mesmo jeito — sem
        resposta final —, mas ficam registrados com motivos estruturados diferentes. As tarefas que
        sobraram na fila são descartadas e citadas no diagnóstico.

        Args:
            error: Falha ou interrupção ocorrida durante o fluxo.

        Yields:
            ThinkingEvent: Evento `error`.
        """
        if not isinstance(error, RalphError):
            self.logger.exception("Falha inesperada no fluxo de thinking")

        failure = self.__to_failure(error=error)
        await self.session_recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=failure)
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.ERROR,
            subtype=ThinkingEventSubtypeEnum.COMPILE,
            phase=failure.phase,
            task=_SYNTHESIS_TASK_LABEL,
            content=_ERROR_CONTENT.format(reason=failure.description),
            context=self.__context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

    def __to_failure(self, error: Exception) -> SessionFailure:
        """Classifica o encerramento e monta o motivo estruturado, com o diagnóstico disponível.

        Args:
            error: Falha ou interrupção ocorrida durante o fluxo.

        Returns:
            SessionFailure: Limite de recursos, quando o erro aponta um limite; erro técnico no demais.
        """
        discarded = self.task_queue.discard_all()
        details = [
            _CONSUMPTION_DETAIL.format(
                tokens=self.session_recorder.session.totals.total_tokens,
                calls=self.session_recorder.session.totals.total_llm_calls,
            )
        ]
        if discarded:
            details.append(_DISCARDED_DETAIL.format(tasks=self.__render_task_ids(tasks=discarded)))
        if self.__pending_criteria_ids:
            details.append(_PENDING_CRITERIA_DETAIL.format(criteria=self.__render_ids(ids=self.__pending_criteria_ids)))
        description = _SENTENCE_SEPARATOR.join([str(error), *details])

        if isinstance(error, ExecutionInterruptedError):
            return self.__resource_failure(
                limit=error.limit,
                phase=error.phase,
                task_id=error.task_id or self.__active_task_id,
                description=description,
            )
        if isinstance(error, PhaseParsingError) and error.limit is not None:
            return self.__resource_failure(
                limit=error.limit, phase=error.phase, task_id=self.__active_task_id, description=description
            )
        return SessionFailure(
            reason=SessionFailureReasonEnum.TECHNICAL_ERROR,
            phase=error.phase if isinstance(error, PhaseParsingError) else self.__running_phase,
            description=description,
            occurred_at=self.clock.now(),
            task_id=self.__active_task_id,
            pending_criteria_ids=self.__pending_criteria_ids,
        )

    def __resource_failure(
        self, limit: BudgetLimitEnum, phase: ThinkingPhaseEnum, task_id: str | None, description: str
    ) -> SessionFailure:
        """Monta a falha por limite de recursos.

        Args:
            limit: Limite responsável pela interrupção.
            phase: Fase em que o fluxo foi interrompido.
            task_id: Tarefa afetada, quando houver.
            description: Descrição legível da causa e do diagnóstico.

        Returns:
            SessionFailure: Falha estruturada por limite de recursos.
        """
        return SessionFailure(
            reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
            phase=phase,
            description=description,
            occurred_at=self.clock.now(),
            limit=limit,
            task_id=task_id,
            pending_criteria_ids=self.__pending_criteria_ids,
        )

    def __new_context(self, phase: ThinkingPhaseEnum, task_id: str | None = None) -> ContextWindow:
        """Cria e passa a considerar corrente uma janela de contexto nova.

        Args:
            phase: Fase de thinking que origina a janela.
            task_id: Tarefa associada, quando houver.

        Returns:
            ContextWindow: Janela recém-criada.
        """
        self.__context = self.context_window_factory.create(phase=phase, task_id=task_id)
        return self.__context

    async def __execute_phase(
        self,
        runner: IThinkingPhase,
        context: ContextWindow,
        variables: dict[str, str],
        validation: ValidationContext | None = None,
        is_retry: bool = False,
    ) -> PhaseOutcome:
        """Executa uma fase registrando qual fase e qual janela estão em andamento.

        O diagnóstico de uma falha técnica precisa apontar a fase que realmente falhou, e não a
        origem da janela corrente: B.2 roda numa janela própria e B.4 reaproveita a janela de B.1.

        Args:
            runner: Fase a executar.
            context: Janela de contexto em que a fase roda.
            variables: Placeholders do template da fase.
            validation: Dados esperados pela chamada, repassados ao parser.
            is_retry: Indica que a execução repete um pedido reprovado, e usa a temperatura de retentativa.

        Returns:
            PhaseOutcome: Resultado da execução da fase.
        """
        self.__context = context
        self.__running_phase = runner.phase
        return await runner.execute(context=context, variables=variables, validation=validation, is_retry=is_retry)

    def __configure_phases(self, input_dto: RalphThinkingInputDTO) -> None:
        """Fixa modelo, teto de tokens e temperatura em todas as fases.

        Args:
            input_dto: Pergunta do usuário e parâmetros do modelo.
        """
        for phase in (
            self.general_criteria_phase,
            self.task_decomposition_phase,
            self.planning_learnings_phase,
            self.task_resolution_phase,
            self.task_verification_phase,
            self.learnings_extraction_phase,
            self.global_verification_phase,
            self.additional_planning_phase,
            self.final_answer_phase,
        ):
            phase.configure(
                model_name=input_dto.model_name,
                max_tokens=input_dto.max_tokens,
                temperature=input_dto.temperature,
                provider=input_dto.provider,
            )

    def __ensure_next_task_can_start(self) -> None:
        """Consulta o guardião de custo antes de iniciar mais uma tarefa.

        Raises:
            ExecutionInterruptedError: Quando o guardião nega a próxima chamada de resolução.
        """
        verdict = self.cost_guard.authorize(
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, reserved_output_tokens=self.__max_tokens
        )
        if not verdict.authorized:
            raise ExecutionInterruptedError(
                limit=verdict.limit, phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, detail=verdict.reason
            )

    def __planning_limits(self) -> dict[str, str]:
        """Informa aos templates de planejamento quantas tarefas a sessão ainda comporta.

        Returns:
            dict[str, str]: Teto de tarefas do lote.
        """
        return {"max_tasks": str(self.cost_guard.remaining_task_slots())}

    def __planning_validation(self) -> ValidationContext:
        """Monta o contexto que o parser usa para validar um lote de tarefas planejado.

        Returns:
            ValidationContext: Teto de tarefas e identificadores já usados na sessão.
        """
        return ValidationContext(
            max_tasks=self.cost_guard.remaining_task_slots(),
            known_task_ids=self.task_queue.known_task_ids(),
        )

    async def __record_and_build(
        self,
        subtype: ThinkingEventSubtypeEnum,
        phase: ThinkingPhaseEnum,
        task: str,
        content: str,
        context: ContextWindow,
        outcome: Any,
        task_id: str | None,
    ) -> ThinkingEvent:
        """Registra na sessão a saída de uma fase e monta o evento correspondente.

        Args:
            subtype: Subtipo do evento emitido.
            phase: Fase de thinking que produziu a saída.
            task: Rótulo da tarefa no evento.
            content: Conteúdo markdown do evento.
            context: Janela de contexto usada pela fase.
            outcome: Resultado devolvido pela fase.
            task_id: Tarefa associada no histórico, quando houver.

        Returns:
            ThinkingEvent: Evento pronto para emissão.
        """
        await self.session_recorder.record_llm_message(
            phase=phase,
            content=content,
            tokens=outcome.tokens,
            inference_time_ms=outcome.inference_time_ms,
            task_id=task_id,
            context_id=context.context_id,
            prompt_input=outcome.prompt_input,
        )
        return self.__build_event(
            event_type=ThinkingEventTypeEnum.THINKING,
            subtype=subtype,
            phase=phase,
            task=task,
            content=content,
            context=context,
            inference_time_ms=outcome.inference_time_ms,
        )

    def __build_event(
        self,
        event_type: ThinkingEventTypeEnum,
        subtype: ThinkingEventSubtypeEnum,
        phase: ThinkingPhaseEnum,
        task: str,
        content: str,
        context: ContextWindow,
        inference_time_ms: int,
    ) -> ThinkingEvent:
        """Constrói o evento a ser emitido pela conexão WebSocket.

        O total de tokens vem sempre da sessão, e portanto nunca decresce; o
        tamanho do contexto vem da janela corrente, e zera a cada janela nova.

        Args:
            event_type: Tipo do evento.
            subtype: Subtipo do evento.
            phase: Fase de thinking que originou o evento.
            task: Rótulo da tarefa no evento.
            content: Conteúdo markdown do evento.
            context: Janela de contexto vigente.
            inference_time_ms: Tempo da chamada ao modelo, zero em etapas programáticas.

        Returns:
            ThinkingEvent: Evento pronto para emissão.
        """
        session = self.session_recorder.session
        return ThinkingEvent(
            type=event_type,
            subtype=subtype,
            phase=phase,
            task=task,
            content=content,
            session_id=session.id,
            total_tokens=session.totals.total_tokens,
            context_id=context.context_id,
            context_size=context.context_size,
            inference_time_ms=inference_time_ms,
        )

    def __resolution_variables(self, task: Task) -> dict[str, str]:
        """Monta as variáveis do Template B.1.

        Args:
            task: Tarefa a resolver.

        Returns:
            dict[str, str]: Descrição da tarefa, seus critérios de aceite e os aprendizados pontuais.
        """
        return {
            "task_description": self.__render_task(task=task),
            "task_acceptance_criteria": self.__render_criteria(criteria=task.acceptance_criteria),
            **self.__learnings_variables(),
        }

    def __verification_variables(self, task: Task, preliminary: str) -> dict[str, str]:
        """Monta as variáveis do Template B.2.

        Args:
            task: Tarefa verificada.
            preliminary: Resultado preliminar produzido por B.1.

        Returns:
            dict[str, str]: Resultado preliminar, critérios de aceite da tarefa e aprendizados pontuais.
        """
        return {
            "preliminary_result": preliminary,
            "task_acceptance_criteria": self.__render_criteria(criteria=task.acceptance_criteria),
            **self.__learnings_variables(),
        }

    def __synthesis_variables(self, stored_results: str) -> dict[str, str]:
        """Monta as variáveis dos Templates C.1 e C.3.

        Args:
            stored_results: Resultados aprovados, já renderizados.

        Returns:
            dict[str, str]: Resultados armazenados, critérios de aceite gerais e aprendizados pontuais,
            cada um na sua área do template: os aprendizados não se misturam aos resultados.
        """
        return {
            "stored_results": stored_results,
            "general_acceptance_criteria": self.__render_criteria(criteria=self.__general_criteria),
            **self.__learnings_variables(),
        }

    def __learnings_variables(self) -> dict[str, str]:
        """Monta a área "Aprendizados Pontuais" comum a todos os templates das fases B e C.

        A área traz todos os aprendizados acumulados até o momento da chamada — as anotações do
        enunciado (A.3) e os aprendizados de cada tarefa concluída (B.4) — e existe mesmo vazia.

        Returns:
            dict[str, str]: Aprendizados pontuais acumulados, já renderizados.
        """
        return {"learnings": self.learnings_memory.render()}

    def __planning_variables(self, report: VerificationReport) -> dict[str, str]:
        """Monta as variáveis do Template C.2.

        Args:
            report: Relatório de C.1 com os critérios gerais não atendidos.

        Returns:
            dict[str, str]: Critérios pendentes, resultados armazenados e o
            número a partir do qual as novas tarefas devem ser numeradas.
        """
        unmet = tuple(
            criterion for criterion in self.__general_criteria if criterion.id in report.unmet_criteria_ids
        )
        return {
            "unmet_criteria": self.__render_criteria(criteria=unmet),
            "stored_results": self.__render_results(),
            "next_task_number": str(self.task_queue.total_created() + _FIRST_TASK_NUMBER),
        }

    def __to_criteria(self, parsed: dict[str, Any]) -> tuple[AcceptanceCriterion, ...]:
        """Converte a saída de A.1 em critérios de aceite gerais.

        Args:
            parsed: Saída já validada de A.1.

        Returns:
            tuple[AcceptanceCriterion, ...]: Critérios gerais da resposta final.
        """
        return tuple(
            AcceptanceCriterion(id=criterion["id"], description=criterion["description"])
            for criterion in parsed["general_acceptance_criteria"]
        )

    def __to_tasks(self, parsed: dict[str, Any], origin_phase: ThinkingPhaseEnum) -> list[Task]:
        """Converte a saída de A.2 ou C.2 em tarefas do domínio.

        Args:
            parsed: Saída já validada da fase de planejamento.
            origin_phase: Fase que originou as tarefas.

        Returns:
            list[Task]: Tarefas prontas para entrar na fila.
        """
        return [
            Task(
                id=task["id"],
                title=task["title"],
                description=task["description"],
                acceptance_criteria=tuple(
                    AcceptanceCriterion(id=criterion["id"], description=criterion["description"])
                    for criterion in task["acceptance_criteria"]
                ),
                origin_phase=origin_phase,
            )
            for task in parsed["tasks"]
        ]

    def __to_report(self, parsed: dict[str, Any]) -> VerificationReport:
        """Converte a saída de B.2 ou C.1 em relatório de verificação.

        Args:
            parsed: Saída já validada da fase de verificação.

        Returns:
            VerificationReport: Relatório com decisão, vereditos e pendências.
        """
        return VerificationReport(
            decision=VerificationDecisionEnum(parsed["decision"]),
            evaluations=tuple(
                CriterionEvaluation(
                    criterion_id=evaluation["criterion_id"],
                    met=evaluation["met"],
                    justification=evaluation["justification"],
                )
                for evaluation in parsed["criteria_evaluation"]
            ),
            unmet_criteria_ids=tuple(parsed["unmet_criteria_ids"]),
        )

    def __to_learnings(self, parsed: dict[str, Any], task_id: str | None) -> list[Learning]:
        """Converte a saída de A.3 ou B.4 em aprendizados pontuais.

        Args:
            parsed: Saída já validada de A.3 ou B.4.
            task_id: Tarefa que originou os aprendizados, ou `None` quando vêm do enunciado.

        Returns:
            list[Learning]: Aprendizados extraídos, possivelmente nenhum.
        """
        return [Learning(content=content, source_task_id=task_id) for content in parsed["learnings"]]

    def __render_criteria(self, criteria: Sequence[AcceptanceCriterion]) -> str:
        """Renderiza critérios de aceite como lista markdown.

        Args:
            criteria: Critérios a renderizar.

        Returns:
            str: Lista markdown, um critério por linha.
        """
        return _ITEM_SEPARATOR.join(
            _CRITERION_ITEM.format(criterion_id=criterion.id, description=criterion.description)
            for criterion in criteria
        )

    def __render_task(self, task: Task) -> str:
        """Renderiza uma tarefa como bloco markdown.

        Args:
            task: Tarefa a renderizar.

        Returns:
            str: Bloco markdown com descrição e critérios.
        """
        return _TASK_CONTENT.format(
            task_id=task.id,
            title=task.title,
            description=task.description,
            criteria=self.__render_criteria(criteria=task.acceptance_criteria),
        )

    def __render_tasks(self, tasks: Sequence[Task]) -> str:
        """Renderiza uma lista de tarefas como blocos markdown.

        Args:
            tasks: Tarefas a renderizar.

        Returns:
            str: Blocos markdown separados por linha em branco.
        """
        return _BLOCK_SEPARATOR.join(self.__render_task(task=task) for task in tasks)

    def __render_task_ids(self, tasks: Sequence[Task]) -> str:
        """Renderiza os identificadores de um conjunto de tarefas.

        Args:
            tasks: Tarefas a listar.

        Returns:
            str: Identificadores separados por vírgula.
        """
        return self.__render_ids(ids=[task.id for task in tasks])

    def __render_ids(self, ids: Sequence[str]) -> str:
        """Renderiza uma lista de identificadores em linha.

        Args:
            ids: Identificadores a listar.

        Returns:
            str: Identificadores separados por vírgula.
        """
        return _LIST_SEPARATOR.join(f"`{identifier}`" for identifier in ids)

    def __render_report(self, report: VerificationReport) -> str:
        """Renderiza um relatório de verificação como markdown.

        Args:
            report: Relatório a renderizar.

        Returns:
            str: Decisão seguida do veredito de cada critério.
        """
        evaluations = _ITEM_SEPARATOR.join(
            _EVALUATION_ITEM.format(
                criterion_id=evaluation.criterion_id,
                status=_MET_LABEL if evaluation.met else _UNMET_LABEL,
                justification=evaluation.justification,
            )
            for evaluation in report.evaluations
        )
        return _REPORT_CONTENT.format(decision=report.decision.value, evaluations=evaluations)

    def __render_learnings(self, learnings: Sequence[Learning], empty_content: str = _NO_LEARNINGS_CONTENT) -> str:
        """Renderiza os aprendizados extraídos de uma tarefa ou do enunciado.

        Args:
            learnings: Aprendizados a renderizar.
            empty_content: Aviso exibido quando nada foi extraído.

        Returns:
            str: Bloco markdown, ou o aviso de que nada foi extraído.
        """
        if not learnings:
            return empty_content
        items = _ITEM_SEPARATOR.join(f"- {learning.content}" for learning in learnings)
        return f"{_LEARNINGS_HEADING}\n\n{items}"

    def __render_results(self) -> str:
        """Renderiza os resultados armazenados em B.3.

        Returns:
            str: Um bloco markdown por resultado, na ordem de armazenamento.
        """
        return _BLOCK_SEPARATOR.join(
            _RESULT_BLOCK.format(task_id=result.task_id, title=result.task_title, content=result.content)
            for result in self.__results.values()
        )
