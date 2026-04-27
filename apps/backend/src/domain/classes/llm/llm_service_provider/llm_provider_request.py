from dataclasses import dataclass, field
from typing import Any

from src.domain.classes.llm.llm_service_provider.llm_provider_message import LLMProviderMessage
from src.domain.classes.llm.models.genai_model import GenaiModel


@dataclass(frozen=True)
class LLMProviderRequest:
    """Payload padronizado para chamadas de APIs de chat de provedores LLM."""

    llm_model: GenaiModel
    messages: list[LLMProviderMessage]
    max_tokens: int
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        temperature = self.temperature

        temperature = float(temperature)
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")

        object.__setattr__(self, "temperature", round(temperature, 1))
