from enum import StrEnum


class BenchmarkSessionStatusEnum(StrEnum):
    """Estados possíveis de uma bateria de benchmark.

    `INTERRUPTED` indica que a bateria foi cancelada (cliente desconectado) antes de terminar;
    `FAILED` indica um erro técnico da própria bateria, como a persistência indisponível.
    """

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
