import re
import unicodedata
from dataclasses import dataclass

from src.domain.errors.invalid_registration_error import InvalidRegistrationError

# Validação deliberadamente simples: um único `@`, parte local e domínio sem espaços, domínio com ponto.
# A prova de posse do endereço não faz parte desta entrega (não há envio de e-mail).
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_EMAIL_LENGTH = 254


@dataclass(frozen=True)
class EmailAddress:
    """E-mail normalizado, chave única de uma conta.

    A normalização (NFKC, sem espaços nas pontas e em minúsculas) garante que grafias equivalentes
    do mesmo endereço resultem no mesmo valor — e, com o índice único do banco, numa única conta.

    Attributes:
        value: Endereço já normalizado.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> "EmailAddress":
        """Normaliza e valida um endereço informado pelo usuário.

        Args:
            raw: Endereço como digitado.

        Returns:
            EmailAddress: Endereço normalizado.

        Raises:
            InvalidRegistrationError: Quando o endereço é vazio, longo demais ou malformado.
        """
        normalized = unicodedata.normalize("NFKC", raw).strip().lower()
        if len(normalized) > _MAX_EMAIL_LENGTH or not _EMAIL_PATTERN.fullmatch(normalized):
            raise InvalidRegistrationError("Informe um e-mail válido.")
        return cls(value=normalized)
