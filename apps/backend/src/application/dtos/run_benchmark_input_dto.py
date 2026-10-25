from dataclasses import dataclass

from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class RunBenchmarkInputDTO:
    """Entrada de uma bateria de benchmark, no vocabulário da camada de aplicação.

    Attributes:
        question_count: Quantas questões executar, das primeiras do dataset; `None` executa todas.
        max_parallel: Máximo de questões executadas em paralelo (workers).
        model_name: Modelo usado em todos os fluxos.
        max_tokens: Limite de tokens de saída de cada chamada.
        temperature: Temperatura de geração.
        provider: Provedor que atende as chamadas.
    """

    question_count: int | None
    max_parallel: int
    model_name: str
    max_tokens: int
    temperature: float
    provider: ModelProviderEnum
