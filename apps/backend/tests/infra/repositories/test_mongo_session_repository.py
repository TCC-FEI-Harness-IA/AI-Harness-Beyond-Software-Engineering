import logging
from datetime import UTC, datetime

from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.mongo_session_repository import MongoSessionRepository

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _nova_sessao(session_id: str = "sess_ab12") -> Session:
    sessao = Session(
        id=session_id,
        user_question="pergunta com acentuação",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        status=SessionStatusEnum.RUNNING,
        created_at=_CRIADO_EM,
        updated_at=_CRIADO_EM,
    )
    sessao.add_message(
        SessionMessage(
            id="msg-0",
            order=0,
            timestamp=_CRIADO_EM,
            phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
            source=MessageSourceEnum.USER,
            content="pergunta com acentuação",
            task_id=None,
            context_id=None,
            tokens_input=0,
            tokens_output=0,
            inference_time_ms=0,
            model_name=None,
        )
    )
    return sessao


def _build_repository() -> MongoSessionRepository:
    colecao = AsyncMongoMockClient()["banco_de_teste"]["sessoes_de_teste"]
    return MongoSessionRepository(
        collection=colecao,
        mapper=SessionDocumentMapper(),
        logger=logging.getLogger("teste"),
    )


async def test_save_seguido_de_find_by_id_devolve_sessao_equivalente() -> None:
    repositorio = _build_repository()
    sessao = _nova_sessao()

    await repositorio.save(session=sessao)

    assert await repositorio.find_by_id(session_id="sess_ab12") == sessao


async def test_save_duas_vezes_sobrescreve_sem_duplicar() -> None:
    repositorio = _build_repository()
    sessao = _nova_sessao()
    await repositorio.save(session=sessao)

    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")
    await repositorio.save(session=sessao)

    assert await repositorio.list_ids() == ["sess_ab12"]
    recuperada = await repositorio.find_by_id(session_id="sess_ab12")
    assert recuperada is not None
    assert recuperada.final_answer == "resposta final"


async def test_documento_gravado_e_o_produzido_pelo_mapper() -> None:
    repositorio = _build_repository()
    sessao = _nova_sessao()

    await repositorio.save(session=sessao)

    colecao = repositorio.collection
    gravado = await colecao.find_one({"_id": "sess_ab12"})
    assert gravado == SessionDocumentMapper().to_document(session=sessao)


async def test_find_by_id_de_sessao_inexistente_devolve_none() -> None:
    assert await _build_repository().find_by_id(session_id="sess_zzz") is None


async def test_list_ids_devolve_os_ids_em_ordem_alfabetica() -> None:
    repositorio = _build_repository()
    for session_id in ["sess_c", "sess_a", "sess_b"]:
        await repositorio.save(session=_nova_sessao(session_id=session_id))

    assert await repositorio.list_ids() == ["sess_a", "sess_b", "sess_c"]


async def test_list_ids_com_colecao_vazia_devolve_lista_vazia() -> None:
    assert await _build_repository().list_ids() == []


async def test_delete_de_sessao_existente_devolve_verdadeiro() -> None:
    repositorio = _build_repository()
    await repositorio.save(session=_nova_sessao())

    assert await repositorio.delete(session_id="sess_ab12") is True
    assert await repositorio.find_by_id(session_id="sess_ab12") is None


async def test_delete_de_sessao_inexistente_devolve_falso() -> None:
    assert await _build_repository().delete(session_id="sess_ab12") is False
