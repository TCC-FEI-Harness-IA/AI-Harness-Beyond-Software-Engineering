from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SealedCredential:
    """Credencial cifrada pronta para virar cookie.

    Attributes:
        value: JWE compacto (`dir` + `A256GCM`).
        expires_at: Fim da validade, também usado como expiração do cookie.
    """

    value: str = field(repr=False)
    expires_at: datetime
