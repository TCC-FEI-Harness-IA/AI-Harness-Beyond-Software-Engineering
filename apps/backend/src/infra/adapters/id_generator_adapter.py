from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.settings_interface import ISettings


class IdGeneratorAdapter(IIdGenerator):
    """Adapter de `IIdGenerator` apoiado em `uuid4`, prefixado pelas configurações."""

    def __init__(self, settings: ISettings) -> None:
        """Inicializa o adapter.

        Args:
            settings: Configurações da aplicação, fonte do prefixo de sessão.
        """
        self.settings: ISettings = settings

    def new_session_id(self) -> str:
        """Gera um novo identificador de sessão.

        Returns:
            str: Identificador único de sessão.
        """
        raise NotImplementedError

    def new_message_id(self) -> str:
        """Gera um novo identificador de mensagem.

        Returns:
            str: Identificador único de mensagem.
        """
        raise NotImplementedError

    def new_context_id(self) -> str:
        """Gera um novo identificador de janela de contexto.

        Returns:
            str: Identificador único de janela de contexto.
        """
        raise NotImplementedError
