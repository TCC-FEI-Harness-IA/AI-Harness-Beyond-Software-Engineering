from abc import ABC, abstractmethod
from datetime import datetime


class IClock(ABC):
    """Fonte de tempo substituível nos testes."""

    @abstractmethod
    def now(self) -> datetime:
        """Instante atual, com fuso UTC."""
        raise NotImplementedError
