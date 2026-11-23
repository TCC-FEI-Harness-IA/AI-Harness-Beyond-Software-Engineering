"""Histórico e pacotes com o critério técnico (nova fase de validação — 02).

Uma sessão nova grava os relatórios de B.2 com `<task_id>-TECH`; uma sessão antiga, sem versão do fluxo e
sem TECH, continua legível sem ser reescrita; a inferência direta segue sem versão. Leitura, consulta,
exportação e importação não passam pelo parser: nenhuma completion antiga é revalidada retroativamente.
"""
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import pytest

from src.domain.entities.benchmark.benchmark_session_bundle import BenchmarkSessionBundle, BenchmarkSessionBundleItem
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.ralph_flow_version_enum import RalphFlowVersionEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum as Sub
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.services.benchmark_session_archive_codec import BenchmarkSessionArchiveCodec
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    aprendizados,
    aprovado,
    criterios,
    global_aprovado,
    plano_aprovado,
    reprovado_tecnico,
    resolucao,
    resposta_final,
    tarefas,
)

_EM = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
_FEEDBACK = "A premissa decisiva nao foi fornecida."
_RELATORIO_ANTIGO = "**Decision:** `approved`\n\n- `T1-AC1` — met: atende"


@pytest.fixture
def proibir_parser(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    """Depois de gerar as sessões, faz falhar qualquer tentativa de revalidar uma completion pelo parser."""
    def proibido(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("O histórico não deve ser revalidado pelo parser.")

    return lambda: monkeypatch.setattr(StructuredResponseParserAdapter, "parse_output", proibido)


async def _sessao_nova() -> Session:
    cenario = RalphScenario(responses=[
        criterios(), tarefas("T1"), plano_aprovado(), anotacoes_do_enunciado(),
        resolucao("primeira"), reprovado_tecnico("T1", _FEEDBACK), resolucao("segunda"), aprovado("T1"),
        aprendizados("fato"), global_aprovado(), resposta_final(),
    ])
    await cenario.run()
    return cenario.session


def _mensagem(order: int, phase: Phase, content: str) -> SessionMessage:
    return SessionMessage(
        id=f"msg-{order}", order=order, timestamp=_EM, phase=phase, source=MessageSourceEnum.LLM_AGENT,
        content=content, task_id="T1" if phase.value.startswith("B") else None, context_id=f"ctx-{order}",
        tokens_input=3, tokens_output=2, inference_time_ms=5, model_name="m",
    )


def _documento_antigo() -> dict[str, Any]:
    """Sessão Ralph gravada antes da versão do fluxo e do critério técnico: B.2 avaliou só `T1-AC1`."""
    sessao = Session(
        id="ralph_antiga", user_question="q", flow=Phase.A1_GENERAL_CRITERIA, model_name="m", max_tokens=100,
        temperature=0.3, status=SessionStatusEnum.RUNNING, created_at=_EM, updated_at=_EM,
    )
    for ordem, (fase, conteudo) in enumerate([
        (Phase.A2_TASK_DECOMPOSITION, "## Planned tasks\n\n### T1 — X\n\n**Acceptance criteria:**\n- `T1-AC1`: c"),
        (Phase.A3_DECOMPOSITION_VALIDATION, "## Extracted learnings\n\n- Dado."),
        (Phase.B1_TASK_RESOLUTION, "resolucao"),
        (Phase.B2_TASK_VERIFICATION, _RELATORIO_ANTIGO),
    ]):
        sessao.add_message(_mensagem(ordem, fase, conteudo))
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="D")
    documento = SessionDocumentMapper().to_document(session=sessao)
    del documento["flow_version"]
    for mensagem in documento["messages"]:
        del mensagem["subtype"]
    return documento


def _sessao_direta() -> Session:
    sessao = Session(
        id="direta", user_question="q", flow=Phase.DIRECT_INFERENCE, model_name="m", max_tokens=100,
        temperature=0.3, status=SessionStatusEnum.RUNNING, created_at=_EM, updated_at=_EM,
    )
    sessao.add_message(_mensagem(0, Phase.DIRECT_INFERENCE, "D"))
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="D")
    return sessao


def _repositorio(caminho: Path) -> JsonFileSessionRepository:
    return JsonFileSessionRepository(
        mapper=SessionDocumentMapper(), settings=FakeSettings(ralph_sessions_storage_path=str(caminho)),
        logger=logging.getLogger("teste.tech.historico"),
    )


async def test_sessao_nova_grava_tech_nos_relatorios_e_o_round_trip_preserva_tudo(
    tmp_path: Path, proibir_parser: Callable[[], None],
) -> None:
    nova = await _sessao_nova()
    proibir_parser()
    repositorio = _repositorio(tmp_path)

    await repositorio.save(session=nova)
    lida = await repositorio.find_by_id(session_id=nova.id)

    assert lida is not None and lida.flow_version is RalphFlowVersionEnum.VALIDATED_PLANNING
    gravado = json.loads((tmp_path / f"{nova.id}.json").read_text(encoding="utf-8"))
    assert SessionDocumentMapper().to_document(session=lida) == gravado
    b2 = [(m.subtype, m.content) for m in lida.messages if m.phase is Phase.B2_TASK_VERIFICATION]
    assert [subtipo for subtipo, _ in b2] == [Sub.VERIFY_FAIL, Sub.VERIFY_PASS]
    assert f"- `T1-TECH` — not met: {_FEEDBACK}" in b2[0][1]
    assert "- `T1-TECH` — met: atende" in b2[1][1]
    assert [m.phase for m in lida.messages if m.subtype in (Sub.PLAN_APPROVED, Sub.TASKS, Sub.LEARN)][:3] == [
        Phase.A3_DECOMPOSITION_VALIDATION, Phase.A3_DECOMPOSITION_VALIDATION, Phase.A4_PLANNING_LEARNINGS]
    assert lida.totals == nova.totals and len(lida.invocations) == len(nova.invocations)


async def test_sessao_antiga_sem_tech_e_lida_sem_ser_reescrita_nem_revalidada(
    tmp_path: Path, proibir_parser: Callable[[], None],
) -> None:
    proibir_parser()
    arquivo = tmp_path / "ralph_antiga.json"
    arquivo.write_text(json.dumps(_documento_antigo(), ensure_ascii=False), encoding="utf-8")
    original = arquivo.read_bytes()

    lida = await _repositorio(tmp_path).find_by_id(session_id="ralph_antiga")

    assert arquivo.read_bytes() == original
    assert lida is not None and lida.flow_version is RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION
    assert lida.messages[3].content == _RELATORIO_ANTIGO
    assert all("TECH" not in mensagem.content for mensagem in lida.messages)


async def test_pacote_exportado_e_importado_preserva_sessoes_nova_antiga_e_direta_sem_revalidar(
    proibir_parser: Callable[[], None],
) -> None:
    mapper = SessionDocumentMapper()
    codec = BenchmarkSessionArchiveCodec(benchmark_mapper=BenchmarkSessionDocumentMapper(), session_mapper=mapper)
    nova = await _sessao_nova()
    proibir_parser()
    antiga, direta = mapper.from_document(document=_documento_antigo()), _sessao_direta()

    for simples, ralph in ((direta, nova), (direta, antiga)):
        benchmark = bateria("Q1")
        for modo, sessao in ((BenchmarkInferenceModeEnum.SIMPLE, simples), (BenchmarkInferenceModeEnum.RALPH, ralph)):
            benchmark.start_flow(question_id="Q1", mode=modo, at=CRIADO_EM)
            benchmark.record_outcome(question_id="Q1", outcome=desfecho(mode=modo, session_id=sessao.id), at=CRIADO_EM)
        benchmark.finish_question(question_id="Q1", at=CRIADO_EM)
        benchmark.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=CRIADO_EM, wall_time_ms=1)
        pacote = BenchmarkSessionBundle(
            benchmark_session=benchmark,
            items=[BenchmarkSessionBundleItem(run=benchmark.questions[0], simple_session=simples, ralph_session=ralph)],
        )

        lido = codec.read(content=codec.build(bundle=pacote, exported_at=CRIADO_EM).content)

        assert [mapper.to_document(session=s) for s in lido.sessions] == [
            mapper.to_document(session=s) for s in pacote.sessions
        ]
        lida_direta = next(s for s in lido.sessions if s.id == "direta")
        assert lida_direta.flow_version is None
