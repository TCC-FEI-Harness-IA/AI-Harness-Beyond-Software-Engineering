import logging

from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.cost_guard_interface import ICostGuard

_MILLISECONDS_PER_SECOND = 1000
_INITIAL_COUNTER = 0
_NO_ATTEMPTS = 0
_MINIMUM_REMAINING = 0
_FIRST_ATTEMPT = 1
_NO_RESERVED_OUTPUT = 0


class CostGuardAdapter(ICostGuard):
    """Adapter de `ICostGuard` que aplica a política de resiliência de custo.

    O guardião é instanciado uma vez por sessão: o marco de tempo capturado na
    construção é o início da sessão, e os contadores acompanham o consumo dessa
    sessão do começo ao fim.
    """

    def __init__(self, budget: CostBudget, clock: IClock, logger: logging.Logger) -> None:
        """Inicializa o adapter.

        Args:
            budget: Snapshot dos limites de custo configurados para a sessão.
            clock: Fonte de tempo do domínio, usada para medir o timeout de sessão.
            logger: Logger do módulo.
        """
        self.budget: CostBudget = budget
        self.clock: IClock = clock
        self.logger = logger
        self.__consumed_tokens: int = _INITIAL_COUNTER
        self.__llm_calls: int = _INITIAL_COUNTER
        self.__tasks_created: int = _INITIAL_COUNTER
        self.__additional_rounds: int = _INITIAL_COUNTER
        self.__attempts_by_task: dict[str, int] = {}
        self.__started_at_ms: int = clock.monotonic_ms()

    def authorize(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = _NO_RESERVED_OUTPUT) -> BudgetVerdict:
        """Consulta se uma chamada ao modelo para a fase informada seria autorizada.

        A ordem de avaliação é normativa: tempo de parede, depois número de
        chamadas, depois orçamento de tokens. A primeira violação encontrada é a
        que responde pela negação. A consulta não conta a chamada.

        O teto de tokens considera o consumo já contabilizado mais o teto de saída da
        chamada. A entrada não é estimada (não há tokenizador confiável), então o consumo
        real pode divergir do cálculo e ultrapassar o teto em até o tamanho da entrada.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.
            reserved_output_tokens: Tokens de saída que a chamada pode produzir, no máximo.

        Returns:
            BudgetVerdict: Veredito da autorização.
        """
        elapsed_ms = self.clock.monotonic_ms() - self.__started_at_ms
        timeout_ms = self.budget.session_timeout_seconds * _MILLISECONDS_PER_SECOND
        if elapsed_ms >= timeout_ms:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.SESSION_TIMEOUT,
                reason=f"Tempo de parede da sessão esgotado: {elapsed_ms}ms de um máximo de {timeout_ms}ms.",
            )

        if self.__llm_calls >= self.budget.max_llm_calls_per_session:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.LLM_CALLS_PER_SESSION,
                reason=(
                    f"Teto de chamadas ao modelo atingido: {self.__llm_calls} de um máximo de "
                    f"{self.budget.max_llm_calls_per_session}."
                ),
            )

        token_ceiling = self.__token_ceiling(phase=phase)
        projected = self.__consumed_tokens + reserved_output_tokens
        if self.__consumed_tokens >= token_ceiling or projected > token_ceiling:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET,
                reason=self.__token_reason(
                    phase=phase, token_ceiling=token_ceiling, reserved_output_tokens=reserved_output_tokens
                ),
            )

        return BudgetVerdict(authorized=True)

    def begin_call(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = _NO_RESERVED_OUTPUT) -> BudgetVerdict:
        """Autoriza e, se autorizada, já conta uma chamada ao modelo, numa só operação.

        Args:
            phase: Fase de thinking que vai chamar o modelo.
            reserved_output_tokens: Tokens de saída que a chamada pode produzir, no máximo.

        Returns:
            BudgetVerdict: Veredito da autorização; só uma chamada autorizada é contada.
        """
        verdict = self.authorize(phase=phase, reserved_output_tokens=reserved_output_tokens)
        if verdict.authorized:
            self.__llm_calls += 1
        return verdict

    def register_usage(self, tokens_input: int, tokens_output: int) -> None:
        """Contabiliza o consumo conhecido de uma chamada já iniciada com `begin_call`.

        Args:
            tokens_input: Tokens de entrada informados pelo provedor.
            tokens_output: Tokens de saída informados pelo provedor.
        """
        self.__consumed_tokens += tokens_input + tokens_output

    def register_task_created(self, quantity: int) -> None:
        """Registra a criação de novas tarefas na sessão.

        Args:
            quantity: Quantidade de tarefas criadas.
        """
        self.__tasks_created += quantity

    def register_task_attempt(self, task_id: str) -> int:
        """Registra mais uma tentativa de resolução de uma tarefa.

        Args:
            task_id: Identificador da tarefa tentada.

        Returns:
            int: Número da tentativa recém-registrada, contado a partir de um.
        """
        attempt = self.__attempts_by_task.get(task_id, _NO_ATTEMPTS) + _FIRST_ATTEMPT
        self.__attempts_by_task[task_id] = attempt
        return attempt

    def can_retry_task(self, task_id: str) -> bool:
        """Informa se a tarefa ainda pode ser retentada.

        Args:
            task_id: Identificador da tarefa avaliada.

        Returns:
            bool: `True` quando o limite de tentativas ainda não foi atingido.
        """
        return self.__attempts_by_task.get(task_id, _NO_ATTEMPTS) < self.budget.max_task_attempts

    def authorize_additional_planning(self, reserved_output_tokens: int = _NO_RESERVED_OUTPUT) -> BudgetVerdict:
        """Consulta se ainda é possível executar mais uma rodada de C.2, e por que não.

        A causa vem do próprio veredito, na ordem: rodadas, slots de tarefa e, por fim, a
        autorização da chamada de C.2 (tempo, chamadas ou tokens). Assim a causa registrada
        é sempre a que de fato impediu a rodada.

        Args:
            reserved_output_tokens: Tokens de saída que a chamada de C.2 pode produzir, no máximo.

        Returns:
            BudgetVerdict: Autorizado, ou negado com o limite responsável.
        """
        phase = ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING
        if self.__additional_rounds >= self.budget.max_additional_planning_rounds:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS,
                reason=(
                    f"Rodadas de planejamento adicional esgotadas: {self.__additional_rounds} de um máximo de "
                    f"{self.budget.max_additional_planning_rounds}."
                ),
            )
        if self.remaining_task_slots() <= _MINIMUM_REMAINING:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.TASKS_PER_SESSION,
                reason=(
                    f"Não há espaço para novas tarefas: {self.__tasks_created} criadas de um máximo de "
                    f"{self.budget.max_tasks_per_session}."
                ),
            )
        return self.authorize(phase=phase, reserved_output_tokens=reserved_output_tokens)

    def register_additional_planning_round(self) -> None:
        """Registra a execução de mais uma rodada de planejamento adicional."""
        self.__additional_rounds += 1

    def remaining_task_slots(self) -> int:
        """Quantidade de tarefas ainda disponíveis dentro do limite da sessão.

        Returns:
            int: Quantidade de tarefas que ainda podem ser criadas, nunca negativa.
        """
        return max(_MINIMUM_REMAINING, self.budget.max_tasks_per_session - self.__tasks_created)

    def remaining_tokens(self) -> int:
        """Tokens ainda disponíveis para o loop, já descontada a reserva.

        Returns:
            int: Tokens ainda disponíveis para o loop, nunca negativo. A reserva da
            resposta final é sempre descontada, por ser intocável pelo loop.
        """
        available = self.budget.session_token_budget - self.budget.final_answer_token_reserve
        return max(_MINIMUM_REMAINING, available - self.__consumed_tokens)

    def __token_ceiling(self, phase: ThinkingPhaseEnum) -> int:
        """Devolve o teto de tokens aplicável à fase informada.

        Somente C.3 enxerga o orçamento completo; todas as demais fases param antes da
        reserva. A reserva é uma margem de melhor esforço para a síntese: ela não garante
        que C.3 será alcançada, pois C.1 também precisa de recursos antes dela.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.

        Returns:
            int: Teto de tokens consumidos a partir do qual a fase é negada.
        """
        if phase is ThinkingPhaseEnum.C3_FINAL_ANSWER:
            return self.budget.session_token_budget
        return self.budget.session_token_budget - self.budget.final_answer_token_reserve

    def __token_reason(self, phase: ThinkingPhaseEnum, token_ceiling: int, reserved_output_tokens: int) -> str:
        """Descreve a negação por tokens, distinguindo o orçamento de trabalho do orçamento total.

        Args:
            phase: Fase de thinking que teve a autorização negada.
            token_ceiling: Teto aplicado à fase.
            reserved_output_tokens: Tokens de saída considerados na conta.

        Returns:
            str: Motivo legível da negação.
        """
        counted = (
            f"{self.__consumed_tokens} consumidos e {reserved_output_tokens} reservados para a saída, "
            f"de um teto de {token_ceiling}"
        )
        if phase is ThinkingPhaseEnum.C3_FINAL_ANSWER:
            return f"Orçamento total da sessão esgotado: {counted}."
        return (
            f"Orçamento de trabalho esgotado (a reserva de {self.budget.final_answer_token_reserve} tokens "
            f"fica para C.3): {counted}."
        )

    def __deny(self, phase: ThinkingPhaseEnum, limit: BudgetLimitEnum, reason: str) -> BudgetVerdict:
        """Monta o veredito negativo e registra o rastro de auditoria da negação.

        Args:
            phase: Fase de thinking que teve a autorização negada.
            limit: Limite responsável pela negação.
            reason: Motivo legível da negação.

        Returns:
            BudgetVerdict: Veredito negativo já identificado pelo limite.
        """
        self.logger.warning(
            "Autorização negada na fase '%s' pelo limite '%s': %s "
            "(tokens_consumidos=%d, chamadas=%d, tarefas_criadas=%d, rodadas_adicionais=%d)",
            phase.value,
            limit.value,
            reason,
            self.__consumed_tokens,
            self.__llm_calls,
            self.__tasks_created,
            self.__additional_rounds,
        )
        return BudgetVerdict(authorized=False, limit=limit, reason=reason)
