from datetime import datetime

from src.domain.interfaces.clock_interface import IClock


class ClockAdapter(IClock):
    """Adapter de `IClock` apoiado no relógio do sistema operacional."""

    def now(self) -> datetime:
        """Devolve o instante atual.

        Returns:
            datetime: Instante atual em UTC, timezone-aware.
        """
        raise NotImplementedError

    def monotonic_ms(self) -> int:
        """Devolve um contador monotônico, usado para medir duração.

        Returns:
            int: Contador monotônico em milissegundos.
        """
        raise NotImplementedError
