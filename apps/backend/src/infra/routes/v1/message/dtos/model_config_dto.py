from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.infra.routes.v1.message.dtos.provider_config_dto import ProviderConfigDTO

_DEFAULT_TEMPERATURE = 0.7


class ModelConfigDTO(BaseModel):
    """Parâmetros do modelo informados pelo cliente."""

    model_config = ConfigDict(protected_namespaces=())

    provider: Literal["local", "open_router"]
    provider_config: ProviderConfigDTO
    max_tokens: int
    temperature: float = Field(default=_DEFAULT_TEMPERATURE)

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_and_round_temperature(cls, value: float | None) -> float:
        """Normaliza a temperatura recebida, recusando valores fora de `[0, 1]`.

        Args:
            value: Temperatura informada no corpo da requisição.

        Returns:
            float: Temperatura arredondada para uma casa decimal.

        Raises:
            ValueError: Quando a temperatura está fora do intervalo `[0, 1]`.
        """
        if not value:
            return _DEFAULT_TEMPERATURE

        temperature = float(value)
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")

        return round(temperature, 1)
