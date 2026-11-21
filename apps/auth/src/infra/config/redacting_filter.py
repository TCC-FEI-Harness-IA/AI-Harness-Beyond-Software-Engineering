import logging
import re

_REDACTED = "[REDACTED]"
# Valores que nunca podem chegar aos logs: tokens Bearer, cookies, chaves OpenRouter e campos de senha.
_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:__host-|__secure-)?ralph_[a-z_]+=)[^;\s]+"),
    re.compile(r"sk-or-[A-Za-z0-9-]+"),
    re.compile(r"(?i)(\"?password\"?\s*[:=]\s*\"?)[^\"\s,}]+"),
)


def redact(text: str) -> str:
    """Substitui segredos conhecidos por `[REDACTED]`."""
    for pattern in _PATTERNS:
        text = pattern.sub(lambda match: (match.group(1) if match.groups() else "") + _REDACTED, text)
    return text


class RedactingFilter(logging.Filter):
    """Filtro de logging que redige segredos da mensagem já formatada."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Reescreve a mensagem do registro sem os segredos; nunca descarta o registro."""
        record.msg = redact(record.getMessage())
        record.args = ()
        return True
