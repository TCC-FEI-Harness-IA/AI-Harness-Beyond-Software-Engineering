from collections import Counter

import pytest

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.services.benchmark_question_selector import select_mmlu_questions


def _questions() -> list[BenchmarkQuestion]:
    return [
        BenchmarkQuestion(f"{subject}_{i}", f"{subject} {i}", {"A": "ok"}, "A", subject)
        for subject, count in (("physics", 7), ("math", 5), ("history", 3)) for i in range(count)
    ]


def test_amostra_reproduzivel_distribui_questoes_e_nao_mexe_no_dataset() -> None:
    questions = _questions()
    selected = select_mmlu_questions(questions, (), 9, 42)
    assert Counter(q.subject for q in selected) == {"physics": 3, "math": 3, "history": 3}
    assert selected == select_mmlu_questions(list(reversed(questions)), (), 9, 42)
    assert selected != select_mmlu_questions(questions, (), 9, 43)
    assert len({q.id for q in selected}) == 9
    assert questions == _questions()


def test_filtro_multiplas_disciplinas_e_bateria_completa() -> None:
    selected = select_mmlu_questions(_questions(), ("physics", "math"), None, 0)
    assert len(selected) == 12
    assert {q.subject for q in selected} == {"physics", "math"}
    assert len(select_mmlu_questions(_questions(), (), None, 42)) == 15


@pytest.mark.parametrize("count", [0, 8])
def test_quantidade_validada_depois_do_filtro(count: int) -> None:
    with pytest.raises(InvalidBenchmarkRequestError, match="entre 1 e 7"):
        select_mmlu_questions(_questions(), ("physics",), count, 42)


def test_disciplina_desconhecida_e_recusada() -> None:
    with pytest.raises(InvalidBenchmarkRequestError, match="unknown"):
        select_mmlu_questions(_questions(), ("unknown",), 1, 42)


@pytest.mark.parametrize("seed", [-1, 2**32])
def test_semente_fora_do_intervalo(seed: int) -> None:
    with pytest.raises(InvalidBenchmarkRequestError, match="sample_seed"):
        select_mmlu_questions(_questions(), (), 1, seed)
