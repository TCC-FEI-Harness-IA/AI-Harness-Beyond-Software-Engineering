import time
from datetime import UTC, datetime

from src.domain.interfaces.clock_interface import IClock

_MILLISECONDS_PER_SECOND = 1000


class ClockAdapter(IClock):
    """Adapter de `IClock` apoiado no relógio do sistema operacional."""

    def now(self) -> datetime:
        """Devolve o instante atual.

        Returns:
            datetime: Instante atual em UTC, timezone-aware.
        """
        return datetime.now(tz=UTC)

    def monotonic_ms(self) -> int:
        """Devolve um contador monotônico, usado para medir duração.

        Returns:
            int: Contador monotônico em milissegundos.
        """
        return int(time.monotonic() * _MILLISECONDS_PER_SECOND)
