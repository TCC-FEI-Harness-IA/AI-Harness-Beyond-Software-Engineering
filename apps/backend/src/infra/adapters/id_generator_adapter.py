from uuid import uuid4

from src.domain.interfaces.id_generator_interface import IIdGenerator
from src.domain.interfaces.settings_interface import ISettings

_CONTEXT_ID_LENGTH = 7
_SESSION_ID_SEPARATOR = "_"


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
            str: Identificador único de sessão, prefixado pelas configurações.
        """
        return f"{self.settings.ralph_session_id_prefix}{_SESSION_ID_SEPARATOR}{self.__new_hex()}"

    def new_message_id(self) -> str:
        """Gera um novo identificador de mensagem.

        Returns:
            str: Identificador único de mensagem.
        """
        return self.__new_hex()

    def new_context_id(self) -> str:
        """Gera um novo identificador de janela de contexto.

        Returns:
            str: Identificador curto de janela de contexto, no formato que o frontend renderiza.
        """
        return self.__new_hex()[:_CONTEXT_ID_LENGTH]

    def __new_hex(self) -> str:
        """Devolve a representação hexadecimal de um `uuid4`."""
        return uuid4().hex
