from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.ralph_error import RalphError


class PhaseParsingError(RalphError):
    """Levantado quando a saída do modelo não é JSON válido para a fase.

    Attributes:
        phase: Fase de thinking em que o parsing falhou.
        raw_output: Saída bruta devolvida pelo modelo.
        reason: Motivo da falha de parsing.
    """

    def __init__(self, phase: ThinkingPhaseEnum, raw_output: str, reason: str) -> None:
        """Inicializa o erro.

        Args:
            phase: Fase de thinking em que o parsing falhou.
            raw_output: Saída bruta devolvida pelo modelo.
            reason: Motivo da falha de parsing.
        """
        self.phase = phase
        self.raw_output = raw_output
        self.reason = reason
        super().__init__(f"Falha ao parsear a saída da fase '{phase.value}': {reason}")
