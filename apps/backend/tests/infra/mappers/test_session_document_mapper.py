import copy
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_ATUALIZADO_EM = datetime(2026, 8, 31, 12, 3, 41, tzinfo=UTC)


def _nova_sessao(com_mensagens: bool = True, final_answer: str | None = "resposta final") -> Session:
    sessao = Session(
        id="sess_ab12",
        user_question="pergunta com acentuação",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        status=SessionStatusEnum.RUNNING,
        created_at=_CRIADO_EM,
        updated_at=_CRIADO_EM,
    )

    if com_mensagens:
        sessao.add_message(
            SessionMessage(
                id="msg-0",
                order=0,
                timestamp=_CRIADO_EM,
                phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
                source=MessageSourceEnum.USER,
                content="pergunta com acentuação",
                task_id=None,
                context_id=None,
                tokens_input=0,
                tokens_output=0,
                inference_time_ms=0,
                model_name=None,
            )
        )
        sessao.add_message(
            SessionMessage(
                id="msg-1",
                order=1,
                timestamp=_ATUALIZADO_EM,
                phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
                source=MessageSourceEnum.LLM_AGENT,
                content="resposta do modelo",
                task_id="T1",
                context_id="b5a9c2e",
                tokens_input=3120,
                tokens_output=1666,
                inference_time_ms=18422,
                model_name="vendor/modelo",
            )
        )
        sessao.register_degradation(
            SessionDegradation(
                limit=BudgetLimitEnum.TASK_ATTEMPTS,
                phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                task_id="T2",
                description="Tarefa aceita após esgotar 3 tentativas.",
                occurred_at=_ATUALIZADO_EM,
            )
        )

    sessao.totals.wall_time_ms = 21008
    sessao.status = SessionStatusEnum.COMPLETED
    sessao.final_answer = final_answer
    sessao.updated_at = _ATUALIZADO_EM
    return sessao


def _build_mapper() -> SessionDocumentMapper:
    return SessionDocumentMapper()


def _documento_valido() -> dict[str, Any]:
    return _build_mapper().to_document(session=_nova_sessao())


def test_documento_carrega_todos_os_campos_da_sessao() -> None:
    documento = _documento_valido()

    assert documento["_id"] == "sess_ab12"
    assert documento["id"] == "sess_ab12"
    assert documento["user_question"] == "pergunta com acentuação"
    assert documento["flow"] == "DIRECT"
    assert documento["model_name"] == "vendor/modelo"
    assert documento["max_tokens"] == 1200
    assert documento["temperature"] == 0.3
    assert documento["status"] == "completed"
    assert documento["created_at"] == "2026-08-31T12:00:00+00:00"
    assert documento["updated_at"] == "2026-08-31T12:03:41+00:00"
    assert documento["final_answer"] == "resposta final"


def test_documento_carrega_os_totais_agregados() -> None:
    documento = _documento_valido()

    assert documento["totals"] == {
        "total_messages": 2,
        "total_llm_calls": 1,
        "tokens_input": 3120,
        "tokens_output": 1666,
        "total_tokens": 4786,
        "inference_time_ms": 18422,
        "wall_time_ms": 21008,
    }


def test_documento_carrega_o_historico_completo_de_mensagens() -> None:
    documento = _documento_valido()

    assert documento["messages"][0] == {
        "id": "msg-0",
        "order": 0,
        "timestamp": "2026-08-31T12:00:00+00:00",
        "phase": "DIRECT",
        "source": "user",
        "content": "pergunta com acentuação",
        "task_id": None,
        "context_id": None,
        "tokens_input": 0,
        "tokens_output": 0,
        "total_tokens": 0,
        "inference_time_ms": 0,
        "model_name": None,
    }
    assert documento["messages"][1]["total_tokens"] == 4786


def test_documento_carrega_as_degradacoes() -> None:
    documento = _documento_valido()

    assert documento["degradations"] == [
        {
            "limit": "task_attempts",
            "phase": "B2",
            "task_id": "T2",
            "description": "Tarefa aceita após esgotar 3 tentativas.",
            "occurred_at": "2026-08-31T12:03:41+00:00",
        }
    ]


def test_sessao_sem_mensagens_gera_listas_vazias() -> None:
    documento = _build_mapper().to_document(session=_nova_sessao(com_mensagens=False))

    assert documento["messages"] == []
    assert documento["degradations"] == []


def test_documento_e_totalmente_serializavel_em_json() -> None:
    assert json.dumps(_documento_valido())


def test_resposta_final_ausente_vira_nulo_e_volta_como_none() -> None:
    mapper = _build_mapper()
    documento = mapper.to_document(session=_nova_sessao(final_answer=None))

    assert documento["final_answer"] is None
    assert mapper.from_document(document=documento).final_answer is None


def test_round_trip_preserva_a_sessao_original() -> None:
    mapper = _build_mapper()
    sessao = _nova_sessao()

    reconstruida = mapper.from_document(document=mapper.to_document(session=sessao))

    assert reconstruida == sessao


def test_round_trip_preserva_o_documento_original() -> None:
    mapper = _build_mapper()
    documento = _documento_valido()

    assert mapper.to_document(session=mapper.from_document(document=documento)) == documento


def test_datas_reconstruidas_sao_timezone_aware() -> None:
    mapper = _build_mapper()

    reconstruida = mapper.from_document(document=_documento_valido())

    assert reconstruida.created_at.tzinfo is not None
    assert reconstruida.messages[0].timestamp.tzinfo is not None
    assert reconstruida.degradations[0].occurred_at.tzinfo is not None


def test_enums_reconstruidos_voltam_como_enum() -> None:
    reconstruida = _build_mapper().from_document(document=_documento_valido())

    assert reconstruida.status is SessionStatusEnum.COMPLETED
    assert reconstruida.flow is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert reconstruida.messages[0].source is MessageSourceEnum.USER
    assert reconstruida.messages[1].phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert reconstruida.degradations[0].limit is BudgetLimitEnum.TASK_ATTEMPTS


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        (("status",), "inexistente"),
        (("flow",), "Z9"),
        (("messages", 0, "source"), "robo"),
        (("messages", 0, "phase"), "Z9"),
        (("degradations", 0, "limit"), "sem_limite"),
        (("degradations", 0, "phase"), "Z9"),
    ],
)
def test_valor_de_enum_desconhecido_e_recusado(caminho: tuple[Any, ...], valor: str) -> None:
    documento = _documento_valido()
    alvo: Any = documento
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    alvo[caminho[-1]] = valor

    with pytest.raises(ValueError, match="inválido"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize(
    "chave",
    ["_id", "user_question", "flow", "model_name", "max_tokens", "temperature", "status", "created_at",
     "updated_at", "final_answer", "totals", "messages", "degradations"],
)
def test_documento_sem_chave_obrigatoria_e_recusado(chave: str) -> None:
    documento = _documento_valido()
    del documento[chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize(
    "chave",
    ["total_messages", "total_llm_calls", "tokens_input", "tokens_output", "inference_time_ms", "wall_time_ms"],
)
def test_totais_sem_chave_obrigatoria_sao_recusados(chave: str) -> None:
    documento = _documento_valido()
    del documento["totals"][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize(
    "chave",
    ["id", "order", "timestamp", "phase", "source", "content", "task_id", "context_id",
     "tokens_input", "tokens_output", "inference_time_ms", "model_name"],
)
def test_mensagem_sem_chave_obrigatoria_e_recusada(chave: str) -> None:
    documento = _documento_valido()
    del documento["messages"][0][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize("chave", ["limit", "phase", "task_id", "description", "occurred_at"])
def test_degradacao_sem_chave_obrigatoria_e_recusada(chave: str) -> None:
    documento = _documento_valido()
    del documento["degradations"][0][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        (("created_at",), "2026-08-31T12:00:00"),
        (("messages", 0, "timestamp"), "2026-08-31T12:00:00"),
        (("degradations", 0, "occurred_at"), "2026-08-31T12:00:00"),
    ],
)
def test_data_sem_fuso_horario_e_recusada(caminho: tuple[Any, ...], valor: str) -> None:
    documento = _documento_valido()
    alvo: Any = documento
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    alvo[caminho[-1]] = valor

    with pytest.raises(ValueError, match="fuso horário"):
        _build_mapper().from_document(document=documento)


def test_data_em_formato_invalido_e_recusada() -> None:
    documento = _documento_valido()
    documento["created_at"] = "ontem"

    with pytest.raises(ValueError, match="ISO-8601"):
        _build_mapper().from_document(document=documento)


def test_from_document_nao_altera_o_documento_recebido() -> None:
    documento = _documento_valido()
    original = copy.deepcopy(documento)

    _build_mapper().from_document(document=documento)

    assert documento == original
