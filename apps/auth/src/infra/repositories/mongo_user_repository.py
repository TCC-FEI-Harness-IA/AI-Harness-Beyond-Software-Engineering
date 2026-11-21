import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from src.domain.entities.user import User
from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.interfaces.user_repository_interface import IUserRepository
from src.infra.repositories.datetime_utils import as_utc


class MongoUserRepository(IUserRepository):
    """Contas na coleção própria do serviço de autenticação, com índice único em `email`."""

    def __init__(self, collection: AsyncIOMotorCollection, logger: logging.Logger) -> None:
        """Inicializa o repositório.

        Args:
            collection: Coleção de usuários.
            logger: Logger do módulo.
        """
        self.collection = collection
        self.logger = logger

    async def ensure_indexes(self) -> None:
        """Cria o índice único do e-mail normalizado (idempotente)."""
        await self.collection.create_index("email", unique=True, name="uniq_email")

    async def insert(self, user: User) -> None:
        """Insere a conta; um e-mail repetido é recusado pelo índice único."""
        try:
            await self.collection.insert_one(self.__to_document(user))
        except DuplicateKeyError as exc:
            raise EmailAlreadyRegisteredError() from exc

    async def find_by_email(self, email: str) -> User | None:
        """Busca pelo e-mail normalizado."""
        return self.__from_optional(await self.collection.find_one({"email": email}))

    async def find_by_id(self, user_id: str) -> User | None:
        """Busca pelo identificador."""
        return self.__from_optional(await self.collection.find_one({"_id": user_id}))

    async def update(self, user: User) -> None:
        """Atualiza hash e perfil de uma conta existente."""
        await self.collection.update_one(
            {"_id": user.id}, {"$set": {"password_hash": user.password_hash, "role": user.role.value}}
        )

    @staticmethod
    def __to_document(user: User) -> dict[str, Any]:
        return {
            "_id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role.value,
            "created_at": user.created_at,
        }

    @staticmethod
    def __from_optional(document: dict[str, Any] | None) -> User | None:
        if document is None:
            return None
        return User(
            id=document["_id"],
            email=document["email"],
            password_hash=document["password_hash"],
            role=UserRoleEnum(document["role"]),
            created_at=as_utc(document["created_at"]),
        )
