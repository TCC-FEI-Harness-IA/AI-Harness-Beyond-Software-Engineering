from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """Porta de hashing de senhas. Senhas nunca são criptografadas de forma reversível."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Gera o hash (com sal) de uma senha."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, password_hash: str, password: str) -> bool:
        """Informa se a senha corresponde ao hash; um hash inválido nunca autentica."""
        raise NotImplementedError

    @abstractmethod
    def needs_rehash(self, password_hash: str) -> bool:
        """Informa se o hash foi gerado com parâmetros diferentes dos atuais."""
        raise NotImplementedError

    @abstractmethod
    def burn_verification(self, password: str) -> None:
        """Executa uma verificação fictícia, para equalizar o tempo quando a conta não existe."""
        raise NotImplementedError
