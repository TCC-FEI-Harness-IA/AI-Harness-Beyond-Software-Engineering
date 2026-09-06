from typing import Literal
from pydantic import BaseModel, Field, field_validator


class MessageInputDTO(BaseModel):
    user_input: str


class ProviderConfigDTO(BaseModel):
    model_name: str | None = None
    endpoint: str | None = None


class ModelConfigDTO(BaseModel):
    provider: Literal["azure_foundry", "open_router", "local", "mock"] = "azure_foundry"
    provider_config: ProviderConfigDTO = Field(default_factory=ProviderConfigDTO)
    max_tokens: int = 1024
    temperature: float = Field(default=0.7)

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_and_round_temperature(cls, value: float | None) -> float:
        if value is None:
            return 0.7
        temp = float(value)
        if not 0 <= temp <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")
        return round(temp, 1)


class DefaultInputDTO(BaseModel):
    message: MessageInputDTO
    llm_model_config: ModelConfigDTO = Field(default_factory=ModelConfigDTO)
