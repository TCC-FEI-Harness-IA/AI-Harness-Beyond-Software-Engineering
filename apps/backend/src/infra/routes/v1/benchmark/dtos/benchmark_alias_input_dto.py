from pydantic import BaseModel, ConfigDict, Field


class BenchmarkAliasInputDTO(BaseModel):
    """Alias opcional; texto vazio ou nulo remove o título da bateria."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    alias: str | None = Field(..., max_length=120)
