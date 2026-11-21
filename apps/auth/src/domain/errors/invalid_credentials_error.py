class InvalidCredentialsError(Exception):
    """E-mail ou senha incorretos — a mensagem não revela qual dos dois."""

    def __init__(self) -> None:
        super().__init__("E-mail ou senha inválidos.")
