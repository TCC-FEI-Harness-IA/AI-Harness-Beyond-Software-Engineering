from src.domain.enums.session_status_enum import SessionStatusEnum


def test_declara_exatamente_os_estados_suportados() -> None:
    assert {member.value for member in SessionStatusEnum} == {"running", "completed", "degraded", "failed"}


def test_valores_de_cada_membro() -> None:
    assert SessionStatusEnum.RUNNING == "running"
    assert SessionStatusEnum.COMPLETED == "completed"
    assert SessionStatusEnum.DEGRADED == "degraded"
    assert SessionStatusEnum.FAILED == "failed"


def test_e_uma_str_enum() -> None:
    assert isinstance(SessionStatusEnum.RUNNING, str)
