from src.domain.entities.llm.context_window import ContextWindow
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.context_window_factory_interface import IContextWindowFactory
from src.domain.interfaces.id_generator_interface import IIdGenerator


class ContextWindowFactoryAdapter(IContextWindowFactory):
    """Adapter de `IContextWindowFactory` apoiado em `IIdGenerator`."""

    def __init__(self, id_generator: IIdGenerator) -> None:
        """Inicializa o adapter.

        Args:
            id_generator: Gerador de identificadores usado para o `context_id`.
        """
        self.id_generator: IIdGenerator = id_generator

    def create(self, phase: ThinkingPhaseEnum, task_id: str | None = None) -> ContextWindow:
        """Cria uma janela de contexto nova, com identidade própria.

        Args:
            phase: Fase de thinking que origina a janela.
            task_id: Tarefa associada, quando houver.

        Returns:
            ContextWindow: Janela de contexto recém-criada, vazia.
        """
        return ContextWindow(
            context_id=self.id_generator.new_context_id(),
            phase=phase,
            task_id=task_id,
        )
