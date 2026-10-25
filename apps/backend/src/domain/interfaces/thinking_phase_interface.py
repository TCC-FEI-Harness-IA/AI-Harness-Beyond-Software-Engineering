from abc import ABC, abstractmethod

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


class IThinkingPhase(ABC):
    """Contrato de uma etapa (Strategy) do fluxo de thinking."""

    @property
    @abstractmethod
    def phase(self) -> ThinkingPhaseEnum:
        """Fase de thinking implementada.

        Returns:
            ThinkingPhaseEnum: Identificador da fase.
        """
        raise NotImplementedError

    @abstractmethod
    def configure(
        self,
        model_name: str,
        max_tokens: int,
        temperature: float,
        provider: ModelProviderEnum,
    ) -> None:
        """Fixa os parâmetros do modelo usados por todas as execuções da fase.

        Args:
            model_name: Nome do modelo a ser usado nas chamadas da fase.
            max_tokens: Limite de tokens de saída das chamadas da fase.
            temperature: Temperatura de geração das chamadas da fase.
            provider: Provedor que atende as chamadas da fase.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self,
        context: ContextWindow,
        variables: dict[str, str],
        validation: ValidationContext | None = None,
        is_retry: bool = False,
    ) -> PhaseOutcome:
        """Executa a fase sobre a janela de contexto informada.

        Args:
            context: Janela de contexto em que a fase é executada.
            variables: Placeholders a substituir no template da fase.
            validation: Dados esperados pela chamada, usados para validar a saída estruturada.
                É obrigatório nas fases de verificação.
            is_retry: Indica que a execução repete um pedido reprovado (a nova tentativa de B.1
                depois de B.2 reprovar): todas as suas chamadas usam a temperatura de retentativa.

        Returns:
            PhaseOutcome: Resultado da execução da fase.
        """
        raise NotImplementedError
