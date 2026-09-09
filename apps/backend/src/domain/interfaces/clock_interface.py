from abc import ABC, abstractmethod
from datetime import datetime


class IClock(ABC):
    """Contrato de acesso ao tempo, isolando o restante do domínio do relógio do SO."""

    @abstractmethod
    def now(self) -> datetime:
        """Devolve o instante atual.

        Returns:
            datetime: Instante atual em UTC, timezone-aware.
        """
        raise NotImplementedError

    @abstractmethod
    def monotonic_ms(self) -> int:
        """Devolve um contador monotônico, usado para medir duração.

        Returns:
            int: Contador monotônico em milissegundos.
        """
        raise NotImplementedError
