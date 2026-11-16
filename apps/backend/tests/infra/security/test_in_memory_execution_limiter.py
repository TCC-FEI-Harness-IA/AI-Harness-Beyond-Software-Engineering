import pytest

from src.domain.errors.execution_limit_exceeded_error import ExecutionLimitExceededError
from src.infra.security.in_memory_execution_limiter import InMemoryExecutionLimiter
from tests.doubles.controllable_clock import ControllableClock


def test_limita_execucoes_simultaneas_por_usuario() -> None:
    limiter = InMemoryExecutionLimiter(clock=ControllableClock(), max_concurrent=2, max_starts=10, window_seconds=60)

    primeira = limiter.acquire("usr_a")
    limiter.acquire("usr_a")
    limiter.acquire("usr_b")

    with pytest.raises(ExecutionLimitExceededError, match="simultâneas"):
        limiter.acquire("usr_a")
    primeira.release()
    primeira.release()
    limiter.acquire("usr_a")


def test_limita_inicios_por_janela() -> None:
    clock = ControllableClock()
    limiter = InMemoryExecutionLimiter(clock=clock, max_concurrent=10, max_starts=2, window_seconds=60)
    limiter.acquire("usr_a").release()
    limiter.acquire("usr_a").release()

    with pytest.raises(ExecutionLimitExceededError) as erro:
        limiter.acquire("usr_a")
    assert erro.value.retry_after_seconds == 60

    clock.advance(seconds=60)
    with limiter.acquire("usr_a"):
        assert limiter.active("usr_a") == 1
    assert limiter.active("usr_a") == 0
