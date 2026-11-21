from datetime import UTC, datetime

from src.infra.adapters.clock_adapter import ClockAdapter


def test_now_devolve_instante_em_utc_com_fuso() -> None:
    antes = datetime.now(tz=UTC)

    agora = ClockAdapter().now()

    assert agora.tzinfo is not None
    assert agora.utcoffset() == UTC.utcoffset(None)
    assert agora >= antes


def test_monotonic_ms_devolve_inteiro_em_milissegundos() -> None:
    assert isinstance(ClockAdapter().monotonic_ms(), int)


def test_monotonic_ms_nunca_decresce_entre_chamadas() -> None:
    relogio = ClockAdapter()

    primeira = relogio.monotonic_ms()
    segunda = relogio.monotonic_ms()

    assert segunda >= primeira
