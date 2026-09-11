from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.cost_guard_interface import ICostGuard

_DEFAULT_MAX_TASK_ATTEMPTS = 3
_DEFAULT_TASK_SLOTS = 12
_DEFAULT_TOKENS_LEFT = 100_000
_NO_ATTEMPTS = 0


class FakeCostGuard(ICostGuard):
    """Dublê de `ICostGuard` com vereditos e limites diretamente programáveis.

    Todos os limites são atributos públicos mutáveis: o teste pode apertá-los no
    meio do fluxo, entre dois eventos consumidos, para provocar a degradação
    exatamente no ponto que pretende exercitar.
    """

    def __init__(
        self,
        authorized: bool = True,
        denied_limit: BudgetLimitEnum = BudgetLimitEnum.SESSION_TOKEN_BUDGET,
        max_task_attempts: int = _DEFAULT_MAX_TASK_ATTEMPTS,
        task_slots: int = _DEFAULT_TASK_SLOTS,
        tokens_left: int = _DEFAULT_TOKENS_LEFT,
        additional_planning_allowed: bool = True,
    ) -> None:
        """Configura o dublê.

        Args:
            authorized: Resposta padrão de `authorize`.
            denied_limit: Limite apontado quando `authorize` nega.
            max_task_attempts: Tentativas máximas por tarefa.
            task_slots: Slots de tarefa ainda disponíveis.
            tokens_left: Tokens ainda disponíveis para o loop.
            additional_planning_allowed: Resposta de `can_run_additional_planning`.
        """
        self.authorized = authorized
        self.denied_limit = denied_limit
        self.max_task_attempts = max_task_attempts
        self.task_slots = task_slots
        self.tokens_left = tokens_left
        self.additional_planning_allowed = additional_planning_allowed
        self.authorizations: list[ThinkingPhaseEnum] = []
        self.registered_calls: list[TokensUsage] = []
        self.tasks_created: list[int] = []
        self.attempts_by_task: dict[str, int] = {}
        self.additional_rounds = 0

    def authorize(self, phase: ThinkingPhaseEnum) -> BudgetVerdict:
        """Registra o pedido e devolve o veredito programado."""
        self.authorizations.append(phase)

        if self.authorized:
            return BudgetVerdict(authorized=True)
        return BudgetVerdict(authorized=False, limit=self.denied_limit, reason="negado pelo dublê")

    def register_call(self, tokens: TokensUsage) -> None:
        """Registra o consumo de uma chamada ao modelo."""
        self.registered_calls.append(tokens)

    def register_task_created(self, quantity: int) -> None:
        """Registra a criação de novas tarefas."""
        self.tasks_created.append(quantity)

    def register_task_attempt(self, task_id: str) -> int:
        """Registra mais uma tentativa da tarefa e devolve o número dela."""
        attempt = self.attempts_by_task.get(task_id, _NO_ATTEMPTS) + 1
        self.attempts_by_task[task_id] = attempt
        return attempt

    def can_retry_task(self, task_id: str) -> bool:
        """Informa se a tarefa ainda pode ser retentada."""
        return self.attempts_by_task.get(task_id, _NO_ATTEMPTS) < self.max_task_attempts

    def can_run_additional_planning(self) -> bool:
        """Informa se ainda é possível executar mais uma rodada de C.2."""
        return self.additional_planning_allowed

    def register_additional_planning_round(self) -> None:
        """Registra a execução de mais uma rodada de planejamento adicional."""
        self.additional_rounds += 1

    def remaining_task_slots(self) -> int:
        """Devolve os slots de tarefa programados."""
        return self.task_slots

    def remaining_tokens(self) -> int:
        """Devolve os tokens restantes programados."""
        return self.tokens_left
