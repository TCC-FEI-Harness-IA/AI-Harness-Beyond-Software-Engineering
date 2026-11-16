import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.entities.auth_session import AuthSession
from src.domain.interfaces.auth_session_repository_interface import IAuthSessionRepository
from src.infra.repositories.datetime_utils import as_utc


class MongoAuthSessionRepository(IAuthSessionRepository):
    """Sessões de autenticação no MongoDB.

    Guarda apenas o SHA-256 do token (índice único). O índice TTL em `expires_at` deixa o próprio
    MongoDB apagar sessões vencidas; um registro apagado equivale a um token desconhecido, então a
    limpeza nunca reabre uma sessão revogada. As sessões sobrevivem a reinícios dos containers
    enquanto o volume do MongoDB existir.
    """

    def __init__(self, collection: AsyncIOMotorCollection, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção de sessões.
            logger: Logger do módulo.
        """
        self.collection = collection
        self.logger = logger

    async def ensure_indexes(self) -> None:
        """Cria os índices de busca do token e de expiração (idempotente)."""
        await self.collection.create_index("token_hash", unique=True, name="uniq_token_hash")
        await self.collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at")

    async def insert(self, session: AuthSession) -> None:
        """Insere a sessão."""
        await self.collection.insert_one(
            {
                "_id": session.id,
                "token_hash": session.token_hash,
                "user_id": session.user_id,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "csrf_token": session.csrf_token,
                "revoked_at": session.revoked_at,
            }
        )

    async def find_by_token_hash(self, token_hash: str) -> AuthSession | None:
        """Busca a sessão pelo resumo do token."""
        document = await self.collection.find_one({"token_hash": token_hash})
        return None if document is None else self.__from_document(document)

    async def revoke(self, token_hash: str, revoked_at: datetime) -> bool:
        """Revoga a sessão ativa do token; uma sessão já revogada não muda."""
        result = await self.collection.update_one(
            {"token_hash": token_hash, "revoked_at": None}, {"$set": {"revoked_at": revoked_at}}
        )
        return result.modified_count > 0

    @staticmethod
    def __from_document(document: dict[str, Any]) -> AuthSession:
        revoked_at = document.get("revoked_at")
        return AuthSession(
            id=document["_id"],
            token_hash=document["token_hash"],
            user_id=document["user_id"],
            created_at=as_utc(document["created_at"]),
            expires_at=as_utc(document["expires_at"]),
            csrf_token=document["csrf_token"],
            revoked_at=as_utc(revoked_at) if revoked_at is not None else None,
        )
