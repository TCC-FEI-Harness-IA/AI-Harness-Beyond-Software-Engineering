"""Consulta pública dos resultados oficiais: sem login, sem chamadas LLM e sem dados privados."""
import asyncio
import logging
from pathlib import Path
from itertools import count

import pytest
from fastapi.testclient import TestClient

from src.application.usecases.publish_official_results_usecase import PublishOfficialResultsUseCase
from src.application.usecases.select_official_batteries_usecase import SelectOfficialBatteriesUseCase
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.infra.repositories.official_publication_repository_factory import OfficialPublicationRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.config.settings import Settings
from src.infra.services import llm_service_factory
from src.main import create_app
from tests.doubles.controllable_clock import ControllableClock
from tests.doubles.publication_doubles import FakePublicationBackup, InMemoryBenchmarkSource, bateria_concluida
from tests.doubles.security_doubles import FakeIdentityProvider, build_security

V, M, G = BenchmarkDatasetEnum.VESTIBULAR, BenchmarkDatasetEnum.MMLU, BenchmarkDatasetEnum.GPQA


@pytest.fixture
def publicado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_OFFICIAL_STORAGE_PATH", str(tmp_path / "official"))
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    origem = InMemoryBenchmarkSource()
    for battery_id, dataset in [("bench_v", V), ("bench_m", M), ("bench_g", G)]:
        origem.add(*bateria_concluida(battery_id, dataset))
    contador = count(1)
    caso = PublishOfficialResultsUseCase(
        repository=OfficialPublicationRepositoryFactory(settings=Settings()).create(),
        backup=FakePublicationBackup(), clock=ControllableClock(), id_generator=lambda: f"pub_{next(contador)}",
        logger=logging.getLogger("teste"),
    )

    async def _publicar() -> None:
        relatorio = await SelectOfficialBatteriesUseCase(source=origem, logger=logging.getLogger("t")).execute()
        await caso.publish_initial(report=relatorio, published_by="admin@exemplo.com", apply=True)

    asyncio.run(_publicar())
    return {"origem": origem}


@pytest.fixture
def visitante() -> TestClient:
    seguranca = build_security()
    provider = seguranca.identity_provider
    assert isinstance(provider, FakeIdentityProvider)
    provider.unavailable = True  # a consulta pública não depende do serviço de autenticação
    return TestClient(create_app(security=seguranca))


def test_lista_as_tres_publicacoes_oficiais_sem_login(publicado: dict, visitante: TestClient) -> None:
    resposta = visitante.get("/v1/public/benchmarks")

    assert resposta.status_code == 200
    publicacoes = resposta.json()["publications"]
    assert [(item["id"], item["dataset"]) for item in publicacoes] == [
        ("pub_1", "vestibular"), ("pub_2", "mmlu"), ("pub_3", "gpqa"),
    ]
    assert publicacoes[0]["benchmark_session"]["id"] == "bench_v"
    assert publicacoes[0]["status"] == "active"
    assert resposta.headers["cache-control"] == "public, max-age=60"
    for privado in ("published_by", "source_label", "owner_id", "admin@exemplo.com"):
        assert privado not in resposta.text


def test_detalhe_e_sessao_filha_da_publicacao(publicado: dict, visitante: TestClient) -> None:
    detalhe = visitante.get("/v1/public/benchmarks/pub_2").json()
    sessao_id = detalhe["benchmark_session"]["session_ids"][0]

    sessao = visitante.get(f"/v1/public/benchmarks/pub_2/sessions/{sessao_id}")

    assert sessao.status_code == 200
    assert sessao.json()["id"] == sessao_id
    assert sessao.json()["user_question"] == "pergunta do usuario"
    assert "owner_id" not in sessao.json()


def test_sessao_de_outra_publicacao_ou_privada_nao_aparece_pelo_caminho_publico(
    publicado: dict, visitante: TestClient, tmp_path: Path
) -> None:
    da_mmlu = visitante.get("/v1/public/benchmarks/pub_2").json()["benchmark_session"]["session_ids"][0]
    privada = SessionRepositoryFactory(settings=Settings(), mapper=SessionDocumentMapper()).create(owner_id="usr_ana")
    asyncio.run(privada.save(bateria_concluida("bench_privada")[1][0]))

    assert visitante.get(f"/v1/public/benchmarks/pub_1/sessions/{da_mmlu}").status_code == 404
    assert visitante.get("/v1/public/benchmarks/pub_1/sessions/bench_privada_Q1_simple").status_code == 404
    assert visitante.get("/v1/public/benchmarks/pub_x").status_code == 404
    assert visitante.get("/v1/public/benchmarks/pub_x/sessions/x").status_code == 404
    assert visitante.get("/v1/public/benchmarks/pub_1/sessions/..%2Fx").status_code in (400, 404)
    assert visitante.get("/v1/sessions/bench_privada_Q1_simple").status_code == 503


def test_gpqa_publico_omite_textos_mas_mantem_a_estrutura(publicado: dict, visitante: TestClient) -> None:
    detalhe = visitante.get("/v1/public/benchmarks/pub_3").json()
    sessao_id = detalhe["benchmark_session"]["session_ids"][1]

    sessao = visitante.get(f"/v1/public/benchmarks/pub_3/sessions/{sessao_id}").json()

    assert sessao["user_question"].startswith("[conteúdo omitido")
    assert sessao["status"] == "completed"
    assert sessao["id"] == sessao_id
    assert detalhe["text_redacted"] is True
    assert visitante.get("/v1/public/benchmarks/pub_1").json()["text_redacted"] is False


def test_consulta_publica_nunca_chama_o_llm(
    publicado: dict, visitante: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _proibido(*_: object, **__: object) -> None:
        raise AssertionError("consulta pública não pode montar serviços de LLM")

    monkeypatch.setattr(llm_service_factory.LLMServiceFactory, "create_all", _proibido)

    for publicacao in visitante.get("/v1/public/benchmarks").json()["publications"]:
        for sessao_id in publicacao["benchmark_session"]["session_ids"]:
            assert visitante.get(f"/v1/public/benchmarks/{publicacao['id']}/sessions/{sessao_id}").status_code == 200


def test_falha_inesperada_vira_500(publicado: dict, visitante: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.infra.routes.v1.public import router as public_router_module

    class _Quebrado:
        def __init__(self) -> None:
            raise RuntimeError("disco fora do ar")

    monkeypatch.setattr(public_router_module, "PublicBenchmarkStartup", _Quebrado)

    assert visitante.get("/v1/public/benchmarks").status_code == 500
    assert visitante.get("/v1/public/benchmarks/pub_1").status_code == 500
    assert visitante.get("/v1/public/benchmarks/pub_1/sessions/x").status_code == 500


def test_sem_publicacoes_a_lista_e_vazia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, visitante: TestClient
) -> None:
    monkeypatch.setenv("RALPH_OFFICIAL_STORAGE_PATH", str(tmp_path / "vazio"))

    assert visitante.get("/v1/public/benchmarks").json() == {"publications": []}
