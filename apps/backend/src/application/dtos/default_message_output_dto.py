from dataclasses import dataclass


@dataclass(frozen=True)
class DefaultMessageOutputDTO:
    """Saída do fluxo baseline, no vocabulário da camada de aplicação.

    Attributes:
        message: Pergunta original do usuário.
        response: Texto produzido pelo modelo.
        tokens_input: Tokens consumidos na entrada.
        tokens_output: Tokens consumidos na saída.
        inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
    """

    message: str
    response: str
    tokens_input: int
    tokens_output: int
    inference_time_ms: int
