import hashlib
import secrets

from src.domain.interfaces.token_generator_interface import ITokenGenerator

_TOKEN_BYTES = 32
_ID_BYTES = 16


class SecureTokenGenerator(ITokenGenerator):
    """Segredos e identificadores gerados pelo CSPRNG do sistema (`secrets`).

    O token de sessão tem 256 bits; por ter alta entropia, um SHA-256 sem sal é suficiente para
    armazená-lo (a força bruta sobre o espaço de tokens é inviável) e permite buscá-lo por índice.
    """

    def session_token(self) -> str:
        """Token opaco de 256 bits, em base64url."""
        return secrets.token_urlsafe(_TOKEN_BYTES)

    def csrf_token(self) -> str:
        """Token anti-CSRF de 256 bits, em base64url."""
        return secrets.token_urlsafe(_TOKEN_BYTES)

    def digest(self, token: str) -> str:
        """SHA-256 hexadecimal do token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def user_id(self) -> str:
        """Identificador estável de usuário (`usr_` + 128 bits)."""
        return f"usr_{secrets.token_hex(_ID_BYTES)}"

    def session_id(self) -> str:
        """Identificador da sessão (`ses_` + 128 bits)."""
        return f"ses_{secrets.token_hex(_ID_BYTES)}"
