from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infra.config.settings import Settings
from src.infra.routes.v1.router import router


def create_app() -> FastAPI:
    """Monta a aplicação FastAPI a partir das configurações de ambiente.

    Returns:
        FastAPI: Aplicação pronta para ser servida.
    """
    load_dotenv()
    settings = Settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
