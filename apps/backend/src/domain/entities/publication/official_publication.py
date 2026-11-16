from dataclasses import dataclass, replace
from datetime import datetime

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum


@dataclass(frozen=True)
class OfficialPublication:
    """Resultado oficial público: uma cópia preservada de uma bateria pessoal e das suas sessões.

    A cópia é independente da bateria de origem: reexecuções ou renomeações posteriores da bateria
    privada não a alteram. Só uma operação administrativa explícita a substitui, e a publicação
    anterior continua guardada (com identificador e data) como `superseded`.

    Attributes:
        id: Identificador da publicação (`pub_...`).
        dataset: Benchmark publicado.
        benchmark_session: Cópia da bateria, com o identificador e os metadados originais.
        published_at: Instante da publicação.
        published_by: Quem publicou (rótulo administrativo; não é exposto publicamente).
        source_label: Origem pessoal de onde a cópia veio (não é exposta publicamente).
        status: Vigente ou substituída.
        supersedes: Publicação que esta substituiu, quando houver.
        superseded_by: Publicação que substituiu esta, quando houver.
        superseded_at: Instante da substituição, quando houver.
    """

    id: str
    dataset: BenchmarkDatasetEnum
    benchmark_session: BenchmarkSession
    published_at: datetime
    published_by: str
    source_label: str
    status: PublicationStatusEnum = PublicationStatusEnum.ACTIVE
    supersedes: str | None = None
    superseded_by: str | None = None
    superseded_at: datetime | None = None

    @property
    def source_benchmark_session_id(self) -> str:
        """Bateria pessoal de origem."""
        return self.benchmark_session.id

    @property
    def session_ids(self) -> list[str]:
        """Sessões filhas que fazem parte da publicação."""
        return self.benchmark_session.session_ids

    def superseded(self, by: str, at: datetime) -> "OfficialPublication":
        """Cópia marcada como substituída, preservando identificador e data de publicação."""
        return replace(self, status=PublicationStatusEnum.SUPERSEDED, superseded_by=by, superseded_at=at)
