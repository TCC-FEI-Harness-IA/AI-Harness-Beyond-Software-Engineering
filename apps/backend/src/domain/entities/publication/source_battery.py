from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession


@dataclass(frozen=True)
class SourceBattery:
    """Bateria lida da origem pessoal: o documento convertido ou o motivo de não ter sido lido.

    Attributes:
        battery_id: Identificador (nome do arquivo ou chave do documento).
        battery: Bateria convertida, quando o documento é válido.
        error: Motivo da falha de leitura, quando o documento é inválido.
    """

    battery_id: str
    battery: BenchmarkSession | None = None
    error: str | None = None
