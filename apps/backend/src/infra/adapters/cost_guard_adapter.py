import logging

from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.cost_guard_interface import ICostGuard


class CostGuardAdapter(ICostGuard):
    """Adapter de `ICostGuard` que aplica a política de resiliência de custo."""

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

    def authorize(self, phase: ThinkingPhaseEnum) -> BudgetVerdict:
        """Autoriza, ou não, mais uma chamada ao modelo para a fase informada.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.

        Returns:
            BudgetVerdict: Veredito da autorização.
        """
        raise NotImplementedError

    def register_call(self, tokens: TokensUsage) -> None:
        """Registra o consumo de uma chamada ao modelo já realizada.

        Args:
            tokens: Consumo de tokens da chamada.
        """
        raise NotImplementedError

    def register_task_created(self, quantity: int) -> None:
        """Registra a criação de novas tarefas na sessão.

        Args:
            quantity: Quantidade de tarefas criadas.
        """
        raise NotImplementedError

    def register_task_attempt(self, task_id: str) -> int:
        """Registra mais uma tentativa de resolução de uma tarefa.

        Args:
            task_id: Identificador da tarefa tentada.

        Returns:
            int: Número da tentativa recém-registrada.
        """
        raise NotImplementedError

    def can_retry_task(self, task_id: str) -> bool:
        """Informa se a tarefa ainda pode ser retentada.

        Args:
            task_id: Identificador da tarefa avaliada.

        Returns:
            bool: `True` quando o limite de tentativas ainda não foi atingido.
        """
        raise NotImplementedError

    def can_run_additional_planning(self) -> bool:
        """Informa se ainda é possível executar mais uma rodada de C.2.

        Returns:
            bool: `True` quando o limite de rodadas ainda não foi atingido.
        """
        raise NotImplementedError

    def register_additional_planning_round(self) -> None:
        """Registra a execução de mais uma rodada de planejamento adicional."""
        raise NotImplementedError

    def remaining_task_slots(self) -> int:
        """Quantidade de tarefas ainda disponíveis dentro do limite da sessão.

        Returns:
            int: Quantidade de tarefas que ainda podem ser criadas.
        """
        raise NotImplementedError

    def remaining_tokens(self) -> int:
        """Tokens ainda disponíveis para o loop, já descontada a reserva.

        Returns:
            int: Tokens ainda disponíveis, já descontada a reserva da resposta final.
        """
        raise NotImplementedError
