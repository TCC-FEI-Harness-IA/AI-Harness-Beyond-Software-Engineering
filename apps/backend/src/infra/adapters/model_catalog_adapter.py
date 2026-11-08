import logging

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.model_info import ModelInfo
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.model_catalog_interface import IModelCatalog
from src.domain.interfaces.model_info_repository_interface import IModelInfoRepository
from src.domain.interfaces.settings_interface import ISettings


class ModelCatalogAdapter(IModelCatalog):
    """Catálogo de modelos apoiado nas allowlists do `ISettings` e nos modelos cadastrados.

    Um modelo está liberado quando aparece em `GENAI_AVAILABLE_MODELS` ou quando foi cadastrado
    no repositório de modelos e carregado por `load_model_info` antes da chamada. O cadastro também
    informa o contexto máximo do modelo, que viaja em `GenaiModel.context_length`.
    """

    def __init__(
        self,
        settings: ISettings,
        logger: logging.Logger,
        model_repository: IModelInfoRepository | None = None,
    ) -> None:
        """Inicializa o catálogo.

        Args:
            settings: Configurações da aplicação, fonte das allowlists.
            logger: Logger do módulo.
            model_repository: Repositório dos modelos cadastrados; sem ele, vale só a allowlist.
        """
        self.settings: ISettings = settings
        self.logger = logger
        self.model_repository: IModelInfoRepository | None = model_repository
        self.registered_models: dict[str, ModelInfo] = {}

    async def load_model_info(self, model_name: str) -> None:
        """Carrega o cadastro do modelo no repositório de modelos.

        Um modelo cadastrado fica liberado mesmo fora da allowlist, e o contexto máximo dele passa a
        acompanhar o `GenaiModel` devolvido por `resolve`. Uma falha na consulta é apenas registrada:
        o modelo da allowlist segue liberado, só que sem o contexto máximo.

        Args:
            model_name: Nome do modelo pretendido.
        """
        if self.model_repository is None:
            return

        try:
            registered = await self.model_repository.find_by_name(model_name=model_name.strip())
        except Exception as exc:
            self.logger.warning("Falha ao consultar o catálogo de modelos cadastrados: %s", exc)
            return

        if registered is not None:
            self.registered_models[self.__normalize(value=registered.model_name)] = registered

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

        registered = self.registered_models.get(self.__normalize(value=model_name))
        return GenaiModel(
            model_name=model_name,
            model_provider=model_provider,
            context_length=registered.context_length if registered is not None else None,
        )

    def is_model_available(self, model_name: str) -> bool:
        """Informa se o modelo está na allowlist ou entre os cadastrados já incluídos.

        Args:
            model_name: Nome do modelo pretendido.

        Returns:
            bool: `True` quando o modelo é permitido.
        """
        normalized = self.__normalize(value=model_name)
        return normalized in self.__available_models() or normalized in self.registered_models

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
