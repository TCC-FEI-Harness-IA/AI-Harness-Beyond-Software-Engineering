from fastapi import FastAPI

from src.infra.routes.v1.router import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="TCC API",
        version="0.1.0",
    )

    app.include_router(router)

    return app


app = create_app()
