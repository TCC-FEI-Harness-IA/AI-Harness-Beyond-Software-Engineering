import pytest

from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from tests.doubles.benchmark_factories import desfecho

_SIMPLES = BenchmarkInferenceModeEnum.SIMPLE
_RALPH = BenchmarkInferenceModeEnum.RALPH


def _questao() -> BenchmarkQuestionRun:
    return BenchmarkQuestionRun(question_id="Q1", expected_alternative="A")


def test_comeca_pendente_sem_desfechos() -> None:
    questao = _questao()

    assert questao.status is BenchmarkQuestionStatusEnum.PENDING
    assert questao.outcomes == []
    assert questao.total_tokens == 0
    assert questao.session_ids == []


def test_executa_os_dois_fluxos_e_termina() -> None:
    questao = _questao()

    questao.start_flow(mode=_SIMPLES)
    assert questao.status is BenchmarkQuestionStatusEnum.RUNNING
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES, tokens=10, session_id="sess_a"))
    questao.start_flow(mode=_RALPH)
    questao.record_outcome(outcome=desfecho(mode=_RALPH, tokens=30, session_id="sess_b"))
    questao.finish()

    assert questao.status is BenchmarkQuestionStatusEnum.FINISHED
    assert questao.outcome(mode=_SIMPLES) is questao.simple
    assert questao.outcome(mode=_RALPH) is questao.ralph
    assert questao.total_tokens == 40
    assert questao.session_ids == ["sess_a", "sess_b"]
    assert questao.current_mode is None


def test_consumo_em_execucao_entra_no_total_e_nunca_decresce() -> None:
    questao = _questao()
    questao.start_flow(mode=_RALPH)

    questao.track_tokens(total_tokens=50)
    questao.track_tokens(total_tokens=20)

    assert questao.current_tokens == 50
    assert questao.total_tokens == 50


def test_desfecho_sem_sessao_nao_aparece_nos_ids() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES, session_id=None))

    assert questao.session_ids == []


def test_nao_inicia_fluxo_em_questao_encerrada() -> None:
    questao = _questao()
    questao.status = BenchmarkQuestionStatusEnum.FINISHED

    with pytest.raises(ValueError, match="já foi encerrada"):
        questao.start_flow(mode=_SIMPLES)


def test_nao_inicia_dois_fluxos_ao_mesmo_tempo() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)

    with pytest.raises(ValueError, match="já executa"):
        questao.start_flow(mode=_RALPH)


def test_nao_repete_fluxo_ja_terminado() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES))

    with pytest.raises(ValueError, match="já terminou"):
        questao.start_flow(mode=_SIMPLES)


def test_consumo_sem_fluxo_em_execucao_e_recusado() -> None:
    with pytest.raises(ValueError, match="não tem fluxo"):
        _questao().track_tokens(total_tokens=1)


def test_desfecho_de_fluxo_que_nao_esta_em_execucao_e_recusado() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)

    with pytest.raises(ValueError, match="não está em execução"):
        questao.record_outcome(outcome=desfecho(mode=_RALPH))


def test_so_termina_depois_dos_dois_fluxos() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES))

    with pytest.raises(ValueError, match="dois fluxos"):
        questao.finish()


def test_interrupcao_marca_so_a_questao_em_execucao_e_preserva_o_consumo() -> None:
    em_execucao = _questao()
    em_execucao.start_flow(mode=_RALPH)
    em_execucao.track_tokens(total_tokens=7)
    pendente = _questao()

    em_execucao.interrupt()
    pendente.interrupt()

    assert em_execucao.status is BenchmarkQuestionStatusEnum.INTERRUPTED
    assert em_execucao.current_mode is _RALPH
    assert em_execucao.total_tokens == 7
    assert pendente.status is BenchmarkQuestionStatusEnum.PENDING


def _questao_encerrada(simples_correto: bool, ralph_correto: bool) -> BenchmarkQuestionRun:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES, correto=simples_correto, session_id="sess_a", tokens=10))
    questao.start_flow(mode=_RALPH)
    questao.record_outcome(outcome=desfecho(mode=_RALPH, correto=ralph_correto, session_id="sess_b", tokens=30))
    questao.finish()
    return questao


@pytest.mark.parametrize(
    ("simples_correto", "ralph_correto", "esperado"),
    [(True, True, []), (False, True, [_SIMPLES]), (True, False, [_RALPH]), (False, False, [_SIMPLES, _RALPH])],
)
def test_fluxos_reexecutaveis_sao_os_errados_de_uma_questao_encerrada(
    simples_correto: bool, ralph_correto: bool, esperado: list[BenchmarkInferenceModeEnum]
) -> None:
    assert _questao_encerrada(simples_correto, ralph_correto).rerunnable_modes == esperado


def test_falha_tecnica_tambem_e_reexecutavel() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)
    questao.record_outcome(outcome=desfecho(mode=_SIMPLES, correto=False, erro="timeout"))
    questao.start_flow(mode=_RALPH)
    questao.record_outcome(outcome=desfecho(mode=_RALPH))
    questao.finish()

    assert questao.rerunnable_modes == [_SIMPLES]


@pytest.mark.parametrize("status", [BenchmarkQuestionStatusEnum.PENDING, BenchmarkQuestionStatusEnum.INTERRUPTED])
def test_questao_nao_encerrada_nao_tem_fluxo_reexecutavel(status: BenchmarkQuestionStatusEnum) -> None:
    questao = _questao()
    questao.simple = desfecho(mode=_SIMPLES, correto=False)
    questao.status = status

    assert questao.rerunnable_modes == []


def test_reexecucao_preserva_o_desfecho_anterior_ate_o_novo_e_o_substitui() -> None:
    questao = _questao_encerrada(simples_correto=True, ralph_correto=False)
    anterior = questao.ralph

    questao.start_rerun(mode=_RALPH)
    questao.track_tokens(total_tokens=7)

    assert questao.status is BenchmarkQuestionStatusEnum.FINISHED
    assert questao.current_mode is _RALPH
    assert questao.ralph is anterior
    assert questao.total_tokens == 10 + 30 + 7

    novo = desfecho(mode=_RALPH, correto=True, session_id="sess_c", tokens=5)
    questao.record_rerun_outcome(outcome=novo)

    assert questao.ralph is novo
    assert questao.current_mode is None
    assert questao.current_tokens == 0
    assert questao.session_ids == ["sess_a", "sess_c"]
    assert questao.rerunnable_modes == []


def test_reexecucao_do_fluxo_simples_substitui_o_simples() -> None:
    questao = _questao_encerrada(simples_correto=False, ralph_correto=True)
    questao.start_rerun(mode=_SIMPLES)
    novo = desfecho(mode=_SIMPLES, correto=True, session_id="sess_c")

    questao.record_rerun_outcome(outcome=novo)

    assert questao.simple is novo


def test_nao_reexecuta_fluxo_que_acertou() -> None:
    questao = _questao_encerrada(simples_correto=True, ralph_correto=False)

    with pytest.raises(ValueError, match="não está errado"):
        questao.start_rerun(mode=_SIMPLES)


def test_nao_reexecuta_dois_fluxos_ao_mesmo_tempo() -> None:
    questao = _questao_encerrada(simples_correto=False, ralph_correto=False)
    questao.start_rerun(mode=_SIMPLES)

    with pytest.raises(ValueError, match="já executa"):
        questao.start_rerun(mode=_RALPH)


def test_desfecho_de_outro_fluxo_nao_substitui_a_reexecucao() -> None:
    questao = _questao_encerrada(simples_correto=False, ralph_correto=False)
    questao.start_rerun(mode=_SIMPLES)

    with pytest.raises(ValueError, match="não está em execução"):
        questao.record_rerun_outcome(outcome=desfecho(mode=_RALPH))


def test_aborto_da_reexecucao_mantem_o_desfecho_anterior() -> None:
    questao = _questao_encerrada(simples_correto=False, ralph_correto=True)
    anterior = questao.simple
    questao.start_rerun(mode=_SIMPLES)
    questao.track_tokens(total_tokens=9)

    questao.abort_rerun()

    assert (questao.current_mode, questao.current_tokens) == (None, 0)
    assert questao.simple is anterior
    assert questao.status is BenchmarkQuestionStatusEnum.FINISHED


def test_aborto_nao_altera_questao_em_execucao_normal() -> None:
    questao = _questao()
    questao.start_flow(mode=_SIMPLES)

    questao.abort_rerun()

    assert questao.current_mode is _SIMPLES
