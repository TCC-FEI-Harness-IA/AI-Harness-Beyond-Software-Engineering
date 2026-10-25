from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from src.domain.interfaces.settings_interface import ISettings


class MongoClientAdapter:
    """Adapter de conexão com o MongoDB, construído a partir de `ISettings`.

    Mantém um único `AsyncIOMotorClient` por instância. O driver abre a conexão
    de forma preguiçosa, na primeira operação feita sobre uma coleção — construir
    o adapter nunca bloqueia nem falha por um MongoDB fora do ar.
    """

    def __init__(self, settings: ISettings) -> None:
        """Inicializa o adapter e o cliente do driver.

        Args:
            settings: Configurações da aplicação, fonte da URI, do banco e da coleção.
        """
        self.settings: ISettings = settings
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_uri)

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

    def close(self) -> None:
        """Fecha a conexão com o MongoDB."""
        self.client.close()
