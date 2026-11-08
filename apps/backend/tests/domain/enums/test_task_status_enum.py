from src.domain.enums.task_status_enum import TaskStatusEnum


def test_declara_exatamente_os_estados_suportados() -> None:
    assert {member.value for member in TaskStatusEnum} == {
        "pending",
        "in_progress",
        "approved",
        "failed",
        "discarded",
    }


def test_valores_de_cada_membro() -> None:
    assert TaskStatusEnum.PENDING == "pending"
    assert TaskStatusEnum.IN_PROGRESS == "in_progress"
    assert TaskStatusEnum.APPROVED == "approved"
    assert TaskStatusEnum.FAILED == "failed"
    assert TaskStatusEnum.DISCARDED == "discarded"


def test_e_uma_str_enum() -> None:
    assert isinstance(TaskStatusEnum.PENDING, str)
