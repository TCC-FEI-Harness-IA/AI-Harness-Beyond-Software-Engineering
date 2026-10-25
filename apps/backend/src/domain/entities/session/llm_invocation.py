from dataclasses import dataclass, replace
from datetime import datetime

from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class LLMInvocation:
    """Registro de uma única chamada ao modelo, feito do envio ao desfecho.

    É a fonte única dos totais de chamadas, tokens e tempo da sessão: cada tentativa de
    parsing e cada retentativa de completion vazia é uma invocação, tenha ou não produzido
    uma fase concluída. Consumo ausente permanece `None` (desconhecido), nunca zero.

    Attributes:
        id: Identificador único da invocação.
        phase: Fase de thinking que fez a chamada.
        task_id: Tarefa associada, quando houver.
        context_id: Janela de contexto associada, quando houver.
        model_name: Modelo solicitado.
        provider: Provedor que atendeu a chamada.
        started_at: Instante do envio, em UTC.
        outcome: Desfecho da chamada; `STARTED` enquanto não concluída.
        duration_ms: Duração da chamada, em milissegundos.
        tokens_input: Tokens de entrada informados pelo provedor, ou `None` se desconhecidos.
        tokens_output: Tokens de saída informados pelo provedor, ou `None` se desconhecidos.
        finish_reason: Motivo de término informado pelo provedor, quando há.
        provider_response_id: Identificador da resposta no provedor, quando há.
        temperature: Temperatura efetivamente pedida na chamada — a do usuário ou, numa
            retentativa, a de retentativa —, ou `None` em registros anteriores a este campo.
    """

    id: str
    phase: ThinkingPhaseEnum
    task_id: str | None
    context_id: str | None
    model_name: str
    provider: ModelProviderEnum
    started_at: datetime
    outcome: InvocationOutcomeEnum = InvocationOutcomeEnum.STARTED
    duration_ms: int = 0
    tokens_input: int | None = None
    tokens_output: int | None = None
    finish_reason: str | None = None
    provider_response_id: str | None = None
    temperature: float | None = None

    @property
    def usage_known(self) -> bool:
        """Informa se o provedor reportou algum consumo de tokens.

        Returns:
            bool: `True` quando ao menos um dos consumos é conhecido.
        """
        return self.tokens_input is not None or self.tokens_output is not None

    def complete(
        self,
        outcome: InvocationOutcomeEnum,
        duration_ms: int,
        tokens_input: int | None,
        tokens_output: int | None,
        finish_reason: str | None = None,
        provider_response_id: str | None = None,
    ) -> "LLMInvocation":
        """Devolve a invocação concluída com o desfecho e o consumo informados.

        Args:
            outcome: Desfecho da chamada, diferente de `STARTED`.
            duration_ms: Duração da chamada, em milissegundos.
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            finish_reason: Motivo de término informado pelo provedor, quando há.
            provider_response_id: Identificador da resposta no provedor, quando há.

        Returns:
            LLMInvocation: Cópia concluída; a original não é alterada.

        Raises:
            ValueError: Quando o desfecho é `started` ou a invocação já foi concluída.
        """
        if outcome is InvocationOutcomeEnum.STARTED:
            raise ValueError("Concluir uma invocação exige um desfecho diferente de 'started'.")
        if self.outcome is not InvocationOutcomeEnum.STARTED:
            raise ValueError(f"A invocação '{self.id}' já foi concluída com o desfecho '{self.outcome.value}'.")

        return replace(
            self,
            outcome=outcome,
            duration_ms=duration_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            finish_reason=finish_reason,
            provider_response_id=provider_response_id,
        )
