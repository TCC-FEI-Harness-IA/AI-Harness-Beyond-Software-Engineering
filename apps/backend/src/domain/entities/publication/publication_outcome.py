from dataclasses import dataclass

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum


@dataclass(frozen=True)
class PublicationOutcome:
    """Desfecho, por dataset, de uma carga inicial ou substituição.

    Attributes:
        dataset: Benchmark.
        action: `publish` (publicada ou a publicar), `already_published` (mesma bateria já vigente),
            `kept_existing` (há outra vigente; só a substituição explícita troca), `absent` (sem
            bateria íntegra) ou `replace` (substituição de uma vigente).
        publication_id: Publicação criada (só quando aplicado).
        battery_id: Bateria de origem considerada.
        previous_publication_id: Publicação vigente antes da operação.
        backup_path: Backup feito antes da escrita.
    """

    dataset: BenchmarkDatasetEnum
    action: str
    publication_id: str | None = None
    battery_id: str | None = None
    previous_publication_id: str | None = None
    backup_path: str | None = None
