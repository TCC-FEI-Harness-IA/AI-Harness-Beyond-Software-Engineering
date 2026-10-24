from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
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
        degradations: Degradações registradas por versões anteriores do fluxo, apenas para leitura.
        provider: Provedor efetivo das chamadas; `None` em sessões anteriores ao registro.
        invocations: Uma entrada por chamada enviada ao modelo, na ordem do envio.
        failure: Motivo estruturado do encerramento sem conclusão, quando houve.
        legacy_totals: Indica que os totais vêm de uma sessão gravada antes do registro por
            invocação, e por isso não têm chamadas individuais correspondentes.
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
    provider: ModelProviderEnum | None = None
    invocations: list[LLMInvocation] = field(default_factory=list)
    failure: SessionFailure | None = None
    legacy_totals: bool = False

    def add_message(self, message: SessionMessage) -> None:
        """Anexa uma mensagem ao histórico e atualiza os totais da sessão.

        Args:
            message: Mensagem a ser registrada.
        """
        self.messages.append(message)
        self.totals.add_message(message=message)
        self.updated_at = message.timestamp

    def start_invocation(self, invocation: LLMInvocation) -> None:
        """Registra o envio de uma chamada ao modelo, que já conta nos totais.

        Args:
            invocation: Invocação recém-iniciada.
        """
        self.invocations.append(invocation)
        self.totals.register_invocation_start()
        self.updated_at = invocation.started_at

    def complete_invocation(
        self,
        invocation_id: str,
        outcome: InvocationOutcomeEnum,
        duration_ms: int,
        tokens_input: int | None,
        tokens_output: int | None,
        finish_reason: str | None = None,
        provider_response_id: str | None = None,
    ) -> LLMInvocation:
        """Conclui uma invocação já registrada e acumula o seu consumo conhecido.

        Args:
            invocation_id: Identificador da invocação iniciada.
            outcome: Desfecho da chamada.
            duration_ms: Duração da chamada, em milissegundos.
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            finish_reason: Motivo de término informado pelo provedor, quando há.
            provider_response_id: Identificador da resposta no provedor, quando há.

        Returns:
            LLMInvocation: Invocação concluída, já substituída no registro.

        Raises:
            ValueError: Quando a invocação não existe ou já foi concluída.
        """
        for index, invocation in enumerate(self.invocations):
            if invocation.id == invocation_id:
                completed = invocation.complete(
                    outcome=outcome,
                    duration_ms=duration_ms,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    finish_reason=finish_reason,
                    provider_response_id=provider_response_id,
                )
                self.invocations[index] = completed
                self.totals.add_usage(tokens_input=tokens_input, tokens_output=tokens_output, duration_ms=duration_ms)
                return completed

        raise ValueError(f"A invocação '{invocation_id}' não pertence à sessão '{self.id}'.")

    def finish(
        self,
        status: SessionStatusEnum,
        final_answer: str | None,
        failure: SessionFailure | None = None,
    ) -> None:
        """Encerra a sessão com o status e a resposta final informados.

        Args:
            status: Estado final da sessão.
            final_answer: Resposta final entregue ao usuário, quando houver.
            failure: Motivo estruturado do encerramento sem conclusão, quando houver.

        Raises:
            ValueError: Quando a sessão já não está em execução ou quando uma falha é
                informada para um status diferente de `failed`.
        """
        if self.status is not SessionStatusEnum.RUNNING:
            raise ValueError(f"Sessão '{self.id}' já foi encerrada com status '{self.status.value}'.")
        if failure is not None and status is not SessionStatusEnum.FAILED:
            raise ValueError(f"Uma falha só pode ser registrada em uma sessão '{SessionStatusEnum.FAILED.value}'.")

        self.status = status
        self.final_answer = final_answer
        self.failure = failure
        self.updated_at = datetime.now(tz=UTC)

    def reopen(self, updated_at: datetime) -> None:
        """Desfaz um encerramento que não chegou a ser persistido, devolvendo a sessão à execução.

        Uma sessão só vale como encerrada depois de gravada. Quando a gravação falha, o estado em
        memória volta a ser o do último estado persistido, para que a falha possa ser tratada e a
        sessão encerrada por outro caminho (por exemplo, como `failed`).

        Args:
            updated_at: Instante da última atualização anterior ao encerramento desfeito.

        Raises:
            ValueError: Quando a sessão já está em execução, sem encerramento a desfazer.
        """
        if self.status is SessionStatusEnum.RUNNING:
            raise ValueError(f"Sessão '{self.id}' ainda está em execução: não há encerramento a desfazer.")

        self.status = SessionStatusEnum.RUNNING
        self.final_answer = None
        self.failure = None
        self.updated_at = updated_at
