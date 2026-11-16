from abc import ABC, abstractmethod


class ILoginAttemptLimiter(ABC):
    """Limita tentativas por chave (e-mail, IP) numa janela de tempo."""

    @abstractmethod
    async def ensure_allowed(self, keys: list[str]) -> None:
        """Recusa a tentativa quando alguma chave estourou o limite.

        Raises:
            TooManyAttemptsError: Quando o limite foi atingido.
        """
        raise NotImplementedError

    @abstractmethod
    async def register_failure(self, keys: list[str]) -> None:
        """Conta uma falha para cada chave."""
        raise NotImplementedError

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Zera o contador de uma chave."""
        raise NotImplementedError
