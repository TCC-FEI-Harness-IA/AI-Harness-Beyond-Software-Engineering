from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.errors.official_publication_not_found_error import OfficialPublicationNotFoundError
from src.infra.startups.public_benchmark_startup import PublicBenchmarkStartup

router = APIRouter(prefix="/public/benchmarks", tags=["public"])


@router.get("", responses={500: {"description": "Internal Server Error"}})
async def list_official_benchmarks() -> dict[str, list[dict[str, Any]]]:
    """Resultados oficiais vigentes (um por benchmark). Não exige login e não chama o modelo."""
    try:
        return {"publications": await PublicBenchmarkStartup().list_publications()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{publication_id}", responses={404: {"description": "Not Found"}})
async def get_official_benchmark(publication_id: str) -> dict[str, Any]:
    """Detalhe de uma publicação oficial."""
    try:
        return await PublicBenchmarkStartup().get_publication(publication_id)
    except (OfficialPublicationNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{publication_id}/sessions/{session_id}", responses={404: {"description": "Not Found"}})
async def get_official_benchmark_session(publication_id: str, session_id: str) -> dict[str, Any]:
    """Sessão filha de uma publicação oficial; uma sessão que não pertence a ela responde 404."""
    try:
        return await PublicBenchmarkStartup().get_session(publication_id, session_id)
    except (OfficialPublicationNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
