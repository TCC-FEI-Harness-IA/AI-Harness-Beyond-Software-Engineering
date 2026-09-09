import logging
from abc import ABC

from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.settings_interface import ISettings
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.domain.interfaces.thinking_phase_interface import IThinkingPhase


class BaseThinkingPhase(IThinkingPhase, ABC):
    """Template Method comum às etapas do fluxo de thinking.

    O esqueleto "montar prompt → chamar LLM → registrar custo → parsear JSON" é
    idêntico para todas as fases; as subclasses variam apenas o template e o
    schema esperado.
    """

    def __init__(
        self,
        llm_completions: ILLMCompletions,
        template_provider: IPromptTemplateProvider,
        parser: IStructuredResponseParser,
        cost_guard: ICostGuard,
        clock: IClock,
        settings: ISettings,
        logger: logging.Logger,
    ) -> None:
        """Inicializa a fase.

        Args:
            llm_completions: Porta de completions do domínio.
            template_provider: Provedor dos templates de prompt.
            parser: Parser da saída estruturada do modelo.
            cost_guard: Ponto único de decisão sobre limites de custo.
            clock: Fonte de tempo do domínio.
            settings: Configurações da aplicação.
            logger: Logger do módulo.
        """
        self.llm_completions: ILLMCompletions = llm_completions
        self.template_provider: IPromptTemplateProvider = template_provider
        self.parser: IStructuredResponseParser = parser
        self.cost_guard: ICostGuard = cost_guard
        self.clock: IClock = clock
        self.settings: ISettings = settings
        self.logger = logger

    async def execute(self, context: ContextWindow, variables: dict[str, str]) -> PhaseOutcome:
        """Executa a fase sobre a janela de contexto informada.

        Args:
            context: Janela de contexto em que a fase é executada.
            variables: Placeholders a substituir no template da fase.

        Returns:
            PhaseOutcome: Resultado da execução da fase.
        """
        raise NotImplementedError
