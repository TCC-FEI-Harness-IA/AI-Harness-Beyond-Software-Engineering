from dataclasses import dataclass

from src.domain.enums.session_status_enum import SessionStatusEnum


@dataclass(frozen=True)
class RalphThinkingOutputDTO:
    """Saída do fluxo harness, no vocabulário da camada de aplicação.

    Attributes:
        session_id: Identificador da sessão que executou o fluxo.
        final_answer: Resposta final entregue ao usuário.
        status: Estado final da sessão.
        total_tokens: Total de tokens consumidos pela sessão.
        total_inference_time_ms: Tempo total de inferência da sessão, em milissegundos.
    """

    session_id: str
    final_answer: str
    status: SessionStatusEnum
    total_tokens: int
    total_inference_time_ms: int
