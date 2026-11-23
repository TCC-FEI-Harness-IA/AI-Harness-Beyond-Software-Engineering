import logging
from dataclasses import asdict
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository

_DOCUMENT_ID_KEY = "_id"
_MODEL_NAME_KEY = "model_name"


class MongoModelInfoRepository(IModelInfoRepository):
    """Catálogo de modelos apoiado em uma coleção do MongoDB.

    Cada documento é o `ModelInfo` serializado, com `_id` igual ao identificador do modelo — o
    que impede, no próprio banco, dois cadastros do mesmo modelo.
    """

    def __init__(self, collection: AsyncIOMotorCollection, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde os modelos são gravados.
            logger: Logger do módulo.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.logger = logger

    async def list_all(self) -> list[ModelInfo]:
        """Lista todos os modelos cadastrados.

        Returns:
            list[ModelInfo]: Modelos em ordem alfabética do identificador.
        """
        documents = await self.collection.find({}).sort(_DOCUMENT_ID_KEY, 1).to_list(length=None)
        return [self.__from_document(document=document) for document in documents]

    async def find_by_name(self, model_name: str) -> ModelInfo | None:
        """Busca um modelo pelo identificador.

        Args:
            model_name: Identificador do modelo procurado.

        Returns:
            ModelInfo | None: Modelo encontrado, ou `None` quando não existe.
        """
        document = await self.collection.find_one({_DOCUMENT_ID_KEY: model_name})
        if document is None:
            return None
        return self.__from_document(document=document)

    async def save(self, model: ModelInfo) -> None:
        """Persiste (insere ou substitui) o modelo.

        Args:
            model: Modelo a ser persistido.
        """
        document = {_DOCUMENT_ID_KEY: model.model_name, **asdict(model)}
        await self.collection.replace_one({_DOCUMENT_ID_KEY: model.model_name}, document, upsert=True)
        self.logger.info("Modelo '%s' persistido", model.model_name)

    async def delete(self, model_name: str) -> bool:
        """Remove um modelo cadastrado.

        Args:
            model_name: Identificador do modelo a remover.

        Returns:
            bool: `True` quando o modelo existia e foi removido.
        """
        result = await self.collection.delete_one({_DOCUMENT_ID_KEY: model_name})
        return result.deleted_count > 0

    def __from_document(self, document: dict[str, Any]) -> ModelInfo:
        """Reconstrói o `ModelInfo`, ignorando chaves que a entidade não conhece (como `_id`)."""
        return ModelInfo(
            model_name=document.get(_MODEL_NAME_KEY) or document[_DOCUMENT_ID_KEY],
            display_name=document.get("display_name"),
            input_price_per_million_tokens=document.get("input_price_per_million_tokens"),
            output_price_per_million_tokens=document.get("output_price_per_million_tokens"),
            context_length=document.get("context_length"),
            throughput_tokens_per_second=document.get("throughput_tokens_per_second"),
        )
