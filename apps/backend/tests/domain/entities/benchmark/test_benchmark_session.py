from datetime import timedelta

import pytest

from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from tests.doubles.benchmark_factories import CRIADO_EM, bateria, desfecho

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH
_DEPOIS = CRIADO_EM + timedelta(seconds=5)


def _executar_questao(sessao, question_id: str, simples_correto: bool, ralph_correto: bool) -> None:
    sessao.start_flow(question_id=question_id, mode=_SIMPLES, at=_DEPOIS)
    sessao.record_outcome(
        question_id=question_id,
        outcome=desfecho(mode=_SIMPLES, correto=simples_correto, tokens=10, session_id=f"{question_id}_s"),
        at=_DEPOIS,
    )
    sessao.start_flow(question_id=question_id, mode=_RALPH, at=_DEPOIS)
    sessao.record_outcome(
        question_id=question_id,
        outcome=desfecho(mode=_RALPH, correto=ralph_correto, tokens=100, session_id=f"{question_id}_r"),
        at=_DEPOIS,
    )
    sessao.finish_question(question_id=question_id, at=_DEPOIS)


def test_contagens_de_progresso_acompanham_as_questoes() -> None:
    sessao = bateria("Q1", "Q2", "Q3")

    sessao.start_flow(question_id="Q1", mode=_SIMPLES, at=_DEPOIS)
    _executar_questao(sessao, "Q2", True, True)

    assert sessao.question_count == 3
    assert (sessao.pending_count, sessao.running_count, sessao.finished_count) == (1, 1, 1)
    assert sessao.interrupted_count == 0
    assert sessao.updated_at == _DEPOIS


def test_totais_e_resumo_por_fluxo_derivam_das_questoes() -> None:
    sessao = bateria("Q1", "Q2")
    _executar_questao(sessao, "Q1", True, True)
    _executar_questao(sessao, "Q2", False, True)

    assert sessao.total_tokens == 220
    assert sessao.session_ids == ["Q1_s", "Q1_r", "Q2_s", "Q2_r"]
    assert sessao.summary(mode=_SIMPLES).correct == 1
    assert sessao.summary(mode=_SIMPLES).wrong == 1
    assert sessao.summary(mode=_RALPH).correct == 2


def test_consumo_em_execucao_entra_no_total() -> None:
    sessao = bateria("Q1")
    sessao.start_flow(question_id="Q1", mode=_RALPH, at=_DEPOIS)

    sessao.track_tokens(question_id="Q1", total_tokens=42)

    assert sessao.total_tokens == 42


def test_questao_desconhecida_e_recusada() -> None:
    with pytest.raises(ValueError, match="não pertence"):
        bateria("Q1").question(question_id="Q9")


def test_tempo_de_execucao_so_muda_enquanto_executa() -> None:
    sessao = bateria("Q1")
    sessao.update_wall_time(wall_time_ms=100)
    _executar_questao(sessao, "Q1", True, True)
    sessao.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=_DEPOIS, wall_time_ms=200)

    sessao.update_wall_time(wall_time_ms=999)

    assert sessao.wall_time_ms == 200


def test_conclusao_registra_status_instante_e_tempo() -> None:
    sessao = bateria("Q1")
    _executar_questao(sessao, "Q1", True, False)

    sessao.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=_DEPOIS, wall_time_ms=1234)

    assert sessao.status is BenchmarkSessionStatusEnum.COMPLETED
    assert sessao.finished_at == _DEPOIS
    assert sessao.updated_at == _DEPOIS
    assert sessao.wall_time_ms == 1234
    assert sessao.error is None


def test_interrupcao_marca_as_questoes_em_execucao_e_mantem_as_pendentes() -> None:
    sessao = bateria("Q1", "Q2")
    sessao.start_flow(question_id="Q1", mode=_SIMPLES, at=_DEPOIS)

    sessao.finish(status=BenchmarkSessionStatusEnum.INTERRUPTED, at=_DEPOIS, wall_time_ms=10)

    assert sessao.question("Q1").status is BenchmarkQuestionStatusEnum.INTERRUPTED
    assert sessao.question("Q2").status is BenchmarkQuestionStatusEnum.PENDING
    assert sessao.interrupted_count == 1


def test_falha_guarda_o_diagnostico() -> None:
    sessao = bateria("Q1")

    sessao.finish(status=BenchmarkSessionStatusEnum.FAILED, at=_DEPOIS, wall_time_ms=10, error="disco cheio")

    assert sessao.error == "disco cheio"


def test_nao_conclui_com_questoes_sem_terminar() -> None:
    with pytest.raises(ValueError, match="todas as questões"):
        bateria("Q1").finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=_DEPOIS, wall_time_ms=1)


def test_nao_encerra_com_status_running() -> None:
    with pytest.raises(ValueError, match="running"):
        bateria("Q1").finish(status=BenchmarkSessionStatusEnum.RUNNING, at=_DEPOIS, wall_time_ms=1)


@pytest.mark.parametrize(
    "operacao",
    [
        lambda sessao: sessao.start_flow(question_id="Q1", mode=_SIMPLES, at=_DEPOIS),
        lambda sessao: sessao.record_outcome(question_id="Q1", outcome=desfecho(), at=_DEPOIS),
        lambda sessao: sessao.finish_question(question_id="Q1", at=_DEPOIS),
        lambda sessao: sessao.finish(status=BenchmarkSessionStatusEnum.FAILED, at=_DEPOIS, wall_time_ms=1),
    ],
)
def test_bateria_encerrada_nao_aceita_alteracoes(operacao) -> None:
    sessao = bateria("Q1", status=BenchmarkSessionStatusEnum.INTERRUPTED)

    with pytest.raises(ValueError, match="já foi encerrada"):
        operacao(sessao)
