from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.thinking.revision_verdict import RevisionVerdict
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum


@dataclass(frozen=True)
class ResultRevision:
    """Registro de auditoria de uma revisão aprovada em B.2 e aplicada em B.3.

    Os conteúdos antigos não são apagados: continuam nas mensagens da sessão. Este registro diz quais
    resultados deixaram de ser vigentes, por qual tarefa, por qual motivo aprovado e o que mudou na
    memória transversal.

    Attributes:
        revising_task_id: Tarefa revisora cuja execução foi aprovada.
        reason: Motivo da investigação planejado por C.2.
        verdicts: Vereditos aprovados, um por resultado investigado.
        approval_justification: Justificativa de B.2 para o critério de revisão.
        suspended_task_ids: Resultados que passaram a aguardar revalidação por dependência explícita.
        reinstated_task_ids: Resultados em revalidação que a revisão confirmou e voltaram a ser vigentes.
        withdrawn_learnings: Aprendizados que saíram da visão vigente por perderem toda fonte vigente.
        restored_learnings: Aprendizados que voltaram à visão vigente.
        current_task_ids: Resultados vigentes depois da revisão, na ordem de armazenamento.
        occurred_at: Instante da aplicação da revisão.
    """

    revising_task_id: str
    reason: str
    verdicts: tuple[RevisionVerdict, ...]
    approval_justification: str
    suspended_task_ids: tuple[str, ...]
    reinstated_task_ids: tuple[str, ...]
    withdrawn_learnings: tuple[str, ...]
    restored_learnings: tuple[str, ...]
    current_task_ids: tuple[str, ...]
    occurred_at: datetime

    def __post_init__(self) -> None:
        """Garante que só uma revisão com vereditos vire registro.

        Raises:
            ValueError: Quando não há nenhum veredito.
        """
        if not self.verdicts:
            raise ValueError("Uma revisão registrada precisa ter ao menos um veredito.")

    @property
    def superseded_task_ids(self) -> tuple[str, ...]:
        """Resultados substituídos pela revisão.

        Returns:
            tuple[str, ...]: Identificadores com veredito `superseded`, na ordem dos vereditos.
        """
        return self.__with(verdict=RevisionVerdictEnum.SUPERSEDED)

    @property
    def confirmed_task_ids(self) -> tuple[str, ...]:
        """Resultados confirmados pela revisão.

        Returns:
            tuple[str, ...]: Identificadores com veredito `confirmed`, na ordem dos vereditos.
        """
        return self.__with(verdict=RevisionVerdictEnum.CONFIRMED)

    def __with(self, verdict: RevisionVerdictEnum) -> tuple[str, ...]:
        """Filtra os alvos pelo veredito.

        Returns:
            tuple[str, ...]: Identificadores com o veredito informado.
        """
        return tuple(item.task_id for item in self.verdicts if item.verdict is verdict)
