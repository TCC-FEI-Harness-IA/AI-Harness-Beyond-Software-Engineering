import copy
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.llm.message import Message
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum

from src.domain.entities.session.session import Session
from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
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
        provider=ModelProviderEnum.OPEN_ROUTER,
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
                prompt_input=(
                    Message(creation_timestamp=_CRIADO_EM, text="prompt da fase B.1", source=MessageSourceEnum.USER),
                ),
            )
        )
        # Degradações só existem em sessões gravadas por versões anteriores do fluxo.
        sessao.degradations.append(
            SessionDegradation(
                limit=BudgetLimitEnum.TASK_ATTEMPTS,
                phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                task_id="T2",
                description="Tarefa aceita após esgotar 3 tentativas.",
                occurred_at=_ATUALIZADO_EM,
            )
        )
        sessao.start_invocation(
            LLMInvocation(
                id="inv-1",
                phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
                task_id="T1",
                context_id="b5a9c2e",
                model_name="vendor/modelo",
                provider=ModelProviderEnum.OPEN_ROUTER,
                started_at=_CRIADO_EM,
                temperature=0.3,
            )
        )
        sessao.complete_invocation(
            invocation_id="inv-1",
            outcome=InvocationOutcomeEnum.SUCCESS,
            duration_ms=18422,
            tokens_input=3120,
            tokens_output=1666,
            finish_reason="stop",
            provider_response_id="resp-1",
        )
        sessao.start_invocation(
            LLMInvocation(
                id="inv-2",
                phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
                task_id="T1",
                context_id="c1d2e3f",
                model_name="vendor/modelo",
                provider=ModelProviderEnum.OPEN_ROUTER,
                started_at=_ATUALIZADO_EM,
            )
        )
        sessao.complete_invocation(
            invocation_id="inv-2",
            outcome=InvocationOutcomeEnum.PROVIDER_ERROR,
            duration_ms=30,
            tokens_input=None,
            tokens_output=None,
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
        "total_llm_calls": 2,
        "tokens_input": 3120,
        "tokens_output": 1666,
        "total_tokens": 4786,
        "inference_time_ms": 18452,
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
        "prompt_input": [],
    }
    assert documento["messages"][1]["total_tokens"] == 4786


def test_documento_carrega_o_prompt_de_entrada_de_cada_mensagem() -> None:
    documento = _documento_valido()

    assert documento["messages"][1]["content"] == "resposta do modelo"
    assert documento["messages"][1]["prompt_input"] == [
        {"source": "user", "text": "prompt da fase B.1", "creation_timestamp": "2026-08-31T12:00:00+00:00"}
    ]


def test_mensagem_legada_sem_prompt_de_entrada_volta_com_conversa_vazia() -> None:
    documento = _documento_valido()
    del documento["messages"][1]["prompt_input"]

    assert _build_mapper().from_document(document=documento).messages[1].prompt_input == ()


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


def test_documento_carrega_o_provedor_efetivo() -> None:
    assert _documento_valido()["provider"] == "open_router"


def test_documento_carrega_uma_entrada_por_invocacao() -> None:
    documento = _documento_valido()

    assert documento["invocations"] == [
        {
            "id": "inv-1",
            "phase": "B1",
            "task_id": "T1",
            "context_id": "b5a9c2e",
            "model_name": "vendor/modelo",
            "provider": "open_router",
            "started_at": "2026-08-31T12:00:00+00:00",
            "outcome": "success",
            "duration_ms": 18422,
            "tokens_input": 3120,
            "tokens_output": 1666,
            "finish_reason": "stop",
            "provider_response_id": "resp-1",
            "temperature": 0.3,
        },
        {
            "id": "inv-2",
            "phase": "B2",
            "task_id": "T1",
            "context_id": "c1d2e3f",
            "model_name": "vendor/modelo",
            "provider": "open_router",
            "started_at": "2026-08-31T12:03:41+00:00",
            "outcome": "provider_error",
            "duration_ms": 30,
            "tokens_input": None,
            "tokens_output": None,
            "finish_reason": None,
            "provider_response_id": None,
            "temperature": None,
        },
    ]


def test_a_temperatura_efetiva_de_cada_invocacao_sobrevive_a_ida_e_volta() -> None:
    mapper = _build_mapper()

    sessao = mapper.from_document(document=_documento_valido())

    assert [invocacao.temperature for invocacao in sessao.invocations] == [0.3, None]


def test_invocacao_gravada_antes_do_registro_da_temperatura_e_lida_com_temperatura_desconhecida() -> None:
    documento = _documento_valido()
    del documento["invocations"][0]["temperature"]

    sessao = _build_mapper().from_document(document=documento)

    assert sessao.invocations[0].temperature is None


def test_documento_de_sessao_nova_nao_e_legado_e_nao_tem_falha() -> None:
    documento = _documento_valido()

    assert documento["legacy_totals"] is False
    assert documento["failure"] is None


def test_documento_carrega_a_falha_estruturada() -> None:
    sessao = _nova_sessao()
    sessao.status = SessionStatusEnum.FAILED
    sessao.failure = SessionFailure(
        reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        description="tentativas esgotadas",
        occurred_at=_ATUALIZADO_EM,
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        task_id="T2",
        pending_criteria_ids=("AC1", "AC2"),
    )

    documento = _build_mapper().to_document(session=sessao)

    assert documento["failure"] == {
        "reason": "resource_limit",
        "phase": "B2",
        "description": "tentativas esgotadas",
        "occurred_at": "2026-08-31T12:03:41+00:00",
        "limit": "task_attempts",
        "task_id": "T2",
        "pending_criteria_ids": ["AC1", "AC2"],
    }
    assert _build_mapper().from_document(document=documento) == sessao


def test_falha_sem_limite_volta_com_limite_nulo() -> None:
    sessao = _nova_sessao()
    sessao.status = SessionStatusEnum.FAILED
    sessao.failure = SessionFailure(
        reason=SessionFailureReasonEnum.TECHNICAL_ERROR,
        phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        description="provedor fora do ar",
        occurred_at=_ATUALIZADO_EM,
    )

    reconstruida = _build_mapper().from_document(document=_build_mapper().to_document(session=sessao))

    assert reconstruida.failure == sessao.failure


def _documento_legado() -> dict[str, Any]:
    """Documento como gravado antes do registro por invocação, da falha e do provedor."""
    documento = _documento_valido()
    for chave in ("provider", "invocations", "failure", "legacy_totals"):
        del documento[chave]
    return documento


def test_documento_legado_sem_invocacoes_continua_legivel_com_os_totais_historicos() -> None:
    reconstruida = _build_mapper().from_document(document=_documento_legado())

    assert reconstruida.invocations == []
    assert reconstruida.legacy_totals is True
    assert reconstruida.provider is None
    assert reconstruida.failure is None
    assert reconstruida.totals.total_llm_calls == 2
    assert reconstruida.totals.total_tokens == 4786


def test_documento_legado_nao_ganha_chamadas_inventadas_ao_voltar_para_documento() -> None:
    mapper = _build_mapper()

    redocumento = mapper.to_document(session=mapper.from_document(document=_documento_legado()))

    assert redocumento["invocations"] == []
    assert redocumento["legacy_totals"] is True
    assert redocumento["totals"] == _documento_legado()["totals"]


def test_documento_legado_com_status_degradado_e_lido_sem_reclassificacao() -> None:
    documento = _documento_legado()
    documento["status"] = "degraded"

    assert _build_mapper().from_document(document=documento).status is SessionStatusEnum.DEGRADED


def test_sessao_sem_mensagens_gera_listas_vazias() -> None:
    documento = _build_mapper().to_document(session=_nova_sessao(com_mensagens=False))

    assert documento["messages"] == []
    assert documento["degradations"] == []
    assert documento["invocations"] == []


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
    assert reconstruida.messages[1].prompt_input[0].source is MessageSourceEnum.USER
    assert reconstruida.degradations[0].limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert reconstruida.provider is ModelProviderEnum.OPEN_ROUTER
    assert reconstruida.invocations[0].outcome is InvocationOutcomeEnum.SUCCESS
    assert reconstruida.invocations[0].phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert reconstruida.invocations[0].provider is ModelProviderEnum.OPEN_ROUTER


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        (("status",), "inexistente"),
        (("flow",), "Z9"),
        (("messages", 0, "source"), "robo"),
        (("messages", 0, "phase"), "Z9"),
        (("degradations", 0, "limit"), "sem_limite"),
        (("degradations", 0, "phase"), "Z9"),
        (("provider",), "nuvem_x"),
        (("invocations", 0, "outcome"), "talvez"),
        (("invocations", 0, "phase"), "Z9"),
        (("invocations", 0, "provider"), "nuvem_x"),
        (("messages", 1, "prompt_input", 0, "source"), "robo"),
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


@pytest.mark.parametrize("chave", ["source", "text", "creation_timestamp"])
def test_prompt_de_entrada_sem_chave_obrigatoria_e_recusado(chave: str) -> None:
    documento = _documento_valido()
    del documento["messages"][1]["prompt_input"][0][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize(
    "chave",
    ["id", "phase", "task_id", "context_id", "model_name", "provider", "started_at", "outcome", "duration_ms",
     "tokens_input", "tokens_output", "finish_reason", "provider_response_id"],
)
def test_invocacao_sem_chave_obrigatoria_e_recusada(chave: str) -> None:
    documento = _documento_valido()
    del documento["invocations"][0][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


@pytest.mark.parametrize("chave", ["reason", "phase", "description", "occurred_at", "limit", "task_id",
                                   "pending_criteria_ids"])
def test_falha_sem_chave_obrigatoria_e_recusada(chave: str) -> None:
    documento = _documento_valido()
    documento["failure"] = _build_mapper().to_document(session=_sessao_falha())["failure"]
    del documento["failure"][chave]

    with pytest.raises(ValueError, match="obrigatória"):
        _build_mapper().from_document(document=documento)


def _sessao_falha() -> Session:
    sessao = _nova_sessao()
    sessao.status = SessionStatusEnum.FAILED
    sessao.failure = SessionFailure(
        reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        description="tentativas esgotadas",
        occurred_at=_ATUALIZADO_EM,
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        task_id="T2",
        pending_criteria_ids=("AC1",),
    )
    return sessao


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
        (("invocations", 0, "started_at"), "2026-08-31T12:00:00"),
        (("messages", 1, "prompt_input", 0, "creation_timestamp"), "2026-08-31T12:00:00"),
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


def test_benchmark_roundtrip_e_sessoes_antigas() -> None:
    session = _nova_sessao()
    session.benchmark_details = BenchmarkDetails(
        is_banchmark=True, question_name="Q1", corret_answer="A) um", providade_answer="A",
        inference_mode=BenchmarkInferenceModeEnum.SIMPLE, run_id="run_1", is_correct=True,
    )
    mapper = _build_mapper()
    document = mapper.to_document(session)
    assert mapper.from_document(document).benchmark_details == session.benchmark_details
    assert json.loads(json.dumps(document))["benchmark_details"]["inference_mode"] == "simple"
    del document["benchmark_details"]
    assert mapper.from_document(document).benchmark_details == BenchmarkDetails()


@pytest.mark.parametrize("value", [[], {"unknown": "invalid"}, {"inference_mode": "invalid"}])
def test_benchmark_malformado_e_recusado(value) -> None:
    document = _documento_valido()
    document["benchmark_details"] = value
    with pytest.raises(ValueError):
        _build_mapper().from_document(document)
