import pytest

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from tests.doubles.benchmark_factories import OPCOES, questao


def test_alternativa_esperada_completa_traz_letra_e_texto() -> None:
    assert questao(gabarito="C").expected_answer == "C) três"


def test_gabarito_fora_das_alternativas_e_recusado() -> None:
    with pytest.raises(ValueError, match="Gabarito 'F'"):
        BenchmarkQuestion(id="Q1", statement="enunciado", options=dict(OPCOES), expected_alternative="F")
