from datetime import datetime
from typing import Any

from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum
from src.domain.interfaces.benchmark_session_document_mapper_interface import IBenchmarkSessionDocumentMapper

_SCHEMA_VERSION = 1


class OfficialPublicationDocumentMapper:
    """Converte uma publicação oficial no documento persistido e de volta.

    O documento leva a bateria no mesmo formato da API privada (`BenchmarkSessionDocumentMapper`),
    sem proprietário, e os metadados administrativos da publicação.
    """

    def __init__(self, benchmark_mapper: IBenchmarkSessionDocumentMapper) -> None:
        """Inicializa o mapper.

        Args:
            benchmark_mapper: Conversor da bateria.
        """
        self.benchmark_mapper = benchmark_mapper

    def to_document(self, publication: OfficialPublication) -> dict[str, Any]:
        """Documento persistido da publicação."""
        return {
            "_id": publication.id,
            "id": publication.id,
            "schema_version": _SCHEMA_VERSION,
            "dataset": publication.dataset.value,
            "status": publication.status.value,
            "published_at": publication.published_at.isoformat(),
            "published_by": publication.published_by,
            "source_label": publication.source_label,
            "supersedes": publication.supersedes,
            "superseded_by": publication.superseded_by,
            "superseded_at": publication.superseded_at.isoformat() if publication.superseded_at else None,
            "source_benchmark_session_id": publication.source_benchmark_session_id,
            "session_ids": publication.session_ids,
            "benchmark_session": self.benchmark_mapper.to_document(benchmark_session=publication.benchmark_session),
        }

    def from_document(self, document: dict[str, Any]) -> OfficialPublication:
        """Publicação a partir do documento persistido.

        Raises:
            ValueError: Quando falta um campo obrigatório ou um valor é inválido.
        """
        try:
            superseded_at = document.get("superseded_at")
            return OfficialPublication(
                id=document["_id"],
                dataset=BenchmarkDatasetEnum(document["dataset"]),
                benchmark_session=self.benchmark_mapper.from_document(document=document["benchmark_session"]),
                published_at=datetime.fromisoformat(document["published_at"]),
                published_by=document["published_by"],
                source_label=document["source_label"],
                status=PublicationStatusEnum(document["status"]),
                supersedes=document.get("supersedes"),
                superseded_by=document.get("superseded_by"),
                superseded_at=datetime.fromisoformat(superseded_at) if superseded_at else None,
            )
        except KeyError as exc:
            raise ValueError(f"Documento de publicação oficial sem o campo {exc}.") from exc
