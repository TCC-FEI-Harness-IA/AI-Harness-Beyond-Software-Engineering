from enum import StrEnum


class BenchmarkQuestionStatusEnum(StrEnum):
    """Estados de uma questão dentro de uma bateria de benchmark.

    `INTERRUPTED` marca a questão que estava em execução quando a bateria foi encerrada sem
    concluir; questões que nem começaram permanecem `PENDING`.
    """

    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    INTERRUPTED = "interrupted"
