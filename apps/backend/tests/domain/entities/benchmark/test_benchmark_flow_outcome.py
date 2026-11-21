from src.domain.entities.benchmark.benchmark_answer_evaluation import BenchmarkAnswerEvaluation
from tests.doubles.benchmark_factories import desfecho


def test_desfecho_com_erro_e_falha() -> None:
    assert desfecho(correto=False, erro="timeout").failed is True


def test_desfecho_sem_erro_nao_e_falha() -> None:
    assert desfecho().failed is False


def test_avaliacao_guarda_os_valores() -> None:
    avaliacao = BenchmarkAnswerEvaluation(selected_alternative="B", is_correct=False, error=None)

    assert (avaliacao.selected_alternative, avaliacao.is_correct, avaliacao.error) == ("B", False, None)
