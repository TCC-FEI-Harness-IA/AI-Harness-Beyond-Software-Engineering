from dataclasses import dataclass, replace
from datetime import datetime

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class LLMInvocation:
    """Registro de uma única chamada ao modelo, feito do envio ao desfecho.

    É a fonte única dos totais de chamadas, tokens e tempo da sessão: cada tentativa de
    parsing e cada retentativa de completion vazia é uma invocação, tenha ou não produzido
    uma fase concluída. Consumo ausente permanece `None` (desconhecido), nunca zero.

    O desfecho (`outcome`) descreve só a resposta do provedor. A aceitação do conteúdo pelo parser é
    registrada à parte, no diagnóstico: uma chamada `success` pode ter produzido conteúdo recusado.

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
        recovers_invocation_id: Invocação original cuja saída recusada esta chamada tenta recuperar;
            `None` fora de uma recuperação ou em registros anteriores a este campo.
        output_diagnostic: Diagnóstico da saída avaliada pelo parser; `None` quando não houve saída a
            avaliar ou em registros anteriores a este campo (desconhecido, nunca sucesso presumido).
        recovery: Recuperação aplicada à saída recusada, quando houve recusa.
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
    recovers_invocation_id: str | None = None
    output_diagnostic: OutputDiagnostic | None = None
    recovery: OutputRecovery | None = None

    @property
    def content_accepted(self) -> bool | None:
        """Informa se o conteúdo da resposta foi aceito pelo parser.

        Returns:
            bool | None: Aceitação ou recusa do conteúdo, ou `None` quando não há diagnóstico.
        """
        if self.output_diagnostic is None:
            return None
        return self.output_diagnostic.content_accepted

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

    def with_output_diagnostic(self, diagnostic: OutputDiagnostic) -> "LLMInvocation":
        """Devolve a invocação com o diagnóstico da saída que ela produziu.

        Args:
            diagnostic: Diagnóstico da saída avaliada pelo parser.

        Returns:
            LLMInvocation: Cópia diagnosticada; a original não é alterada.

        Raises:
            ValueError: Quando a chamada não terminou com resposta do provedor (`success`) ou já
                tem diagnóstico: cada saída é diagnosticada uma única vez.
        """
        if self.outcome is not InvocationOutcomeEnum.SUCCESS:
            raise ValueError(
                f"Só uma invocação concluída com '{InvocationOutcomeEnum.SUCCESS.value}' tem saída a diagnosticar; "
                f"'{self.id}' está em '{self.outcome.value}'."
            )
        if self.output_diagnostic is not None:
            raise ValueError(f"A invocação '{self.id}' já tem diagnóstico de saída.")
        return replace(self, output_diagnostic=diagnostic)

    def with_recovery(self, recovery: OutputRecovery) -> "LLMInvocation":
        """Devolve a invocação com a recuperação aplicada à sua saída recusada.

        Args:
            recovery: Estratégia e resultado da recuperação.

        Returns:
            LLMInvocation: Cópia atualizada; a original não é alterada.

        Raises:
            ValueError: Quando a saída não foi recusada ou a recuperação já tem resultado final.
        """
        if self.content_accepted is not False:
            raise ValueError(f"Só uma saída recusada recebe recuperação; '{self.id}' não tem saída recusada.")
        if self.recovery is not None and self.recovery.is_final:
            raise ValueError(
                f"A recuperação da invocação '{self.id}' já tem resultado final '{self.recovery.result.value}'."
            )
        return replace(self, recovery=recovery)
