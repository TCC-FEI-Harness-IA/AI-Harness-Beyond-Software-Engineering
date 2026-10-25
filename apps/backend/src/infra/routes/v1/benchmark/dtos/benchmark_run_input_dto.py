from pydantic import BaseModel, ConfigDict, Field

from src.infra.routes.v1.message.dtos.model_config_dto import ModelConfigDTO

_DEFAULT_MAX_PARALLEL = 5
_MIN_VALUE = 1


class BenchmarkRunInputDTO(BaseModel):
    """Frame de abertura do WebSocket de benchmark, enviado uma única vez.

    `question_count` ausente executa todas as questões do dataset; um valor menor executa as
    primeiras, na ordem do dataset. `max_parallel` é o máximo de questões em execução ao mesmo
    tempo. Os limites superiores dependem do dataset e de `RALPH_BENCHMARK_MAX_PARALLEL`, e são
    conferidos pelo caso de uso.
    """

    model_config = ConfigDict(protected_namespaces=())

    question_count: int | None = Field(default=None, ge=_MIN_VALUE)
    max_parallel: int = Field(default=_DEFAULT_MAX_PARALLEL, ge=_MIN_VALUE)
    llm_model_config: ModelConfigDTO
