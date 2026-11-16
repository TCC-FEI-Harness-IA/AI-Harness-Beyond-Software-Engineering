import pytest

from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from src.domain.services.password_policy import PasswordPolicy


def test_aceita_senha_dentro_dos_limites() -> None:
    PasswordPolicy(min_length=12, max_length=128).validate("uma senha longa o bastante")


def test_recusa_senha_curta() -> None:
    with pytest.raises(InvalidRegistrationError, match="12"):
        PasswordPolicy(min_length=12, max_length=128).validate("curta")


def test_recusa_senha_longa_demais() -> None:
    with pytest.raises(InvalidRegistrationError, match="128"):
        PasswordPolicy(min_length=12, max_length=128).validate("x" * 129)


def test_recusa_senha_so_com_espacos() -> None:
    with pytest.raises(InvalidRegistrationError):
        PasswordPolicy(min_length=4, max_length=128).validate("      ")


def test_politica_recusa_limites_incoerentes() -> None:
    with pytest.raises(ValueError):
        PasswordPolicy(min_length=8, max_length=4)
