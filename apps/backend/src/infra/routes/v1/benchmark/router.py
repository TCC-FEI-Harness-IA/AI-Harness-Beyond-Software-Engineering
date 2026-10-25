from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from src.infra.config.settings import Settings
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO
from src.infra.routes.v1.benchmark.dtos.benchmark_run_input_dto import BenchmarkRunInputDTO
from src.infra.startups.benchmark_export_startup import BenchmarkExportStartup
from src.infra.startups.benchmark_query_startup import BenchmarkQueryStartup
from src.infra.startups.benchmark_run_startup import BenchmarkRunStartup

_ERROR_FRAME_TYPE = "error"
_COMPLETED_STATUS = "completed"
_CLOSE_NORMAL = 1000
_CLOSE_UNSUPPORTED_DATA = 1003
_CLOSE_MESSAGE_TOO_BIG = 1009
_CLOSE_INTERNAL_ERROR = 1011

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get(
    "/questions",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def describe_questions() -> dict[str, Any]:
    """Lista as questões do dataset, na ordem de execução, e o limite de paralelismo."""
    try:
        return BenchmarkQueryStartup().describe_dataset()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def list_benchmark_sessions() -> dict[str, list[dict[str, Any]]]:
    """Lista as baterias de benchmark persistidas, da mais recente para a mais antiga."""
    try:
        return {"benchmark_sessions": await BenchmarkQueryStartup().list_benchmark_session_documents()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{benchmark_session_id}",
    status_code=200,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_benchmark_session(benchmark_session_id: str) -> dict[str, Any]:
    """Consulta uma bateria de benchmark persistida pelo identificador."""
    try:
        return await BenchmarkQueryStartup().get_benchmark_session_document(benchmark_session_id=benchmark_session_id)
    except BenchmarkSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions/{benchmark_session_id}/ralph-loop-errors/export",
    status_code=200,
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP com uma pasta por questão errada no Ralph Loop"},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        409: {"description": "Bateria em execução ou sem erros do Ralph Loop para exportar"},
        500: {"description": "Internal Server Error"},
    },
)
async def export_ralph_loop_errors(benchmark_session_id: str) -> Response:
    """Baixa, em ZIP, as questões erradas no Ralph Loop de uma bateria encerrada."""
    try:
        archive = await BenchmarkExportStartup().export_ralph_errors(benchmark_session_id=benchmark_session_id)
    except BenchmarkSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (BenchmarkSessionNotFinishedError, NoBenchmarkErrorsToExportError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=archive.content,
        media_type=archive.media_type,
        headers={"Content-Disposition": f'attachment; filename="{archive.filename}"'},
    )


@router.websocket("/run")
async def run_benchmark(websocket: WebSocket) -> None:
    """Executa uma bateria de benchmark, emitindo o estado da bateria a cada mudança.

    Fecha com `1000` quando a bateria conclui e com `1011` quando ela falha. Se o cliente
    desconecta, a bateria é interrompida e as sessões em execução são encerradas como `failed`.
    """
    settings = Settings()
    logger = settings.logger(module_file=__file__)

    await websocket.accept()

    raw = await websocket.receive_text()
    if len(raw.encode("utf-8")) > settings.ralph_websocket_max_message_bytes:
        await websocket.close(code=_CLOSE_MESSAGE_TOO_BIG)
        return

    try:
        payload = BenchmarkRunInputDTO.model_validate_json(raw)
    except ValidationError as error:
        await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": str(error)})
        await websocket.close(code=_CLOSE_UNSUPPORTED_DATA)
        return

    generator: AsyncGenerator[BenchmarkFrameDTO, None] | None = None
    final_status: str | None = None
    try:
        generator = BenchmarkRunStartup().run(payload=payload)
        async for frame in generator:
            await websocket.send_json(frame.model_dump())
            final_status = frame.benchmark_session["status"]
        await websocket.close(code=_CLOSE_NORMAL if final_status == _COMPLETED_STATUS else _CLOSE_INTERNAL_ERROR)
    except InvalidBenchmarkRequestError as error:
        await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": str(error)})
        await websocket.close(code=_CLOSE_UNSUPPORTED_DATA)
    except WebSocketDisconnect:
        logger.info("Cliente desconectou durante a bateria de benchmark")
    except Exception as error:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": str(error)})
            await websocket.close(code=_CLOSE_INTERNAL_ERROR)
        logger.exception("Erro ao executar a bateria de benchmark")
    finally:
        if generator is not None:
            await generator.aclose()
