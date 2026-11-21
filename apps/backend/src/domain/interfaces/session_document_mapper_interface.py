from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.session.session import Session


class ISessionDocumentMapper(ABC):
    """Contrato de conversão entre `Session` e o documento persistido."""

    @abstractmethod
    def to_document(self, session: Session) -> dict[str, Any]:
        """Converte uma sessão no documento a ser persistido.

        Args:
            session: Sessão a ser convertida.

        Returns:
            dict[str, Any]: Documento equivalente à sessão.
        """
        raise NotImplementedError

    @abstractmethod
    def from_document(self, document: dict[str, Any]) -> Session:
        """Converte um documento persistido de volta em uma sessão.

        Args:
            document: Documento persistido.

        Returns:
            Session: Sessão equivalente ao documento.
        """
        raise NotImplementedError
