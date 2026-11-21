from abc import ABC, abstractmethod

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.enums.model_provider_enum import ModelProviderEnum


class IModelCatalog(ABC):
    """Contrato do catálogo de modelos permitidos pela aplicação.

    Centraliza a consulta às allowlists de modelos e provedores, mantendo a
    entidade `GenaiModel` livre de qualquer dependência de configuração.
    """

    @abstractmethod
    def resolve(self, model_name: str, model_provider: ModelProviderEnum) -> GenaiModel:
        """Valida nome e provedor contra as allowlists e devolve o modelo.

        Args:
            model_name: Nome do modelo pretendido.
            model_provider: Provedor pretendido.

        Returns:
            GenaiModel: Modelo validado.

        Raises:
            ValueError: Quando o modelo ou o provedor não está liberado.
        """
        raise NotImplementedError

    @abstractmethod
    def is_model_available(self, model_name: str) -> bool:
        """Informa se o modelo está na allowlist.

        Args:
            model_name: Nome do modelo pretendido.

        Returns:
            bool: `True` quando o modelo é permitido.
        """
        raise NotImplementedError

    @abstractmethod
    def is_provider_available(self, model_provider: ModelProviderEnum) -> bool:
        """Informa se o provedor está na allowlist.

        Args:
            model_provider: Provedor pretendido.

        Returns:
            bool: `True` quando o provedor é permitido.
        """
        raise NotImplementedError
