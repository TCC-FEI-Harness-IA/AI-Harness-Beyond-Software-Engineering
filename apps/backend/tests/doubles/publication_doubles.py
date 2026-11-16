"""Fábricas e dublês das publicações oficiais de benchmark."""
from dataclasses import replace
from datetime import datetime, timedelta

from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.interfaces.official_publication_repository_interface import IOfficialPublicationRepository
from src.domain.interfaces.publication_backup_interface import IPublicationBackup
from tests.doubles.benchmark_factories import CRIADO_EM, configuracao, desfecho
from tests.doubles.session_factories import nova_sessao

_DEFINICOES = {
    BenchmarkDatasetEnum.VESTIBULAR: BenchmarkDefinition(),
    BenchmarkDatasetEnum.MMLU: BenchmarkDefinition(
        dataset=BenchmarkDatasetEnum.MMLU, revision="c3069", protocol="generative_5shot", few_shot=5, sample_seed=42
    ),
    BenchmarkDatasetEnum.GPQA: BenchmarkDefinition(
        dataset=BenchmarkDatasetEnum.GPQA, revision="5668", split="diamond", sample_seed=42
    ),
}


def bateria_concluida(
    battery_id: str,
    dataset: BenchmarkDatasetEnum = BenchmarkDatasetEnum.VESTIBULAR,
    horas: float = 0,
    questoes: tuple[str, ...] = ("Q1", "Q2"),
    falha_tecnica: bool = False,
) -> tuple[BenchmarkSession, list[Session]]:
    """Bateria concluída (com respostas certas, erradas e, se pedido, uma falha técnica) e as sessões filhas."""
    criada = CRIADO_EM + timedelta(hours=horas)
    bateria = BenchmarkSession(
        id=battery_id,
        llm_config=configuracao(),
        max_parallel=2,
        status=BenchmarkSessionStatusEnum.RUNNING,
        created_at=criada,
        updated_at=criada,
        questions=[BenchmarkQuestionRun(question_id=item, expected_alternative="A") for item in questoes],
        benchmark=_DEFINICOES[dataset],
        alias=f"execução {battery_id}",
    )
    sessoes: list[Session] = []
    for indice, questao in enumerate(questoes):
        for modo in (BenchmarkInferenceModeEnum.SIMPLE, BenchmarkInferenceModeEnum.RALPH):
            sessao = replace(
                nova_sessao(session_id=f"{battery_id}_{questao}_{modo.value}"),
                status=SessionStatusEnum.FAILED if falha_tecnica and indice == 0 else SessionStatusEnum.COMPLETED,
                benchmark_details=BenchmarkDetails(
                    is_banchmark=True, question_name=questao, inference_mode=modo, run_id=battery_id
                ),
            )
            sessoes.append(sessao)
            bateria.start_flow(question_id=questao, mode=modo, at=criada)
            erro = "falha técnica" if falha_tecnica and indice == 0 else None
            bateria.record_outcome(
                question_id=questao,
                outcome=desfecho(mode=modo, correto=indice % 2 == 0, erro=erro, session_id=sessao.id),
                at=criada,
            )
        bateria.finish_question(question_id=questao, at=criada)
    bateria.finish(status=BenchmarkSessionStatusEnum.COMPLETED, at=criada + timedelta(minutes=5), wall_time_ms=1)
    return bateria, sessoes


class InMemoryBenchmarkSource(IBenchmarkSource):
    """Origem pessoal em memória: baterias (inclusive ilegíveis) e sessões."""

    def __init__(self) -> None:
        self.batteries: list[SourceBattery] = []
        self.sessions: dict[str, Session | Exception] = {}

    def add(self, battery: BenchmarkSession, sessions: list[Session]) -> None:
        self.batteries.append(SourceBattery(battery_id=battery.id, battery=battery))
        for session in sessions:
            self.sessions[session.id] = session

    def describe(self) -> str:
        return "origem em memória"

    async def list_batteries(self) -> list[SourceBattery]:
        return list(self.batteries)

    async def find_session(self, session_id: str) -> Session | None:
        value = self.sessions.get(session_id)
        if isinstance(value, Exception):
            raise value
        return value


class InMemoryOfficialPublicationRepository(IOfficialPublicationRepository):
    """Publicações em memória, guardando cópias independentes como o armazenamento real."""

    def __init__(self) -> None:
        self.publications: dict[str, OfficialPublication] = {}
        self.sessions: dict[tuple[str, str], Session] = {}
        self.writes = 0

    async def create(self, publication: OfficialPublication, sessions: list[Session]) -> None:
        self.writes += 1
        for session in sessions:
            self.sessions[(publication.id, session.id)] = session
        self.publications[publication.id] = publication

    async def find(self, publication_id: str) -> OfficialPublication | None:
        return self.publications.get(publication_id)

    async def list_all(self) -> list[OfficialPublication]:
        return sorted(self.publications.values(), key=lambda item: item.published_at, reverse=True)

    async def find_session(self, publication_id: str, session_id: str) -> Session | None:
        return self.sessions.get((publication_id, session_id))

    async def list_sessions(self, publication_id: str) -> list[Session]:
        return [session for (pub, _), session in self.sessions.items() if pub == publication_id]

    async def mark_superseded(self, publication_id: str, superseded_by: str, at: datetime) -> None:
        self.writes += 1
        self.publications[publication_id] = self.publications[publication_id].superseded(by=superseded_by, at=at)


class FakePublicationBackup(IPublicationBackup):
    """Registra os backups pedidos."""

    def __init__(self) -> None:
        self.labels: list[str] = []

    async def backup(self, label: str) -> str:
        self.labels.append(label)
        return f"/backups/{len(self.labels)}-{label}"
