from src.domain.errors.ralph_error import RalphError


class ModelNotFoundError(RalphError):
    """Levantado quando um modelo consultado não está cadastrado no catálogo.

    Attributes:
        model_name: Identificador do modelo procurado.
    """

    def __init__(self, model_name: str) -> None:
        """Inicializa o erro.

        Args:
            model_name: Identificador do modelo procurado.
        """
        self.model_name = model_name
        super().__init__(f"Modelo '{model_name}' não cadastrado.")
