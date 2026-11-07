from src.domain.errors.ralph_error import RalphError


class ModelAlreadyRegisteredError(RalphError):
    """Levantado ao cadastrar um modelo cujo identificador já está no catálogo.

    Attributes:
        model_name: Identificador do modelo repetido.
    """

    def __init__(self, model_name: str) -> None:
        """Inicializa o erro.

        Args:
            model_name: Identificador do modelo repetido.
        """
        self.model_name = model_name
        super().__init__(f"Modelo '{model_name}' já está cadastrado.")
