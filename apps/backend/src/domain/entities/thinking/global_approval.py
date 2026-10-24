from dataclasses import dataclass

from src.domain.entities.thinking.verification_report import VerificationReport


@dataclass(frozen=True)
class GlobalApproval:
    """Aprovação global de C.1, vinculada ao conjunto de resultados que ela avaliou.

    É a condição de entrada de C.3: a síntese só recebe o conjunto de resultados contido
    aqui, de modo que um resultado acrescentado depois exige uma nova verificação global.

    Attributes:
        report: Relatório de C.1, necessariamente aprovado.
        stored_results: Resultados aprovados, renderizados como C.1 os avaliou.
        task_ids: Identificadores das tarefas cujos resultados foram avaliados.
    """

    report: VerificationReport
    stored_results: str
    task_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Garante que só um relatório aprovado vire aprovação global.

        Raises:
            ValueError: Quando o relatório não foi aprovado.
        """
        if not self.report.approved:
            raise ValueError("Uma aprovação global exige um relatório aprovado.")
