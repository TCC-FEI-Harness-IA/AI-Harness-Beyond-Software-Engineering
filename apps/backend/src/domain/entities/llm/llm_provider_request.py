from dataclasses import dataclass, field
from typing import Any

from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.genai_model import GenaiModel


@dataclass(frozen=True)
class LLMProviderRequest:
    """Payload padronizado para chamadas de APIs de chat de provedores LLM."""

    llm_model: GenaiModel
    messages: list[LLMProviderMessage]
    max_tokens: int
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Converte e valida a temperatura, preservando exatamente o valor recebido.

        Raises:
            ValueError: Quando a temperatura está fora do intervalo `[0, 1]` ou não é finita.
        """
        temperature = float(self.temperature)
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")

        object.__setattr__(self, "temperature", temperature)
