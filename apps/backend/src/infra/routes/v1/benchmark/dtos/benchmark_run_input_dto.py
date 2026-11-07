from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.gpqa_subset_enum import GPQASubsetEnum
from src.infra.routes.v1.message.dtos.model_config_dto import ModelConfigDTO

_DEFAULT_MAX_PARALLEL = 5
_MIN_VALUE = 1


class BenchmarkRunInputDTO(BaseModel):
    """Frame de abertura do WebSocket de benchmark, enviado uma única vez.

    `subject_counts` escolhe quantidades por matéria nos vestibulares; `question_count`, se enviado,
    deve coincidir com a soma das cotas. Sem cotas, `question_count` ausente executa todas as questões
    do dataset; um valor menor executa as
    primeiras nos vestibulares ou uma amostra estratificada no MMLU/GPQA. `max_parallel` limita questões
    em execução ao mesmo tempo. Os limites dependem do dataset e de `RALPH_BENCHMARK_MAX_PARALLEL`, e são
    conferidos pelo caso de uso.
    """

    model_config = ConfigDict(protected_namespaces=())

    question_count: int | None = Field(default=None, ge=_MIN_VALUE)
    max_parallel: int = Field(default=_DEFAULT_MAX_PARALLEL, ge=_MIN_VALUE)
    llm_model_config: ModelConfigDTO
    benchmark: BenchmarkDatasetEnum = BenchmarkDatasetEnum.VESTIBULAR
    few_shot: Literal[0, 5] = 0
    subjects: list[str] = Field(default_factory=list)
    sample_seed: int = Field(default=42, ge=0, le=2**32 - 1)
    gpqa_subset: GPQASubsetEnum = GPQASubsetEnum.DIAMOND
    subject_counts: dict[str, Annotated[int, Field(strict=True, ge=0)]] | None = None

    @model_validator(mode="after")
    def validate_protocol(self) -> Self:
        """Confere os protocolos suportados por cada dataset."""
        if self.benchmark is BenchmarkDatasetEnum.GPQA and self.few_shot:
            raise ValueError("GPQA aceita somente few_shot 0.")
        if self.benchmark is not BenchmarkDatasetEnum.GPQA and self.gpqa_subset is not GPQASubsetEnum.DIAMOND:
            raise ValueError("gpqa_subset é uma opção exclusiva do GPQA.")
        if self.benchmark is BenchmarkDatasetEnum.VESTIBULAR and (self.few_shot or self.subjects):
            raise ValueError("Vestibulares não aceita few_shot ou subjects.")
        if self.subject_counts is not None and self.benchmark is not BenchmarkDatasetEnum.VESTIBULAR:
            raise ValueError("subject_counts é uma opção exclusiva de Vestibulares.")
        return self
