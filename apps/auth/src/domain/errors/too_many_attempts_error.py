class TooManyAttemptsError(Exception):
    """Limite de tentativas excedido na janela configurada.

    Attributes:
        retry_after_seconds: Segundos até a janela atual terminar.
    """

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Muitas tentativas. Aguarde antes de tentar novamente.")
        self.retry_after_seconds = max(1, retry_after_seconds)
