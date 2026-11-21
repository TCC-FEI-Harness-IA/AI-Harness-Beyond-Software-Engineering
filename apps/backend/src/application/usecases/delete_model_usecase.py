import logging

from src.domain.errors.model_not_found_error import ModelNotFoundError
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class DeleteModelUseCase:
    """Remove um modelo do catálogo."""

    def __init__(self, repository: IModelInfoRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório do catálogo de modelos.
            logger: Logger do módulo.
        """
        self.repository: IModelInfoRepository = repository
        self.logger = logger

    async def execute(self, model_name: str) -> None:
        """Remove o modelo informado.

        Args:
            model_name: Identificador do modelo a remover.

        Raises:
            ModelNotFoundError: Quando o modelo não está cadastrado.
        """
        self.logger.info("Iniciando execução de DeleteModelUseCase")

        if not await self.repository.delete(model_name=model_name):
            raise ModelNotFoundError(model_name=model_name)
