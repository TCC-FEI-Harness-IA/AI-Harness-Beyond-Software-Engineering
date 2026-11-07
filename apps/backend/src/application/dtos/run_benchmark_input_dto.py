from dataclasses import dataclass

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class RunBenchmarkInputDTO:
    """Entrada de uma bateria de benchmark, no vocabulário da camada de aplicação.

    Attributes:
        question_count: Quantas questões executar; primeiras nos vestibulares, amostra no MMLU; `None` executa todas.
        max_parallel: Máximo de questões executadas em paralelo (workers).
        model_name: Modelo usado em todos os fluxos.
        max_tokens: Limite de tokens de cada sessão gerada pela bateria.
        temperature: Temperatura de geração.
        provider: Provedor que atende as chamadas.
        benchmark: Dataset da bateria, vestibular por padrão.
        few_shot: Exemplos dev no prompt MMLU, zero ou cinco.
        subjects: Disciplinas MMLU desejadas; vazio seleciona todas.
        sample_seed: Semente da amostragem MMLU reproduzível.
    """

    question_count: int | None
    max_parallel: int
    model_name: str
    max_tokens: int
    temperature: float
    provider: ModelProviderEnum
    benchmark: BenchmarkDatasetEnum = BenchmarkDatasetEnum.VESTIBULAR
    few_shot: int = 0
    subjects: tuple[str, ...] = ()
    sample_seed: int = 42
