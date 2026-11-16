class EmailAlreadyRegisteredError(Exception):
    """Já existe uma conta com o e-mail normalizado."""

    def __init__(self) -> None:
        super().__init__("Não foi possível concluir o cadastro com este e-mail.")
