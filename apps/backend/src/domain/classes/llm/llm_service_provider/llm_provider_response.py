from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMProviderResponse:
    """Resposta padronizada de APIs de chat de provedores LLM."""

    output_text: str
    input_tokens: int
    output_tokens: int
    finish_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
