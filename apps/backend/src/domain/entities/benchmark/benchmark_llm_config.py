from dataclasses import dataclass

from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class BenchmarkLLMConfig:
    """Configuração do modelo usada em todos os fluxos de uma bateria de benchmark.

    Attributes:
        model_name: Modelo pedido em todas as chamadas.
        provider: Provedor que atende as chamadas.
        max_tokens: Limite de tokens de saída de cada chamada.
        temperature: Temperatura de geração.
    """

    model_name: str
    provider: ModelProviderEnum
    max_tokens: int
    temperature: float
