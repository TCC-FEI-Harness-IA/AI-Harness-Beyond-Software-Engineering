import logging

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.errors.model_already_registered_error import ModelAlreadyRegisteredError
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository


class RegisterModelUseCase:
    """Cadastra um novo modelo no catálogo."""

    def __init__(self, repository: IModelInfoRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório do catálogo de modelos.
            logger: Logger do módulo.
        """
        self.repository: IModelInfoRepository = repository
        self.logger = logger

    async def execute(self, model: ModelInfo) -> ModelInfo:
        """Cadastra o modelo, recusando um identificador que já existe.

        Args:
            model: Modelo a cadastrar.

        Returns:
            ModelInfo: Modelo cadastrado.

        Raises:
            ModelAlreadyRegisteredError: Quando já existe um modelo com o mesmo identificador.
        """
        self.logger.info("Iniciando execução de RegisterModelUseCase")

        if await self.repository.find_by_name(model_name=model.model_name) is not None:
            raise ModelAlreadyRegisteredError(model_name=model.model_name)

        await self.repository.save(model=model)
        return model
