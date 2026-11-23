from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from src.domain.interfaces.settings_interface import ISettings


class MongoClientAdapter:
    """Adapter de conexão com o MongoDB, construído a partir de `ISettings`.

    Mantém um único `AsyncIOMotorClient` por instância. O driver abre a conexão
    de forma preguiçosa, na primeira operação feita sobre uma coleção — construir
    o adapter nunca bloqueia nem falha por um MongoDB fora do ar.
    """

    def __init__(self, settings: ISettings, server_selection_timeout_ms: int | None = None) -> None:
        """Inicializa o adapter e o cliente do driver.

        Args:
            settings: Configurações da aplicação, fonte da URI, do banco e da coleção.
            server_selection_timeout_ms: Espera máxima por um servidor disponível; sem ela, vale o
                padrão do driver (30 s).
        """
        self.settings: ISettings = settings
        options: dict[str, int] = {}
        if server_selection_timeout_ms is not None:
            options["serverSelectionTimeoutMS"] = server_selection_timeout_ms
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_uri, **options)

    @property
    def sessions_collection(self) -> AsyncIOMotorCollection:
        """Coleção configurada para os documentos de sessão.

        Returns:
            AsyncIOMotorCollection: Coleção do banco e nome configurados em `ISettings`.
        """
        database = self.client[self.settings.mongodb_database]
        return database[self.settings.mongodb_sessions_collection]

    @property
    def benchmark_sessions_collection(self) -> AsyncIOMotorCollection:
        """Coleção configurada para os documentos das baterias de benchmark.

        Returns:
            AsyncIOMotorCollection: Coleção do banco e nome configurados em `ISettings`.
        """
        database = self.client[self.settings.mongodb_database]
        return database[self.settings.mongodb_benchmark_sessions_collection]

    @property
    def models_collection(self) -> AsyncIOMotorCollection:
        """Coleção configurada para o catálogo de modelos.

        Returns:
            AsyncIOMotorCollection: Coleção do banco e nome configurados em `ISettings`.
        """
        database = self.client[self.settings.mongodb_database]
        return database[self.settings.mongodb_models_collection]

    def close(self) -> None:
        """Fecha a conexão com o MongoDB."""
        self.client.close()
