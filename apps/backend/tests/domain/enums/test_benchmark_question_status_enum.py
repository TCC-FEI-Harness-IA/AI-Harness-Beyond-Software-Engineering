from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum


def test_declara_exatamente_os_estados_suportados() -> None:
    assert {member.value for member in BenchmarkQuestionStatusEnum} == {
        "pending", "running", "finished", "interrupted",
    }


def test_e_uma_str_enum() -> None:
    assert isinstance(BenchmarkQuestionStatusEnum.PENDING, str)
