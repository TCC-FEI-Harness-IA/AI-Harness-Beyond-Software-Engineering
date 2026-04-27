from pydantic import BaseModel
from typing import Literal


class MessageInputDTO(BaseModel):
    user_input: str


class ProviderConfigDTO(BaseModel):
    model_name: str
    endpoint: str | None = None


class ModelConfigDTO(BaseModel):
    provider: Literal["local", "open_router"]
    provider_config: ProviderConfigDTO
    max_tokens: int


class PredefinedStrategyDTO(BaseModel):
    number_of_phases: int


class StrategiesDTO(BaseModel):
    predefined: PredefinedStrategyDTO


class ReasoningConfigDTO(BaseModel):
    phase_breaking_strategy: Literal["autonomous", "predefined"]
    strategies: StrategiesDTO | None = None
    next_phase_strategy: Literal["ai_based", "algorithmic"]


class ReasoningInputDTO(BaseModel):
    message: MessageInputDTO
    llm_model_config: ModelConfigDTO
    reasoning_config: ReasoningConfigDTO
