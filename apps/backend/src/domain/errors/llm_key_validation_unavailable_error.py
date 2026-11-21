class LLMKeyValidationUnavailableError(Exception):
    """Não foi possível validar a chave agora (OpenRouter indisponível ou limitando)."""

    def __init__(self) -> None:
        super().__init__("Não foi possível validar a chave com a OpenRouter agora. Tente novamente.")
