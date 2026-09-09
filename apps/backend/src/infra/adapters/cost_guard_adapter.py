import logging

from src.domain.entities.llm.tokens_usage import TokensUsage
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

    def authorize(self, phase: ThinkingPhaseEnum) -> BudgetVerdict:
        """Autoriza, ou não, mais uma chamada ao modelo para a fase informada.

        A ordem de avaliação é normativa: tempo de parede, depois número de
        chamadas, depois orçamento de tokens. A primeira violação encontrada é a
        que responde pela negação.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.

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
        if self.__consumed_tokens >= token_ceiling:
            return self.__deny(
                phase=phase,
                limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET,
                reason=(
                    f"Orçamento de tokens esgotado para a fase: {self.__consumed_tokens} consumidos de um "
                    f"teto de {token_ceiling}."
                ),
            )

        return BudgetVerdict(authorized=True)

    def register_call(self, tokens: TokensUsage) -> None:
        """Registra o consumo de uma chamada ao modelo já realizada.

        Args:
            tokens: Consumo de tokens da chamada.
        """
        self.__consumed_tokens += tokens.tokens_input + tokens.tokens_output
        self.__llm_calls += 1

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

    def can_run_additional_planning(self) -> bool:
        """Informa se ainda é possível executar mais uma rodada de C.2.

        Returns:
            bool: `True` quando o limite de rodadas ainda não foi atingido, ainda
            há slot de tarefa disponível e o orçamento autoriza a chamada de C.2.
        """
        if self.__additional_rounds >= self.budget.max_additional_planning_rounds:
            return False
        if self.remaining_task_slots() <= _MINIMUM_REMAINING:
            return False
        return self.authorize(phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING).authorized

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

        Somente C.3 enxerga o orçamento completo; todas as demais fases param antes
        da reserva, o que garante que a resposta final sempre possa ser produzida.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.

        Returns:
            int: Teto de tokens consumidos a partir do qual a fase é negada.
        """
        if phase is ThinkingPhaseEnum.C3_FINAL_ANSWER:
            return self.budget.session_token_budget
        return self.budget.session_token_budget - self.budget.final_answer_token_reserve

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
