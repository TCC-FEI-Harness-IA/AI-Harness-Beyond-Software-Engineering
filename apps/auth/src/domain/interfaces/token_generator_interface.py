from abc import ABC, abstractmethod


class ITokenGenerator(ABC):
    """Porta de geração de segredos e identificadores aleatórios."""

    @abstractmethod
    def session_token(self) -> str:
        """Token opaco da sessão de autenticação, entregue só no cookie."""
        raise NotImplementedError

    @abstractmethod
    def csrf_token(self) -> str:
        """Token anti-CSRF vinculado à sessão."""
        raise NotImplementedError

    @abstractmethod
    def digest(self, token: str) -> str:
        """Resumo do token armazenado no banco; o token em si nunca é persistido."""
        raise NotImplementedError

    @abstractmethod
    def user_id(self) -> str:
        """Identificador estável de usuário."""
        raise NotImplementedError

    @abstractmethod
    def session_id(self) -> str:
        """Identificador público (não secreto) da sessão de autenticação."""
        raise NotImplementedError
