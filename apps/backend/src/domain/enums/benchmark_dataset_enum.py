from enum import StrEnum


class BenchmarkDatasetEnum(StrEnum):
    """Datasets disponíveis para comparação entre inferência simples e Ralph."""

    VESTIBULAR = "vestibular"
    MMLU = "mmlu"
