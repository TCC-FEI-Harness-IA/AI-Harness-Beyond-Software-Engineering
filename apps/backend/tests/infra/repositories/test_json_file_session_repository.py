import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories import json_file_session_repository
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from tests.doubles.fake_settings import FakeSettings

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_IDS_INVALIDOS = ["../etc/passwd", "a/b", "", "a b", "sess.1", "sess$1"]


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


def _build_repository(storage_path: Path) -> JsonFileSessionRepository:
    return JsonFileSessionRepository(
        mapper=SessionDocumentMapper(),
        settings=FakeSettings(ralph_sessions_storage_path=str(storage_path)),
        logger=logging.getLogger("teste"),
    )


@pytest.fixture
def storage_path(tmp_path: Path) -> Path:
    """Diretório de sessões que ainda não existe, dentro do `tmp_path` do teste."""
    return tmp_path / "sessions"


async def test_save_cria_o_diretorio_e_o_arquivo_da_sessao(storage_path: Path) -> None:
    await _build_repository(storage_path=storage_path).save(session=_nova_sessao())

    assert (storage_path / "sess_ab12.json").is_file()


async def test_save_seguido_de_find_by_id_devolve_sessao_equivalente(storage_path: Path) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    sessao = _nova_sessao()

    await repositorio.save(session=sessao)

    assert await repositorio.find_by_id(session_id="sess_ab12") == sessao


async def test_save_duas_vezes_sobrescreve_sem_duplicar(storage_path: Path) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    sessao = _nova_sessao()
    await repositorio.save(session=sessao)

    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")
    await repositorio.save(session=sessao)

    assert len(list(storage_path.iterdir())) == 1
    recuperada = await repositorio.find_by_id(session_id="sess_ab12")
    assert recuperada is not None
    assert recuperada.final_answer == "resposta final"


async def test_save_nao_deixa_arquivo_temporario_remanescente(storage_path: Path) -> None:
    await _build_repository(storage_path=storage_path).save(session=_nova_sessao())

    assert list(storage_path.glob("*.tmp")) == []


async def test_arquivo_gravado_e_utf8_legivel_e_indentado(storage_path: Path) -> None:
    await _build_repository(storage_path=storage_path).save(session=_nova_sessao())

    conteudo = (storage_path / "sess_ab12.json").read_text(encoding="utf-8")
    assert "pergunta com acentuação" in conteudo
    assert '\n  "id": "sess_ab12"' in conteudo


async def test_find_by_id_de_sessao_inexistente_devolve_none(storage_path: Path) -> None:
    assert await _build_repository(storage_path=storage_path).find_by_id(session_id="sess_zzz") is None


async def test_find_by_id_de_arquivo_com_json_invalido_e_recusado(storage_path: Path) -> None:
    storage_path.mkdir(parents=True)
    (storage_path / "sess_ab12.json").write_text("{invalido", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON inválido"):
        await _build_repository(storage_path=storage_path).find_by_id(session_id="sess_ab12")


async def test_list_ids_devolve_os_ids_em_ordem_alfabetica(storage_path: Path) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    for session_id in ["sess_c", "sess_a", "sess_b"]:
        await repositorio.save(session=_nova_sessao(session_id=session_id))

    assert await repositorio.list_ids() == ["sess_a", "sess_b", "sess_c"]


async def test_list_ids_ignora_temporarios_e_arquivos_de_outra_extensao(storage_path: Path) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    await repositorio.save(session=_nova_sessao(session_id="sess_a"))
    (storage_path / "sess_b.json.tmp").write_text("{}", encoding="utf-8")
    (storage_path / "anotacoes.txt").write_text("nada", encoding="utf-8")
    (storage_path / "subpasta").mkdir()

    assert await repositorio.list_ids() == ["sess_a"]


async def test_list_ids_com_diretorio_inexistente_devolve_lista_vazia(storage_path: Path) -> None:
    assert await _build_repository(storage_path=storage_path).list_ids() == []


async def test_delete_de_sessao_existente_devolve_verdadeiro(storage_path: Path) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    await repositorio.save(session=_nova_sessao())

    assert await repositorio.delete(session_id="sess_ab12") is True
    assert await repositorio.find_by_id(session_id="sess_ab12") is None


async def test_delete_de_sessao_inexistente_devolve_falso(storage_path: Path) -> None:
    assert await _build_repository(storage_path=storage_path).delete(session_id="sess_ab12") is False


@pytest.mark.parametrize("session_id", _IDS_INVALIDOS)
async def test_save_recusa_identificador_invalido(storage_path: Path, session_id: str) -> None:
    with pytest.raises(ValueError, match="Identificador de sessão inválido"):
        await _build_repository(storage_path=storage_path).save(session=_nova_sessao(session_id=session_id))

    assert not storage_path.exists()


@pytest.mark.parametrize("session_id", _IDS_INVALIDOS)
async def test_find_by_id_recusa_identificador_invalido(storage_path: Path, session_id: str) -> None:
    with pytest.raises(ValueError, match="Identificador de sessão inválido"):
        await _build_repository(storage_path=storage_path).find_by_id(session_id=session_id)


@pytest.mark.parametrize("session_id", _IDS_INVALIDOS)
async def test_delete_recusa_identificador_invalido(storage_path: Path, session_id: str) -> None:
    with pytest.raises(ValueError, match="Identificador de sessão inválido"):
        await _build_repository(storage_path=storage_path).delete(session_id=session_id)


async def test_documento_gravado_e_o_produzido_pelo_mapper(storage_path: Path) -> None:
    sessao = _nova_sessao()
    await _build_repository(storage_path=storage_path).save(session=sessao)

    gravado = json.loads((storage_path / "sess_ab12.json").read_text(encoding="utf-8"))
    assert gravado == SessionDocumentMapper().to_document(session=sessao)


async def test_save_interrompido_nao_corrompe_o_documento_anterior(
    storage_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositorio = _build_repository(storage_path=storage_path)
    sessao = _nova_sessao()
    await repositorio.save(session=sessao)
    documento_anterior = SessionDocumentMapper().to_document(session=sessao)

    def _promocao_interrompida(origem: object, destino: object) -> None:
        raise OSError("processo interrompido antes de promover o arquivo temporário")

    monkeypatch.setattr(json_file_session_repository.os, "replace", _promocao_interrompida)
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    with pytest.raises(OSError, match="processo interrompido"):
        await repositorio.save(session=sessao)

    monkeypatch.undo()
    assert json.loads((storage_path / "sess_ab12.json").read_text(encoding="utf-8")) == documento_anterior
