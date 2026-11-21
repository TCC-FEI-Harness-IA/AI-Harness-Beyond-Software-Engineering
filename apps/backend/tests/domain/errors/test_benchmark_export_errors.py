from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.no_benchmark_errors_to_export_error import NoBenchmarkErrorsToExportError
from src.domain.errors.ralph_error import RalphError


def test_bateria_em_execucao_nomeia_a_bateria() -> None:
    erro = BenchmarkSessionNotFinishedError(benchmark_session_id="bench_1")

    assert isinstance(erro, RalphError)
    assert erro.benchmark_session_id == "bench_1"
    assert "bench_1" in str(erro)


def test_bateria_sem_erros_nomeia_a_bateria() -> None:
    erro = NoBenchmarkErrorsToExportError(benchmark_session_id="bench_1")

    assert isinstance(erro, RalphError)
    assert erro.benchmark_session_id == "bench_1"
    assert "bench_1" in str(erro)
