from dataclasses import dataclass

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.gpqa_subset_enum import GPQASubsetEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class RunBenchmarkInputDTO:
    """Entrada de uma bateria de benchmark, no vocabulário da camada de aplicação.

    Attributes:
        question_count: Quantas questões executar; primeiras nos vestibulares, amostra no MMLU/GPQA.
            Com subject_counts, deve coincidir com sua soma; `None` usa as cotas ou executa todas.
        max_parallel: Máximo de questões executadas em paralelo (workers).
        model_name: Modelo usado em todos os fluxos.
        max_tokens: Limite de tokens de cada sessão gerada pela bateria.
        temperature: Temperatura de geração.
        provider: Provedor que atende as chamadas.
        benchmark: Dataset da bateria, vestibular por padrão.
        few_shot: Exemplos dev no prompt MMLU, zero ou cinco.
        subjects: Disciplinas MMLU/GPQA desejadas; vazio seleciona todas.
        sample_seed: Semente da amostragem MMLU/GPQA reproduzível.
        gpqa_subset: Subconjunto GPQA; Diamond por padrão para preservar clientes anteriores.
        subject_counts: Quantidades por matéria ou disciplina; as omitidas não são executadas. No MMLU/GPQA
            cada cota é amostrada com `sample_seed`.
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
    gpqa_subset: GPQASubsetEnum = GPQASubsetEnum.DIAMOND
    subject_counts: dict[str, int] | None = None
