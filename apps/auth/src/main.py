from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.password_hasher_interface import IPasswordHasher
from src.infra.adapters.argon2_password_hasher import Argon2PasswordHasher
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.settings import Settings
from src.infra.routes.auth_router import router as auth_router
from src.infra.routes.internal_router import router as internal_router
from src.infra.routes.http_security import NO_STORE
from src.infra.startups.auth_container import AuthContainer


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Retorna erros sem ecoar senhas, tokens ou o corpo recebido e impede seu cache."""
    errors = [{"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)}, headers=NO_STORE)


def create_app(
    mongo_client: AsyncIOMotorClient | None = None,
    clock: IClock | None = None,
    hasher: IPasswordHasher | None = None,
) -> FastAPI:
    """Monta o serviço de autenticação; a configuração inválida falha aqui, antes de servir.

    Args:
        mongo_client: Cliente MongoDB; por padrão, o real a partir de `AUTH_MONGODB_URI`.
        clock: Fonte de tempo; por padrão, o relógio do sistema.
        hasher: Hash de senhas; por padrão, Argon2id com os parâmetros configurados.

    Returns:
        FastAPI: Aplicação pronta para ser servida.
    """
    load_dotenv()
    settings = Settings()
    container = AuthContainer(
        settings=settings,
        mongo_client=mongo_client or AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True),
        clock=clock or ClockAdapter(),
        hasher=hasher
        or Argon2PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost_kib=settings.argon2_memory_cost_kib,
            parallelism=settings.argon2_parallelism,
        ),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await container.ensure_indexes()
        yield

    app = FastAPI(title="Ralph Auth", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.container = container
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(auth_router)
    app.include_router(internal_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
