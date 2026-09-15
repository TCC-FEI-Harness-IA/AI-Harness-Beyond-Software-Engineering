import json
import logging

import pytest

from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.fake_structured_parser import FakeStructuredParser
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_FASE = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_SAIDA_VALIDA = json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "responder em pt-BR"}]})


def _parser_real() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser"))


def _janela() -> ContextWindow:
    return ContextWindow(context_id="ctx-1", phase=_FASE)


def _fase(
    llm_completions: ScriptedLLMCompletions,
    parser: IStructuredResponseParser | None = None,
    template_provider: FakePromptTemplateProvider | None = None,
    cost_guard: FakeCostGuard | None = None,
    clock: FakeClock | None = None,
    settings: FakeSettings | None = None,
) -> GeneralCriteriaPhase:
    return GeneralCriteriaPhase(
        llm_completions=llm_completions,
        template_provider=template_provider or FakePromptTemplateProvider(),
        parser=parser or _parser_real(),
        cost_guard=cost_guard or FakeCostGuard(),
        clock=clock or FakeClock(monotonic_values=[100, 912]),
        settings=settings or FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )


async def test_execucao_feliz_devolve_o_resultado_da_fase() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    fase = _fase(llm_completions=llm, clock=FakeClock(monotonic_values=[100, 912]))

    resultado = await fase.execute(context=_janela(), variables={"user_question": "pergunta"})

    assert resultado.raw_output == _SAIDA_VALIDA
    assert resultado.parsed["general_acceptance_criteria"][0]["id"] == "AC1"
    assert resultado.tokens.tokens_input == 40
    assert resultado.tokens.tokens_output == 12
    assert resultado.inference_time_ms == 812
    assert resultado.context_id == "ctx-1"


async def test_contexto_guarda_o_prompt_e_a_resposta_do_modelo() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "Pergunta: {{user_question}}"})

    await _fase(llm_completions=llm, template_provider=provider).execute(
        context=janela, variables={"user_question": "pergunta"}
    )

    assert [mensagem.text for mensagem in janela.messages] == ["Pergunta: pergunta", _SAIDA_VALIDA]
    assert janela.messages[0].source is MessageSourceEnum.USER
    assert janela.messages[1].source is MessageSourceEnum.LLM_AGENT


async def test_a_conversa_enviada_e_exatamente_a_janela_na_ordem() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "prompt da fase"})

    await _fase(llm_completions=llm, template_provider=provider).execute(context=janela, variables={})

    assert llm.texts_of(0) == ["prompt da fase"]


async def test_a_janela_acumula_os_tokens_da_chamada() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    janela = _janela()

    await _fase(llm_completions=llm).execute(context=janela, variables={})

    assert janela.context_size == 52


async def test_autoriza_antes_de_chamar_o_modelo_e_contabiliza_depois() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    guardiao = FakeCostGuard()

    await _fase(llm_completions=llm, cost_guard=guardiao).execute(context=_janela(), variables={})

    assert guardiao.authorizations == [_FASE]
    assert len(guardiao.registered_calls) == 1


async def test_autorizacao_negada_impede_a_chamada_ao_modelo() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    guardiao = FakeCostGuard(authorized=False, denied_limit=BudgetLimitEnum.LLM_CALLS_PER_SESSION)

    with pytest.raises(BudgetExceededError) as erro:
        await _fase(llm_completions=llm, cost_guard=guardiao).execute(context=_janela(), variables={})

    assert erro.value.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION
    assert llm.call_count == 0


async def test_configure_repassa_modelo_e_parametros_ao_provedor() -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    fase = _fase(llm_completions=llm)

    fase.configure(model_name="vendor/modelo", max_tokens=1200, temperature=0.3)
    await fase.execute(context=_janela(), variables={})

    assert llm.calls == [{"model_name": "vendor/modelo", "max_tokens": 1200, "temperature": 0.3}]


async def test_falha_de_parsing_seguida_de_sucesso_reaproveita_o_contexto() -> None:
    llm = ScriptedLLMCompletions(responses=["saida ruim", _SAIDA_VALIDA], tokens_input=10, tokens_output=4)
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="saida ruim", reason="json ausente"),
            {"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]},
        ]
    )
    janela = _janela()

    resultado = await _fase(llm_completions=llm, parser=parser).execute(context=janela, variables={})

    assert llm.call_count == 2
    assert any("json ausente" in mensagem.text for mensagem in janela.messages)
    assert resultado.tokens.tokens_input == 20
    assert resultado.tokens.tokens_output == 8


async def test_a_segunda_tentativa_enxerga_a_mensagem_de_correcao() -> None:
    llm = ScriptedLLMCompletions(responses=["saida ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="saida ruim", reason="json ausente"),
            {"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]},
        ]
    )

    await _fase(llm_completions=llm, parser=parser).execute(context=_janela(), variables={})

    assert "saida ruim" in llm.texts_of(1)
    assert any("json ausente" in texto for texto in llm.texts_of(1))


async def test_falha_de_parsing_alem_do_limite_repropaga_o_erro() -> None:
    erros = [
        PhaseParsingError(phase=_FASE, raw_output="ruim", reason=f"falha {indice}") for indice in range(3)
    ]
    llm = ScriptedLLMCompletions(responses=["ruim", "ruim", "ruim"])
    settings = FakeSettings(ralph_json_parse_max_retries=2)

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            parser=FakeStructuredParser(outcomes=list(erros)),
            settings=settings,
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 3


async def test_sem_retentativa_configurada_a_primeira_falha_ja_e_fatal() -> None:
    llm = ScriptedLLMCompletions(responses=["ruim"])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha")]
    )

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            parser=parser,
            settings=FakeSettings(ralph_json_parse_max_retries=0),
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 1


# ── Completion vazia ─────────────────────────────────────────────────────────
#
# Modelos de raciocínio às vezes gastam todo o `max_tokens` pensando e devolvem `content`
# nulo — de forma intermitente, na mesma pergunta. Como não há saída para corrigir, a fase
# só repete a chamada; o que não pode é a sessão inteira morrer numa falha passageira.

async def test_completion_vazia_seguida_de_sucesso_e_recuperada() -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA],
        tokens_input=10,
        tokens_output=4,
    )
    clock = FakeClock(monotonic_values=[100, 912])

    resultado = await _fase(llm_completions=llm, clock=clock).execute(context=_janela(), variables={})

    assert llm.call_count == 2
    assert resultado.parsed["general_acceptance_criteria"][0]["id"] == "AC1"


async def test_completion_vazia_nao_soma_tokens_nem_suja_a_janela() -> None:
    """A chamada sem conteúdo não produziu mensagem: a retentativa vê o contexto original."""
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA],
        tokens_input=10,
        tokens_output=4,
    )
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "prompt da fase"})
    clock = FakeClock(monotonic_values=[100, 912])

    resultado = await _fase(llm_completions=llm, template_provider=provider, clock=clock).execute(
        context=janela, variables={}
    )

    assert llm.texts_of(1) == ["prompt da fase"]
    assert resultado.tokens.tokens_input == 10
    assert resultado.tokens.tokens_output == 4


async def test_completion_vazia_alem_do_limite_repropaga_o_erro() -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length") for _ in range(3)]
    )

    with pytest.raises(EmptyCompletionError):
        await _fase(
            llm_completions=llm,
            settings=FakeSettings(ralph_json_parse_max_retries=2),
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 3


async def test_a_retentativa_tambem_pede_autorizacao_e_contabiliza_o_custo() -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha"),
            {"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]},
        ]
    )
    guardiao = FakeCostGuard()

    await _fase(llm_completions=llm, parser=parser, cost_guard=guardiao).execute(
        context=_janela(), variables={}
    )

    assert guardiao.authorizations == [_FASE, _FASE]
    assert len(guardiao.registered_calls) == 2
