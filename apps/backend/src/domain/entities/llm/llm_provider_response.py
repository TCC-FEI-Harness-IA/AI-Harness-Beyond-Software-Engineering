from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMProviderResponse:
    """Resposta padronizada de APIs de chat de provedores LLM.

    Attributes:
        output_text: Texto gerado pelo modelo.
        input_tokens: Tokens de entrada informados pelo provedor, ou `None` se não informados.
        output_tokens: Tokens de saída informados pelo provedor, ou `None` se não informados.
        finish_reason: Motivo de término informado pelo provedor, quando há.
        raw_response: Corpo bruto da resposta do provedor.
        response_id: Identificador da resposta no provedor, quando há.
    """

    output_text: str
    input_tokens: int | None
    output_tokens: int | None
    finish_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
    response_id: str | None = None
