import json
import logging
from datetime import timedelta
from pathlib import Path

import pytest

from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.repositories.json_file_benchmark_session_repository import JsonFileBenchmarkSessionRepository
from tests.doubles.benchmark_factories import bateria
from tests.doubles.fake_settings import FakeSettings


def _repositorio(diretorio: Path) -> JsonFileBenchmarkSessionRepository:
    return JsonFileBenchmarkSessionRepository(
        mapper=BenchmarkSessionDocumentMapper(),
        settings=FakeSettings(ralph_benchmark_sessions_storage_path=str(diretorio)),
        logger=logging.getLogger("teste"),
    )


async def test_save_seguido_de_find_by_id_devolve_bateria_equivalente(tmp_path: Path) -> None:
    repositorio = _repositorio(tmp_path / "baterias")
    original = bateria("Q1", "Q2")

    await repositorio.save(benchmark_session=original)

    assert await repositorio.find_by_id(benchmark_session_id="bench_1") == original
    assert not list((tmp_path / "baterias").glob("*.tmp"))


async def test_bateria_inexistente_devolve_none(tmp_path: Path) -> None:
    assert await _repositorio(tmp_path).find_by_id(benchmark_session_id="bench_9") is None


async def test_listagem_ordena_da_mais_recente_e_ignora_outros_arquivos(tmp_path: Path) -> None:
    repositorio = _repositorio(tmp_path)
    antiga = bateria("Q1")
    recente = bateria("Q1")
    recente.id = "bench_2"
    recente.created_at = antiga.created_at + timedelta(days=1)
    await repositorio.save(benchmark_session=antiga)
    await repositorio.save(benchmark_session=recente)
    (tmp_path / "anotacao.txt").write_text("ignorado", encoding="utf-8")
    (tmp_path / "subpasta.json").mkdir()

    assert [item.id for item in await repositorio.list_all()] == ["bench_2", "bench_1"]


async def test_listagem_sem_diretorio_e_vazia(tmp_path: Path) -> None:
    assert await _repositorio(tmp_path / "inexistente").list_all() == []


@pytest.mark.parametrize("identificador", ["../fora", "bench 1", ""])
async def test_identificador_invalido_e_recusado(tmp_path: Path, identificador: str) -> None:
    with pytest.raises(ValueError, match="inválido"):
        await _repositorio(tmp_path).find_by_id(benchmark_session_id=identificador)


async def test_identificador_invalido_e_recusado_na_gravacao(tmp_path: Path) -> None:
    sessao = bateria("Q1")
    sessao.id = "../fora"

    with pytest.raises(ValueError, match="inválido"):
        await _repositorio(tmp_path).save(benchmark_session=sessao)


async def test_json_invalido_e_recusado(tmp_path: Path) -> None:
    (tmp_path / "bench_1.json").write_text("{não é json", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON inválido"):
        await _repositorio(tmp_path).find_by_id(benchmark_session_id="bench_1")


async def test_documento_gravado_e_o_do_mapper(tmp_path: Path) -> None:
    sessao = bateria("Q1")
    await _repositorio(tmp_path).save(benchmark_session=sessao)

    documento = json.loads((tmp_path / "bench_1.json").read_text(encoding="utf-8"))

    assert documento == BenchmarkSessionDocumentMapper().to_document(benchmark_session=sessao)
