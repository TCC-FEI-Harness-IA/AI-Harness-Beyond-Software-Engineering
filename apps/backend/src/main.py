from collections.abc import Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.security_settings import SecuritySettings
from src.infra.config.settings import Settings
from src.infra.routes.v1.router import router
from src.infra.security.security_services import SecurityServices

_PUBLIC_PREFIX = "/v1/public/"
_PUBLIC_CACHE = "public, max-age=60"
_PRIVATE_CACHE = "no-store, private"


async def _cache_policy(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Respostas públicas podem ser cacheadas; as privadas (dados pessoais, credenciais) nunca."""
    response = await call_next(request)
    if request.url.path.startswith(_PUBLIC_PREFIX):
        response.headers.setdefault("Cache-Control", _PUBLIC_CACHE)
    else:
        response.headers["Cache-Control"] = _PRIVATE_CACHE
        response.headers["Vary"] = ", ".join(filter(None, [response.headers.get("Vary"), "Cookie"]))
    return response


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 sem ecoar os valores recebidos (que podem conter segredos)."""
    errors = [{"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


def create_app(security: SecurityServices | None = None) -> FastAPI:
    """Monta a aplicação FastAPI a partir das configurações de ambiente.

    Em produção os serviços de segurança são sempre os reais; só os testes injetam `security`.
    Segredos ausentes ou inválidos fazem a criação falhar antes de servir qualquer requisição.

    Args:
        security: Serviços de segurança já montados (testes).

    Returns:
        FastAPI: Aplicação pronta para ser servida.
    """
    load_dotenv()
    settings = Settings()
    if security is None:
        security = SecurityServices.from_settings(
            settings=SecuritySettings.from_env(),
            clock=ClockAdapter(),
            logger=settings.logger(module_file=__file__),
        )

    app = FastAPI(title=settings.app_title, version=settings.app_version)
    app.state.security = security

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(_cache_policy)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(router)

    return app
