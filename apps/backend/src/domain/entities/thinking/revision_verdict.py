from dataclasses import dataclass

from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum


@dataclass(frozen=True)
class RevisionVerdict:
    """Veredito de uma tarefa revisora sobre um resultado sob investigação, proposto em B.1.

    Attributes:
        task_id: Tarefa cujo resultado foi investigado.
        verdict: Confirmação ou substituição do resultado investigado.
        justification: Motivo do veredito, demonstrado pela investigação.
    """

    task_id: str
    verdict: RevisionVerdictEnum
    justification: str
