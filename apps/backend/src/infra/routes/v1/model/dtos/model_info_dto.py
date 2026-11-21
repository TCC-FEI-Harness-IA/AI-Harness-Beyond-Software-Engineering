from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities.llm.model_info import ModelInfo


class ModelInfoFieldsDTO(BaseModel):
    """Informações editáveis de um modelo do catálogo; campos ausentes ficam desconhecidos."""

    model_config = ConfigDict(protected_namespaces=())

    display_name: str | None = None
    input_price_per_million_tokens: float | None = Field(default=None, ge=0)
    output_price_per_million_tokens: float | None = Field(default=None, ge=0)
    context_length: int | None = Field(default=None, gt=0)
    throughput_tokens_per_second: float | None = Field(default=None, gt=0)

    def to_entity(self, model_name: str) -> ModelInfo:
        """Converte o corpo da requisição na entidade de domínio.

        Args:
            model_name: Identificador do modelo, vindo do corpo (cadastro) ou do caminho (edição).

        Returns:
            ModelInfo: Modelo com nome amigável vazio normalizado para `None`.
        """
        display_name = (self.display_name or "").strip() or None
        return ModelInfo(
            model_name=model_name.strip(),
            display_name=display_name,
            input_price_per_million_tokens=self.input_price_per_million_tokens,
            output_price_per_million_tokens=self.output_price_per_million_tokens,
            context_length=self.context_length,
            throughput_tokens_per_second=self.throughput_tokens_per_second,
        )


class ModelInfoInputDTO(ModelInfoFieldsDTO):
    """Corpo de `POST /v1/models`: o identificador do modelo e as suas informações."""

    model_name: str = Field(min_length=1)
