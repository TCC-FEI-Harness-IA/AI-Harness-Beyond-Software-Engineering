from abc import ABC, abstractmethod

from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class ICostGuard(ABC):
    """Contrato do ponto único de decisão sobre limites de custo da sessão."""

    @abstractmethod
    def authorize(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Consulta se uma chamada ao modelo para a fase informada seria autorizada.

        É uma consulta sem efeito: não conta a chamada. Quem de fato vai chamar o modelo
        usa `begin_call`.

        Args:
            phase: Fase de thinking que pretende chamar o modelo.
            reserved_output_tokens: Tokens de saída que a chamada pode produzir, no máximo. A
                entrada não é estimada, então a contabilização real pode divergir deste cálculo.

        Returns:
            BudgetVerdict: Veredito da autorização.
        """
        raise NotImplementedError

    @abstractmethod
    def begin_call(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Autoriza e, se autorizada, já conta uma chamada ao modelo, numa só operação.

        A chamada é contada no envio, e não na resposta: uma chamada que devolve conteúdo
        vazio, JSON inválido ou erro também consumiu o limite. Uma negação não conta nada.

        Args:
            phase: Fase de thinking que vai chamar o modelo.
            reserved_output_tokens: Tokens de saída que a chamada pode produzir, no máximo.

        Returns:
            BudgetVerdict: Veredito da autorização.
        """
        raise NotImplementedError

    @abstractmethod
    def register_usage(self, tokens_input: int, tokens_output: int) -> None:
        """Contabiliza o consumo conhecido de uma chamada já iniciada com `begin_call`.

        Args:
            tokens_input: Tokens de entrada informados pelo provedor.
            tokens_output: Tokens de saída informados pelo provedor.
        """
        raise NotImplementedError

    @abstractmethod
    def register_task_created(self, quantity: int) -> None:
        """Registra a criação de novas tarefas na sessão.

        Args:
            quantity: Quantidade de tarefas criadas.
        """
        raise NotImplementedError

    @abstractmethod
    def register_task_attempt(self, task_id: str) -> int:
        """Registra mais uma tentativa de resolução de uma tarefa.

        Args:
            task_id: Identificador da tarefa tentada.

        Returns:
            int: Número da tentativa recém-registrada.
        """
        raise NotImplementedError

    @abstractmethod
    def can_retry_task(self, task_id: str) -> bool:
        """Informa se a tarefa ainda pode ser retentada.

        Args:
            task_id: Identificador da tarefa avaliada.

        Returns:
            bool: `True` quando o limite de tentativas ainda não foi atingido.
        """
        raise NotImplementedError

    @abstractmethod
    def authorize_additional_planning(self, reserved_output_tokens: int = 0) -> BudgetVerdict:
        """Consulta se ainda é possível executar mais uma rodada de C.2, e por que não.

        Args:
            reserved_output_tokens: Tokens de saída que a chamada de C.2 pode produzir, no máximo.

        Returns:
            BudgetVerdict: Autorizado, ou negado com o limite que de fato impede a rodada:
            rodadas, slots de tarefa, chamadas, tokens ou tempo.
        """
        raise NotImplementedError

    @abstractmethod
    def register_additional_planning_round(self) -> None:
        """Registra a execução de mais uma rodada de planejamento adicional."""
        raise NotImplementedError

    @abstractmethod
    def remaining_task_slots(self) -> int:
        """Quantidade de tarefas ainda disponíveis dentro do limite da sessão.

        Returns:
            int: Quantidade de tarefas que ainda podem ser criadas.
        """
        raise NotImplementedError

    @abstractmethod
    def remaining_tokens(self) -> int:
        """Tokens ainda disponíveis para o loop, já descontada a reserva.

        Returns:
            int: Tokens ainda disponíveis, já descontada a reserva da resposta final.
        """
        raise NotImplementedError
