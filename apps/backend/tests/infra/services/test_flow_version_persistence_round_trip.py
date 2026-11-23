"""Versão do fluxo ponta a ponta na persistência, na consulta e nos pacotes de benchmark.

Uma sessão Ralph antiga (sem `flow_version`) continua lida como versão 1, com `A3` de extração; uma nova
traz a versão 2, com `A3` de validação e `A4` de extração; a inferência direta não ganha versão. A leitura
não reescreve os arquivos persistidos, e exportação/importação preservam versão, fases, subtipos e conteúdo.
"""
import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
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
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkRalphErrorsArchiveBuilder
from src.infra.services.benchmark_session_archive_codec import BenchmarkSessionArchiveCodec
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho
from tests.doubles.fake_settings import FakeSettings

_EM = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
_EXTRACAO_HISTORICA = "## Extracted learnings\n\n- Alternativas: A) 2; B) 4."


def _mensagem(order: int, phase: Phase, content: str, subtype: Sub | None = None,
              source: MessageSourceEnum = MessageSourceEnum.LLM_AGENT) -> SessionMessage:
    return SessionMessage(
        id=f"msg-{order}", order=order, timestamp=_EM, phase=phase, source=source, content=content,
        task_id=None, context_id=f"ctx-{order}", tokens_input=3, tokens_output=2, inference_time_ms=5,
        model_name="m", subtype=subtype,
    )


def _sessao(identificador: str, mensagens: list[SessionMessage],
            flow_version: RalphFlowVersionEnum | None) -> Session:
    sessao = Session(
        id=identificador, user_question="q", flow=Phase.A1_GENERAL_CRITERIA, model_name="m", max_tokens=100,
        temperature=0.3, status=SessionStatusEnum.RUNNING, created_at=_EM, updated_at=_EM, flow_version=flow_version,
    )
    for mensagem in mensagens:
        sessao.add_message(mensagem)
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="D")
    return sessao


def _sessao_nova() -> Session:
    return _sessao("ralph_nova", [
        _mensagem(0, Phase.A2_TASK_DECOMPOSITION, "## Candidate plan — attempt 1\n\n### T1 — X", Sub.PLAN_CANDIDATE),
        _mensagem(1, Phase.A3_DECOMPOSITION_VALIDATION, "**Plan decision:** `rejected`", Sub.PLAN_REJECTED),
        _mensagem(2, Phase.A2_TASK_DECOMPOSITION, "## Candidate plan — attempt 2\n\n### T1 — Y", Sub.PLAN_CANDIDATE),
        _mensagem(3, Phase.A3_DECOMPOSITION_VALIDATION, "**Plan decision:** `approved`", Sub.PLAN_APPROVED),
        _mensagem(4, Phase.A3_DECOMPOSITION_VALIDATION, "## Planned tasks\n\n### T1 — Y", Sub.TASKS,
                  MessageSourceEnum.SYSTEM),
        _mensagem(5, Phase.A4_PLANNING_LEARNINGS, _EXTRACAO_HISTORICA, Sub.LEARN),
    ], RalphFlowVersionEnum.current())


def _documento_antigo() -> dict[str, Any]:
    """Documento Ralph gravado antes de `flow_version` e de `subtype`: `A3` é a extração do enunciado."""
    documento = SessionDocumentMapper().to_document(session=_sessao("ralph_antiga", [
        _mensagem(0, Phase.A2_TASK_DECOMPOSITION, "## Planned tasks\n\n### T1 — X"),
        _mensagem(1, Phase.A3_DECOMPOSITION_VALIDATION, _EXTRACAO_HISTORICA),
    ], None))
    del documento["flow_version"]
    for mensagem in documento["messages"]:
        del mensagem["subtype"]
    return documento


def _repositorio(caminho: Path) -> JsonFileSessionRepository:
    return JsonFileSessionRepository(
        mapper=SessionDocumentMapper(), settings=FakeSettings(ralph_sessions_storage_path=str(caminho)),
        logger=logging.getLogger("teste.versao"),
    )


async def test_leitura_de_sessao_antiga_nao_reescreve_o_arquivo_e_mantem_a3_como_extracao(tmp_path: Path) -> None:
    arquivo = tmp_path / "ralph_antiga.json"
    arquivo.write_text(json.dumps(_documento_antigo(), ensure_ascii=False), encoding="utf-8")
    original = arquivo.read_bytes()

    sessao = await _repositorio(tmp_path).find_by_id(session_id="ralph_antiga")

    assert arquivo.read_bytes() == original
    assert sessao is not None and sessao.flow_version is RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION
    assert [(m.phase.value, m.content) for m in sessao.messages][1] == ("A3", _EXTRACAO_HISTORICA)
    consultado = SessionDocumentMapper().to_document(session=sessao)
    assert consultado["flow_version"] == 1 and consultado["messages"][1]["subtype"] is None


async def test_sessao_nova_e_gravada_e_lida_com_versao_fases_e_subtipos(tmp_path: Path) -> None:
    repositorio = _repositorio(tmp_path)
    await repositorio.save(session=_sessao_nova())

    gravado = json.loads((tmp_path / "ralph_nova.json").read_text(encoding="utf-8"))
    lido = await repositorio.find_by_id(session_id="ralph_nova")

    assert gravado["flow_version"] == 2
    assert [(m["phase"], m["subtype"]) for m in gravado["messages"]] == [
        ("A2", "plan_candidate"), ("A3", "plan_rejected"), ("A2", "plan_candidate"), ("A3", "plan_approved"),
        ("A3", "tasks"), ("A4", "learn"),
    ]
    assert SessionDocumentMapper().to_document(session=lido) == gravado


def _pacote(simples: Session, ralph: Session) -> BenchmarkSessionBundle:
    benchmark = bateria("Q1")
    for modo, sessao in ((BenchmarkInferenceModeEnum.SIMPLE, simples), (BenchmarkInferenceModeEnum.RALPH, ralph)):
        benchmark.start_flow(question_id="Q1", mode=modo, at=CRIADO_EM)
        benchmark.record_outcome(question_id="Q1", outcome=desfecho(mode=modo, session_id=sessao.id), at=CRIADO_EM)
    benchmark.finish_question(question_id="Q1", at=CRIADO_EM)
    benchmark.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=CRIADO_EM, wall_time_ms=1)
    return BenchmarkSessionBundle(
        benchmark_session=benchmark,
        items=[BenchmarkSessionBundleItem(run=benchmark.questions[0], simple_session=simples, ralph_session=ralph)],
    )


def test_pacote_completo_preserva_versao_fases_e_conteudo_das_sessoes_antiga_e_nova() -> None:
    mapper = SessionDocumentMapper()
    codec = BenchmarkSessionArchiveCodec(benchmark_mapper=BenchmarkSessionDocumentMapper(), session_mapper=mapper)
    antiga = mapper.from_document(document=_documento_antigo())
    nova = _sessao_nova()

    for simples, ralph in ((antiga, nova), (nova, antiga)):
        pacote = _pacote(simples, ralph)
        lido = codec.read(content=codec.build(bundle=pacote, exported_at=CRIADO_EM).content)
        assert [mapper.to_document(session=s) for s in lido.sessions] == [
            mapper.to_document(session=s) for s in pacote.sessions
        ]

    lido_antigo = next(s for s in lido.sessions if s.id == "ralph_antiga")
    lido_novo = next(s for s in lido.sessions if s.id == "ralph_nova")
    assert lido_antigo.flow_version is RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION
    assert lido_antigo.messages[1].phase is Phase.A3_DECOMPOSITION_VALIDATION
    assert lido_antigo.messages[1].content == _EXTRACAO_HISTORICA and lido_antigo.messages[1].subtype is None
    assert lido_novo.flow_version is RalphFlowVersionEnum.VALIDATED_PLANNING
    assert [m.subtype for m in lido_novo.messages][:2] == [Sub.PLAN_CANDIDATE, Sub.PLAN_REJECTED]


def test_exportacao_dos_erros_do_ralph_leva_a_versao_do_fluxo() -> None:
    nova = _sessao_nova()
    benchmark = _pacote(nova, nova).benchmark_session
    erro = BenchmarkRalphError(
        question_id="Q1", expected_alternative="A", outcome=benchmark.questions[0].ralph, question=None, session=nova,
    )

    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=SessionDocumentMapper()).build(
        benchmark_session_id=benchmark.id, errors=[erro]
    )

    with zipfile.ZipFile(io.BytesIO(arquivo.content)) as zip_:
        documentos = [json.loads(zip_.read(nome)) for nome in zip_.namelist() if nome.endswith(".json")]
    [documento] = [documento for documento in documentos if isinstance(documento, dict) and "session" in documento]
    assert documento["session"]["flow_version"] == 2
    assert [m["phase"] for m in documento["session"]["messages"]] == ["A2", "A3", "A2", "A3", "A3", "A4"]
