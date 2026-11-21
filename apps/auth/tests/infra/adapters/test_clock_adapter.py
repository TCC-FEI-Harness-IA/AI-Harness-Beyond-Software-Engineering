from datetime import UTC, datetime

from src.infra.adapters.clock_adapter import ClockAdapter


def test_relogio_real_em_utc() -> None:
    antes = datetime.now(UTC)
    agora = ClockAdapter().now()

    assert agora.tzinfo is UTC
    assert agora >= antes
