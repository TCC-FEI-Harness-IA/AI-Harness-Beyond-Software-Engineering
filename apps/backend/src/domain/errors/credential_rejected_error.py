class CredentialRejectedError(Exception):
    """A OpenRouter recusou a chave informada (ou ela nem tem formato de chave)."""

    def __init__(self) -> None:
        super().__init__("A OpenRouter recusou a chave informada.")
