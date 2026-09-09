from typing import Any

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_document_mapper_interface import ISessionDocumentMapper


class SessionDocumentMapper(ISessionDocumentMapper):
    """Data Mapper entre `Session` e o documento persistido (`dict`)."""

    def to_document(self, session: Session) -> dict[str, Any]:
        """Converte uma sessão no documento a ser persistido.

        Args:
            session: Sessão a ser convertida.

        Returns:
            dict[str, Any]: Documento equivalente à sessão.
        """
        raise NotImplementedError

    def from_document(self, document: dict[str, Any]) -> Session:
        """Converte um documento persistido de volta em uma sessão.

        Args:
            document: Documento persistido.

        Returns:
            Session: Sessão equivalente ao documento.
        """
        raise NotImplementedError
