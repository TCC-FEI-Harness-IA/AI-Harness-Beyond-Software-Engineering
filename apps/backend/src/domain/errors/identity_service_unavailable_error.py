class IdentityServiceUnavailableError(Exception):
    """O serviço de autenticação não respondeu de forma válida; operações privadas falham fechadas."""

    def __init__(self) -> None:
        super().__init__("Serviço de autenticação indisponível.")
