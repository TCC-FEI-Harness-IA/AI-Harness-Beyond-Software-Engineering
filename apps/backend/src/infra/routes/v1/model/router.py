from typing import Any

from fastapi import APIRouter, HTTPException, Response

from src.domain.errors.model_already_registered_error import ModelAlreadyRegisteredError
from src.domain.errors.model_not_found_error import ModelNotFoundError
from src.infra.routes.v1.model.dtos.model_info_dto import ModelInfoFieldsDTO, ModelInfoInputDTO
from src.infra.startups.model_catalog_startup import ModelCatalogStartup

router = APIRouter(prefix="/models", tags=["model"])

# Os identificadores têm barra (`vendor/modelo`), por isso o parâmetro usa o conversor `path`.
_MODEL_PATH = "/{model_name:path}"


@router.get(
    "",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def list_models() -> dict[str, list[dict[str, Any]]]:
    """Lista os modelos cadastrados com preço, contexto máximo e vazão."""
    try:
        startup = ModelCatalogStartup()
        return {"models": await startup.list_models()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "",
    status_code=201,
    responses={
        400: {"description": "Bad Request"},
        409: {"description": "Conflict"},
        500: {"description": "Internal Server Error"},
    },
)
async def register_model(payload: ModelInfoInputDTO) -> dict[str, Any]:
    """Cadastra um novo modelo no catálogo."""
    try:
        startup = ModelCatalogStartup()
        return await startup.register_model(payload=payload)
    except ModelAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put(
    _MODEL_PATH,
    status_code=200,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def update_model(model_name: str, payload: ModelInfoFieldsDTO) -> dict[str, Any]:
    """Atualiza as informações de um modelo cadastrado."""
    try:
        startup = ModelCatalogStartup()
        return await startup.update_model(model_name=model_name, payload=payload)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete(
    _MODEL_PATH,
    status_code=204,
    responses={
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def delete_model(model_name: str) -> Response:
    """Remove um modelo do catálogo."""
    try:
        startup = ModelCatalogStartup()
        await startup.delete_model(model_name=model_name)
        return Response(status_code=204)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
