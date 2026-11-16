import logging
from dataclasses import asdict
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.llm.model_info import ModelInfo
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository
from src.infra.repositories.owner_scope import OWNER_KEY, scoped_key, validate_owner_id

_DOCUMENT_ID_KEY = "_id"
_MODEL_NAME_KEY = "model_name"


class MongoModelInfoRepository(IModelInfoRepository):
    """Catálogo de modelos apoiado em uma coleção do MongoDB.

    Sem proprietário, é o catálogo compartilhado (coleção `models`, `_id` igual ao modelo),
    mantido por administradores via script. Com proprietário, é o catálogo pessoal da conta
    (coleção `user_models`): `_id` é `<owner_id>/<modelo>` e o índice único `(owner_id, model_name)`
    garante, no banco, um cadastro por modelo por conta — dois usuários podem cadastrar o mesmo
    modelo sem interferência.
    """

    def __init__(self, collection: AsyncIOMotorCollection, logger: logging.Logger, owner_id: str | None = None) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção do MongoDB onde os modelos são gravados.
            logger: Logger do módulo.
            owner_id: Conta dona do catálogo pessoal; `None` para o catálogo compartilhado.

        Raises:
            ValueError: Quando o proprietário é inválido.
        """
        self.collection: AsyncIOMotorCollection = collection
        self.logger = logger
        self.owner_id = validate_owner_id(owner_id) if owner_id is not None else None

    async def ensure_indexes(self) -> None:
        """Cria o índice único `(owner_id, model_name)` do catálogo pessoal (idempotente)."""
        await self.collection.create_index(
            [(OWNER_KEY, 1), (_MODEL_NAME_KEY, 1)], unique=True, name="uniq_owner_model",
            partialFilterExpression={OWNER_KEY: {"$exists": True}},
        )

    async def list_all(self) -> list[ModelInfo]:
        """Lista os modelos deste catálogo.

        Returns:
            list[ModelInfo]: Modelos em ordem alfabética do identificador.
        """
        documents = await self.collection.find(self.__scope_filter()).to_list(length=None)
        models = [self.__from_document(document=document) for document in documents]
        return sorted(models, key=lambda item: item.model_name)

    async def find_by_name(self, model_name: str) -> ModelInfo | None:
        """Busca um modelo deste catálogo pelo identificador.

        Args:
            model_name: Identificador do modelo procurado.

        Returns:
            ModelInfo | None: Modelo encontrado, ou `None` quando não existe.
        """
        document = await self.collection.find_one({_DOCUMENT_ID_KEY: self.__key(model_name)})
        if document is None:
            return None
        return self.__from_document(document=document)

    async def save(self, model: ModelInfo) -> None:
        """Persiste (insere ou substitui) o modelo.

        Args:
            model: Modelo a ser persistido.
        """
        key = self.__key(model.model_name)
        document: dict[str, Any] = {_DOCUMENT_ID_KEY: key, **asdict(model)}
        if self.owner_id is not None:
            document[OWNER_KEY] = self.owner_id
        await self.collection.replace_one({_DOCUMENT_ID_KEY: key}, document, upsert=True)
        self.logger.info("Modelo '%s' persistido", model.model_name)

    async def delete(self, model_name: str) -> bool:
        """Remove um modelo deste catálogo.

        Args:
            model_name: Identificador do modelo a remover.

        Returns:
            bool: `True` quando o modelo existia e foi removido.
        """
        result = await self.collection.delete_one({_DOCUMENT_ID_KEY: self.__key(model_name)})
        return result.deleted_count > 0

    def __key(self, model_name: str) -> str:
        return model_name if self.owner_id is None else scoped_key(self.owner_id, model_name)

    def __scope_filter(self) -> dict[str, Any]:
        if self.owner_id is None:
            return {OWNER_KEY: {"$exists": False}}
        return {OWNER_KEY: self.owner_id}

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
