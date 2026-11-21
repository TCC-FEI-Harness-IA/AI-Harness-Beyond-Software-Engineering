import pytest

from src.domain.entities.email_address import EmailAddress
from src.domain.errors.invalid_registration_error import InvalidRegistrationError


def test_normaliza_maiusculas_e_espacos() -> None:
    assert EmailAddress.parse("  Pessoa.Teste@Exemplo.COM ").value == "pessoa.teste@exemplo.com"


def test_normaliza_unicode_compativel() -> None:
    # "ｅ" (fullwidth) vira "e" pela NFKC: duas grafias do mesmo endereço não criam duas contas.
    assert EmailAddress.parse("ｅva@exemplo.com").value == "eva@exemplo.com"


@pytest.mark.parametrize(
    "bruto",
    [
        "", "   ", "sem-arroba", "@exemplo.com", "pessoa@", "pessoa@exemplo", "a b@exemplo.com",
        "x@" + "a" * 250 + ".com",
    ],
)
def test_recusa_enderecos_invalidos(bruto: str) -> None:
    with pytest.raises(InvalidRegistrationError):
        EmailAddress.parse(bruto)


def test_igualdade_pelo_valor_normalizado() -> None:
    assert EmailAddress.parse("A@B.co") == EmailAddress.parse("a@b.co")
