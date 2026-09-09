from src.domain.enums.verification_decision_enum import VerificationDecisionEnum


def test_declara_exatamente_as_decisoes_suportadas() -> None:
    assert {member.value for member in VerificationDecisionEnum} == {"approved", "reproved"}


def test_valores_de_cada_membro() -> None:
    assert VerificationDecisionEnum.APPROVED == "approved"
    assert VerificationDecisionEnum.REPROVED == "reproved"


def test_e_uma_str_enum() -> None:
    assert isinstance(VerificationDecisionEnum.APPROVED, str)
