import copy
import json
from typing import Any

import pytest

from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from tests.doubles.output_diagnostic_factories import (
    DIAGNOSTICO_Q037,
    DIAGNOSTICO_REPARADO,
    RECUPERACAO,
    sessao_com_recusa_recuperada,
)


def _documento() -> dict[str, Any]:
    return SessionDocumentMapper().to_document(session=sessao_com_recusa_recuperada())


def _ler(documento: dict[str, Any]):
    return SessionDocumentMapper().from_document(document=documento)


def test_documento_da_invocacao_recusada_traz_diagnostico_recuperacao_e_aceite() -> None:
    recusada = _documento()["invocations"][0]

    assert recusada["outcome"] == "success"
    assert recusada["finish_reason"] == "stop"
    assert recusada["content_accepted"] is False
    assert recusada["recovers_invocation_id"] is None
    assert recusada["output_diagnostic"] == {
        "syntax_status": "valid",
        "contract_status": "invalid",
        "finish_reason": "stop",
        "length_interruption": "not_detected",
        "repaired_closings": None,
        "problem": {
            "code": "decision_consistency",
            "reason": "A decisão 'approved' é incoerente com as avaliações.",
            "field": "decision",
            "affected_ids": ["T1-AC2"],
        },
    }
    assert recusada["recovery"] == {
        "strategy": "correction_prompt",
        "result": "recovered",
        "resolved_by_invocation_id": "inv-2",
    }


def test_documento_da_correcao_aponta_a_original_e_registra_o_reparo() -> None:
    correcao = _documento()["invocations"][1]

    assert correcao["recovers_invocation_id"] == "inv-1"
    assert correcao["content_accepted"] is True
    assert correcao["output_diagnostic"]["syntax_status"] == "valid_after_repair"
    assert correcao["output_diagnostic"]["repaired_closings"] == "]}"
    assert correcao["output_diagnostic"]["finish_reason"] is None
    assert correcao["output_diagnostic"]["length_interruption"] == "suspected"
    assert correcao["output_diagnostic"]["problem"] is None
    assert correcao["recovery"] is None


def test_mensagem_de_auditoria_aponta_a_invocacao() -> None:
    assert _documento()["messages"][0]["invocation_id"] == "inv-1"


def test_ida_e_volta_preserva_diagnosticos_recuperacao_e_vinculos() -> None:
    original = sessao_com_recusa_recuperada()

    reconstruida = _ler(_documento())

    assert reconstruida.invocations == original.invocations
    assert reconstruida.invocations[0].output_diagnostic == DIAGNOSTICO_Q037
    assert reconstruida.invocations[0].recovery == RECUPERACAO
    assert reconstruida.invocations[1].output_diagnostic == DIAGNOSTICO_REPARADO
    assert reconstruida.messages == original.messages
    assert reconstruida.rejected_output_count == 1
    assert reconstruida.totals.total_llm_calls == 2


def test_documento_com_diagnosticos_e_serializavel_em_json() -> None:
    documento = _documento()

    assert json.loads(json.dumps(documento)) == documento


def test_conteudo_aceito_gravado_e_ignorado_na_leitura_e_derivado_do_diagnostico() -> None:
    documento = _documento()
    documento["invocations"][0]["content_accepted"] = True

    assert _ler(documento).invocations[0].content_accepted is False


# ── Compatibilidade com sessões antigas ──────────────────────────────────────


def test_invocacao_antiga_sem_os_campos_novos_fica_com_diagnostico_desconhecido() -> None:
    documento = _documento()
    for invocacao in documento["invocations"]:
        for chave in ("recovers_invocation_id", "content_accepted", "output_diagnostic", "recovery"):
            del invocacao[chave]
    del documento["messages"][0]["invocation_id"]

    reconstruida = _ler(documento)

    for invocacao in reconstruida.invocations:
        assert invocacao.output_diagnostic is None
        assert invocacao.content_accepted is None
        assert invocacao.recovery is None
        assert invocacao.recovers_invocation_id is None
    assert reconstruida.messages[0].invocation_id is None
    assert reconstruida.rejected_output_count == 0


def test_invocacao_antiga_volta_ao_documento_com_ausencia_explicita_e_nao_com_sucesso() -> None:
    documento = _documento()
    del documento["invocations"][0]["output_diagnostic"]
    del documento["invocations"][0]["recovery"]

    regravado = SessionDocumentMapper().to_document(session=_ler(documento))

    assert regravado["invocations"][0]["outcome"] == "success"
    assert regravado["invocations"][0]["output_diagnostic"] is None
    assert regravado["invocations"][0]["content_accepted"] is None


# ── Leitura defensiva ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("caminho", "valor"),
    [
        (("output_diagnostic", "syntax_status"), "quase_valido"),
        (("output_diagnostic", "contract_status"), "talvez"),
        (("output_diagnostic", "length_interruption"), "provavel"),
        (("output_diagnostic", "problem", "code"), "erro_misterioso"),
        (("recovery", "strategy"), "rezar"),
        (("recovery", "result"), "quase"),
    ],
)
def test_valor_desconhecido_nos_diagnosticos_e_recusado(caminho: tuple[str, ...], valor: str) -> None:
    documento = _documento()
    alvo = documento["invocations"][0]
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    alvo[caminho[-1]] = valor

    with pytest.raises(ValueError, match="valor inválido"):
        _ler(documento)


@pytest.mark.parametrize(
    "caminho",
    [
        ("output_diagnostic", "syntax_status"),
        ("output_diagnostic", "contract_status"),
        ("output_diagnostic", "finish_reason"),
        ("output_diagnostic", "length_interruption"),
        ("output_diagnostic", "repaired_closings"),
        ("output_diagnostic", "problem"),
        ("output_diagnostic", "problem", "code"),
        ("output_diagnostic", "problem", "reason"),
        ("output_diagnostic", "problem", "field"),
        ("output_diagnostic", "problem", "affected_ids"),
        ("recovery", "strategy"),
        ("recovery", "result"),
        ("recovery", "resolved_by_invocation_id"),
    ],
)
def test_diagnostico_gravado_sem_chave_obrigatoria_e_recusado(caminho: tuple[str, ...]) -> None:
    documento = _documento()
    alvo = documento["invocations"][0]
    for chave in caminho[:-1]:
        alvo = alvo[chave]
    del alvo[caminho[-1]]

    with pytest.raises(ValueError, match="obrigatória"):
        _ler(documento)


def test_sintaxe_nula_gravada_volta_como_desconhecida() -> None:
    documento = _documento()
    diagnostico = documento["invocations"][0]["output_diagnostic"]
    diagnostico.update(syntax_status=None, contract_status="not_evaluated")
    diagnostico["problem"]["code"] = "unclassified"

    assert _ler(documento).invocations[0].output_diagnostic.syntax_status is None


def test_diagnostico_incoerente_gravado_e_recusado() -> None:
    documento = _documento()
    documento["invocations"][0]["output_diagnostic"]["problem"] = None

    with pytest.raises(ValueError, match="problema"):
        _ler(documento)


def test_from_document_nao_altera_o_documento_recebido() -> None:
    documento = _documento()
    copia = copy.deepcopy(documento)

    _ler(documento)

    assert documento == copia
