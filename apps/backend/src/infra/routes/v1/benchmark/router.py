from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.benchmark_question_not_rerunnable_error import BenchmarkQuestionNotRerunnableError
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.benchmark_session_import_conflict_error import BenchmarkSessionImportConflictError
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.gpqa_subset_enum import GPQASubsetEnum
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from src.infra.config.settings import Settings
from src.infra.routes.v1.benchmark.dtos.benchmark_frame_dto import BenchmarkFrameDTO
from src.infra.routes.v1.benchmark.dtos.benchmark_alias_input_dto import BenchmarkAliasInputDTO
from src.infra.routes.v1.benchmark.dtos.benchmark_run_input_dto import BenchmarkRunInputDTO
from src.infra.routes.v1.benchmark.dtos.benchmark_rerun_input_dto import BenchmarkRerunInputDTO
from src.infra.security.request_security import current_identity, writer_identity
from src.infra.security.websocket_security import WebSocketExecution, open_websocket_execution
from src.infra.services.benchmark_session_archive_codec import MAX_ARCHIVE_BYTES
from src.infra.startups.benchmark_export_startup import BenchmarkExportStartup
from src.infra.startups.benchmark_query_startup import BenchmarkQueryStartup
from src.infra.startups.benchmark_alias_startup import BenchmarkAliasStartup
from src.infra.startups.benchmark_rerun_startup import BenchmarkRerunStartup
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
async def describe_questions(
    benchmark: BenchmarkDatasetEnum = BenchmarkDatasetEnum.VESTIBULAR,
    gpqa_subset: GPQASubsetEnum = GPQASubsetEnum.DIAMOND,
) -> dict[str, Any]:
    """Lista as questões do dataset, na ordem de execução, e o limite de paralelismo."""
    if benchmark is not BenchmarkDatasetEnum.GPQA and gpqa_subset is not GPQASubsetEnum.DIAMOND:
        raise HTTPException(status_code=422, detail="gpqa_subset é uma opção exclusiva do GPQA.")
    try:
        startup = BenchmarkQueryStartup()
        if benchmark is BenchmarkDatasetEnum.GPQA:
            return startup.describe_dataset(benchmark=benchmark, gpqa_subset=gpqa_subset)
        if benchmark is BenchmarkDatasetEnum.VESTIBULAR:
            return startup.describe_dataset()
        return startup.describe_dataset(benchmark=benchmark)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/sessions",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def list_benchmark_sessions(
    identity: AuthenticatedUser = Depends(current_identity),
) -> dict[str, list[dict[str, Any]]]:
    """Lista as baterias da conta autenticada, da mais recente para a mais antiga."""
    try:
        startup = BenchmarkQueryStartup(owner_id=identity.user_id)
        return {"benchmark_sessions": await startup.list_benchmark_session_documents()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/sessions/import",
    status_code=201,
    responses={
        201: {"description": "Bateria importada; devolve o documento dela"},
        400: {"description": "Arquivo vazio, inválido ou inconsistente"},
        409: {"description": "A bateria ou alguma das suas sessões já existe"},
        413: {"description": "Arquivo grande demais"},
        500: {"description": "Internal Server Error"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def import_benchmark_session(
    request: Request, identity: AuthenticatedUser = Depends(writer_identity)
) -> dict[str, Any]:
    """Importa uma bateria completa para a conta autenticada (corpo bruto `application/zip`).

    O dono é sempre a conta da sessão: campos de proprietário, perfil ou publicação oficial
    eventualmente presentes no arquivo são ignorados.
    """
    content = await _read_limited_body(request=request, limit=MAX_ARCHIVE_BYTES)
    if not content:
        raise HTTPException(status_code=400, detail="Envie o arquivo ZIP no corpo da requisição.")
    try:
        return await BenchmarkExportStartup(owner_id=identity.user_id).import_session(content=content)
    except InvalidBenchmarkArchiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BenchmarkSessionImportConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _read_limited_body(request: Request, limit: int) -> bytes:
    """Lê o corpo da requisição em partes, recusando com 413 o que passa do limite."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="O arquivo enviado excede o tamanho máximo permitido.")
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > limit:
            raise HTTPException(status_code=413, detail="O arquivo enviado excede o tamanho máximo permitido.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get(
    "/sessions/{benchmark_session_id}",
    status_code=200,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_benchmark_session(
    benchmark_session_id: str, identity: AuthenticatedUser = Depends(current_identity)
) -> dict[str, Any]:
    """Consulta uma bateria da conta autenticada; a de outra conta responde 404."""
    try:
        startup = BenchmarkQueryStartup(owner_id=identity.user_id)
        return await startup.get_benchmark_session_document(benchmark_session_id=benchmark_session_id)
    except BenchmarkSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put(
    "/sessions/{benchmark_session_id}/alias",
    responses={
        400: {"description": "Alias inválido"},
        404: {"description": "Bateria não encontrada"},
        409: {"description": "Bateria ainda em execução"},
        500: {"description": "Internal Server Error"},
    },
)
async def update_benchmark_alias(
    benchmark_session_id: str, payload: BenchmarkAliasInputDTO, identity: AuthenticatedUser = Depends(writer_identity)
) -> dict[str, Any]:
    """Define ou remove o alias de uma bateria encerrada da conta autenticada."""
    try:
        return await BenchmarkAliasStartup(owner_id=identity.user_id).update_alias(
            benchmark_session_id=benchmark_session_id, alias=payload.alias
        )
    except BenchmarkSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BenchmarkSessionNotFinishedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
async def export_ralph_loop_errors(
    benchmark_session_id: str, identity: AuthenticatedUser = Depends(current_identity)
) -> Response:
    """Baixa, em ZIP, as questões erradas no Ralph Loop de uma bateria encerrada da conta."""
    try:
        startup = BenchmarkExportStartup(owner_id=identity.user_id)
        archive = await startup.export_ralph_errors(benchmark_session_id=benchmark_session_id)
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


@router.get(
    "/sessions/{benchmark_session_id}/export",
    status_code=200,
    response_class=Response,
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP com a bateria completa"},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        409: {"description": "Bateria em execução"},
        500: {"description": "Internal Server Error"},
    },
)
async def export_benchmark_session(
    benchmark_session_id: str, identity: AuthenticatedUser = Depends(current_identity)
) -> Response:
    """Baixa a bateria encerrada completa da conta: bateria, enunciados, gabaritos e as duas execuções."""
    try:
        startup = BenchmarkExportStartup(owner_id=identity.user_id)
        archive = await startup.export_session(benchmark_session_id=benchmark_session_id)
    except BenchmarkSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BenchmarkSessionNotFinishedError as exc:
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
    execution = await open_websocket_execution(websocket)
    if execution is None:
        return
    try:
        await _run_benchmark(websocket, execution)
    finally:
        execution.release()


async def _run_benchmark(websocket: WebSocket, execution: WebSocketExecution) -> None:
    """Corpo da execução da bateria, já autorizada."""
    settings = Settings()
    logger = settings.logger(module_file=__file__)

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
        generator = BenchmarkRunStartup(owner_id=execution.owner_id, authorization=execution.authorization).run(
            payload=payload
        )
        frames = generator

        async def pump() -> None:
            nonlocal final_status
            async for frame in frames:
                await websocket.send_json(frame.model_dump())
                final_status = frame.benchmark_session["status"]

        if not await execution.run(pump()):
            await generator.aclose()
            logger.info("Bateria interrompida: a sessão de autenticação deixou de valer")
            await execution.close_revoked()
            return
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


@router.websocket("/sessions/{benchmark_session_id}/questions/{question_id}/rerun")
async def rerun_benchmark_question(websocket: WebSocket, benchmark_session_id: str, question_id: str) -> None:
    """Reexecuta uma questão sem frame de abertura, preservando o contrato individual."""
    await _stream_benchmark_rerun(websocket, benchmark_session_id, question_id)


@router.websocket("/sessions/{benchmark_session_id}/questions/rerun")
async def rerun_benchmark_questions(websocket: WebSocket, benchmark_session_id: str) -> None:
    """Recebe `question_ids` na abertura e reexecuta o lote no paralelismo da bateria."""
    await _stream_benchmark_rerun(websocket, benchmark_session_id)


async def _stream_benchmark_rerun(
    websocket: WebSocket, benchmark_session_id: str, question_id: str | None = None
) -> None:
    """Compartilha autorização, streaming, recusa de pedidos e cancelamento entre reexecução individual e em lote."""
    execution = await open_websocket_execution(websocket)
    if execution is None:
        return
    try:
        await _rerun(websocket, execution, benchmark_session_id, question_id)
    finally:
        execution.release()


async def _rerun(
    websocket: WebSocket, execution: WebSocketExecution, benchmark_session_id: str, question_id: str | None
) -> None:
    """Corpo da reexecução, já autorizada; só baterias da própria conta podem ser reexecutadas."""
    settings = Settings()
    logger = settings.logger(module_file=__file__)

    generator: AsyncGenerator[BenchmarkFrameDTO, None] | None = None
    try:
        startup = BenchmarkRerunStartup(owner_id=execution.owner_id, authorization=execution.authorization)
        if question_id is None:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > settings.ralph_websocket_max_message_bytes:
                await websocket.close(code=_CLOSE_MESSAGE_TOO_BIG)
                return
            payload = BenchmarkRerunInputDTO.model_validate_json(raw)
            generator = startup.run_many(benchmark_session_id=benchmark_session_id, question_ids=payload.question_ids)
        else:
            generator = startup.run(benchmark_session_id=benchmark_session_id, question_id=question_id)
        frames = generator

        async def pump() -> None:
            async for frame in frames:
                await websocket.send_json(frame.model_dump())

        if not await execution.run(pump()):
            await generator.aclose()
            logger.info("Reexecução interrompida: a sessão de autenticação deixou de valer")
            await execution.close_revoked()
            return
        await websocket.close(code=_CLOSE_NORMAL)
    except (
        BenchmarkSessionNotFoundError,
        BenchmarkSessionNotFinishedError,
        BenchmarkQuestionNotRerunnableError,
        InvalidBenchmarkRequestError,
        ValidationError,
    ) as error:
        await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": str(error)})
        await websocket.close(code=_CLOSE_UNSUPPORTED_DATA)
    except WebSocketDisconnect:
        logger.info("Cliente desconectou durante a reexecução da bateria '%s'", benchmark_session_id)
    except Exception as error:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": str(error)})
            await websocket.close(code=_CLOSE_INTERNAL_ERROR)
        logger.exception("Erro ao reexecutar questões da bateria '%s'", benchmark_session_id)
    finally:
        if generator is not None:
            await generator.aclose()
