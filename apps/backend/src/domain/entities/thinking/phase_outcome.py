from dataclasses import dataclass
from typing import Any

from src.domain.entities.llm.tokens_usage import TokensUsage


@dataclass(frozen=True)
class PhaseOutcome:
    """Representa o resultado da execução de uma `IThinkingPhase`.

    Attributes:
        raw_output: Saída bruta devolvida pelo modelo.
        parsed: Saída da fase já parseada e validada contra o schema esperado.
        tokens: Consumo de tokens da chamada.
        inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
        context_id: Identidade da janela de contexto usada na chamada.
    """

    raw_output: str
    parsed: dict[str, Any]
    tokens: TokensUsage
    inference_time_ms: int
    context_id: str
