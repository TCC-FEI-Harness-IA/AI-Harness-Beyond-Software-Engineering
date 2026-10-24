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
    meio do fluxo, entre dois eventos consumidos, para provocar a interrupção
    exatamente no ponto que pretende exercitar. Diferente do guardião real, este
    dublê não deriva nada do consumo registrado: ele só obedece ao que foi programado.
    """

    def __init__(
        self,
        authorized: bool = True,
        denied_limit: BudgetLimitEnum = BudgetLimitEnum.SESSION_TOKEN_BUDGET,
        max_task_attempts: int = _DEFAULT_MAX_TASK_ATTEMPTS,
        task_slots: int = _DEFAULT_TASK_SLOTS,
        tokens_left: int = _DEFAULT_TOKENS_LEFT,
        additional_planning_allowed: bool = True,
        additional_planning_denied_limit: BudgetLimitEnum = BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS,
    ) -> None:
        """Configura o dublê.

        Args:
            authorized: Resposta padrão de `authorize` e `begin_call`.
            denied_limit: Limite apontado quando a autorização nega.
            max_task_attempts: Tentativas máximas por tarefa.
            task_slots: Slots de tarefa ainda disponíveis.
            tokens_left: Tokens ainda disponíveis para o loop.
            additional_planning_allowed: Se `authorize_additional_planning` autoriza.
            additional_planning_denied_limit: Limite apontado quando o planejamento adicional é negado.
        """
        self.authorized = authorized
        self.denied_limit = denied_limit
        self.max_task_attempts = max_task_attempts
        self.task_slots = task_slots
        self.tokens_left = tokens_left
        self.additional_planning_allowed = additional_planning_allowed
        self.additional_planning_denied_limit = additional_planning_denied_limit
        self.authorizations: list[tuple[ThinkingPhaseEnum, int]] = []
        self.started_calls: list[tuple[ThinkingPhaseEnum, int]] = []
        self.registered_usages: list[tuple[int, int]] = []
        self.tasks_created: list[int] = []
        self.attempts_by_task: dict[str, int] = {}
        self.additional_rounds = 0

    def authorize(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Registra a consulta e devolve o veredito programado."""
        self.authorizations.append((phase, reserved_output_tokens))
        return self.__verdict()

    def begin_call(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Registra o início da chamada e devolve o veredito programado."""
        verdict = self.__verdict()
        if verdict.authorized:
            self.started_calls.append((phase, reserved_output_tokens))
        return verdict

    def register_usage(self, tokens_input: int, tokens_output: int) -> None:
        """Registra o consumo de uma chamada ao modelo."""
        self.registered_usages.append((tokens_input, tokens_output))

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

    def authorize_additional_planning(self, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Devolve o veredito programado para o planejamento adicional."""
        if self.additional_planning_allowed:
            return BudgetVerdict(authorized=True)
        return BudgetVerdict(
            authorized=False, limit=self.additional_planning_denied_limit, reason="planejamento negado pelo dublê"
        )

    def register_additional_planning_round(self) -> None:
        """Registra a execução de mais uma rodada de planejamento adicional."""
        self.additional_rounds += 1

    def remaining_task_slots(self) -> int:
        """Devolve os slots de tarefa programados."""
        return self.task_slots

    def remaining_tokens(self) -> int:
        """Devolve os tokens restantes programados."""
        return self.tokens_left

    def __verdict(self) -> BudgetVerdict:
        """Monta o veredito de autorização programado."""
        if self.authorized:
            return BudgetVerdict(authorized=True)
        return BudgetVerdict(authorized=False, limit=self.denied_limit, reason="negado pelo dublê")
