from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum


def test_declara_exatamente_os_motivos_suportados() -> None:
    assert {member.value for member in SessionFailureReasonEnum} == {"resource_limit", "technical_error"}


def test_valores_de_cada_membro() -> None:
    assert SessionFailureReasonEnum.RESOURCE_LIMIT == "resource_limit"
    assert SessionFailureReasonEnum.TECHNICAL_ERROR == "technical_error"


def test_e_uma_str_enum() -> None:
    assert isinstance(SessionFailureReasonEnum.RESOURCE_LIMIT, str)
