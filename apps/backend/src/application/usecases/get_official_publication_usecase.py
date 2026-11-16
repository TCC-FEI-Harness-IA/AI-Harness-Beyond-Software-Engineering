from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum
from src.domain.errors.official_publication_not_found_error import OfficialPublicationNotFoundError
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository

_DATASET_ORDER = {dataset: index for index, dataset in enumerate(BenchmarkDatasetEnum)}


class GetOfficialPublicationUseCase:
    """Consultas públicas: só publicações oficiais e só sessões que pertencem a elas.

    Nunca chama o modelo nem lê dados pessoais: tudo vem do armazenamento oficial.
    """

    def __init__(self, repository: IOfficialPublicationRepository) -> None:
        """Inicializa o caso de uso."""
        self.repository = repository

    async def list_active(self) -> list[OfficialPublication]:
        """Publicações vigentes, na ordem vestibular, MMLU e GPQA."""
        publications = [
            item for item in await self.repository.list_all() if item.status is PublicationStatusEnum.ACTIVE
        ]
        return sorted(publications, key=lambda item: _DATASET_ORDER[item.dataset])

    async def get(self, publication_id: str) -> OfficialPublication:
        """Publicação pelo identificador (vigente ou do histórico).

        Raises:
            OfficialPublicationNotFoundError: Quando não existe.
        """
        publication = await self.repository.find(publication_id)
        if publication is None:
            raise OfficialPublicationNotFoundError(publication_id)
        return publication

    async def get_session(self, publication_id: str, session_id: str) -> tuple[OfficialPublication, Session]:
        """Sessão filha, só se ela faz parte da publicação pedida.

        Raises:
            OfficialPublicationNotFoundError: Publicação inexistente ou sessão que não pertence a ela.
        """
        publication = await self.get(publication_id)
        if session_id not in publication.session_ids:
            raise OfficialPublicationNotFoundError(session_id)
        session = await self.repository.find_session(publication_id, session_id)
        if session is None:
            raise OfficialPublicationNotFoundError(session_id)
        return publication, session
