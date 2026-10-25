import pytest

from src.domain.services.benchmark_answer_evaluator import BenchmarkAnswerEvaluator
from tests.doubles.benchmark_factories import OPCOES, questao


@pytest.mark.parametrize(
    ("resposta", "esperado"),
    [
        ("A", "A"),
        ("A) um", "A"),
        ("Descarto B e C.\nRESPOSTA_FINAL: A", "A"),
        ("**RESPOSTA_FINAL: B**", "B"),
        ("A ou B", None),
        ("A) dois", None),
        ("RESPOSTA_FINAL: A\nRESPOSTA_FINAL: B", None),
        ("RESPOSTA_FINAL: F", None),
        ("RESPOSTA_FINAL: A\nAfinal, B.", None),
        ("", None),
    ],
)
def test_identifica_somente_uma_escolha_inequivoca(resposta: str, esperado: str | None) -> None:
    assert BenchmarkAnswerEvaluator().select_alternative(response=resposta, options=OPCOES) == esperado


def test_resposta_correta_e_acerto() -> None:
    avaliacao = BenchmarkAnswerEvaluator().evaluate(question=questao(gabarito="B"), response="B", error=None)

    assert (avaliacao.selected_alternative, avaliacao.is_correct, avaliacao.error) == ("B", True, None)


def test_resposta_errada_e_erro_sem_diagnostico() -> None:
    avaliacao = BenchmarkAnswerEvaluator().evaluate(question=questao(gabarito="B"), response="C", error=None)

    assert (avaliacao.selected_alternative, avaliacao.is_correct, avaliacao.error) == ("C", False, None)


def test_resposta_invalida_e_erro_com_diagnostico() -> None:
    avaliacao = BenchmarkAnswerEvaluator().evaluate(question=questao(), response="não sei", error=None)

    assert avaliacao.selected_alternative is None
    assert avaliacao.is_correct is False
    assert "sem alternativa" in avaliacao.error


def test_falha_tecnica_e_erro_mesmo_com_resposta_valida() -> None:
    avaliacao = BenchmarkAnswerEvaluator().evaluate(question=questao(), response="A", error="timeout")

    assert (avaliacao.selected_alternative, avaliacao.is_correct, avaliacao.error) == (None, False, "timeout")
