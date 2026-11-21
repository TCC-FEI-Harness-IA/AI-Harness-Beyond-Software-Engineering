"""Temperatura efetiva por execução (refinamentos 03, mudança 5.2).

A fase recebe, por execução, a temperatura da primeira chamada sem sobrescrever a temperatura configurada da
sessão. As recuperações de saída inválida ou vazia continuam a `1`, na janela da mesma execução, e a
temperatura enviada ao provedor é a mesma registrada na invocação.
"""
import json
import logging

import pytest

from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_FASE = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_SAIDA_VALIDA = json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "responder em pt-BR"}]})
_TEMPERATURA_DA_SESSAO = 0.2
_TEMPERATURA_DA_EXECUCAO = 0.5
_TEMPERATURA_DE_RETENTATIVA = 1.0


def _janela(context_id: str = "ctx-1") -> ContextWindow:
    return ContextWindow(context_id=context_id, phase=_FASE)


def _fase(llm: ScriptedLLMCompletions, recorder: SessionRecorderAdapter) -> GeneralCriteriaPhase:
    fase = GeneralCriteriaPhase(
        llm_completions=llm,
        template_provider=FakePromptTemplateProvider(),
        parser=StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser")),
        cost_guard=FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(monotonic_values=list(range(0, 400, 7))),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )
    fase.configure(
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=_TEMPERATURA_DA_SESSAO,
        provider=ModelProviderEnum.OPEN_ROUTER,
    )
    return fase


def _enviadas(llm: ScriptedLLMCompletions) -> list[float | None]:
    return [chamada["temperature"] for chamada in llm.calls]


def _registradas(recorder: SessionRecorderAdapter) -> list[float]:
    return [invocacao.temperature for invocacao in recorder.session.invocations]


async def test_temperatura_da_execucao_vale_na_primeira_chamada_validada_enviada_e_registrada(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])

    await _fase(llm, recorder).execute(context=_janela(), variables={}, temperature=_TEMPERATURA_DA_EXECUCAO)

    assert [validacao["temperature"] for validacao in llm.validations] == [_TEMPERATURA_DA_EXECUCAO]
    assert _enviadas(llm) == [_TEMPERATURA_DA_EXECUCAO]
    assert _registradas(recorder) == [_TEMPERATURA_DA_EXECUCAO]


async def test_saida_invalida_recupera_a_1_na_mesma_janela_depois_da_temperatura_da_execucao(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])
    janela = _janela()

    await _fase(llm, recorder).execute(context=janela, variables={}, temperature=_TEMPERATURA_DA_EXECUCAO)

    assert _enviadas(llm) == [_TEMPERATURA_DA_EXECUCAO, _TEMPERATURA_DE_RETENTATIVA]
    assert _registradas(recorder) == _enviadas(llm)
    assert len(llm.conversations[1]) == 3  # template, saída recusada e correção: a mesma janela
    assert recorder.session.invocations[1].recovers_invocation_id == recorder.session.invocations[0].id


async def test_resposta_vazia_tambem_recupera_a_1(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[EmptyCompletionError(finish_reason="stop"), _SAIDA_VALIDA])

    await _fase(llm, recorder).execute(context=_janela(), variables={}, temperature=_TEMPERATURA_DA_EXECUCAO)

    assert _enviadas(llm) == [_TEMPERATURA_DA_EXECUCAO, _TEMPERATURA_DE_RETENTATIVA]
    assert _registradas(recorder) == _enviadas(llm)


async def test_temperatura_configurada_nao_e_sobrescrita_e_volta_na_execucao_seguinte(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA, _SAIDA_VALIDA])
    fase = _fase(llm, recorder)

    await fase.execute(context=_janela("ctx-1"), variables={}, temperature=_TEMPERATURA_DA_EXECUCAO)
    await fase.execute(context=_janela("ctx-2"), variables={})

    assert fase.temperature == _TEMPERATURA_DA_SESSAO
    assert _enviadas(llm) == [_TEMPERATURA_DA_EXECUCAO, _TEMPERATURA_DA_SESSAO]
    assert _registradas(recorder) == _enviadas(llm)


async def test_sem_temperatura_explicita_a_execucao_usa_a_configurada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    assert _enviadas(llm) == [_TEMPERATURA_DA_SESSAO]


async def test_temperatura_explicita_e_retentativa_juntas_sao_ambiguas_e_recusadas_antes_da_chamada(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    janela = _janela()

    with pytest.raises(ValueError, match="temperatura"):
        await _fase(llm, recorder).execute(
            context=janela, variables={}, temperature=_TEMPERATURA_DA_EXECUCAO, is_retry=True
        )

    assert llm.call_count == 0 and llm.validations == []
    assert janela.is_empty()
