from datetime import UTC, datetime

from src.domain.interfaces.clock_interface import IClock


class ClockAdapter(IClock):
    """Relógio real, em UTC."""

    def now(self) -> datetime:
        """Instante atual com fuso UTC."""
        return datetime.now(UTC)
