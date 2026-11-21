from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum


def test_declara_exatamente_os_desfechos_suportados() -> None:
    assert {member.value for member in InvocationOutcomeEnum} == {
        "started",
        "success",
        "empty_completion",
        "provider_error",
    }


def test_valores_de_cada_membro() -> None:
    assert InvocationOutcomeEnum.STARTED == "started"
    assert InvocationOutcomeEnum.SUCCESS == "success"
    assert InvocationOutcomeEnum.EMPTY_COMPLETION == "empty_completion"
    assert InvocationOutcomeEnum.PROVIDER_ERROR == "provider_error"


def test_e_uma_str_enum() -> None:
    assert isinstance(InvocationOutcomeEnum.STARTED, str)
