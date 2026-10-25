from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum


def test_declara_exatamente_os_estados_suportados() -> None:
    assert {member.value for member in BenchmarkSessionStatusEnum} == {
        "running", "completed", "failed", "interrupted",
    }


def test_e_uma_str_enum() -> None:
    assert isinstance(BenchmarkSessionStatusEnum.RUNNING, str)
