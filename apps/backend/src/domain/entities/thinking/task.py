from dataclasses import dataclass, field

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.harness_criteria import (
    revision_criterion,
    revision_criterion_id,
    technical_criterion,
    technical_criterion_id,
)
from src.domain.entities.thinking.review_request import ReviewRequest
from src.domain.entities.thinking.task_attempt import TaskAttempt
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.entities.thinking.verification_report import VerificationReport
from src.domain.enums.task_status_enum import TaskStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass
class Task:
    """Representa uma tarefa de objetivo único produzida por A.2 ou C.2.

    Attributes:
        id: Identificador único da tarefa.
        title: Título curto da tarefa.
        description: Descrição da responsabilidade única da tarefa.
        acceptance_criteria: Critérios de aceite de autoria do planejador (A.2 ou C.2). Os critérios que o
            harness acrescenta na verificação (`<id>-TECH` e, numa revisora, `<id>-REV`) não entram aqui.
        status: Estado atual da tarefa no loop de execução.
        origin_phase: Fase que originou a tarefa (A.2 ou C.2).
        attempts: Tentativas de resolução já realizadas para a tarefa.
        review: Resultados armazenados que a tarefa investiga, quando C.2 a planejou como revisora.
        depends_on: Tarefas cujos resultados o planejamento declarou como base desta tarefa.
    """

    id: str
    title: str
    description: str
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    origin_phase: ThinkingPhaseEnum = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
    attempts: list[TaskAttempt] = field(default_factory=list)
    review: ReviewRequest | None = None
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Recusa referências estruturadas que a tarefa não pode honrar.

        Raises:
            ValueError: Quando uma dependência se repete, está em branco, aponta a própria tarefa ou um
                resultado que ela revisa; quando a tarefa revisa a si mesma; ou quando um critério
                planejado usa o identificador reservado ao critério técnico (em qualquer tarefa) ou ao
                critério de revisão (numa revisora).
        """
        # Antes do retorno antecipado das tarefas comuns: o critério técnico é reservado em toda tarefa.
        reserved_technical = technical_criterion_id(self.id)
        if any(criterion.id == reserved_technical for criterion in self.acceptance_criteria):
            raise ValueError(f"O critério '{reserved_technical}' é reservado ao critério técnico do harness.")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"A tarefa '{self.id}' repete uma dependência.")
        if any(not task_id.strip() for task_id in self.depends_on):
            raise ValueError(f"A tarefa '{self.id}' declara uma dependência em branco.")
        if self.id in self.depends_on:
            raise ValueError(f"A tarefa '{self.id}' não pode depender de si mesma.")
        if self.review is None:
            return
        if self.id in self.review.task_ids:
            raise ValueError(f"A tarefa '{self.id}' não pode revisar a si mesma.")
        if set(self.depends_on) & set(self.review.task_ids):
            raise ValueError(f"A tarefa '{self.id}' não pode depender de um resultado que revisa.")
        if any(criterion.id == revision_criterion_id(self.id) for criterion in self.acceptance_criteria):
            raise ValueError(f"O critério '{revision_criterion_id(self.id)}' é reservado à revisão.")

    @property
    def technical_criterion(self) -> AcceptanceCriterion:
        """Critério técnico fixo com que B.2 avalia a validade da resolução desta tarefa.

        É acrescentado pelo harness a toda tarefa, comum ou revisora, de A.2 ou de C.2; o planejador não o
        cria, não o escolhe e não pode removê-lo.

        Returns:
            AcceptanceCriterion: Critério `<id>-TECH`.
        """
        return technical_criterion(self.id)

    @property
    def revision_criterion(self) -> AcceptanceCriterion | None:
        """Critério com que B.2 avalia explicitamente a proposta de revisão de uma tarefa revisora.

        Não substitui nem reescreve os critérios planejados: é acrescentado só na verificação, para que
        a aprovação da tarefa inclua um veredito explícito sobre a revisão proposta.

        Returns:
            AcceptanceCriterion | None: Critério `<id>-REV`, ou `None` numa tarefa normal.
        """
        if self.review is None:
            return None
        return revision_criterion(self.id)

    def harness_criteria(self) -> tuple[AcceptanceCriterion, ...]:
        """Critérios acrescentados pelo harness, sem autoria do planejador.

        Returns:
            tuple[AcceptanceCriterion, ...]: `<id>-TECH` e, numa tarefa revisora, `<id>-REV`, nessa ordem.
        """
        revision = self.revision_criterion
        return (self.technical_criterion,) if revision is None else (self.technical_criterion, revision)

    def verification_criteria(self) -> tuple[AcceptanceCriterion, ...]:
        """Conjunto efetivo de critérios que B.1 conhece e B.2 avalia, composto deterministicamente.

        É o mesmo conjunto em toda tentativa: os planejados, o critério técnico e, numa tarefa revisora, o
        critério de revisão, cada um uma única vez.

        Returns:
            tuple[AcceptanceCriterion, ...]: Critérios verificados, na ordem de avaliação.
        """
        return (*self.acceptance_criteria, *self.harness_criteria())

    def approved_result(self) -> TaskResult:
        """Devolve o resultado aprovado da tarefa, a única coisa que B.3 pode armazenar.

        Returns:
            TaskResult: Saída da última tentativa, cujo relatório de verificação foi aprovado, com as
            dependências declaradas e, numa tarefa revisora, os vereditos aprovados.

        Raises:
            ValueError: Quando a tarefa não foi aprovada, quando a última tentativa não tem
                relatório aprovado ou quando os vereditos não correspondem a um por resultado revisado.
        """
        if self.status is not TaskStatusEnum.APPROVED:
            raise ValueError(f"A tarefa '{self.id}' não foi aprovada; só um resultado aprovado pode ser armazenado.")

        last_attempt = self.attempts[-1] if self.attempts else None
        if last_attempt is None or last_attempt.report is None or not last_attempt.report.approved:
            raise ValueError(f"A tarefa '{self.id}' não tem um relatório aprovado na última tentativa.")

        reviewed = [verdict.task_id for verdict in last_attempt.revision_verdicts]
        expected = list(self.review.task_ids) if self.review is not None else []
        if sorted(reviewed) != sorted(expected):
            raise ValueError(f"A tarefa '{self.id}' não tem exatamente um veredito por resultado revisado.")

        return TaskResult(
            task_id=self.id,
            task_title=self.title,
            task_description=self.description,
            content=last_attempt.output,
            conclusion=last_attempt.conclusion,
            depends_on=self.depends_on,
            revision_verdicts=last_attempt.revision_verdicts,
        )

    def revision_approval_justification(self) -> str | None:
        """Justificativa com que B.2 aprovou o critério de revisão na última tentativa.

        Returns:
            str | None: Justificativa do critério `<id>-REV`, ou `None` quando não há esse veredito.
        """
        last_report = self.attempts[-1].report if self.attempts else None
        criterion_id = revision_criterion_id(self.id)
        for evaluation in last_report.evaluations if last_report is not None else ():
            if evaluation.criterion_id == criterion_id:
                return evaluation.justification
        return None

    def verified_attempts(self) -> tuple[tuple[TaskAttempt, VerificationReport], ...]:
        """Devolve as tentativas já verificadas, cada uma com o seu relatório: o histórico que B.4 recebe.

        Returns:
            tuple[tuple[TaskAttempt, VerificationReport], ...]: Tentativas com relatório, em ordem.
        """
        return tuple((attempt, attempt.report) for attempt in self.attempts if attempt.report is not None)
