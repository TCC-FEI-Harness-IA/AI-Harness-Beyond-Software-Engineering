from pydantic import BaseModel, Field, field_validator
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
    temperature: float = Field(default=0.7)

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_and_round_temperature(cls, value: float) -> float:
        if not value:
            return 0.7

        temperature = float(value)
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")

        return round(temperature, 1)


class DefaultInputDTO(BaseModel):
    message: MessageInputDTO
    llm_model_config: ModelConfigDTO
