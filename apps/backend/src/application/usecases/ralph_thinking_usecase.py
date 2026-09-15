import logging
from typing import Any, AsyncGenerator, Sequence

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.llm.message import Message
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.learning import Learning
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum
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
_NO_REMAINING = 0
_FIRST_TASK_NUMBER = 1
_LAST_ATTEMPT = -1

_CRITERIA_HEADING = "## Critérios de aceite gerais"
_TASKS_HEADING = "## Tarefas planejadas"
_LEARNINGS_HEADING = "## Aprendizados extraídos"
_NO_LEARNINGS_CONTENT = "Nenhum aprendizado foi extraído desta tarefa."
_RESET_CONTENT = "Contexto reinicializado para a tarefa `{task_id}`. Nova janela: `{context_id}`."
_TASK_CONTENT = (
    "### {task_id} — {title}\n\n{description}\n\n"
    "**Entrada esperada:** {expected_input}\n\n"
    "**Saída esperada:** {expected_output}\n\n"
    "**Critérios de aceite:**\n{criteria}"
)
_STORE_CONTENT = "Resultado da tarefa `{task_id}` armazenado."
_REPORT_CONTENT = "**Decisão:** `{decision}`\n\n{evaluations}"
_EVALUATION_ITEM = "- `{criterion_id}` — {status}: {justification}"
_MET_LABEL = "atendido"
_UNMET_LABEL = "não atendido"
_REPROVED_ATTEMPT_CONTENT = (
    "A tentativa anterior foi reprovada.\n\n"
    "**Resultado reprovado:**\n\n{preliminary}\n\n"
    "**Critérios não satisfeitos:** {unmet}\n\n"
    "**Veredito do validador:**\n\n{report}\n\n"
    "Refaça a resolução da tarefa corrigindo exatamente esses pontos."
)
_RESULT_BLOCK = "## {task_id} — {title}\n\n{content}"
_DEGRADATION_CONTENT = "**Degradação:** limite `{limit}` atingido. {detail}"
_ATTEMPTS_DETAIL = "A última tentativa da tarefa `{task_id}` foi aceita como está."
_BUDGET_DETAIL = "O loop de execução foi interrompido e as tarefas restantes foram descartadas: {tasks}."
_PLANNING_DETAIL = "Nenhum planejamento adicional será executado; a resposta final usa os resultados existentes."
_ERROR_CONTENT = "**Erro:** {reason}"
_ITEM_SEPARATOR = "\n"
_BLOCK_SEPARATOR = "\n\n"
_LIST_SEPARATOR = ", "
_CRITERION_ITEM = "- `{criterion_id}`: {description}"
_EMPTY_LIST_CONTENT = "—"


class RalphThinkingUseCase:
    """Orquestra o fluxo completo do Ralph Loop adaptado.

    Executa Planejamento → Execução em Loop → Criação da Resposta Final,
    conforme o pseudocódigo canônico do orquestrador descrito no paper.
    """

    def __init__(
        self,
        general_criteria_phase: IThinkingPhase,
        task_decomposition_phase: IThinkingPhase,
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
        self.__general_criteria: tuple[AcceptanceCriterion, ...] = ()
        self.__results: dict[str, TaskResult] = {}
        self.__degraded: bool = False
        self.__context: ContextWindow = ContextWindow(context_id="", phase=_RALPH_FLOW)

    async def execute(self, input_dto: RalphThinkingInputDTO) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o fluxo completo de thinking, emitindo um evento por etapa.

        Args:
            input_dto: Pergunta do usuário e parâmetros do modelo.

        Yields:
            ThinkingEvent: Evento correspondente a cada etapa do fluxo.

        Raises:
            Exception: Toda falha é registrada, emitida como evento `error`,
                encerra a sessão como falha e é repropagada ao chamador.
        """
        self.__user_question = input_dto.user_input
        await self.session_recorder.start(
            user_question=input_dto.user_input,
            flow=_RALPH_FLOW,
            model_name=input_dto.model_name,
            max_tokens=input_dto.max_tokens,
            temperature=input_dto.temperature,
        )
        await self.session_recorder.record_user_input(content=input_dto.user_input)
        self.__configure_phases(input_dto=input_dto)

        try:
            async for event in self.__run_planning():
                yield event
            async for event in self.__run_synthesis():
                yield event
        except Exception as error:
            async for event in self.__fail(error=error):
                yield event
            raise

    async def __run_planning(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa A.1 e A.2, produzindo os critérios gerais e a fila inicial.

        Yields:
            ThinkingEvent: Eventos `setup` (A.1) e `tasks` (A.2).
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA)
        outcome = await self.general_criteria_phase.execute(
            context=context, variables={"user_question": self.__user_question}
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
        outcome = await self.task_decomposition_phase.execute(
            context=context, variables={"user_question": self.__user_question}
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

    async def __run_loop(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o loop de execução até a fila de tarefas se esvaziar.

        Yields:
            ThinkingEvent: Eventos de cada tarefa executada e da eventual degradação
            por esgotamento do orçamento, que descarta as tarefas restantes.
        """
        while not self.task_queue.is_empty():
            limit = self.__loop_budget_limit()
            if limit is not None:
                discarded = self.task_queue.discard_all()
                detail = _BUDGET_DETAIL.format(tasks=self.__render_task_ids(tasks=discarded))
                async for event in self.__degrade(
                    limit=limit,
                    phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
                    subtype=ThinkingEventSubtypeEnum.EXECUTE,
                    detail=detail,
                    context=self.__context,
                    task_id=None,
                ):
                    yield event
                return

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

        if not self.learnings_memory.is_empty():
            context.append(
                message=Message(
                    creation_timestamp=self.clock.now(),
                    text=self.learnings_memory.render(),
                    source=MessageSourceEnum.SYSTEM,
                )
            )

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

    async def __resolve_task(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o ciclo de tentativas de B.1 e B.2 para uma tarefa.

        A janela da tarefa é a mesma em toda retentativa: a tentativa reprovada,
        os critérios não satisfeitos e o veredito do validador permanecem no
        contexto e guiam a correção. É esse mesmo contexto completo — tentativas
        reprovadas e interações com o validador — que B.4 recebe ao final.

        Args:
            task: Tarefa em execução.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Eventos `reasoning`, `verify_pass`/`verify_fail` e a
            eventual degradação por esgotamento das tentativas.
        """
        while True:
            attempt = self.cost_guard.register_task_attempt(task_id=task.id)
            outcome = await self.task_resolution_phase.execute(
                context=context, variables=self.__resolution_variables(task=task)
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
            outcome = await self.task_verification_phase.execute(
                context=verification_context,
                variables=self.__verification_variables(task=task, preliminary=preliminary),
            )
            report = self.__to_report(parsed=outcome.parsed)
            task.attempts.append(TaskAttempt(number=attempt, output=preliminary, report=report))
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
                task.status = TaskStatusEnum.DEGRADED
                async for event in self.__degrade(
                    limit=BudgetLimitEnum.TASK_ATTEMPTS,
                    phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                    subtype=ThinkingEventSubtypeEnum.VERIFY_FAIL,
                    detail=_ATTEMPTS_DETAIL.format(task_id=task.id),
                    context=context,
                    task_id=task.id,
                ):
                    yield event
                return

            context.append(
                message=Message(
                    creation_timestamp=self.clock.now(),
                    text=_REPROVED_ATTEMPT_CONTENT.format(
                        preliminary=preliminary,
                        unmet=self.__render_ids(ids=report.unmet_criteria_ids),
                        report=self.__render_report(report=report),
                    ),
                    source=MessageSourceEnum.USER,
                )
            )

    async def __store_result(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Armazena o resultado aprovado de uma tarefa (B.3), sem chamar o modelo.

        Args:
            task: Tarefa recém-concluída.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Evento `store`, sempre com tempo de inferência zero.
        """
        self.__results[task.id] = TaskResult(
            task_id=task.id,
            task_title=task.title,
            content=task.attempts[_LAST_ATTEMPT].output,
            degraded=task.status is TaskStatusEnum.DEGRADED,
        )
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

        Usa a janela completa da tarefa, que contém todas as tentativas, inclusive
        as reprovadas — é lá que fatos úteis podem ter emergido.

        Args:
            task: Tarefa recém-concluída.
            context: Janela de contexto da tarefa.

        Yields:
            ThinkingEvent: Evento `learn`.
        """
        outcome = await self.learnings_extraction_phase.execute(context=context, variables={})
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

        Yields:
            ThinkingEvent: Eventos do loop, `compile` (C.1), `replan` (C.2),
            `compile` (C.3) e, por último, o evento `result`.
        """
        while True:
            async for event in self.__run_loop():
                yield event

            context = self.__new_context(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)
            outcome = await self.global_verification_phase.execute(
                context=context, variables=self.__synthesis_variables()
            )
            report = self.__to_report(parsed=outcome.parsed)
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
                break

            if not self.cost_guard.can_run_additional_planning():
                async for event in self.__degrade(
                    limit=self.__planning_limit(),
                    phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
                    subtype=ThinkingEventSubtypeEnum.REPLAN,
                    detail=_PLANNING_DETAIL,
                    context=context,
                    task_id=None,
                ):
                    yield event
                break

            async for event in self.__run_additional_planning(report=report):
                yield event

        async for event in self.__run_final_answer():
            yield event

    async def __run_additional_planning(self, report: VerificationReport) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa C.2, inserindo as novas tarefas no topo da fila.

        Args:
            report: Relatório de C.1 com os critérios gerais não atendidos.

        Yields:
            ThinkingEvent: Evento `replan`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)
        outcome = await self.additional_planning_phase.execute(
            context=context, variables=self.__planning_variables(report=report)
        )
        tasks = self.__to_tasks(parsed=outcome.parsed, origin_phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)
        tasks = tasks[: self.cost_guard.remaining_task_slots()]
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

    async def __run_final_answer(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa C.3 e encerra a sessão.

        Yields:
            ThinkingEvent: Evento `compile` de C.3 e o evento final `result`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER)
        outcome = await self.final_answer_phase.execute(context=context, variables=self.__synthesis_variables())
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

        await self.session_recorder.finish(
            status=SessionStatusEnum.DEGRADED if self.__degraded else SessionStatusEnum.COMPLETED,
            final_answer=final_answer,
        )
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.RESULT,
            subtype=ThinkingEventSubtypeEnum.COMPILE,
            phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
            task=_SYNTHESIS_TASK_LABEL,
            content=final_answer,
            context=context,
            inference_time_ms=outcome.inference_time_ms,
        )

    async def __degrade(
        self,
        limit: BudgetLimitEnum,
        phase: ThinkingPhaseEnum,
        subtype: ThinkingEventSubtypeEnum,
        detail: str,
        context: ContextWindow,
        task_id: str | None,
    ) -> AsyncGenerator[ThinkingEvent, None]:
        """Aplica a política de degradação quando um limite de orçamento é atingido.

        A sessão nunca é abortada: a degradação é registrada, emitida e o fluxo
        segue até entregar uma resposta ao usuário.

        Args:
            limit: Limite de orçamento responsável pela degradação.
            phase: Fase de thinking em que a degradação ocorreu.
            subtype: Subtipo do evento emitido.
            detail: Descrição do efeito prático da degradação.
            context: Janela de contexto vigente no momento da degradação.
            task_id: Tarefa afetada, quando a degradação é de uma tarefa.

        Yields:
            ThinkingEvent: Evento `degraded`.
        """
        self.__degraded = True
        content = _DEGRADATION_CONTENT.format(limit=limit.value, detail=detail)
        self.logger.warning("Degradação por '%s' na fase '%s'", limit.value, phase.value)
        await self.session_recorder.record_degradation(
            degradation=SessionDegradation(
                limit=limit,
                phase=phase,
                task_id=task_id,
                description=content,
                occurred_at=self.clock.now(),
            )
        )
        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.DEGRADED,
            subtype=subtype,
            phase=phase,
            task=task_id or _SYNTHESIS_TASK_LABEL,
            content=content,
            context=context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

    async def __fail(self, error: Exception) -> AsyncGenerator[ThinkingEvent, None]:
        """Encerra a sessão como falha e emite o evento de erro.

        Args:
            error: Falha ocorrida durante o fluxo.

        Yields:
            ThinkingEvent: Evento `error`.
        """
        if not isinstance(error, RalphError):
            self.logger.exception("Falha inesperada no fluxo de thinking")

        yield self.__build_event(
            event_type=ThinkingEventTypeEnum.ERROR,
            subtype=ThinkingEventSubtypeEnum.COMPILE,
            phase=self.__context.phase,
            task=_SYNTHESIS_TASK_LABEL,
            content=_ERROR_CONTENT.format(reason=str(error)),
            context=self.__context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )
        await self.session_recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None)

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

    def __configure_phases(self, input_dto: RalphThinkingInputDTO) -> None:
        """Fixa modelo, teto de tokens e temperatura em todas as fases.

        Args:
            input_dto: Pergunta do usuário e parâmetros do modelo.
        """
        for phase in (
            self.general_criteria_phase,
            self.task_decomposition_phase,
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

    def __loop_budget_limit(self) -> BudgetLimitEnum | None:
        """Consulta o guardião de custo antes de iniciar mais uma tarefa.

        Returns:
            BudgetLimitEnum | None: Limite que impede a próxima tarefa, ou `None`
            quando o loop pode prosseguir.
        """
        if self.cost_guard.remaining_tokens() <= _NO_REMAINING:
            return BudgetLimitEnum.SESSION_TOKEN_BUDGET

        verdict = self.cost_guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)
        if verdict.authorized:
            return None
        return verdict.limit

    def __planning_limit(self) -> BudgetLimitEnum:
        """Identifica o limite que impediu mais uma rodada de C.2.

        Returns:
            BudgetLimitEnum: Limite de tarefas, quando não há mais slot, ou o
            limite de rodadas de planejamento adicional.
        """
        if self.cost_guard.remaining_task_slots() <= _NO_REMAINING:
            return BudgetLimitEnum.TASKS_PER_SESSION
        return BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS

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
            dict[str, str]: Descrição da tarefa e seus critérios de aceite.
        """
        return {
            "task_description": self.__render_task(task=task),
            "task_acceptance_criteria": self.__render_criteria(criteria=task.acceptance_criteria),
        }

    def __verification_variables(self, task: Task, preliminary: str) -> dict[str, str]:
        """Monta as variáveis do Template B.2.

        Args:
            task: Tarefa verificada.
            preliminary: Resultado preliminar produzido por B.1.

        Returns:
            dict[str, str]: Resultado preliminar e critérios de aceite da tarefa.
        """
        return {
            "preliminary_result": preliminary,
            "task_acceptance_criteria": self.__render_criteria(criteria=task.acceptance_criteria),
        }

    def __synthesis_variables(self) -> dict[str, str]:
        """Monta as variáveis dos Templates C.1 e C.3.

        Returns:
            dict[str, str]: Resultados armazenados e critérios de aceite gerais.
        """
        return {
            "stored_results": self.__render_results(),
            "general_acceptance_criteria": self.__render_criteria(criteria=self.__general_criteria),
        }

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
                expected_input=task["expected_input"],
                expected_output=task["expected_output"],
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

    def __to_learnings(self, parsed: dict[str, Any], task_id: str) -> list[Learning]:
        """Converte a saída de B.4 em aprendizados pontuais.

        Args:
            parsed: Saída já validada de B.4.
            task_id: Tarefa que originou os aprendizados.

        Returns:
            list[Learning]: Aprendizados extraídos, possivelmente nenhum.
        """
        return [Learning(content=content, source_task_id=task_id) for content in parsed["learnings"]]

    def __render_criteria(self, criteria: Sequence[AcceptanceCriterion]) -> str:
        """Renderiza critérios de aceite como lista markdown.

        Args:
            criteria: Critérios a renderizar.

        Returns:
            str: Lista markdown, ou um traço quando não há critérios.
        """
        if not criteria:
            return _EMPTY_LIST_CONTENT
        return _ITEM_SEPARATOR.join(
            _CRITERION_ITEM.format(criterion_id=criterion.id, description=criterion.description)
            for criterion in criteria
        )

    def __render_task(self, task: Task) -> str:
        """Renderiza uma tarefa como bloco markdown.

        Args:
            task: Tarefa a renderizar.

        Returns:
            str: Bloco markdown com descrição, entradas, saídas e critérios.
        """
        return _TASK_CONTENT.format(
            task_id=task.id,
            title=task.title,
            description=task.description,
            expected_input=task.expected_input,
            expected_output=task.expected_output,
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

    def __render_learnings(self, learnings: Sequence[Learning]) -> str:
        """Renderiza os aprendizados extraídos de uma tarefa.

        Args:
            learnings: Aprendizados a renderizar.

        Returns:
            str: Bloco markdown, ou o aviso de que nada foi extraído.
        """
        if not learnings:
            return _NO_LEARNINGS_CONTENT
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
