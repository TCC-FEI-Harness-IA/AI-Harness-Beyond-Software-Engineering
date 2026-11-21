from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorCollection

from src.domain.errors.too_many_attempts_error import TooManyAttemptsError
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.login_attempt_limiter_interface import ILoginAttemptLimiter
from src.infra.repositories.datetime_utils import as_utc


class MongoLoginAttemptLimiter(ILoginAttemptLimiter):
    """Limite de tentativas em janela fixa, guardado no MongoDB.

    Por ficar no banco, o limite vale para todas as instâncias do serviço e sobrevive a reinícios.
    Cada chave (`email:...`, `ip:...`) tem um contador e o início da sua janela; um índice TTL
    remove contadores antigos.
    """

    def __init__(
        self, collection: AsyncIOMotorCollection, clock: IClock, max_attempts: int, window_seconds: int
    ) -> None:
        """Inicializa o limitador.

        Args:
            collection: Coleção dos contadores.
            clock: Fonte de tempo.
            max_attempts: Falhas permitidas por janela.
            window_seconds: Duração da janela.
        """
        self.collection = collection
        self.clock = clock
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)

    async def ensure_indexes(self) -> None:
        """Cria o índice TTL dos contadores (idempotente)."""
        await self.collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at")

    async def ensure_allowed(self, keys: list[str]) -> None:
        """Recusa quando alguma chave atingiu o limite dentro da janela vigente."""
        now = self.clock.now()
        async for document in self.collection.find({"_id": {"$in": keys}}):
            window_end = as_utc(document["window_started_at"]) + self.window
            if now < window_end and document["count"] >= self.max_attempts:
                raise TooManyAttemptsError(retry_after_seconds=int((window_end - now).total_seconds()))

    async def register_failure(self, keys: list[str]) -> None:
        """Soma uma falha a cada chave, abrindo uma nova janela quando a anterior terminou."""
        now = self.clock.now()
        for key in keys:
            document = await self.collection.find_one({"_id": key})
            if document is None or now >= as_utc(document["window_started_at"]) + self.window:
                await self.collection.replace_one(
                    {"_id": key},
                    {"_id": key, "count": 1, "window_started_at": now, "expires_at": now + self.window},
                    upsert=True,
                )
            else:
                await self.collection.update_one({"_id": key}, {"$inc": {"count": 1}})

    async def reset(self, key: str) -> None:
        """Remove o contador da chave."""
        await self.collection.delete_one({"_id": key})
