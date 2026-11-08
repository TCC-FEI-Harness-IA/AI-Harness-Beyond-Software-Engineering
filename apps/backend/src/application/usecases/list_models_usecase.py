import logging

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class ListModelsUseCase:
    """Lista os modelos cadastrados no catálogo, com as informações que ajudam a escolher entre eles."""

    def __init__(self, repository: IModelInfoRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório do catálogo de modelos.
            logger: Logger do módulo.
        """
        self.repository: IModelInfoRepository = repository
        self.logger = logger

    async def execute(self) -> list[ModelInfo]:
        """Devolve todos os modelos cadastrados.

        Returns:
            list[ModelInfo]: Modelos em ordem alfabética do identificador.
        """
        self.logger.info("Iniciando execução de ListModelsUseCase")

        return await self.repository.list_all()
