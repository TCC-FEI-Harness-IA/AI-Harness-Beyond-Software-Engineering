import json
from datetime import datetime
from typing import Any

from joserfc import jwe
from joserfc.errors import JoseError
from joserfc.jwk import OctKey

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.entities.llm.llm_credential import LLMCredential
from src.domain.errors.credential_invalid_error import CredentialInvalidError
from src.domain.interfaces.clock_interface import IClock
from src.infra.security.sealed_credential import SealedCredential

_KEY_BYTES = 32
_ALGORITHMS = ["dir", "A256GCM"]
_PROTECTED_HEADER = {"alg": "dir", "enc": "A256GCM", "typ": "ralph-llm-credential+jwe"}
_PAYLOAD_VERSION = 1
_MAX_COOKIE_CHARS = 4096
_INVALID = "Credencial OpenRouter inválida. Informe a chave novamente."
_EXPIRED = "A credencial OpenRouter expirou. Informe a chave novamente."
_OTHER = "A credencial OpenRouter pertence a outra conta ou sessão. Informe a chave novamente."


class JweCredentialCookieCodec:
    """Cifra e decifra a credencial LLM do cookie com JWE (RFC 7516), via `joserfc`.

    Usa criptografia autenticada (`dir` + `A256GCM`) com a chave de aplicação de 256 bits: o
    conteúdo é confidencial e qualquer alteração no cookie (cabeçalho, IV, texto cifrado ou tag) é
    detectada. O payload vincula a chave à conta (`sub`), à sessão (`sid`) e à expiração (`exp`),
    que nunca passa do fim da sessão. Só o backend conhece a chave de aplicação.
    """

    def __init__(self, encryption_key: bytes, clock: IClock) -> None:
        """Inicializa o codec.

        Args:
            encryption_key: Chave de aplicação de exatamente 32 bytes.
            clock: Fonte de tempo.

        Raises:
            ValueError: Quando a chave não tem 32 bytes.
        """
        if len(encryption_key) != _KEY_BYTES:
            raise ValueError("A chave de criptografia da credencial precisa ter 32 bytes (256 bits).")
        self.__key = OctKey.import_key(encryption_key)
        self.clock = clock

    def seal(self, api_key: str, identity: AuthenticatedUser) -> SealedCredential:
        """Cifra a chave vinculando-a à conta e à sessão atuais.

        Args:
            api_key: Chave OpenRouter já validada.
            identity: Identidade validada da requisição.

        Returns:
            SealedCredential: JWE e a sua expiração (o fim da sessão).
        """
        now = self.clock.now()
        expires_at = identity.session_expires_at
        payload = {
            "v": _PAYLOAD_VERSION,
            "sub": identity.user_id,
            "sid": identity.session_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "key": api_key,
        }
        token = jwe.encrypt_compact(_PROTECTED_HEADER, json.dumps(payload).encode("utf-8"), self.__key)
        return SealedCredential(value=token, expires_at=expires_at)

    def open(self, value: str, identity: AuthenticatedUser) -> LLMCredential:
        """Decifra e valida o cookie para a identidade atual.

        Args:
            value: Conteúdo do cookie.
            identity: Identidade validada da requisição.

        Returns:
            LLMCredential: Credencial em memória.

        Raises:
            CredentialInvalidError: Cookie adulterado, ilegível, expirado ou de outra conta/sessão.
        """
        payload = self.__decrypt(value)
        expires_at = payload["exp"]
        if self.clock.now().timestamp() >= expires_at:
            raise CredentialInvalidError(_EXPIRED)
        if payload["sub"] != identity.user_id or payload["sid"] != identity.session_id:
            raise CredentialInvalidError(_OTHER)
        return LLMCredential(
            api_key=payload["key"],
            owner_id=payload["sub"],
            session_id=payload["sid"],
            expires_at=datetime.fromtimestamp(expires_at, tz=identity.session_expires_at.tzinfo),
        )

    def __decrypt(self, value: str) -> dict[str, Any]:
        if not value or len(value) > _MAX_COOKIE_CHARS:
            raise CredentialInvalidError(_INVALID)
        try:
            decrypted = jwe.decrypt_compact(value, self.__key, algorithms=_ALGORITHMS)
            payload = json.loads(decrypted.plaintext or b"")
        except (JoseError, ValueError, TypeError) as exc:
            raise CredentialInvalidError(_INVALID) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("v") != _PAYLOAD_VERSION
            or not all(isinstance(payload.get(key), str) for key in ("sub", "sid", "key"))
            or not isinstance(payload.get("exp"), int)
        ):
            raise CredentialInvalidError(_INVALID)
        return payload
