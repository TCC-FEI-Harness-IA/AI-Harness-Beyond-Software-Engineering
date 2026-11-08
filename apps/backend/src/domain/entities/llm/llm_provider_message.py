from dataclasses import dataclass


@dataclass(frozen=True)
class LLMProviderMessage:
    """Representa uma mensagem no formato esperado por APIs de LLM."""

    role: str
    content: str
