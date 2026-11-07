from dataclasses import dataclass

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum


@dataclass(frozen=True)
class BenchmarkDefinition:
    """Proveniência e protocolo de uma bateria, preservados junto dos resultados."""

    dataset: BenchmarkDatasetEnum = BenchmarkDatasetEnum.VESTIBULAR
    revision: str = "vestibular-v1"
    protocol: str = "generative_0shot"
    split: str = "test"
    few_shot: int = 0
    subjects: tuple[str, ...] = ()
    sample_seed: int | None = None
