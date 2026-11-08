import logging
from typing import Any, AsyncGenerator, Sequence

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation
from src.domain.entities.thinking.global_approval import GlobalApproval
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.entities.thinking.plan_validation_issue import PlanValidationIssue
from src.domain.entities.thinking.plan_validation_report import PlanValidationReport
from src.domain.entities.thinking.learning import Learning
from src.domain.entities.thinking.ledger_change import LedgerChange
from src.domain.entities.thinking.result_revision import ResultRevision
from src.domain.entities.thinking.review_request import ReviewRequest
from src.domain.entities.thinking.revision_verdict import RevisionVerdict
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.ralph_flow_version_enum import RalphFlowVersionEnum
from src.domain.enums.result_status_enum import ResultStatusEnum
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
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
from src.domain.interfaces.results_ledger_interface import IResultsLedger
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

_CRITERIA_HEADING = "## General acceptance criteria"
_TASKS_HEADING = "## Planned tasks"
# Planejamento validado (fluxo versão 2). O candidato de A.2 só vira tarefa da fila depois da aprovação de
# A.3; a revisão de A.2 recebe, como material delimitado, só o último candidato e o relatório dele.
_CANDIDATE_HEADING = "## Candidate plan — attempt {attempt}"
_PLAN_DECISION_CONTENT = "**Plan decision:** `{decision}`"
_PLAN_APPROVED_LABEL = "approved"
_PLAN_REJECTED_LABEL = "rejected"
_PLAN_APPROVED_CONTENT = "No blocking issue: the candidate plan is confirmed in the task queue."
_PLAN_ISSUE_ITEM = "- {scope}: {problem}\n  - **Adjustment:** {adjustment}"
_PLAN_WIDE_SCOPE = "Whole plan"
_TASK_SCOPE = "`{task_id}`"
_CRITERION_SCOPE = "`{task_id}` / `{criterion_id}`"
_FIRST_CANDIDATE_CONTENT = "None: this is the first candidate plan."
_PLAN_REVISION_CONTENT = (
    "<previous_candidate>\n{plan}\n</previous_candidate>\n\n"
    "<validation_report>\n{report}\n</validation_report>\n\n"
    "{instruction}"
)
_PLAN_REVISION_INSTRUCTION = (
    "The validation stage rejected the previous candidate plan above. Produce a complete revised plan that "
    "resolves every issue in the report. Change the number, content, order, identifiers or dependencies of "
    "the tasks when an issue requires it; preserve the parts the report did not question and keep the plan "
    "covering the whole request. Each adjustment describes what to investigate or verify: keep the unknown "
    "results open instead of replacing one anticipated conclusion with another. Your complete output "
    "replaces the previous candidate."
)
_LEARNINGS_HEADING = "## Extracted learnings"
_DISCARDED_LEARNINGS_HEADING = "## Repeated learnings already recorded (not stored again)"
_NO_LEARNINGS_CONTENT = "No learnings were extracted from this task."
_NO_PLANNING_LEARNINGS_CONTENT = "No learnings were extracted from the question."
_RESET_CONTENT = "Context reset for task `{task_id}`. New window: `{context_id}`."
_TASK_HEADER_CONTENT = "### {task_id} — {title}\n\n{description}"
_TASK_CONTENT = (
    f"{_TASK_HEADER_CONTENT}\n\n"
    "{links}**Acceptance criteria:**\n{criteria}"
)
_TASK_REVIEW_CONTENT = "**Reviews:** {ids} — {reason}\n\n"
_TASK_DEPENDENCIES_CONTENT = "**Depends on:** {ids}\n\n"
_STORE_CONTENT = "Result of task `{task_id}` stored."
_STORE_CHANGE_CONTENT = "{label}: {ids}."
_STORE_WITHDRAWN_CONTENT = "Learnings withdrawn from the current view: {count}."
_STORE_RESTORED_CONTENT = "Learnings restored to the current view: {count}."
_SUPERSEDED_LABEL = "Superseded results"
_CONFIRMED_LABEL = "Confirmed results"
_SUSPENDED_LABEL = "Results awaiting revalidation"
_REINSTATED_LABEL = "Reinstated results"
_WITHHELD_LEARNINGS_HEADING = "## Learnings withheld while the result awaits revalidation"
# Revisão de resultados (thinking 05): só referências estruturadas mudam o estado vigente. As áreas abaixo
# entregam às fases, como material delimitado, o que está sob investigação e o que deixou de ser vigente.
_NO_REVIEW_CONTENT = "None: this task does not review stored results."
_REVIEW_REASON_CONTENT = "**Reason for the investigation (from planning):** {reason}"
_REVIEWED_RESULT_CONTENT = (
    "### {task_id} — {title}\n\n**Statement:**\n\n{description}\n\n**Conclusion under review:** {conclusion}"
)
_PROPOSED_VERDICT_CONTENT = "**Proposed verdict for `{task_id}`:** `{verdict}`\n\n**Justification:** {justification}"
_PREVIOUS_REVISION_CONTENT = "**Revision proposed:**\n\n{verdicts}\n\n"
_PREVIOUS_VERDICT_ITEM = "- `{task_id}`: `{verdict}` — {justification}"
_NO_REVISIONS_CONTENT = "No stored result has been revised or suspended."
_SUPERSEDED_RECORD_HEADING = (
    "### Superseded results\n\n"
    "History only: these conclusions were replaced by an approved review and are not current facts."
)
_SUPERSEDED_RECORD_ITEM = "- `{task_id}` — {title}: superseded by `{revising_task_id}`. Approved reason: {reason}"
# Uma confirmação aprovada não muda o estado do alvo, mas precisa constar no registro: sem ela, C.1 e C.2
# veriam o conflito já investigado como pendente e o registro afirmaria que nada foi revisado.
_CONFIRMED_RECORD_HEADING = (
    "### Results confirmed by an approved review\n\n"
    "Current facts: an approved investigation checked each claim below and confirmed it; they remain among "
    "the current results because of that investigation, not because of recency."
)
_CONFIRMED_RECORD_ITEM = "- `{task_id}` — {title}: confirmed by `{revising_task_id}`. Approved reason: {reason}"
_AWAITING_RECORD_HEADING = (
    "### Results awaiting revalidation\n\n"
    "Not current facts: each one explicitly depends on a result that stopped being current, and it can support "
    "the answer again only after an approved review confirms or replaces it."
)
_AWAITING_RECORD_ITEM = "- `{task_id}` — {title}: depends on {dependencies}."
_AWAITING_PLANNING_DETAIL = (
    "\n  - **Statement:** {description}\n  - **Conclusion awaiting revalidation:** {conclusion}"
)
_REPORT_CONTENT = "**Decision:** `{decision}`\n\n{evaluations}"
_EVALUATION_ITEM = "- `{criterion_id}` — {status}: {justification}"
_MET_LABEL = "met"
_UNMET_LABEL = "not met"
# Entradas explícitas montadas a partir do registro da tarefa (`Task.attempts`). Toda mudança de fase
# abre uma janela nova: o feedback da nova tentativa de B.1 e o histórico que B.4 recebe chegam como
# material delimitado nas variáveis do template, e nunca herdando a conversa de outra janela.
_NO_PREVIOUS_ATTEMPTS_CONTENT = "None: this is the first attempt at this task."
_PREVIOUS_ATTEMPTS_CONTENT = "<previous_attempts>\n{attempts}\n</previous_attempts>\n\n{instruction}"
_PREVIOUS_ATTEMPT_CONTENT = (
    "### Attempt {attempt} — rejected\n\n"
    "**Result presented:**\n\n{output}\n\n"
    "{revision}**Validator verdict:**\n\n{report}"
)
_RETRY_INSTRUCTION_CONTENT = (
    "The previous attempt was rejected. Criteria not met: {unmet}.\n\n"
    "Redo the resolution of the task. Address the concrete problem that each verdict identifies in "
    "these criteria. Keep the conclusions that the verdict did not refute; correct those it shows to "
    "rest on an error in data, conditions or calculation."
)
_DISCARDED_RESOLUTION_CONTENT = (
    "#### Discarded resolution output ({defect})\n\n"
    "The resolution returned an invalid output and was instructed to correct it.\n\n"
    "**Invalid output:**\n\n{raw_output}\n\n**Rejection reason:** {reason}"
)
_INVALID_VERIFIER_OUTPUT_CONTENT = (
    "#### Invalid validator output ({defect})\n\n"
    "The validator returned an invalid output and was instructed to correct it.\n\n"
    "**Invalid output:**\n\n{raw_output}\n\n**Rejection reason:** {reason}"
)
_RESULT_BLOCK = "## {task_id} — {title}\n\n{content}"
_RESULT_SUMMARY_BLOCK = "## {task_id} — {title}\n\n**Statement:**\n\n{description}\n\n**Conclusion:** {conclusion}"
_HISTORY_ATTEMPT_HEADER = "### Attempt {attempt} — {status}"
_HISTORY_OUTPUT_CONTENT = "**Preliminary result:**\n\n{output}"
_HISTORY_APPROVED_OUTPUT_CONTENT = "**Preliminary result:** it is the approved result, shown in its own area."
_HISTORY_REPORT_CONTENT = "**Validator verdict:**\n\n{report}"
_APPROVED_ATTEMPT_LABEL = "approved"
_REPROVED_ATTEMPT_LABEL = "rejected"
_ERROR_CONTENT = "**Erro:** {reason}"
_CONSUMPTION_DETAIL = "Consumo conhecido: {tokens} tokens em {calls} chamadas ao modelo."
_DISCARDED_DETAIL = "Tarefas descartadas: {tasks}."
_PENDING_CRITERIA_DETAIL = "Critérios gerais pendentes: {criteria}."
_ATTEMPTS_DETAIL = (
    "A tarefa `{task_id}` foi reprovada nas {attempts} tentativas permitidas; nenhum resultado foi "
    "armazenado e a execução foi encerrada sem resposta final."
)
_PLANNING_DETAIL = "{reason} Critérios gerais ainda não atendidos: {criteria}."
_PLANNING_ATTEMPTS_DETAIL = (
    "A validação da decomposição (A.3) reprovou os {attempts} planos candidatos permitidos; nenhum plano foi "
    "confirmado na fila, A.4 e as tarefas não foram executadas e a execução foi encerrada sem resposta final."
)
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
        decomposition_validation_phase: IThinkingPhase,
        planning_learnings_phase: IThinkingPhase,
        task_resolution_phase: IThinkingPhase,
        task_verification_phase: IThinkingPhase,
        learnings_extraction_phase: IThinkingPhase,
        global_verification_phase: IThinkingPhase,
        additional_planning_phase: IThinkingPhase,
        final_answer_phase: IThinkingPhase,
        task_queue: ITaskQueue,
        learnings_memory: ILearningsMemory,
        results_ledger: IResultsLedger,
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
            decomposition_validation_phase: Fase A.3, validação da decomposição.
            planning_learnings_phase: Fase A.4, aprendizados do enunciado.
            task_resolution_phase: Fase B.1.
            task_verification_phase: Fase B.2.
            learnings_extraction_phase: Fase B.4.
            global_verification_phase: Fase C.1.
            additional_planning_phase: Fase C.2.
            final_answer_phase: Fase C.3.
            task_queue: Fila de tarefas do loop de execução.
            learnings_memory: Armazenamento dos aprendizados pontuais.
            results_ledger: Resultados armazenados em B.3 e o seu estado vigente.
            context_window_factory: Fábrica de janelas de contexto novas.
            cost_guard: Ponto único de decisão sobre limites de custo.
            session_recorder: Rastreador e persistidor do histórico da sessão.
            clock: Fonte de tempo do domínio.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.general_criteria_phase: IThinkingPhase = general_criteria_phase
        self.task_decomposition_phase: IThinkingPhase = task_decomposition_phase
        self.decomposition_validation_phase: IThinkingPhase = decomposition_validation_phase
        self.planning_learnings_phase: IThinkingPhase = planning_learnings_phase
        self.task_resolution_phase: IThinkingPhase = task_resolution_phase
        self.task_verification_phase: IThinkingPhase = task_verification_phase
        self.learnings_extraction_phase: IThinkingPhase = learnings_extraction_phase
        self.global_verification_phase: IThinkingPhase = global_verification_phase
        self.additional_planning_phase: IThinkingPhase = additional_planning_phase
        self.final_answer_phase: IThinkingPhase = final_answer_phase
        self.task_queue: ITaskQueue = task_queue
        self.learnings_memory: ILearningsMemory = learnings_memory
        self.results_ledger: IResultsLedger = results_ledger
        self.context_window_factory: IContextWindowFactory = context_window_factory
        self.cost_guard: ICostGuard = cost_guard
        self.session_recorder: ISessionRecorder = session_recorder
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger
        self.__user_question: str = ""
        self.__session_token_limit: int = 0
        self.__general_criteria: tuple[AcceptanceCriterion, ...] = ()
        self.__active_task_id: str | None = None
        self.__pending_criteria_ids: tuple[str, ...] = ()
        self.__context: ContextWindow = ContextWindow(context_id="", phase=_RALPH_FLOW)
        self.__resolution_context: ContextWindow = self.__context
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
        self.__session_token_limit = input_dto.max_tokens
        await self.session_recorder.start(
            user_question=input_dto.user_input,
            flow=_RALPH_FLOW,
            model_name=input_dto.model_name,
            max_tokens=input_dto.max_tokens,
            temperature=input_dto.temperature,
            provider=input_dto.provider,
            flow_version=RalphFlowVersionEnum.current(),
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
        """Executa A.1, o ciclo A.2 ⇄ A.3 até um plano aprovado e A.4.

        A.2 gera um plano candidato e A.3 o julga; reprovado, A.2 gera o próximo a partir do último
        candidato e do relatório dele. Só o plano aprovado entra na fila, uma única vez; os candidatos
        recusados não consomem os espaços de tarefa nem reservam identificadores. Cada candidato é
        validado contra o espaço de tarefas da sessão antes de ser julgado: um lote acima do teto é
        devolvido ao planejador para correção, e nunca truncado. A.4 roda depois da confirmação.

        Yields:
            ThinkingEvent: Eventos `setup` (A.1), `plan_candidate` (A.2), `plan_rejected`/`plan_approved`
            (A.3), `tasks` (confirmação na fila, depois da aprovação) e `learn` (A.4).

        Raises:
            ExecutionInterruptedError: Quando os planos candidatos permitidos se esgotam sem aprovação.
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

        plan_revision = _FIRST_CANDIDATE_CONTENT
        while True:
            attempt = self.cost_guard.register_planning_attempt()
            candidate, event = await self.__generate_candidate(attempt=attempt, plan_revision=plan_revision)
            yield event
            report, event = await self.__validate_candidate(candidate=candidate)
            yield event
            if report.approved:
                break
            if not self.cost_guard.can_retry_planning():
                raise ExecutionInterruptedError(
                    limit=BudgetLimitEnum.PLANNING_ATTEMPTS,
                    phase=ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION,
                    detail=_PLANNING_ATTEMPTS_DETAIL.format(attempts=attempt),
                )
            plan_revision = _PLAN_REVISION_CONTENT.format(
                plan=self.__render_tasks(tasks=candidate),
                report=self.__render_plan_report(report=report),
                instruction=_PLAN_REVISION_INSTRUCTION,
            )

        yield await self.__confirm_plan(tasks=candidate)

        async for event in self.__extract_planning_learnings():
            yield event

    async def __generate_candidate(self, attempt: int, plan_revision: str) -> tuple[list[Task], ThinkingEvent]:
        """Executa A.2 numa janela nova e registra o plano candidato, sem tocar a fila.

        A primeira geração usa a temperatura da sessão; uma geração depois de uma reprovação repete o
        pedido e usa a temperatura de retentativa. O teto e os identificadores conhecidos vêm só das
        tarefas confirmadas: candidatos anteriores não contam.

        Args:
            attempt: Número do candidato, a partir de um.
            plan_revision: Último candidato reprovado e o relatório dele, ou o aviso de primeiro candidato.

        Returns:
            tuple[list[Task], ThinkingEvent]: Tarefas do candidato, ainda fora da fila, e o evento
            `plan_candidate`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION)
        outcome = await self.__execute_phase(
            runner=self.task_decomposition_phase,
            context=context,
            variables={
                "user_question": self.__user_question,
                "plan_revision": plan_revision,
                **self.__planning_limits(),
            },
            validation=self.__planning_validation(),
            is_retry=attempt > _FIRST_ATTEMPT,
        )
        candidate = self.__to_tasks(parsed=outcome.parsed, origin_phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION)
        event = await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.PLAN_CANDIDATE,
            phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
            task=_SETUP_TASK_LABEL,
            content=f"{_CANDIDATE_HEADING.format(attempt=attempt)}\n\n{self.__render_tasks(tasks=candidate)}",
            context=context,
            outcome=outcome,
            task_id=None,
        )
        return candidate, event

    async def __validate_candidate(self, candidate: Sequence[Task]) -> tuple[PlanValidationReport, ThinkingEvent]:
        """Executa A.3 numa janela nova sobre um único plano candidato.

        A fase recebe o pedido original, os critérios gerais e só este candidato, renderizado com
        descrições, critérios e dependências; o parser confere as referências contra ele. A avaliação
        volta sempre à temperatura da sessão. O relatório julga a cópia do candidato que o orquestrador
        guardou: A.3 não devolve um plano substituto.

        Args:
            candidate: Plano candidato julgado.

        Returns:
            tuple[PlanValidationReport, ThinkingEvent]: Relatório da validação e o evento `plan_approved`
            ou `plan_rejected`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION)
        outcome = await self.__execute_phase(
            runner=self.decomposition_validation_phase,
            context=context,
            variables={
                "user_question": self.__user_question,
                "general_acceptance_criteria": self.__render_criteria(criteria=self.__general_criteria),
                "candidate_plan": self.__render_tasks(tasks=candidate),
            },
            validation=ValidationContext(
                candidate_plan={
                    task.id: tuple(criterion.id for criterion in task.acceptance_criteria) for task in candidate
                }
            ),
        )
        report = self.__to_plan_report(parsed=outcome.parsed)
        event = await self.__record_and_build(
            subtype=(
                ThinkingEventSubtypeEnum.PLAN_APPROVED if report.approved else ThinkingEventSubtypeEnum.PLAN_REJECTED
            ),
            phase=ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION,
            task=_SETUP_TASK_LABEL,
            content=self.__render_plan_report(report=report),
            context=context,
            outcome=outcome,
            task_id=None,
        )
        return report, event

    async def __confirm_plan(self, tasks: Sequence[Task]) -> ThinkingEvent:
        """Confirma o plano aprovado na fila, uma única vez, sem chamar o modelo.

        É a única entrada do planejamento inicial na fila e na contagem de tarefas da sessão. A etapa é
        registrada com a janela da avaliação que aprovou o plano.

        Args:
            tasks: Plano aprovado por A.3.

        Returns:
            ThinkingEvent: Evento `tasks`, com tempo de inferência zero.
        """
        context = self.__context
        self.task_queue.push_back(tasks=list(tasks))
        self.cost_guard.register_task_created(quantity=len(tasks))
        content = f"{_TASKS_HEADING}\n\n{self.__render_tasks(tasks=tasks)}"
        await self.session_recorder.record_programmatic_step(
            phase=ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION,
            content=content,
            task_id=None,
            context_id=context.context_id,
            subtype=ThinkingEventSubtypeEnum.TASKS,
        )
        return self.__build_event(
            event_type=ThinkingEventTypeEnum.THINKING,
            subtype=ThinkingEventSubtypeEnum.TASKS,
            phase=ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION,
            task=_SETUP_TASK_LABEL,
            content=content,
            context=context,
            inference_time_ms=_NO_INFERENCE_TIME_MS,
        )

    async def __extract_planning_learnings(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Extrai os aprendizados pontuais do enunciado (A.4; A.3 no fluxo versão 1).

        São as anotações dos pontos que chamam a atenção na pergunta — valores com unidades,
        alternativas, fórmulas, condições. A fase enxerga só o enunciado, numa janela própria, e roda
        uma única vez, depois da aprovação do plano; o que ela extrai entra na memória antes de qualquer
        tarefa. Assim as alternativas e os dados fornecidos chegam ao contexto novo de todas as tarefas,
        mesmo àquelas cuja descrição não os repetiu. Como os demais aprendizados, chegam à área
        "Aprendizados Pontuais" de todo prompt das fases B e C.

        Yields:
            ThinkingEvent: Evento `learn`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.A4_PLANNING_LEARNINGS)
        outcome = await self.__execute_phase(
            runner=self.planning_learnings_phase, context=context, variables={"user_question": self.__user_question}
        )
        extracted = self.__to_learnings(parsed=outcome.parsed, task_id=None)
        learnings = self.learnings_memory.append(learnings=extracted)
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.LEARN,
            phase=ThinkingPhaseEnum.A4_PLANNING_LEARNINGS,
            task=_SETUP_TASK_LABEL,
            content=self.__render_learnings(
                extracted=extracted, stored=learnings, empty_content=_NO_PLANNING_LEARNINGS_CONTENT
            ),
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

        O evento `reset` marca o início da tarefa (*Fresh Context*) e anuncia a janela da primeira
        tentativa. Cada execução de fase da tarefa abre, além dela, a sua própria janela.

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
            subtype=ThinkingEventSubtypeEnum.RESET,
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
        async for event in self.__store_result(task=task):
            yield event
        async for event in self.__extract_learnings(task=task):
            yield event
        self.__active_task_id = None

    async def __resolve_task(self, task: Task, context: ContextWindow) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o ciclo de tentativas de B.1 e B.2 para uma tarefa.

        Cada execução de fase tem a sua janela: B.1 → B.2 e B.2 → B.1 são mudanças de fase. A nova
        tentativa de B.1 não restaura a conversa da anterior: as tentativas reprovadas e os vereditos
        do validador chegam como entrada explícita do Template B.1 (`previous_attempts`), montada a
        partir do registro da tarefa. Cada tentativa fica registrada em `task.attempts`, com as saídas
        inválidas que B.1 e B.2 tiveram de corrigir, porque é dali que B.4 recebe o histórico.

        Toda tentativa depois de uma reprovação é uma retentativa: B.1 é chamada com a temperatura de
        retentativa, e a verificação dessa tentativa volta à temperatura do usuário.

        A função só retorna quando a última tentativa foi aprovada. Se as tentativas se esgotam,
        a tarefa não é aprovada, nada é armazenado e a execução é interrompida.

        Args:
            task: Tarefa em execução.
            context: Janela nova da primeira tentativa, anunciada pelo evento `reset`.

        Yields:
            ThinkingEvent: Eventos `reasoning` e `verify_pass`/`verify_fail`.

        Raises:
            ExecutionInterruptedError: Quando as tentativas se esgotam sem aprovação.
        """
        while True:
            attempt = self.cost_guard.register_task_attempt(task_id=task.id)
            if attempt > _FIRST_ATTEMPT:
                context = self.__new_context(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, task_id=task.id)
            self.__resolution_context = context
            outcome = await self.__execute_phase(
                runner=self.task_resolution_phase,
                context=context,
                variables=self.__resolution_variables(task=task),
                validation=ValidationContext(review_target_ids=task.review.task_ids if task.review else None),
                is_retry=attempt > _FIRST_ATTEMPT,
            )
            preliminary = outcome.parsed["result"]
            conclusion = outcome.parsed["conclusion"]
            revision_verdicts = self.__to_verdicts(parsed=outcome.parsed)
            resolution_invalid_outputs = outcome.invalid_outputs
            yield await self.__record_and_build(
                subtype=ThinkingEventSubtypeEnum.REASONING,
                phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
                task=task.id,
                content=preliminary,
                context=context,
                outcome=outcome,
                task_id=task.id,
            )

            verification_context = self.__new_context(phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION, task_id=task.id)
            outcome = await self.__execute_phase(
                runner=self.task_verification_phase,
                context=verification_context,
                variables=self.__verification_variables(
                    task=task, preliminary=preliminary, revision_verdicts=revision_verdicts
                ),
                validation=ValidationContext(
                    expected_criteria_ids=tuple(criterion.id for criterion in task.verification_criteria())
                ),
            )
            report = self.__to_report(parsed=outcome.parsed)
            task.attempts.append(
                TaskAttempt(
                    number=attempt,
                    output=preliminary,
                    conclusion=conclusion,
                    report=report,
                    resolution_invalid_outputs=resolution_invalid_outputs,
                    verification_invalid_outputs=outcome.invalid_outputs,
                    revision_verdicts=revision_verdicts,
                )
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

    async def __store_result(self, task: Task) -> AsyncGenerator[ThinkingEvent, None]:
        """Armazena o resultado aprovado de uma tarefa (B.3), sem chamar o modelo.

        Só uma tarefa aprovada, cuja última tentativa tem relatório aprovado, tem resultado a
        armazenar; a própria tarefa garante isso ao entregá-lo. A etapa não abre janela: ela é
        registrada com a janela da tentativa aprovada, que produziu o resultado armazenado.

        É aqui, e só aqui, que uma revisão muda o estado vigente: os vereditos que B.2 aprovou junto
        com o resultado são aplicados pelo livro de resultados, de forma atômica; os aprendizados das
        tarefas que deixaram de ser vigentes saem da visão vigente da memória (sem serem apagados) e os
        das restauradas voltam. Uma revisora deixa um registro de auditoria na sessão.

        Args:
            task: Tarefa recém-aprovada.

        Yields:
            ThinkingEvent: Evento `store`, sempre com tempo de inferência zero.
        """
        self.__running_phase = ThinkingPhaseEnum.B3_RESULT_STORAGE
        context = self.__resolution_context
        change = self.results_ledger.store(result=task.approved_result())
        withdrawn = self.learnings_memory.withdraw(task_ids=change.withdrawn_task_ids)
        restored = self.learnings_memory.restore(task_ids=change.reinstated_task_ids)
        if task.review is not None:
            await self.session_recorder.record_result_revision(
                revision=self.__to_revision(
                    task=task, review=task.review, change=change, withdrawn=withdrawn, restored=restored
                )
            )
        content = self.__render_store(task_id=task.id, change=change, withdrawn=withdrawn, restored=restored)
        await self.session_recorder.record_programmatic_step(
            phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
            content=content,
            task_id=task.id,
            context_id=context.context_id,
            subtype=ThinkingEventSubtypeEnum.STORE,
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

    async def __extract_learnings(self, task: Task) -> AsyncGenerator[ThinkingEvent, None]:
        """Extrai os aprendizados pontuais de uma tarefa (B.4), numa janela de contexto própria.

        B.4 não herda a conversa de B.1: tudo o que a extração precisa chega como entrada explícita
        do template — a tarefa, o resultado aprovado (o mesmo que B.3 armazenou), o histórico de
        todas as tentativas com as interações com o validador e os aprendizados já registrados,
        para que a extração não repita o que a tarefa só usou. Um fato já registrado que a tarefa
        reestabeleceu de forma independente volta, copiado literalmente, para que a memória registre
        a tarefa como fonte adicional sem armazená-lo duas vezes; o evento mostra o que entrou e o que
        já constava na memória. Quando o resultado aguarda revalidação, os aprendizados ficam
        registrados, mas retidos fora da visão vigente.

        Args:
            task: Tarefa recém-aprovada.

        Yields:
            ThinkingEvent: Evento `learn`.
        """
        context = self.__new_context(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION, task_id=task.id)
        outcome = await self.__execute_phase(
            runner=self.learnings_extraction_phase, context=context, variables=self.__extraction_variables(task=task)
        )
        extracted = self.__to_learnings(parsed=outcome.parsed, task_id=task.id)
        learnings = self.learnings_memory.append(learnings=extracted)
        withheld = [learning for learning in extracted if learning.content.strip()]
        if self.results_ledger.status_of(task_id=task.id) is not ResultStatusEnum.CURRENT and withheld:
            content = f"{_WITHHELD_LEARNINGS_HEADING}\n\n{self.__render_items(learnings=withheld)}"
        else:
            content = self.__render_learnings(extracted=extracted, stored=learnings)
        yield await self.__record_and_build(
            subtype=ThinkingEventSubtypeEnum.LEARN,
            phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION,
            task=task.id,
            content=content,
            context=context,
            outcome=outcome,
            task_id=task.id,
        )

    async def __run_synthesis(self) -> AsyncGenerator[ThinkingEvent, None]:
        """Executa o loop de tarefas, C.1, C.2 (quando necessário) e C.3.

        C.3 só é alcançada com uma aprovação global em mãos. Enquanto C.1 reprova, o fluxo
        volta ao loop pela C.2; se C.2 não puder rodar, a execução é interrompida. Toda revisão
        aplicada no loop é seguida de uma nova C.1: a aprovação global vale só para os resultados
        vigentes que essa passagem avaliou, nunca para um conjunto anterior a uma revisão.

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
            evaluated_task_ids = self.results_ledger.current_task_ids()
            synthesis = self.__synthesis_variables(stored_results=self.__render_results())
            outcome = await self.__execute_phase(
                runner=self.global_verification_phase,
                context=context,
                variables={
                    **synthesis,
                    "result_revisions": self.__render_revision_record(for_planning=False),
                },
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
                    report=report,
                    stored_results=synthesis["stored_results"],
                    task_ids=evaluated_task_ids,
                    learnings=synthesis["learnings"],
                )
                continue

            verdict = self.cost_guard.authorize_additional_planning(
                reserved_output_tokens=self.__next_call_max_tokens(phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)
            )
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

        C.3 recebe os resultados vigentes e a área de aprendizados exatamente como a última C.1 os
        avaliou, guardados na aprovação; nada é renderizado de novo a partir do estado corrente. A
        conferência de fidelidade é uma instrução do próprio template C.3, na mesma chamada: não há
        fase nem verificador depois da síntese. A sessão só é concluída depois que a síntese válida
        foi produzida e persistida; o evento terminal é emitido por último.

        Args:
            approval: Aprovação global, de onde vêm os resultados e a memória que C.3 pode usar.

        Yields:
            ThinkingEvent: Evento `compile` de C.3 e o evento final `result`.

        Raises:
            ValueError: Quando os resultados vigentes mudaram depois da aprovação global.
        """
        self.__running_phase = ThinkingPhaseEnum.C3_FINAL_ANSWER
        approval.ensure_current(current_task_ids=self.results_ledger.current_task_ids())
        context = self.__new_context(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER)
        outcome = await self.__execute_phase(
            runner=self.final_answer_phase,
            context=context,
            variables={
                **self.__synthesis_variables(stored_results=approval.stored_results),
                "learnings": approval.learnings,
            },
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

        O diagnóstico de uma falha técnica precisa apontar a fase que realmente falhou e a janela em
        que ela rodava; cada execução de fase tem a sua janela.

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
            self.decomposition_validation_phase,
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
        phase = ThinkingPhaseEnum.B1_TASK_RESOLUTION
        verdict = self.cost_guard.authorize(
            phase=phase, reserved_output_tokens=self.__next_call_max_tokens(phase=phase)
        )
        if not verdict.authorized:
            raise ExecutionInterruptedError(
                limit=verdict.limit, phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION, detail=verdict.reason
            )

    def __next_call_max_tokens(self, phase: ThinkingPhaseEnum) -> int:
        """Teto de saída que a próxima chamada da fase pediria: o saldo da sessão, até o limite pedido.

        É a mesma conta das fases, para que a consulta antecipada ao guardião avalie a chamada
        que de fato seria feita.

        Args:
            phase: Fase que faria a próxima chamada.

        Returns:
            int: Tokens de saída que a chamada pediria.
        """
        return min(self.__session_token_limit, self.cost_guard.available_output_tokens(phase=phase))

    def __planning_limits(self) -> dict[str, str]:
        """Informa aos templates de planejamento quantas tarefas a sessão ainda comporta.

        Returns:
            dict[str, str]: Teto de tarefas do lote.
        """
        return {"max_tasks": str(self.cost_guard.remaining_task_slots())}

    def __planning_validation(self) -> ValidationContext:
        """Monta o contexto que o parser usa para validar um lote de tarefas planejado.

        Returns:
            ValidationContext: Teto de tarefas, identificadores já usados na sessão e os resultados
            que o lote pode revisar ou declarar como dependência.
        """
        return ValidationContext(
            max_tasks=self.cost_guard.remaining_task_slots(),
            known_task_ids=self.task_queue.known_task_ids(),
            reviewable_task_ids=self.results_ledger.reviewable_task_ids(),
            dependable_task_ids=frozenset(self.results_ledger.current_task_ids()),
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
            subtype=subtype,
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
            flow_version=session.flow_version or RalphFlowVersionEnum.current(),
        )

    def __resolution_variables(self, task: Task) -> dict[str, str]:
        """Monta as variáveis do Template B.1.

        Args:
            task: Tarefa a resolver.

        Returns:
            dict[str, str]: Descrição da tarefa (sem duplicar os critérios), o conjunto efetivo de
            critérios — planejados, técnico e, numa revisora, o de revisão — que B.2 avaliará, os
            resultados sob investigação (numa revisora), os aprendizados pontuais e o feedback das
            tentativas anteriores.
        """
        return {
            "task_description": self.__render_task_header(task=task),
            "task_acceptance_criteria": self.__render_criteria(criteria=task.verification_criteria()),
            "results_under_review": self.__render_results_under_review(task=task),
            "previous_attempts": self.__render_previous_attempts(task=task),
            **self.__learnings_variables(),
        }

    def __verification_variables(
        self, task: Task, preliminary: str, revision_verdicts: Sequence[RevisionVerdict]
    ) -> dict[str, str]:
        """Monta as variáveis do Template B.2.

        Args:
            task: Tarefa verificada.
            preliminary: Resultado preliminar produzido por B.1.
            revision_verdicts: Proposta de revisão de B.1, vazia numa tarefa normal.

        Returns:
            dict[str, str]: Cada entrada na sua área do template: a identificação, o título e a descrição
            da tarefa (o escopo, sem os critérios), o resultado preliminar, o conjunto efetivo de critérios
            (o mesmo que B.1 recebeu), a proposta explícita de revisão e os aprendizados pontuais. Nada da
            conversa de B.1 nem do planejamento é encaminhado.
        """
        return {
            "task_description": self.__render_task_header(task=task),
            "preliminary_result": preliminary,
            "task_acceptance_criteria": self.__render_criteria(criteria=task.verification_criteria()),
            "revision_proposal": self.__render_revision_proposal(task=task, revision_verdicts=revision_verdicts),
            **self.__learnings_variables(),
        }

    def __extraction_variables(self, task: Task) -> dict[str, str]:
        """Monta as variáveis do Template B.4.

        Args:
            task: Tarefa recém-aprovada.

        Returns:
            dict[str, str]: Tarefa (sem os critérios, que não são fatos do problema), resultado
            aprovado, histórico das tentativas e aprendizados pontuais já registrados, cada um na
            sua área do template.
        """
        return {
            "task_description": self.__render_task_header(task=task),
            "approved_result": self.results_ledger.get(task_id=task.id).content,
            "task_history": self.__render_history(task=task),
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
        enunciado (A.4) e os aprendizados de cada tarefa concluída (B.4) — e existe mesmo vazia.

        Returns:
            dict[str, str]: Aprendizados pontuais acumulados, já renderizados.
        """
        return {"learnings": self.learnings_memory.render()}

    def __planning_variables(self, report: VerificationReport) -> dict[str, str]:
        """Monta as variáveis do Template C.2.

        Args:
            report: Relatório de C.1 com os critérios gerais não atendidos.

        Returns:
            dict[str, str]: Prompt original, critérios pendentes, relatório de C.1 com os motivos
            das lacunas, resultados vigentes resumidos (enunciado e conclusão de cada tarefa), o
            registro de revisões (com as conclusões que aguardam revalidação, para que possam ser
            revisadas) e o número inicial das novas tarefas. O relatório é feedback diagnóstico,
            separado dos resultados.
        """
        unmet = tuple(
            criterion for criterion in self.__general_criteria if criterion.id in report.unmet_criteria_ids
        )
        return {
            "user_question": self.__user_question,
            "unmet_criteria": self.__render_criteria(criteria=unmet),
            "global_verification_feedback": self.__render_report(report=report),
            "stored_results": self.__render_result_summaries(),
            "result_revisions": self.__render_revision_record(for_planning=True),
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
                review=(
                    ReviewRequest(task_ids=tuple(task["review"]["task_ids"]), reason=task["review"]["reason"])
                    if task.get("review") is not None
                    else None
                ),
                depends_on=tuple(task.get("depends_on") or ()),
            )
            for task in parsed["tasks"]
        ]

    def __to_verdicts(self, parsed: dict[str, Any]) -> tuple[RevisionVerdict, ...]:
        """Converte a proposta de revisão de B.1 em vereditos do domínio.

        Args:
            parsed: Saída já validada de B.1; numa tarefa normal, sem proposta.

        Returns:
            tuple[RevisionVerdict, ...]: Um veredito por resultado sob investigação, ou nenhum.
        """
        return tuple(
            RevisionVerdict(
                task_id=verdict["task_id"],
                verdict=RevisionVerdictEnum(verdict["verdict"]),
                justification=verdict["justification"],
            )
            for verdict in parsed.get("revision") or ()
        )

    def __to_revision(
        self,
        task: Task,
        review: ReviewRequest,
        change: LedgerChange,
        withdrawn: Sequence[Learning],
        restored: Sequence[Learning],
    ) -> ResultRevision:
        """Monta o registro de auditoria de uma revisão aprovada e aplicada.

        Args:
            task: Tarefa revisora aprovada.
            review: Pedido de revisão planejado por C.2 para a tarefa.
            change: Mudança de estado aplicada pelo livro de resultados.
            withdrawn: Aprendizados que saíram da visão vigente.
            restored: Aprendizados que voltaram à visão vigente.

        Returns:
            ResultRevision: Quais resultados mudaram, por qual tarefa, por qual motivo aprovado e o
            estado vigente resultante.
        """
        result = self.results_ledger.get(task_id=task.id)
        return ResultRevision(
            revising_task_id=task.id,
            reason=review.reason,
            verdicts=result.revision_verdicts,
            approval_justification=task.revision_approval_justification() or "",
            suspended_task_ids=change.suspended_task_ids,
            reinstated_task_ids=change.reinstated_task_ids,
            withdrawn_learnings=tuple(learning.content for learning in withdrawn),
            restored_learnings=tuple(learning.content for learning in restored),
            current_task_ids=self.results_ledger.current_task_ids(),
            occurred_at=self.clock.now(),
        )

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

    def __to_plan_report(self, parsed: dict[str, Any]) -> PlanValidationReport:
        """Converte a saída de A.3 no relatório da validação da decomposição.

        Args:
            parsed: Saída já validada de A.3, com referências conferidas contra o candidato julgado.

        Returns:
            PlanValidationReport: Decisão booleana e problemas, exatamente como o modelo os relatou.
        """
        return PlanValidationReport(
            approved=parsed["approved"],
            issues=tuple(
                PlanValidationIssue(
                    task_id=issue["task_id"],
                    criterion_id=issue["criterion_id"],
                    problem=issue["problem"],
                    adjustment=issue["adjustment"],
                )
                for issue in parsed["issues"]
            ),
        )

    def __render_plan_report(self, report: PlanValidationReport) -> str:
        """Renderiza o relatório de A.3 como markdown, para o evento, a auditoria e a revisão de A.2.

        Args:
            report: Relatório da validação da decomposição.

        Returns:
            str: Decisão seguida de um item por problema, com o escopo, o defeito e o ajuste.
        """
        decision = _PLAN_DECISION_CONTENT.format(
            decision=_PLAN_APPROVED_LABEL if report.approved else _PLAN_REJECTED_LABEL
        )
        if report.approved:
            return f"{decision}{_BLOCK_SEPARATOR}{_PLAN_APPROVED_CONTENT}"
        issues = _ITEM_SEPARATOR.join(
            _PLAN_ISSUE_ITEM.format(scope=self.__render_issue_scope(issue=issue), problem=issue.problem,
                                    adjustment=issue.adjustment)
            for issue in report.issues
        )
        return f"{decision}{_BLOCK_SEPARATOR}{issues}"

    def __render_issue_scope(self, issue: PlanValidationIssue) -> str:
        """Renderiza o escopo de um problema: o plano inteiro, a tarefa ou o critério da tarefa.

        Args:
            issue: Problema apontado por A.3.

        Returns:
            str: Rótulo do escopo do problema.
        """
        if issue.task_id is None:
            return _PLAN_WIDE_SCOPE
        if issue.criterion_id is None:
            return _TASK_SCOPE.format(task_id=issue.task_id)
        return _CRITERION_SCOPE.format(task_id=issue.task_id, criterion_id=issue.criterion_id)

    def __to_learnings(self, parsed: dict[str, Any], task_id: str | None) -> list[Learning]:
        """Converte a saída de A.4 ou B.4 em aprendizados pontuais.

        Preserva cada texto sem interpretar seu domínio ou modificar associações e qualificações.
        A origem distingue dados do enunciado das conclusões das tarefas; não altera os resultados.

        Args:
            parsed: Saída já validada de A.4 ou B.4.
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

    def __render_task_header(self, task: Task) -> str:
        """Renderiza a identificação, o título e a descrição de uma tarefa, sem os critérios.

        Args:
            task: Tarefa a identificar.

        Returns:
            str: Cabeçalho `### <id> — <título>` seguido da descrição.
        """
        return _TASK_HEADER_CONTENT.format(task_id=task.id, title=task.title, description=task.description)

    def __render_task(self, task: Task) -> str:
        """Renderiza uma tarefa como bloco markdown.

        Args:
            task: Tarefa a renderizar.

        Returns:
            str: Bloco markdown com descrição, resultados revisados, dependências e critérios.
        """
        links = ""
        if task.review is not None:
            links += _TASK_REVIEW_CONTENT.format(
                ids=self.__render_ids(ids=task.review.task_ids), reason=task.review.reason
            )
        if task.depends_on:
            links += _TASK_DEPENDENCIES_CONTENT.format(ids=self.__render_ids(ids=task.depends_on))
        return _TASK_CONTENT.format(
            task_id=task.id,
            title=task.title,
            description=task.description,
            links=links,
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

    def __render_history(self, task: Task) -> str:
        """Renderiza o histórico da tarefa entregue a B.4: todas as tentativas, em ordem.

        Cada tentativa traz o resultado preliminar, as saídas inválidas que o validador corrigiu e o
        veredito. O resultado da tentativa aprovada não é repetido: ele tem área própria no template.

        Args:
            task: Tarefa recém-aprovada.

        Returns:
            str: Um bloco markdown por tentativa.
        """
        blocks = []
        for attempt, report in task.verified_attempts():
            parts = [
                _HISTORY_ATTEMPT_HEADER.format(
                    attempt=attempt.number,
                    status=_APPROVED_ATTEMPT_LABEL if report.approved else _REPROVED_ATTEMPT_LABEL,
                ),
                *(
                    _DISCARDED_RESOLUTION_CONTENT.format(
                        defect=invalid.defect.label, raw_output=invalid.raw_output, reason=invalid.reason
                    )
                    for invalid in attempt.resolution_invalid_outputs
                ),
                (
                    _HISTORY_APPROVED_OUTPUT_CONTENT
                    if report.approved
                    else _HISTORY_OUTPUT_CONTENT.format(output=attempt.output)
                ),
                *(
                    _INVALID_VERIFIER_OUTPUT_CONTENT.format(
                        defect=invalid.defect.label, raw_output=invalid.raw_output, reason=invalid.reason
                    )
                    for invalid in attempt.verification_invalid_outputs
                ),
                _HISTORY_REPORT_CONTENT.format(report=self.__render_report(report=report)),
            ]
            blocks.append(_BLOCK_SEPARATOR.join(parts))
        return _BLOCK_SEPARATOR.join(blocks)

    def __render_learnings(
        self,
        extracted: Sequence[Learning],
        stored: Sequence[Learning],
        empty_content: str = _NO_LEARNINGS_CONTENT,
    ) -> str:
        """Renderiza os aprendizados extraídos de uma tarefa ou do enunciado.

        Args:
            extracted: Aprendizados devolvidos pelo modelo.
            stored: Aprendizados que de fato entraram na memória.
            empty_content: Aviso exibido quando nada entrou na memória.

        Returns:
            str: Bloco markdown com os aprendizados acumulados (ou o aviso de que nada foi extraído),
            seguido, quando houver, dos que repetiam a memória e não foram armazenados de novo.
        """
        blocks = [
            f"{_LEARNINGS_HEADING}\n\n{self.__render_items(learnings=stored)}" if stored else empty_content
        ]
        # A memória devolve os aceitos na ordem recebida: o que não casa com o próximo aceito foi descartado.
        discarded: list[Learning] = []
        pending = iter(stored)
        next_stored = next(pending, None)
        for learning in extracted:
            if learning == next_stored:
                next_stored = next(pending, None)
            elif learning.content.strip():
                discarded.append(learning)
        if discarded:
            blocks.append(f"{_DISCARDED_LEARNINGS_HEADING}\n\n{self.__render_items(learnings=discarded)}")
        return _BLOCK_SEPARATOR.join(blocks)

    def __render_items(self, learnings: Sequence[Learning]) -> str:
        """Renderiza aprendizados como lista markdown.

        Args:
            learnings: Aprendizados a renderizar.

        Returns:
            str: Um item por aprendizado.
        """
        return _ITEM_SEPARATOR.join(f"- {learning.content.strip()}" for learning in learnings)

    def __render_previous_attempts(self, task: Task) -> str:
        """Renderiza o feedback que a nova tentativa de B.1 recebe como entrada explícita.

        Args:
            task: Tarefa em execução.

        Returns:
            str: As tentativas reprovadas, com resultado e veredito, delimitadas e seguidas da
            instrução de refazer; ou o aviso de que esta é a primeira tentativa.
        """
        if not task.attempts:
            return _NO_PREVIOUS_ATTEMPTS_CONTENT
        attempts = _BLOCK_SEPARATOR.join(
            _PREVIOUS_ATTEMPT_CONTENT.format(
                attempt=attempt.number,
                output=attempt.output,
                revision=(
                    _PREVIOUS_REVISION_CONTENT.format(
                        verdicts=self.__render_verdicts(verdicts=attempt.revision_verdicts)
                    )
                    if attempt.revision_verdicts
                    else ""
                ),
                report=self.__render_report(report=attempt.report),
            )
            for attempt in task.attempts
        )
        instruction = _RETRY_INSTRUCTION_CONTENT.format(
            unmet=self.__render_ids(ids=task.attempts[-1].report.unmet_criteria_ids)
        )
        return _PREVIOUS_ATTEMPTS_CONTENT.format(attempts=attempts, instruction=instruction)

    def __render_results(self) -> str:
        """Renderiza os resultados vigentes armazenados em B.3.

        Resultados substituídos ou aguardando revalidação não entram: não são fatos vigentes.

        Returns:
            str: Um bloco markdown por resultado vigente, na ordem de armazenamento.
        """
        return _BLOCK_SEPARATOR.join(
            _RESULT_BLOCK.format(task_id=result.task_id, title=result.task_title, content=result.content)
            for result in self.results_ledger.current()
        )

    def __render_result_summaries(self) -> str:
        """Renderiza os resultados armazenados em B.3 sem o raciocínio que levou a eles.

        É a visão que C.2 recebe: basta saber o que cada tarefa pedia e a que conclusão chegou para
        planejar só o que falta, sem herdar as resoluções completas.

        Returns:
            str: Um bloco markdown por resultado, com o enunciado e a conclusão da tarefa, na ordem
            de armazenamento.
        """
        return _BLOCK_SEPARATOR.join(
            _RESULT_SUMMARY_BLOCK.format(
                task_id=result.task_id,
                title=result.task_title,
                description=result.task_description,
                conclusion=result.conclusion,
            )
            for result in self.results_ledger.current()
        )

    def __render_results_under_review(self, task: Task) -> str:
        """Renderiza, para B.1, os resultados que a tarefa revisora investiga.

        Args:
            task: Tarefa em resolução.

        Returns:
            str: O motivo planejado e, para cada resultado investigado, o enunciado e a conclusão sob
            investigação; ou o aviso de que a tarefa não revisa resultados.
        """
        if task.review is None:
            return _NO_REVIEW_CONTENT
        blocks = [_REVIEW_REASON_CONTENT.format(reason=task.review.reason)]
        blocks.extend(self.__render_reviewed_result(task_id=task_id) for task_id in task.review.task_ids)
        return _BLOCK_SEPARATOR.join(blocks)

    def __render_revision_proposal(self, task: Task, revision_verdicts: Sequence[RevisionVerdict]) -> str:
        """Renderiza, para B.2, a proposta explícita de revisão que o critério de revisão avalia.

        Args:
            task: Tarefa verificada.
            revision_verdicts: Proposta de B.1, um veredito por resultado investigado.

        Returns:
            str: O motivo planejado e, para cada resultado investigado, o enunciado, a conclusão sob
            investigação, o veredito proposto e a sua justificativa; ou o aviso de que não há revisão.
        """
        if task.review is None:
            return _NO_REVIEW_CONTENT
        blocks = [_REVIEW_REASON_CONTENT.format(reason=task.review.reason)]
        for verdict in revision_verdicts:
            blocks.append(self.__render_reviewed_result(task_id=verdict.task_id))
            blocks.append(
                _PROPOSED_VERDICT_CONTENT.format(
                    task_id=verdict.task_id, verdict=verdict.verdict.value, justification=verdict.justification
                )
            )
        return _BLOCK_SEPARATOR.join(blocks)

    def __render_reviewed_result(self, task_id: str) -> str:
        """Renderiza o enunciado e a conclusão de um resultado sob investigação.

        Args:
            task_id: Tarefa cujo resultado é investigado.

        Returns:
            str: Bloco markdown do resultado investigado.
        """
        result = self.results_ledger.get(task_id=task_id)
        return _REVIEWED_RESULT_CONTENT.format(
            task_id=result.task_id, title=result.task_title, description=result.task_description,
            conclusion=result.conclusion,
        )

    def __render_verdicts(self, verdicts: Sequence[RevisionVerdict]) -> str:
        """Renderiza uma proposta de revisão como lista markdown.

        Args:
            verdicts: Vereditos propostos.

        Returns:
            str: Um item por veredito.
        """
        return _ITEM_SEPARATOR.join(
            _PREVIOUS_VERDICT_ITEM.format(
                task_id=verdict.task_id, verdict=verdict.verdict.value, justification=verdict.justification
            )
            for verdict in verdicts
        )

    def __render_revision_record(self, for_planning: bool) -> str:
        """Renderiza o registro de revisões entregue a C.1 e C.2: o que deixou de ser vigente e o que foi confirmado.

        Os resultados substituídos aparecem só como histórico, sem a conclusão antiga. Os confirmados por
        uma revisora vigente aparecem com o motivo aprovado: continuam vigentes por essa investigação. Os
        que aguardam revalidação aparecem com as dependências explícitas; só C.2 recebe também o enunciado
        e a conclusão deles, para poder planejar a revisão, rotulados como não vigentes.

        Args:
            for_planning: Indica que o registro vai para C.2.

        Returns:
            str: Seções de substituídos e de aguardando revalidação, ou o aviso de que não há nenhum.
        """
        blocks = []
        superseded = self.results_ledger.superseded()
        if superseded:
            items = [
                _SUPERSEDED_RECORD_ITEM.format(
                    task_id=result.task_id, title=result.task_title,
                    revising_task_id=self.results_ledger.superseded_by(task_id=result.task_id),
                    reason=self.__superseding_reason(task_id=result.task_id),
                )
                for result in superseded
            ]
            blocks.append(f"{_SUPERSEDED_RECORD_HEADING}\n\n{_ITEM_SEPARATOR.join(items)}")
        confirmed = self.__render_confirmations()
        if confirmed:
            blocks.append(f"{_CONFIRMED_RECORD_HEADING}\n\n{_ITEM_SEPARATOR.join(confirmed)}")
        awaiting = self.results_ledger.awaiting_revalidation()
        if awaiting:
            items = [
                _AWAITING_RECORD_ITEM.format(
                    task_id=result.task_id, title=result.task_title,
                    dependencies=self.__render_ids(ids=result.depends_on),
                )
                + (
                    _AWAITING_PLANNING_DETAIL.format(description=result.task_description, conclusion=result.conclusion)
                    if for_planning
                    else ""
                )
                for result in awaiting
            ]
            blocks.append(f"{_AWAITING_RECORD_HEADING}\n\n{_ITEM_SEPARATOR.join(items)}")
        return _BLOCK_SEPARATOR.join(blocks) or _NO_REVISIONS_CONTENT

    def __render_confirmations(self) -> list[str]:
        """Lista as confirmações aprovadas que ainda sustentam um resultado vigente.

        Só contam as confirmações feitas por uma revisora vigente cujo alvo continua vigente: uma
        confirmação cuja revisora ou cujo alvo deixou de ser vigente já aparece nas outras seções.

        Returns:
            list[str]: Um item por resultado confirmado, na ordem de armazenamento das revisoras.
        """
        return [
            _CONFIRMED_RECORD_ITEM.format(
                task_id=verdict.task_id, title=self.results_ledger.get(task_id=verdict.task_id).task_title,
                revising_task_id=revising.task_id, reason=verdict.justification,
            )
            for revising in self.results_ledger.current()
            for verdict in revising.revision_verdicts
            if verdict.verdict is RevisionVerdictEnum.CONFIRMED
            and self.results_ledger.status_of(task_id=verdict.task_id) is ResultStatusEnum.CURRENT
        ]

    def __superseding_reason(self, task_id: str) -> str:
        """Devolve a justificativa aprovada do veredito que substituiu o resultado.

        Args:
            task_id: Tarefa substituída.

        Returns:
            str: Justificativa do veredito `superseded` da tarefa revisora.
        """
        revising = self.results_ledger.get(task_id=self.results_ledger.superseded_by(task_id=task_id) or "")
        return next(verdict.justification for verdict in revising.revision_verdicts if verdict.task_id == task_id)

    def __render_store(
        self, task_id: str, change: LedgerChange, withdrawn: Sequence[Learning], restored: Sequence[Learning]
    ) -> str:
        """Renderiza o registro da etapa B.3, com as mudanças de estado que ela aplicou.

        Args:
            task_id: Tarefa armazenada.
            change: Mudança de estado aplicada pelo livro de resultados.
            withdrawn: Aprendizados que saíram da visão vigente.
            restored: Aprendizados que voltaram à visão vigente.

        Returns:
            str: Confirmação do armazenamento seguida de uma linha por mudança.
        """
        lines = [_STORE_CONTENT.format(task_id=task_id)]
        for label, ids in (
            (_SUPERSEDED_LABEL, change.superseded_task_ids),
            (_CONFIRMED_LABEL, change.confirmed_task_ids),
            (_SUSPENDED_LABEL, change.suspended_task_ids),
            (_REINSTATED_LABEL, change.reinstated_task_ids),
        ):
            if ids:
                lines.append(_STORE_CHANGE_CONTENT.format(label=label, ids=self.__render_ids(ids=ids)))
        if withdrawn:
            lines.append(_STORE_WITHDRAWN_CONTENT.format(count=len(withdrawn)))
        if restored:
            lines.append(_STORE_RESTORED_CONTENT.format(count=len(restored)))
        return _SENTENCE_SEPARATOR.join(lines)
