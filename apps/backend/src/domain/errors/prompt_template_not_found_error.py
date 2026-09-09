from src.domain.errors.ralph_error import RalphError


class PromptTemplateNotFoundError(RalphError):
    """Levantado quando o arquivo de template de uma fase não é encontrado.

    Attributes:
        template_name: Nome do template procurado.
        path: Caminho onde o template deveria estar.
    """

    def __init__(self, template_name: str, path: str) -> None:
        """Inicializa o erro.

        Args:
            template_name: Nome do template procurado.
            path: Caminho onde o template deveria estar.
        """
        self.template_name = template_name
        self.path = path
        super().__init__(f"Template '{template_name}' não encontrado em '{path}'.")
