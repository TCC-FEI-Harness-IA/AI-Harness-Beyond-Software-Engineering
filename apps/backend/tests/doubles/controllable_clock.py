from datetime import UTC, datetime, timedelta

from src.domain.interfaces.clock_interface import IClock


class ControllableClock(IClock):
    """Relógio que só anda quando o teste manda (`advance`), para prazos de sessão e credencial."""

    def __init__(self, now: datetime = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)) -> None:
        self.current = now
        self.monotonic = 1000

    def now(self) -> datetime:
        return self.current

    def monotonic_ms(self) -> int:
        return self.monotonic

    def advance(self, **kwargs: float) -> None:
        delta = timedelta(**kwargs)
        self.current += delta
        self.monotonic += int(delta.total_seconds() * 1000)
