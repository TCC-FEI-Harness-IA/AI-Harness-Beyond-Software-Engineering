import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.settings_interface import ISettings


class FilePromptTemplateProvider(IPromptTemplateProvider):
    """Adapter de `IPromptTemplateProvider` apoiado em arquivos `.md` locais."""

    def __init__(self, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o provider.

        Args:
            settings: Configurações da aplicação, fonte do diretório de templates.
            logger: Logger do módulo.
        """
        self.settings: ISettings = settings
        self.logger = logger

    def get(self, phase: ThinkingPhaseEnum) -> str:
        """Devolve o texto do template daquela fase.

        Args:
            phase: Fase de thinking cujo template deve ser carregado.

        Returns:
            str: Texto bruto do template.

        Raises:
            PromptTemplateNotFoundError: Quando o template não existe.
        """
        raise NotImplementedError

    def render(self, phase: ThinkingPhaseEnum, variables: dict[str, str]) -> str:
        """Devolve o template da fase com os placeholders substituídos.

        Args:
            phase: Fase de thinking cujo template deve ser renderizado.
            variables: Mapa de placeholder para valor a substituir no template.

        Returns:
            str: Template renderizado.

        Raises:
            PromptTemplateNotFoundError: Quando o template não existe.
        """
        raise NotImplementedError
