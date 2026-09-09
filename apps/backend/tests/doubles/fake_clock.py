from datetime import UTC, datetime

from src.domain.interfaces.clock_interface import IClock

_DEFAULT_NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_DEFAULT_MONOTONIC_MS = 1000


class FakeClock(IClock):
    """Dublê de `IClock` com sequências programadas de instantes e de contador monotônico.

    Cada chamada consome o próximo valor da respectiva sequência. Quando a
    sequência se esgota, o último valor programado passa a ser repetido, de forma
    que o teste só precise programar os valores que pretende afirmar.
    """

    def __init__(
        self,
        now_values: list[datetime] | None = None,
        monotonic_values: list[int] | None = None,
    ) -> None:
        """Configura o dublê.

        Args:
            now_values: Sequência devolvida por `now`.
            monotonic_values: Sequência devolvida por `monotonic_ms`.
        """
        self.now_values = list(now_values) if now_values else [_DEFAULT_NOW]
        self.monotonic_values = list(monotonic_values) if monotonic_values else [_DEFAULT_MONOTONIC_MS]
        self.now_calls = 0
        self.monotonic_calls = 0

    def now(self) -> datetime:
        """Devolve o próximo instante programado."""
        value = self.now_values[min(self.now_calls, len(self.now_values) - 1)]
        self.now_calls += 1
        return value

    def monotonic_ms(self) -> int:
        """Devolve o próximo valor programado do contador monotônico."""
        value = self.monotonic_values[min(self.monotonic_calls, len(self.monotonic_values) - 1)]
        self.monotonic_calls += 1
        return value
