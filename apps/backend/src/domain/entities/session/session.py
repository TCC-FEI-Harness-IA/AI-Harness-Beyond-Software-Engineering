from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass
class Session:
    """Representa uma sessão de inferência, baseline ou harness, persistida.

    Attributes:
        id: Identificador único da sessão.
        user_question: Pergunta original enviada pelo usuário.
        flow: Fluxo usado pela sessão (baseline ou marcador do fluxo Ralph).
        model_name: Nome do modelo usado na sessão.
        max_tokens: Limite de tokens de saída configurado para a sessão.
        temperature: Temperatura de geração configurada para a sessão.
        status: Estado atual da sessão.
        created_at: Data e hora de criação em UTC.
        updated_at: Data e hora da última atualização em UTC.
        messages: Histórico de mensagens da sessão, em ordem.
        totals: Totais acumulados da sessão.
        final_answer: Resposta final entregue ao usuário, quando concluída.
        degradations: Degradações ocorridas durante a sessão.
    """

    id: str
    user_question: str
    flow: ThinkingPhaseEnum
    model_name: str
    max_tokens: int
    temperature: float
    status: SessionStatusEnum
    created_at: datetime
    updated_at: datetime
    messages: list[SessionMessage] = field(default_factory=list)
    totals: SessionTotals = field(default_factory=SessionTotals)
    final_answer: str | None = None
    degradations: list[SessionDegradation] = field(default_factory=list)

    def add_message(self, message: SessionMessage) -> None:
        """Anexa uma mensagem ao histórico e atualiza os totais da sessão.

        Args:
            message: Mensagem a ser registrada.
        """
        raise NotImplementedError

    def register_degradation(self, degradation: SessionDegradation) -> None:
        """Registra uma degradação ocorrida durante a sessão.

        Args:
            degradation: Degradação a ser registrada.
        """
        raise NotImplementedError

    def finish(self, status: SessionStatusEnum, final_answer: str | None) -> None:
        """Encerra a sessão com o status e a resposta final informados.

        Args:
            status: Estado final da sessão.
            final_answer: Resposta final entregue ao usuário, quando houver.
        """
        raise NotImplementedError
