"""Auditoria das revisões de resultados na sessão: ida e volta, exportação e sessões antigas."""
import copy
import json
import logging
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.thinking.result_revision import ResultRevision
from src.domain.entities.thinking.revision_verdict import RevisionVerdict
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.session_factories import sessao_ralph

_INSTANTE = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def _revisao() -> ResultRevision:
    return ResultRevision(
        revising_task_id="T4",
        reason="T3 afirma força maior nos blocos, incompatível com T1.",
        verdicts=(
            RevisionVerdict(task_id="T3", verdict=RevisionVerdictEnum.SUPERSEDED, justification="Impulso trocado."),
            RevisionVerdict(task_id="T2", verdict=RevisionVerdictEnum.CONFIRMED, justification="Dissipação mantida."),
        ),
        approval_justification="A investigação demonstra o erro de T3 e mantém T2.",
        suspended_task_ids=("T5",),
        reinstated_task_ids=(),
        withdrawn_learnings=("A força média nos blocos é maior.",),
        restored_learnings=(),
        current_task_ids=("T1", "T2", "T4"),
        occurred_at=_INSTANTE,
    )


def _sessao_com_revisao() -> Session:
    sessao = sessao_ralph()
    sessao.add_result_revision(revision=_revisao())
    return sessao


def test_documento_carrega_a_revisao_aprovada_com_substituidos_motivo_e_estado_vigente() -> None:
    documento = SessionDocumentMapper().to_document(session=_sessao_com_revisao())

    [revisao] = documento["result_revisions"]
    assert revisao["revising_task_id"] == "T4"
    assert revisao["superseded_task_ids"] == ["T3"]
    assert revisao["confirmed_task_ids"] == ["T2"]
    assert revisao["verdicts"][0] == {"task_id": "T3", "verdict": "superseded", "justification": "Impulso trocado."}
    assert revisao["approval_justification"].startswith("A investigação")
    assert revisao["current_task_ids"] == ["T1", "T2", "T4"]
    assert revisao["occurred_at"] == _INSTANTE.isoformat()
    json.dumps(documento, ensure_ascii=False)


def test_round_trip_preserva_a_revisao() -> None:
    mapper = SessionDocumentMapper()
    sessao = _sessao_com_revisao()

    reconstruida = mapper.from_document(document=mapper.to_document(session=sessao))

    assert reconstruida.result_revisions == [_revisao()]
    assert mapper.to_document(session=reconstruida) == mapper.to_document(session=sessao)


def test_sessao_antiga_sem_auditoria_de_revisao_e_lida_sem_revisao_presumida() -> None:
    mapper = SessionDocumentMapper()
    documento = mapper.to_document(session=sessao_ralph())
    del documento["result_revisions"]

    sessao = mapper.from_document(document=documento)

    assert sessao.result_revisions == []
    assert sessao.status is SessionStatusEnum.COMPLETED


@pytest.mark.parametrize(("caminho", "valor"), [
    (("revising_task_id",), None),
    (("verdicts", 0, "verdict"), "replaced"),
    (("occurred_at",), "2026-11-07T12:00:00"),
])
def test_revisao_malformada_e_recusada(caminho: tuple, valor: object) -> None:
    mapper = SessionDocumentMapper()
    documento = mapper.to_document(session=_sessao_com_revisao())
    alvo = documento["result_revisions"][0]
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    if valor is None:
        del alvo[caminho[-1]]
    else:
        alvo[caminho[-1]] = valor

    with pytest.raises(ValueError):
        mapper.from_document(document=copy.deepcopy(documento))


async def test_gravador_persiste_a_revisao_na_sessao_consultavel() -> None:
    repositorio = InMemorySessionRepository()
    gravador = SessionRecorderAdapter(
        repository=repositorio, clock=FakeClock(), id_generator=FakeIdGenerator(),
        settings=FakeSettings(), logger=logging.getLogger("teste.gravador.revisao"),
    )
    await gravador.start(user_question="p", flow=ThinkingPhaseEnum.A1_GENERAL_CRITERIA, model_name="m",
                         max_tokens=10, temperature=0.0)

    await gravador.record_result_revision(revision=_revisao())

    persistida = repositorio.sessions[gravador.session.id]
    assert persistida.result_revisions == [_revisao()]
