from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.errors.invalid_benchmark_request_error import InvalidBenchmarkRequestError
from src.domain.errors.ralph_error import RalphError


def test_bateria_nao_encontrada_carrega_o_id_e_o_cita_na_mensagem() -> None:
    erro = BenchmarkSessionNotFoundError(benchmark_session_id="bench_1")

    assert isinstance(erro, RalphError)
    assert erro.benchmark_session_id == "bench_1"
    assert "bench_1" in str(erro)


def test_pedido_invalido_herda_de_ralph_error() -> None:
    assert issubclass(InvalidBenchmarkRequestError, RalphError)
