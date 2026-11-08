from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.prompt_template_not_found_error import PromptTemplateNotFoundError
from src.domain.interfaces.prompt_template_provider_interface import IPromptTemplateProvider

_FAKE_PATH = "templates-de-teste"


class FakePromptTemplateProvider(IPromptTemplateProvider):
    """Dublê de `IPromptTemplateProvider` com templates programáveis por fase.

    Registra as variáveis recebidas em cada renderização, para que os testes
    afirmem o que cada fase entrega ao template.
    """

    def __init__(self, templates: dict[ThinkingPhaseEnum, str] | None = None) -> None:
        """Configura o dublê.

        Args:
            templates: Texto de template por fase. Fases não programadas recebem
                um template padrão que ecoa o nome da fase.
        """
        self.templates = dict(templates) if templates else {}
        self.rendered: list[tuple[ThinkingPhaseEnum, dict[str, str]]] = []

    def variables_of(self, phase: ThinkingPhaseEnum) -> list[dict[str, str]]:
        """Devolve as variáveis recebidas em cada renderização daquela fase.

        Args:
            phase: Fase de thinking consultada.

        Returns:
            list[dict[str, str]]: Variáveis recebidas, em ordem de renderização.
        """
        return [variables for rendered_phase, variables in self.rendered if rendered_phase is phase]

    def get(self, phase: ThinkingPhaseEnum) -> str:
        """Devolve o template programado, ou o padrão que ecoa a fase.

        Raises:
            PromptTemplateNotFoundError: Quando a fase foi programada sem template.
        """
        if phase in self.templates and not self.templates[phase]:
            raise PromptTemplateNotFoundError(template_name=phase.value, path=_FAKE_PATH)
        return self.templates.get(phase, f"TEMPLATE {phase.value}")

    def render(self, phase: ThinkingPhaseEnum, variables: dict[str, str]) -> str:
        """Registra as variáveis e devolve o template com os placeholders trocados."""
        self.rendered.append((phase, dict(variables)))

        rendered = self.get(phase=phase)
        for name, value in variables.items():
            rendered = rendered.replace(f"{{{{{name}}}}}", value)
        return rendered
