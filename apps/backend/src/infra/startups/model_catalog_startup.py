from dataclasses import asdict
from inspect import getfile
from typing import Any

from src.application.usecases.delete_model_usecase import DeleteModelUseCase
from src.application.usecases.list_models_usecase import ListModelsUseCase
from src.application.usecases.register_model_usecase import RegisterModelUseCase
from src.application.usecases.update_model_usecase import UpdateModelUseCase
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.config.settings import Settings
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository
from src.infra.routes.v1.model.dtos.model_info_dto import ModelInfoFieldsDTO, ModelInfoInputDTO


class ModelCatalogStartup:
    """Composition root do catálogo de modelos (listagem, cadastro, edição e remoção)."""

    def __init__(self) -> None:
        """Instancia e injeta todas as dependências do catálogo de modelos."""
        self.settings: ISettings = Settings()
        self.logger = self.settings.logger(module_file=__file__)

        self.model_repository: IModelInfoRepository = MongoModelInfoRepository(
            collection=MongoClientAdapter(settings=self.settings).models_collection,
            logger=self.settings.logger(module_file=getfile(MongoModelInfoRepository)),
        )
        self.list_models_use_case = ListModelsUseCase(
            repository=self.model_repository,
            logger=self.settings.logger(module_file=getfile(ListModelsUseCase)),
        )
        self.register_model_use_case = RegisterModelUseCase(
            repository=self.model_repository,
            logger=self.settings.logger(module_file=getfile(RegisterModelUseCase)),
        )
        self.update_model_use_case = UpdateModelUseCase(
            repository=self.model_repository,
            logger=self.settings.logger(module_file=getfile(UpdateModelUseCase)),
        )
        self.delete_model_use_case = DeleteModelUseCase(
            repository=self.model_repository,
            logger=self.settings.logger(module_file=getfile(DeleteModelUseCase)),
        )
        self.logger.info("ModelCatalogStartup inicializado")

    async def list_models(self) -> list[dict[str, Any]]:
        """Lista os modelos cadastrados.

        Returns:
            list[dict[str, Any]]: Um documento por modelo, serializável em JSON.
        """
        self.logger.info("Listando os modelos cadastrados")

        models = await self.list_models_use_case.execute()
        return [asdict(model) for model in models]

    async def register_model(self, payload: ModelInfoInputDTO) -> dict[str, Any]:
        """Cadastra um novo modelo.

        Args:
            payload: Corpo da requisição no contrato de transporte.

        Returns:
            dict[str, Any]: Documento do modelo cadastrado.

        Raises:
            ModelAlreadyRegisteredError: Quando o modelo já está cadastrado.
            ValueError: Quando as informações são inválidas.
        """
        self.logger.info("Cadastrando o modelo '%s'", payload.model_name)

        model = await self.register_model_use_case.execute(model=payload.to_entity(model_name=payload.model_name))
        return asdict(model)

    async def update_model(self, model_name: str, payload: ModelInfoFieldsDTO) -> dict[str, Any]:
        """Atualiza as informações de um modelo cadastrado.

        Args:
            model_name: Identificador do modelo a atualizar.
            payload: Novas informações, no contrato de transporte.

        Returns:
            dict[str, Any]: Documento do modelo atualizado.

        Raises:
            ModelNotFoundError: Quando o modelo não está cadastrado.
            ValueError: Quando as informações são inválidas.
        """
        self.logger.info("Atualizando o modelo '%s'", model_name)

        model = await self.update_model_use_case.execute(model=payload.to_entity(model_name=model_name))
        return asdict(model)

    async def delete_model(self, model_name: str) -> None:
        """Remove um modelo cadastrado.

        Args:
            model_name: Identificador do modelo a remover.

        Raises:
            ModelNotFoundError: Quando o modelo não está cadastrado.
        """
        self.logger.info("Removendo o modelo '%s'", model_name)

        await self.delete_model_use_case.execute(model_name=model_name)
