from dataclasses import dataclass
from typing import Any

from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.thinking.invalid_output import InvalidOutput


@dataclass(frozen=True)
class PhaseOutcome:
    """Representa o resultado da execução de uma `IThinkingPhase`.

    O consumo e o tempo aqui são uma agregação das chamadas da fase, para exibição; o
    registro de cada chamada e os totais da sessão vêm das invocações.

    Attributes:
        raw_output: Saída bruta devolvida pelo modelo.
        parsed: Saída da fase já parseada e validada contra o schema esperado.
        tokens: Consumo de tokens agregado das chamadas da fase.
        inference_time_ms: Tempo agregado das chamadas da fase, em milissegundos.
        context_id: Identidade da janela de contexto usada na chamada.
        invalid_outputs: Saídas recusadas pelo parser e corrigidas antes da saída válida.
    """

    raw_output: str
    parsed: dict[str, Any]
    tokens: TokensUsage
    inference_time_ms: int
    context_id: str
    invalid_outputs: tuple[InvalidOutput, ...] = ()
