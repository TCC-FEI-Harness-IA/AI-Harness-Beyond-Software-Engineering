from abc import ABC, abstractmethod


class IIdGenerator(ABC):
    """Contrato de geração de identificadores únicos do domínio."""

    @abstractmethod
    def new_session_id(self) -> str:
        """Gera um novo identificador de sessão.

        Returns:
            str: Identificador único de sessão.
        """
        raise NotImplementedError

    @abstractmethod
    def new_message_id(self) -> str:
        """Gera um novo identificador de mensagem.

        Returns:
            str: Identificador único de mensagem.
        """
        raise NotImplementedError

    @abstractmethod
    def new_context_id(self) -> str:
        """Gera um novo identificador de janela de contexto.

        Returns:
            str: Identificador único de janela de contexto.
        """
        raise NotImplementedError

    @abstractmethod
    def new_invocation_id(self) -> str:
        """Gera um novo identificador de invocação ao modelo.

        Returns:
            str: Identificador único de invocação.
        """
        raise NotImplementedError
