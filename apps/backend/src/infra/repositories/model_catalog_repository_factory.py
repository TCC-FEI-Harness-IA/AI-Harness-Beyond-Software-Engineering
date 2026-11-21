from inspect import getfile

from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.repositories.layered_model_info_repository import LayeredModelInfoRepository
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository


class ModelCatalogRepositoryFactory:
    """Monta o catálogo de modelos visto por uma conta: o pessoal sobre o compartilhado."""

    def __init__(self, settings: ISettings, server_selection_timeout_ms: int | None = None) -> None:
        """Inicializa a fábrica.

        Args:
            settings: Configurações (URI, banco e coleções).
            server_selection_timeout_ms: Espera máxima pelo MongoDB; nos fluxos LLM ela é curta, porque
                o catálogo só complementa a allowlist.
        """
        self.settings = settings
        self.server_selection_timeout_ms = server_selection_timeout_ms

    def create(self, owner_id: str) -> LayeredModelInfoRepository:
        """Cria o catálogo em camadas da conta.

        Args:
            owner_id: Conta dona do catálogo pessoal.

        Returns:
            LayeredModelInfoRepository: Catálogo pessoal sobre o compartilhado (somente leitura).
        """
        client = MongoClientAdapter(
            settings=self.settings, server_selection_timeout_ms=self.server_selection_timeout_ms
        )
        logger = self.settings.logger(module_file=getfile(MongoModelInfoRepository))
        return LayeredModelInfoRepository(
            personal=MongoModelInfoRepository(
                collection=client.user_models_collection, logger=logger, owner_id=owner_id
            ),
            shared=MongoModelInfoRepository(collection=client.models_collection, logger=logger),
        )
