from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class BenchmarkRerunInputDTO(BaseModel):
    """Questões selecionadas para reexecução dentro da mesma bateria."""

    model_config = ConfigDict(extra="forbid")

    question_ids: list[Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]] = Field(
        min_length=1
    )
