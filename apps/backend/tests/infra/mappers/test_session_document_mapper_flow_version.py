"""Versão do fluxo e subtipo persistido das mensagens (nova fase de validação — 01).

Nas sessões Ralph novas (versão 2), `A3` é a validação da decomposição e `A4` a extração; nas gravadas
antes do campo `flow_version`, `A3` continua sendo a extração (versão 1). A inferência direta não tem versão
de fluxo Ralph. A leitura não reescreve nada: a versão inferida aparece só no objeto e no documento devolvido.
"""
import copy
from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.ralph_flow_version_enum import RalphFlowVersionEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum as Sub
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.mappers.session_document_mapper import SessionDocumentMapper

_EM = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def _mensagem(order: int, phase: Phase, subtype: Sub | None, content: str = "c") -> SessionMessage:
    return SessionMessage(
        id=f"msg-{order}", order=order, timestamp=_EM, phase=phase, source=MessageSourceEnum.LLM_AGENT,
        content=content, task_id=None, context_id=f"ctx-{order}", tokens_input=1, tokens_output=1,
        inference_time_ms=1, model_name="m", subtype=subtype,
    )


def _sessao(flow: Phase, flow_version: RalphFlowVersionEnum | None) -> Session:
    sessao = Session(
        id="sess_v", user_question="q", flow=flow, model_name="m", max_tokens=100, temperature=0.3,
        status=SessionStatusEnum.COMPLETED, created_at=_EM, updated_at=_EM, flow_version=flow_version,
    )
    if flow is Phase.A1_GENERAL_CRITERIA:
        sessao.add_message(_mensagem(0, Phase.A2_TASK_DECOMPOSITION, Sub.PLAN_CANDIDATE, "## Candidate plan"))
        sessao.add_message(_mensagem(1, Phase.A3_DECOMPOSITION_VALIDATION, Sub.PLAN_REJECTED))
        sessao.add_message(_mensagem(2, Phase.A4_PLANNING_LEARNINGS, Sub.LEARN))
    return sessao


def _mapper() -> SessionDocumentMapper:
    return SessionDocumentMapper()


def test_sessao_ralph_nova_grava_e_le_a_versao_2_e_os_subtipos() -> None:
    documento = _mapper().to_document(session=_sessao(Phase.A1_GENERAL_CRITERIA, RalphFlowVersionEnum.current()))

    assert documento["flow_version"] == 2
    assert [m["phase"] for m in documento["messages"]] == ["A2", "A3", "A4"]
    assert [m["subtype"] for m in documento["messages"]] == ["plan_candidate", "plan_rejected", "learn"]
    sessao = _mapper().from_document(document=documento)
    assert sessao.flow_version is RalphFlowVersionEnum.VALIDATED_PLANNING
    assert [m.subtype for m in sessao.messages] == [Sub.PLAN_CANDIDATE, Sub.PLAN_REJECTED, Sub.LEARN]
    assert _mapper().to_document(session=sessao) == documento


def test_sessao_ralph_antiga_sem_versao_e_lida_como_versao_1_e_a3_continua_extracao() -> None:
    documento = _mapper().to_document(session=_sessao(Phase.A1_GENERAL_CRITERIA, None))
    del documento["flow_version"]
    for mensagem in documento["messages"]:
        del mensagem["subtype"]
    documento["messages"] = [documento["messages"][0] | {"phase": "A2"}, documento["messages"][1] | {"phase": "A3"}]
    original = copy.deepcopy(documento)

    sessao = _mapper().from_document(document=documento)

    assert documento == original
    assert sessao.flow_version is RalphFlowVersionEnum.PLANNING_WITHOUT_VALIDATION
    assert [m.subtype for m in sessao.messages] == [None, None]
    assert [m.phase for m in sessao.messages] == [Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION]
    devolvido = _mapper().to_document(session=sessao)
    assert devolvido["flow_version"] == 1
    assert [m["phase"] for m in devolvido["messages"]] == ["A2", "A3"]
    assert [m["content"] for m in devolvido["messages"]] == [m["content"] for m in original["messages"]]


def test_inferencia_direta_nao_adquire_versao_de_fluxo_ralph() -> None:
    documento = _mapper().to_document(session=_sessao(Phase.DIRECT_INFERENCE, None))

    assert documento["flow_version"] is None
    assert _mapper().from_document(document=documento).flow_version is None
    del documento["flow_version"]
    assert _mapper().from_document(document=documento).flow_version is None


def test_versao_explicita_nao_e_reinterpretada_por_default() -> None:
    documento = _mapper().to_document(session=_sessao(Phase.A1_GENERAL_CRITERIA, RalphFlowVersionEnum.legacy()))

    assert _mapper().from_document(document=documento).flow_version is RalphFlowVersionEnum.legacy()


@pytest.mark.parametrize("valor", [3, 0, "2", True, 2.0])
def test_versao_desconhecida_ou_de_tipo_errado_e_recusada(valor: Any) -> None:
    documento = _mapper().to_document(session=_sessao(Phase.A1_GENERAL_CRITERIA, RalphFlowVersionEnum.current()))
    documento["flow_version"] = valor

    with pytest.raises(ValueError, match="flow_version"):
        _mapper().from_document(document=documento)


def test_subtipo_desconhecido_e_recusado() -> None:
    documento = _mapper().to_document(session=_sessao(Phase.A1_GENERAL_CRITERIA, RalphFlowVersionEnum.current()))
    documento["messages"][0]["subtype"] = "candidato"

    with pytest.raises(ValueError, match="inválido"):
        _mapper().from_document(document=documento)
