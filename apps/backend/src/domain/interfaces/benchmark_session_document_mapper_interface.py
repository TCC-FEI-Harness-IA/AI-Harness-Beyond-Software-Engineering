from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession


class IBenchmarkSessionDocumentMapper(ABC):
    """Contrato de conversão entre `BenchmarkSession` e o documento persistido."""

    @abstractmethod
    def to_document(self, benchmark_session: BenchmarkSession) -> dict[str, Any]:
        """Converte uma bateria no documento a ser persistido.

        Args:
            benchmark_session: Bateria a ser convertida.

        Returns:
            dict[str, Any]: Documento equivalente à bateria.
        """
        raise NotImplementedError

    @abstractmethod
    def from_document(self, document: dict[str, Any]) -> BenchmarkSession:
        """Converte um documento persistido de volta em uma bateria.

        Args:
            document: Documento persistido.

        Returns:
            BenchmarkSession: Bateria equivalente ao documento.
        """
        raise NotImplementedError
