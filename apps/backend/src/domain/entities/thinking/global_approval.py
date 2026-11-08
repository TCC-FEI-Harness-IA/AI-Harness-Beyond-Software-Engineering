from dataclasses import dataclass

from src.domain.entities.thinking.verification_report import VerificationReport


@dataclass(frozen=True)
class GlobalApproval:
    """Aprovação global de C.1, vinculada ao conjunto de resultados e à memória que ela avaliou.

    É a condição de entrada de C.3: a síntese recebe exatamente os resultados vigentes e a área de
    aprendizados contidos aqui, como C.1 os viu. Um resultado acrescentado, substituído ou suspenso
    depois exige uma nova verificação global; a síntese não roda sobre uma aprovação desatualizada.

    Attributes:
        report: Relatório de C.1, necessariamente aprovado.
        stored_results: Resultados vigentes, renderizados como C.1 os avaliou.
        task_ids: Identificadores das tarefas cujos resultados foram avaliados.
        learnings: Área de aprendizados vigentes, renderizada como C.1 a recebeu.
    """

    report: VerificationReport
    stored_results: str
    task_ids: tuple[str, ...]
    learnings: str

    def __post_init__(self) -> None:
        """Garante que só um relatório aprovado vire aprovação global.

        Raises:
            ValueError: Quando o relatório não foi aprovado.
        """
        if not self.report.approved:
            raise ValueError("Uma aprovação global exige um relatório aprovado.")

    def ensure_current(self, current_task_ids: tuple[str, ...]) -> None:
        """Confirma que os resultados vigentes ainda são os que esta aprovação avaliou.

        Args:
            current_task_ids: Identificadores dos resultados vigentes no momento da síntese.

        Raises:
            ValueError: Quando o conjunto vigente mudou depois da aprovação.
        """
        if current_task_ids != self.task_ids:
            raise ValueError(
                "Os resultados vigentes mudaram depois da aprovação global; a síntese exige uma nova "
                f"verificação global. Aprovados: {list(self.task_ids)}; vigentes: {list(current_task_ids)}."
            )
