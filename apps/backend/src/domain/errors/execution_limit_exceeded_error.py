class ExecutionLimitExceededError(Exception):
    """A conta atingiu o limite de execuções simultâneas ou de inícios na janela.

    Attributes:
        retry_after_seconds: Sugestão de espera antes de tentar de novo.
    """

    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = max(1, retry_after_seconds)
