"""Os diagnósticos de saída sobrevivem aos adapters existentes: JSON, MongoDB, consulta e exportação."""
import io
import json
import logging
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.repositories.mongo_session_repository import MongoSessionRepository
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkRalphErrorsArchiveBuilder
from src.main import create_app
from tests.doubles.benchmark_factories import desfecho, questao
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.output_diagnostic_factories import DIAGNOSTICO_Q037, RECUPERACAO, sessao_com_recusa_recuperada


def _repositorio_json(caminho: Path) -> JsonFileSessionRepository:
    return JsonFileSessionRepository(
        mapper=SessionDocumentMapper(),
        settings=FakeSettings(ralph_sessions_storage_path=str(caminho)),
        logger=logging.getLogger("teste"),
    )


async def test_repositorio_json_preserva_diagnosticos_e_recuperacao(tmp_path: Path) -> None:
    repositorio = _repositorio_json(tmp_path)
    sessao = sessao_com_recusa_recuperada()

    await repositorio.save(session=sessao)
    lida = await repositorio.find_by_id(session_id=sessao.id)

    assert lida is not None
    assert lida.invocations == sessao.invocations
    assert lida.invocations[0].output_diagnostic == DIAGNOSTICO_Q037
    assert lida.invocations[0].recovery == RECUPERACAO
    assert lida.invocations[1].recovers_invocation_id == "inv-1"
    assert lida.messages[0].invocation_id == "inv-1"
    assert lida.totals.total_llm_calls == 2


async def test_repositorio_json_le_sessao_antiga_sem_os_campos_novos(tmp_path: Path) -> None:
    repositorio = _repositorio_json(tmp_path)
    sessao = sessao_com_recusa_recuperada()
    await repositorio.save(session=sessao)
    arquivo = next(tmp_path.glob("*.json"))
    documento = json.loads(arquivo.read_text(encoding="utf-8"))
    for invocacao in documento["invocations"]:
        for chave in ("recovers_invocation_id", "content_accepted", "output_diagnostic", "recovery"):
            invocacao.pop(chave)
    for mensagem in documento["messages"]:
        mensagem.pop("invocation_id")
    arquivo.write_text(json.dumps(documento), encoding="utf-8")

    lida = await repositorio.find_by_id(session_id=sessao.id)

    assert lida is not None
    assert [invocacao.content_accepted for invocacao in lida.invocations] == [None, None]
    assert lida.rejected_output_count == 0
    assert lida.totals.total_llm_calls == 2


async def test_repositorio_mongo_preserva_diagnosticos_e_recuperacao() -> None:
    repositorio = MongoSessionRepository(
        collection=AsyncMongoMockClient()["banco"]["sessoes"],
        mapper=SessionDocumentMapper(),
        logger=logging.getLogger("teste"),
    )
    sessao = sessao_com_recusa_recuperada()

    await repositorio.save(session=sessao)
    lida = await repositorio.find_by_id(session_id=sessao.id)

    assert lida is not None
    assert lida.invocations == sessao.invocations
    assert lida.rejected_output_count == 1


async def test_consulta_da_sessao_devolve_os_diagnosticos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    caminho = tmp_path / "sessions"
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(caminho))
    sessao = sessao_com_recusa_recuperada()
    await _repositorio_json(caminho).save(session=sessao)

    resposta = TestClient(create_app()).get(f"/v1/sessions/{sessao.id}")

    assert resposta.status_code == 200
    invocacoes = resposta.json()["invocations"]
    assert invocacoes[0]["content_accepted"] is False
    assert invocacoes[0]["output_diagnostic"]["problem"]["code"] == "decision_consistency"
    assert invocacoes[0]["recovery"]["result"] == "recovered"
    assert invocacoes[1]["recovers_invocation_id"] == "inv-1"


def test_exportacao_dos_erros_do_benchmark_leva_os_diagnosticos() -> None:
    sessao = sessao_com_recusa_recuperada()
    erro = BenchmarkRalphError(
        question_id="Q037",
        expected_alternative="A",
        outcome=desfecho(mode=BenchmarkInferenceModeEnum.RALPH, correto=False, session_id=sessao.id),
        question=questao("Q037"),
        session=sessao,
    )

    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build("bench_1", [erro])

    with zipfile.ZipFile(io.BytesIO(arquivo.content)) as zip_:
        execucao = json.loads(zip_.read("questao-Q037/execucao-ralph-loop.json").decode("utf-8"))
    invocacoes = execucao["session"]["invocations"]
    assert invocacoes[0]["output_diagnostic"]["problem"]["affected_ids"] == ["T1-AC2"]
    assert invocacoes[0]["recovery"]["resolved_by_invocation_id"] == "inv-2"
    assert invocacoes[1]["output_diagnostic"]["syntax_status"] == "valid_after_repair"
