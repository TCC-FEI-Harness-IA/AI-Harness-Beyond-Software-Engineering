from src.domain.errors.benchmark_session_import_conflict_error import BenchmarkSessionImportConflictError
from src.domain.errors.invalid_benchmark_archive_error import InvalidBenchmarkArchiveError
from src.domain.errors.ralph_error import RalphError


def test_conflito_so_da_bateria_nomeia_a_bateria() -> None:
    erro = BenchmarkSessionImportConflictError(benchmark_session_id="bench_1", conflicting_ids=["bench_1"])

    assert isinstance(erro, RalphError)
    assert erro.benchmark_session_id == "bench_1"
    assert erro.conflicting_ids == ["bench_1"]
    assert str(erro) == "A bateria de benchmark 'bench_1' já existe; a importação foi cancelada."


def test_conflito_de_sessoes_lista_os_registros_existentes() -> None:
    erro = BenchmarkSessionImportConflictError(benchmark_session_id="bench_1", conflicting_ids=["s1", "s2"])

    assert "'s1', 's2'" in str(erro)
    assert "bench_1" in str(erro)


def test_arquivo_invalido_traz_o_motivo() -> None:
    erro = InvalidBenchmarkArchiveError("manifesto ausente.")

    assert isinstance(erro, RalphError)
    assert erro.reason == "manifesto ausente."
    assert str(erro) == "Arquivo de bateria inválido: manifesto ausente."
