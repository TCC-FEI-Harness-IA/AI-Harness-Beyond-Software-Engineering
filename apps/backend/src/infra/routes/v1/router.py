from fastapi import APIRouter

from src.infra.config.settings import Settings
from src.infra.routes.v1.benchmark.router import router as benchmark_router
from src.infra.routes.v1.message.router import router as message_router
from src.infra.routes.v1.session.router import router as session_router

router = APIRouter(prefix="/v1")

router.include_router(message_router)
router.include_router(session_router)
router.include_router(benchmark_router)


@router.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """Verifica se a aplicação está no ar."""
    return {"status": "ok"}


@router.get("/limits", status_code=200)
async def describe_limits() -> dict[str, int]:
    """Informa os limites do backend que o cliente precisa respeitar ao montar uma requisição.

    `max_tokens_limit` é o teto de tokens por sessão (`LLM_MAX_TOKENS`): o `max_tokens` pedido nunca
    pode passar dele.
    """
    return {"max_tokens_limit": Settings().llm_max_tokens}
