from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum


@dataclass(frozen=True)
class SelectedBattery:
    """Bateria íntegra escolhida para publicação, com todas as sessões filhas.

    Attributes:
        battery: Bateria concluída.
        sessions: Sessões filhas referenciadas pela bateria, na ordem das questões.
    """

    battery: BenchmarkSession
    sessions: list[Session]


@dataclass(frozen=True)
class DiscardedBattery:
    """Bateria não publicável, com os motivos.

    Attributes:
        battery_id: Identificador da bateria.
        created_at: Criação, quando o documento pôde ser lido.
        reasons: Motivos do descarte (incompleta, inconsistente ou ilegível).
    """

    battery_id: str
    created_at: datetime | None
    reasons: list[str]


@dataclass(frozen=True)
class DatasetSelection:
    """Resultado da seleção de um dataset: a escolhida (ou nenhuma) e as mais recentes descartadas."""

    dataset: BenchmarkDatasetEnum
    selected: SelectedBattery | None
    discarded: list[DiscardedBattery] = field(default_factory=list)


@dataclass(frozen=True)
class SelectionReport:
    """Relatório da seleção sobre uma origem pessoal explícita.

    Attributes:
        source_description: Descrição da origem lida (armazenamento e caminhos/coleções).
        selections: Uma seleção por dataset, na ordem vestibular, MMLU e GPQA.
        unreadable: Documentos de bateria que não puderam ser lidos.
    """

    source_description: str
    selections: list[DatasetSelection]
    unreadable: list[DiscardedBattery] = field(default_factory=list)

    def selection(self, dataset: BenchmarkDatasetEnum) -> DatasetSelection:
        """Seleção de um dataset."""
        return next(item for item in self.selections if item.dataset is dataset)
