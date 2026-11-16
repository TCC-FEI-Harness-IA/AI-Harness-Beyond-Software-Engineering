import logging

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.publication.battery_selection import (
    DatasetSelection,
    DiscardedBattery,
    SelectedBattery,
    SelectionReport,
)
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.errors.official_battery_not_eligible_error import OfficialBatteryNotEligibleError
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.services.battery_integrity_checker import BatteryIntegrityChecker

_DATASETS = (BenchmarkDatasetEnum.VESTIBULAR, BenchmarkDatasetEnum.MMLU, BenchmarkDatasetEnum.GPQA)


class SelectOfficialBatteriesUseCase:
    """Escolhe, numa origem pessoal explícita, a bateria oficial de cada dataset (somente leitura).

    "Mais recente" é a bateria concluída e íntegra de maior `created_at` (nunca `updated_at`, que
    muda com renomeações e reexecuções); no empate, o menor identificador. As baterias mais recentes
    que a escolhida e descartadas por estarem incompletas ou inconsistentes entram no relatório.
    """

    def __init__(self, source: IBenchmarkSource, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            source: Origem pessoal indicada explicitamente pelo administrador.
            logger: Logger do módulo.
        """
        self.source = source
        self.logger = logger
        self.checker = BatteryIntegrityChecker()

    async def execute(self) -> SelectionReport:
        """Seleciona uma bateria por dataset.

        Returns:
            SelectionReport: Escolhidas, descartadas e ilegíveis.
        """
        entries = await self.source.list_batteries()
        unreadable = [
            DiscardedBattery(battery_id=item.battery_id, created_at=None, reasons=[item.error or "documento ilegível"])
            for item in entries
            if item.battery is None
        ]
        batteries = [item.battery for item in entries if item.battery is not None]
        selections = [await self.__select(dataset, batteries) for dataset in _DATASETS]
        return SelectionReport(
            source_description=self.source.describe(), selections=selections, unreadable=unreadable
        )

    async def inspect(self, battery_id: str) -> SelectedBattery:
        """Verifica uma bateria específica (substituição explícita).

        Raises:
            OfficialBatteryNotEligibleError: Quando ela não existe ou não está íntegra.
        """
        for entry in await self.source.list_batteries():
            if entry.battery_id == battery_id and entry.battery is not None:
                selected, reasons = await self.__check(entry.battery)
                if selected is None:
                    raise OfficialBatteryNotEligibleError("; ".join(reasons))
                return selected
        raise OfficialBatteryNotEligibleError(f"Bateria '{battery_id}' não encontrada ou ilegível na origem.")

    async def __select(self, dataset: BenchmarkDatasetEnum, batteries: list[BenchmarkSession]) -> DatasetSelection:
        candidates = sorted(
            (item for item in batteries if item.benchmark.dataset is dataset),
            key=lambda item: (-item.created_at.timestamp(), item.id),
        )
        discarded: list[DiscardedBattery] = []
        for battery in candidates:
            selected, reasons = await self.__check(battery)
            if selected is not None:
                return DatasetSelection(dataset=dataset, selected=selected, discarded=discarded)
            discarded.append(DiscardedBattery(battery_id=battery.id, created_at=battery.created_at, reasons=reasons))
        return DatasetSelection(dataset=dataset, selected=None, discarded=discarded)

    async def __check(self, battery: BenchmarkSession) -> tuple[SelectedBattery | None, list[str]]:
        problems = self.checker.battery_problems(battery)
        if problems:
            return None, problems
        sessions: list[Session] = []
        for session_id in battery.session_ids:
            try:
                session = await self.source.find_session(session_id)
            except ValueError as exc:
                problems.append(f"sessão '{session_id}' ilegível: {exc}")
                continue
            problems.extend(self.checker.session_problems(battery, session_id, session))
            if session is not None:
                sessions.append(session)
        if problems:
            return None, problems
        return SelectedBattery(battery=battery, sessions=sessions), []
