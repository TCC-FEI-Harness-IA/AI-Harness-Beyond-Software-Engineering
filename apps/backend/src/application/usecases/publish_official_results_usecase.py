import copy
import logging
from collections.abc import Callable

from src.domain.entities.publication.battery_selection import SelectedBattery, SelectionReport
from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.publication.publication_outcome import PublicationOutcome
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository
from src.domain.interfaces.publication_backup_interface import IPublicationBackup

_PUBLISH = "publish"
_ALREADY = "already_published"
_KEPT = "kept_existing"
_ABSENT = "absent"
_REPLACE = "replace"


class PublishOfficialResultsUseCase:
    """Publica cópias preservadas das baterias selecionadas, sem nunca substituir em silêncio.

    A carga inicial só publica datasets sem publicação vigente e é idempotente; trocar uma
    publicação vigente exige `replace`, explícito. Sem `apply`, nada é escrito (inspeção). Antes de
    qualquer escrita, o armazenamento oficial é copiado para um backup.
    """

    def __init__(
        self,
        repository: IOfficialPublicationRepository,
        backup: IPublicationBackup,
        clock: IClock,
        id_generator: Callable[[], str],
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso."""
        self.repository = repository
        self.backup = backup
        self.clock = clock
        self.id_generator = id_generator
        self.logger = logger

    async def publish_initial(
        self, report: SelectionReport, published_by: str, apply: bool
    ) -> list[PublicationOutcome]:
        """Carga inicial dos resultados oficiais.

        Args:
            report: Seleção feita na origem pessoal.
            published_by: Rótulo de quem publica.
            apply: Grava de fato; sem ele, só informa o que seria feito.

        Returns:
            list[PublicationOutcome]: Um desfecho por dataset.
        """
        active = await self.__active_by_dataset()
        plan: list[tuple[PublicationOutcome, SelectedBattery | None]] = []
        for selection in report.selections:
            selected = selection.selected
            current = active.get(selection.dataset)
            if selected is None:
                action = _ABSENT
            elif current is None:
                action = _PUBLISH
            elif current.source_benchmark_session_id == selected.battery.id:
                action = _ALREADY
            else:
                action = _KEPT
            plan.append((
                PublicationOutcome(
                    dataset=selection.dataset,
                    action=action,
                    battery_id=selected.battery.id if selected is not None else None,
                    previous_publication_id=current.id if current is not None else None,
                ),
                selected if action == _PUBLISH else None,
            ))
        if not apply or all(selected is None for _, selected in plan):
            return [outcome for outcome, _ in plan]

        backup_path = await self.backup.backup("publish-initial")
        results: list[PublicationOutcome] = []
        for outcome, selected in plan:
            if selected is None:
                results.append(outcome)
                continue
            publication = await self.__create(selected, published_by=published_by, supersedes=None)
            results.append(
                PublicationOutcome(
                    dataset=outcome.dataset, action=_PUBLISH, publication_id=publication.id,
                    battery_id=outcome.battery_id, backup_path=backup_path,
                )
            )
        return results

    async def replace(self, selected: SelectedBattery, published_by: str, apply: bool) -> PublicationOutcome:
        """Substituição administrativa explícita da publicação vigente de um dataset.

        Args:
            selected: Bateria íntegra escolhida pelo administrador.
            published_by: Rótulo de quem publica.
            apply: Grava de fato; sem ele, só informa.

        Returns:
            PublicationOutcome: Desfecho da substituição.
        """
        dataset = selected.battery.benchmark.dataset
        current = (await self.__active_by_dataset()).get(dataset)
        if current is not None and current.source_benchmark_session_id == selected.battery.id:
            return PublicationOutcome(
                dataset=dataset, action=_ALREADY, battery_id=selected.battery.id, previous_publication_id=current.id
            )
        action = _REPLACE if current is not None else _PUBLISH
        previous_id = current.id if current is not None else None
        if not apply:
            return PublicationOutcome(
                dataset=dataset, action=action, battery_id=selected.battery.id, previous_publication_id=previous_id
            )
        backup_path = await self.backup.backup(f"replace-{dataset.value}")
        publication = await self.__create(selected, published_by=published_by, supersedes=previous_id)
        if current is not None:
            await self.repository.mark_superseded(current.id, superseded_by=publication.id, at=self.clock.now())
        self.logger.info("Publicação '%s' substitui '%s' (%s)", publication.id, previous_id, dataset.value)
        return PublicationOutcome(
            dataset=dataset, action=action, publication_id=publication.id, battery_id=selected.battery.id,
            previous_publication_id=previous_id, backup_path=backup_path,
        )

    async def __active_by_dataset(self) -> dict[BenchmarkDatasetEnum, OfficialPublication]:
        return {
            item.dataset: item
            for item in await self.repository.list_all()
            if item.status is PublicationStatusEnum.ACTIVE
        }

    async def __create(
        self, selected: SelectedBattery, published_by: str, supersedes: str | None
    ) -> OfficialPublication:
        """Grava cópias profundas: alterações posteriores na origem não alcançam a publicação."""
        publication = OfficialPublication(
            id=self.id_generator(),
            dataset=selected.battery.benchmark.dataset,
            benchmark_session=copy.deepcopy(selected.battery),
            published_at=self.clock.now(),
            published_by=published_by,
            source_label=f"bateria pessoal '{selected.battery.id}'",
            supersedes=supersedes,
        )
        await self.repository.create(publication, sessions=copy.deepcopy(selected.sessions))
        self.logger.info("Bateria '%s' publicada como '%s'", selected.battery.id, publication.id)
        return publication
