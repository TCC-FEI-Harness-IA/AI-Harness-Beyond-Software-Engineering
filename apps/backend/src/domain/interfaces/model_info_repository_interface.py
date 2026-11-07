from abc import ABC, abstractmethod

from src.domain.entities.llm.model_info import ModelInfo


class IModelInfoRepository(ABC):
    """Contrato de persistência do catálogo de modelos."""

    @abstractmethod
    async def list_all(self) -> list[ModelInfo]:
        """Lista todos os modelos cadastrados.

        Returns:
            list[ModelInfo]: Modelos em ordem alfabética do identificador.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_name(self, model_name: str) -> ModelInfo | None:
        """Busca um modelo pelo identificador.

        Args:
            model_name: Identificador do modelo procurado.

        Returns:
            ModelInfo | None: Modelo encontrado, ou `None` quando não existe.
        """
        raise NotImplementedError

    @abstractmethod
    async def save(self, model: ModelInfo) -> None:
        """Persiste (insere ou substitui) o modelo.

        Args:
            model: Modelo a ser persistido.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, model_name: str) -> bool:
        """Remove um modelo cadastrado.

        Args:
            model_name: Identificador do modelo a remover.

        Returns:
            bool: `True` quando o modelo existia e foi removido.
        """
        raise NotImplementedError
