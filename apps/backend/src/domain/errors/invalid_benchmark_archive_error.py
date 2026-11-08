from src.domain.errors.ralph_error import RalphError


class InvalidBenchmarkArchiveError(RalphError):
    """Levantado quando o arquivo enviado não é um ZIP de bateria de benchmark válido.

    Cobre ZIP corrompido ou grande demais, manifesto ausente ou de formato desconhecido e
    documentos inconsistentes entre si (questões, sessões e identificadores).
    """

    def __init__(self, reason: str) -> None:
        """Inicializa o erro.

        Args:
            reason: Motivo legível da recusa.
        """
        self.reason = reason
        super().__init__(f"Arquivo de bateria inválido: {reason}")
