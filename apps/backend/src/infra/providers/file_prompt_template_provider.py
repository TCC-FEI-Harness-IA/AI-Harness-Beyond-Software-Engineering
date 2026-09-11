import logging
import re
from pathlib import Path

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.prompt_template_not_found_error import PromptTemplateNotFoundError
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider
from src.domain.interfaces.settings_interface import ISettings

_FILE_NAME_BY_PHASE: dict[ThinkingPhaseEnum, str] = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: "a1_general_criteria.md",
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: "a2_task_decomposition.md",
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: "b1_task_resolution.md",
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: "b2_task_verification.md",
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: "b4_learnings_extraction.md",
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: "c1_global_verification.md",
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: "c2_additional_planning.md",
    ThinkingPhaseEnum.C3_FINAL_ANSWER: "c3_final_answer.md",
}
_PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")
_FILE_ENCODING = "utf-8"


class FilePromptTemplateProvider(IPromptTemplateProvider):
    """Adapter de `IPromptTemplateProvider` apoiado em arquivos `.md` locais.

    Cada template é lido do disco uma única vez por instância; as leituras
    seguintes são servidas do cache em memória.
    """

    def __init__(self, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o provider.

        Args:
            settings: Configurações da aplicação, fonte do diretório de templates.
            logger: Logger do módulo.
        """
        self.settings: ISettings = settings
        self.logger = logger
        self.__cache: dict[ThinkingPhaseEnum, str] = {}

    def get(self, phase: ThinkingPhaseEnum) -> str:
        """Devolve o texto do template daquela fase.

        Args:
            phase: Fase de thinking cujo template deve ser carregado.

        Returns:
            str: Texto bruto do template.

        Raises:
            PromptTemplateNotFoundError: Quando a fase não tem template ou o
                arquivo não existe no diretório configurado.
        """
        if phase not in self.__cache:
            self.__cache[phase] = self.__read(phase=phase)
        return self.__cache[phase]

    def render(self, phase: ThinkingPhaseEnum, variables: dict[str, str]) -> str:
        """Devolve o template da fase com os placeholders substituídos.

        Args:
            phase: Fase de thinking cujo template deve ser renderizado.
            variables: Mapa de placeholder para valor a substituir no template.
                Chaves não usadas pelo template são ignoradas.

        Returns:
            str: Template renderizado.

        Raises:
            PromptTemplateNotFoundError: Quando o template não existe.
            ValueError: Quando o template usa um placeholder ausente em `variables`.
        """
        template = self.get(phase=phase)

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in variables:
                raise ValueError(
                    f"O template da fase '{phase.value}' exige o placeholder '{name}', ausente nas variáveis."
                )
            return variables[name]

        return _PLACEHOLDER_PATTERN.sub(_replace, template)

    def __read(self, phase: ThinkingPhaseEnum) -> str:
        """Lê do disco o template da fase informada.

        Args:
            phase: Fase de thinking cujo template deve ser lido.

        Returns:
            str: Texto bruto do template.

        Raises:
            PromptTemplateNotFoundError: Quando a fase não tem template ou o
                arquivo não existe no diretório configurado.
        """
        directory = self.settings.ralph_prompt_templates_path

        if phase not in _FILE_NAME_BY_PHASE:
            raise PromptTemplateNotFoundError(template_name=phase.value, path=directory)

        file_name = _FILE_NAME_BY_PHASE[phase]
        path = Path(directory) / file_name

        if not path.is_file():
            raise PromptTemplateNotFoundError(template_name=file_name, path=directory)

        self.logger.info("Template '%s' carregado do disco", file_name)
        return path.read_text(encoding=_FILE_ENCODING)
