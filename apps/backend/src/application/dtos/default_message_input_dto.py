from dataclasses import dataclass


@dataclass(frozen=True)
class DefaultMessageInputDTO:
    """Entrada do fluxo baseline, no vocabulário da camada de aplicação.

    Attributes:
        user_input: Pergunta enviada pelo usuário.
        model_name: Nome do modelo a ser usado na chamada.
        max_tokens: Limite de tokens de saída.
        temperature: Temperatura da geração.
    """

    user_input: str
    model_name: str
    max_tokens: int
    temperature: float
