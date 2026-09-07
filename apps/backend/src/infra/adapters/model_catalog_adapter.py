import logging

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.model_catalog_interface import IModelCatalog
from src.domain.interfaces.settings_interface import ISettings


class ModelCatalogAdapter(IModelCatalog):
    """Catálogo de modelos apoiado nas allowlists expostas pelo `ISettings`."""

    def __init__(self, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o catálogo.

        Args:
            settings: Configurações da aplicação, fonte das allowlists.
            logger: Logger do módulo.
        """
        self.settings: ISettings = settings
        self.logger = logger

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
        if not self.is_model_available(model_name=model_name):
            raise ValueError(f"Model '{model_name}' is not available.")

        if not self.is_provider_available(model_provider=model_provider):
            raise ValueError(f"Provider '{model_provider.value}' is not available.")

        return GenaiModel(model_name=model_name, model_provider=model_provider)

    def is_model_available(self, model_name: str) -> bool:
        """Informa se o modelo está na allowlist.

        Args:
            model_name: Nome do modelo pretendido.

        Returns:
            bool: `True` quando o modelo é permitido.
        """
        return self.__normalize(value=model_name) in self.__available_models()

    def is_provider_available(self, model_provider: ModelProviderEnum) -> bool:
        """Informa se o provedor está na allowlist.

        Args:
            model_provider: Provedor pretendido.

        Returns:
            bool: `True` quando o provedor é permitido.
        """
        return self.__normalize(value=model_provider.value) in self.__available_providers()

    def __available_models(self) -> set[str]:
        """Devolve o conjunto normalizado de modelos permitidos."""
        return {self.__normalize(value=item) for item in self.settings.genai_available_models}

    def __available_providers(self) -> set[str]:
        """Devolve o conjunto normalizado de provedores permitidos."""
        return {self.__normalize(value=item) for item in self.settings.genai_available_providers}

    def __normalize(self, value: str) -> str:
        """Normaliza um identificador para comparação case-insensitive."""
        return value.strip().lower()
