from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.config.settings import Settings
from src.infra.routes.v1.message.dtos.provider_config_dto import ProviderConfigDTO

_DEFAULT_TEMPERATURE = 0.7


class ModelConfigDTO(BaseModel):
    """Parâmetros do modelo informados pelo cliente."""

    model_config = ConfigDict(protected_namespaces=())

    # O enum é o próprio contrato: um provedor sem implementação por trás vira `422`
    # na fronteira, em vez de falhar na hora de escolher o serviço.
    provider: ModelProviderEnum
    provider_config: ProviderConfigDTO
    # Limite de tokens (entrada + saída) da sessão inteira, e não de cada chamada ao modelo.
    max_tokens: int = Field(gt=0)
    temperature: float = Field(default=_DEFAULT_TEMPERATURE)

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, value: int) -> int:
        """Recusa um limite de tokens da sessão acima do teto do backend.

        Args:
            value: Limite de tokens da sessão informado no corpo da requisição.

        Returns:
            int: O próprio limite, quando cabe no teto.

        Raises:
            ValueError: Quando o limite passa de `LLM_MAX_TOKENS`.
        """
        backend_limit = Settings().llm_max_tokens
        if value > backend_limit:
            raise ValueError(f"max_tokens não pode passar do limite de tokens por sessão do backend ({backend_limit})")
        return value

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature(cls, value: float | None) -> float:
        """Valida a temperatura recebida, aplicando o default apenas à ausência.

        Zero é uma temperatura válida e pedida de propósito, e por isso é preservado; só `None`
        (ausente) recebe o default. O valor não é arredondado.

        Args:
            value: Temperatura informada no corpo da requisição.

        Returns:
            float: Temperatura exatamente como solicitada, ou o default quando ausente.

        Raises:
            ValueError: Quando a temperatura está fora do intervalo `[0, 1]` ou não é finita.
        """
        if value is None:
            return _DEFAULT_TEMPERATURE

        temperature = float(value)
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")

        return temperature
