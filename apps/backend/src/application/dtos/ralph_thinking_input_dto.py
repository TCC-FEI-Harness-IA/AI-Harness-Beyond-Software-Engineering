from dataclasses import dataclass

from src.domain.enums.model_provider_enum import ModelProviderEnum


@dataclass(frozen=True)
class RalphThinkingInputDTO:
    """Entrada do fluxo harness, no vocabulário da camada de aplicação.

    Attributes:
        user_input: Pergunta enviada pelo usuário.
        model_name: Nome do modelo a ser usado na sessão.
        max_tokens: Limite de tokens de saída.
        temperature: Temperatura da geração.
        provider: Provedor que atende todas as chamadas da sessão.
    """

    user_input: str
    model_name: str
    max_tokens: int
    temperature: float
    provider: ModelProviderEnum
