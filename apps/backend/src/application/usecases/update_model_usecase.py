import logging

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.errors.model_not_found_error import ModelNotFoundError
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class UpdateModelUseCase:
    """Atualiza as informações de um modelo já cadastrado."""

    def __init__(self, repository: IModelInfoRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório do catálogo de modelos.
            logger: Logger do módulo.
        """
        self.repository: IModelInfoRepository = repository
        self.logger = logger

    async def execute(self, model: ModelInfo) -> ModelInfo:
        """Substitui as informações do modelo de mesmo identificador.

        Args:
            model: Novas informações do modelo.

        Returns:
            ModelInfo: Modelo atualizado.

        Raises:
            ModelNotFoundError: Quando o modelo não está cadastrado.
        """
        self.logger.info("Iniciando execução de UpdateModelUseCase")

        if await self.repository.find_by_name(model_name=model.model_name) is None:
            raise ModelNotFoundError(model_name=model.model_name)

        await self.repository.save(model=model)
        return model
