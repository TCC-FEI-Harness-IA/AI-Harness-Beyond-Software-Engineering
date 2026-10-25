import pytest

from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH


def _bateria_com_historia():
    sessao = bateria("Q1", "Q2", "Q3")
    sessao.start_flow(question_id="Q1", mode=_SIMPLES, at=CRIADO_EM)
    sessao.record_outcome(question_id="Q1", outcome=desfecho(mode=_SIMPLES, session_id="s1"), at=CRIADO_EM)
    sessao.start_flow(question_id="Q1", mode=_RALPH, at=CRIADO_EM)
    sessao.record_outcome(
        question_id="Q1", outcome=desfecho(mode=_RALPH, correto=False, erro="falha", session_id="s2"), at=CRIADO_EM
    )
    sessao.finish_question(question_id="Q1", at=CRIADO_EM)
    sessao.start_flow(question_id="Q2", mode=_SIMPLES, at=CRIADO_EM)
    sessao.track_tokens(question_id="Q2", total_tokens=5)
    return sessao


def test_documento_traz_os_campos_de_origem_e_os_derivados() -> None:
    documento = BenchmarkSessionDocumentMapper().to_document(benchmark_session=_bateria_com_historia())

    assert documento["_id"] == documento["id"] == "bench_1"
    assert documento["status"] == "running"
    assert documento["provider"] == "open_router"
    assert documento["finished_at"] is None
    assert documento["progress"] == {"total": 3, "pending": 1, "running": 1, "finished": 1, "interrupted": 0}
    assert documento["total_tokens"] == 25
    assert documento["session_ids"] == ["s1", "s2"]
    assert documento["summary"]["simple"]["correct"] == 1
    assert documento["summary"]["ralph"] == {
        "executed": 1, "correct": 0, "wrong": 1, "failures": 1, "accuracy": 0.0,
        "total_tokens": 10, "duration_seconds": 1.5,
    }
    assert documento["questions"][1]["current_mode"] == "simple"
    assert documento["questions"][1]["simple"] is None
    assert documento["questions"][0]["ralph"]["error"] == "falha"


def test_ida_e_volta_preservam_a_bateria() -> None:
    mapper = BenchmarkSessionDocumentMapper()
    original = _bateria_com_historia()

    reconstruida = mapper.from_document(document=mapper.to_document(benchmark_session=original))

    assert reconstruida == original


def test_ida_e_volta_preservam_a_bateria_encerrada() -> None:
    mapper = BenchmarkSessionDocumentMapper()
    original = _bateria_com_historia()
    original.finish(status=BenchmarkSessionStatusEnum.INTERRUPTED, at=CRIADO_EM, wall_time_ms=9, error="parou")

    reconstruida = mapper.from_document(document=mapper.to_document(benchmark_session=original))

    assert reconstruida == original
    assert reconstruida.finished_at == CRIADO_EM


def test_chave_obrigatoria_ausente_e_recusada() -> None:
    mapper = BenchmarkSessionDocumentMapper()
    documento = mapper.to_document(benchmark_session=bateria("Q1"))
    del documento["questions"][0]["status"]

    with pytest.raises(ValueError, match="Chave obrigatória 'status'"):
        mapper.from_document(document=documento)


def test_enum_desconhecido_e_recusado() -> None:
    mapper = BenchmarkSessionDocumentMapper()
    documento = mapper.to_document(benchmark_session=bateria("Q1"))
    documento["status"] = "pausada"

    with pytest.raises(ValueError, match="BenchmarkSessionStatusEnum"):
        mapper.from_document(document=documento)


@pytest.mark.parametrize(("valor", "mensagem"), [("ontem", "ISO-8601"), ("2026-10-25T12:00:00", "fuso horário")])
def test_data_invalida_e_recusada(valor: str, mensagem: str) -> None:
    mapper = BenchmarkSessionDocumentMapper()
    documento = mapper.to_document(benchmark_session=bateria("Q1"))
    documento["created_at"] = valor

    with pytest.raises(ValueError, match=mensagem):
        mapper.from_document(document=documento)
