class SessionInvalidError(Exception):
    """Token ausente, desconhecido, revogado ou expirado."""

    def __init__(self) -> None:
        super().__init__("Sessão inválida ou expirada.")
