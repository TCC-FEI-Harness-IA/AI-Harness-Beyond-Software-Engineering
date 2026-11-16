from abc import ABC, abstractmethod


class IPublicationBackup(ABC):
    """Cópia de segurança do armazenamento oficial antes de qualquer alteração."""

    @abstractmethod
    async def backup(self, label: str) -> str:
        """Faz o backup e devolve onde ele ficou."""
        raise NotImplementedError
