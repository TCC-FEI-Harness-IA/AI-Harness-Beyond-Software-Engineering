import json
import logging

import pytest

from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.application.phases.task_verification_phase import TaskVerificationPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.invalid_output import InvalidOutput
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.fake_structured_parser import FakeStructuredParser
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_FASE = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_SAIDA_VALIDA = json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "responder em pt-BR"}]})
_CRITERIOS_VALIDOS = {"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}


def _parser_real() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser"))


def _janela() -> ContextWindow:
    return ContextWindow(context_id="ctx-1", phase=_FASE)


def _fase(
    llm_completions: ScriptedLLMCompletions,
    recorder: SessionRecorderAdapter,
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
        session_recorder=recorder,
        clock=clock or FakeClock(monotonic_values=[100, 912]),
        settings=settings or FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )


async def test_execucao_feliz_devolve_o_resultado_da_fase(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    fase = _fase(llm_completions=llm, recorder=recorder, clock=FakeClock(monotonic_values=[100, 912]))

    resultado = await fase.execute(context=_janela(), variables={"user_question": "pergunta"})

    assert resultado.raw_output == _SAIDA_VALIDA
    assert resultado.parsed["general_acceptance_criteria"][0]["id"] == "AC1"
    assert resultado.tokens.tokens_input == 40
    assert resultado.tokens.tokens_output == 12
    assert resultado.inference_time_ms == 812
    assert resultado.context_id == "ctx-1"
    assert resultado.invalid_outputs == ()


async def test_contexto_guarda_o_prompt_e_a_resposta_do_modelo(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "Pergunta: {{user_question}}"})

    await _fase(llm_completions=llm, recorder=recorder, template_provider=provider).execute(
        context=janela, variables={"user_question": "pergunta"}
    )

    assert [mensagem.text for mensagem in janela.messages] == ["Pergunta: pergunta", _SAIDA_VALIDA]
    assert janela.messages[0].source is MessageSourceEnum.USER
    assert janela.messages[1].source is MessageSourceEnum.LLM_AGENT


async def test_a_conversa_enviada_e_exatamente_a_janela_na_ordem(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "prompt da fase"})

    await _fase(llm_completions=llm, recorder=recorder, template_provider=provider).execute(
        context=janela, variables={}
    )

    assert llm.texts_of(0) == ["prompt da fase"]


async def test_a_janela_acumula_os_tokens_da_chamada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    janela = _janela()

    await _fase(llm_completions=llm, recorder=recorder).execute(context=janela, variables={})

    assert janela.context_size == 52


async def test_inicia_a_chamada_no_guardiao_reservando_o_teto_de_saida(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    guardiao = FakeCostGuard()
    fase = _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao)
    fase.configure(model_name="vendor/modelo", max_tokens=777, temperature=0.3, provider=ModelProviderEnum.OPENAI)

    await fase.execute(context=_janela(), variables={})

    assert guardiao.started_calls == [(_FASE, 777)]
    assert guardiao.registered_usages == [(40, 12)]


async def test_sem_configure_a_reserva_de_saida_e_o_teto_padrao_das_configuracoes(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    guardiao = FakeCostGuard()

    await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao).execute(
        context=_janela(), variables={}
    )

    assert guardiao.started_calls == [(_FASE, 1024)]


async def test_autorizacao_negada_impede_a_chamada_e_o_registro_da_invocacao(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    guardiao = FakeCostGuard(authorized=False, denied_limit=BudgetLimitEnum.LLM_CALLS_PER_SESSION)

    with pytest.raises(BudgetExceededError) as erro:
        await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao).execute(
            context=_janela(), variables={}
        )

    assert erro.value.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION
    assert erro.value.phase is _FASE
    assert erro.value.detail == "negado pelo dublê"
    assert llm.call_count == 0
    assert recorder.session.invocations == []
    assert recorder.session.totals.total_llm_calls == 0


async def test_configure_repassa_modelo_e_parametros_ao_provedor(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    fase = _fase(llm_completions=llm, recorder=recorder)

    fase.configure(
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        provider=ModelProviderEnum.OPENAI,
    )
    await fase.execute(context=_janela(), variables={})

    assert llm.calls == [
        {
            "model_name": "vendor/modelo",
            "max_tokens": 1200,
            "temperature": 0.3,
            "provider": ModelProviderEnum.OPENAI,
        }
    ]


async def test_falha_de_parsing_seguida_de_sucesso_reaproveita_o_contexto(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["saida ruim", _SAIDA_VALIDA], tokens_input=10, tokens_output=4)
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="saida ruim", reason="json ausente"),
            _CRITERIOS_VALIDOS,
        ]
    )
    janela = _janela()

    resultado = await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=janela, variables={}
    )

    assert llm.call_count == 2
    assert any("json ausente" in mensagem.text for mensagem in janela.messages)
    assert resultado.tokens.tokens_input == 20
    assert resultado.tokens.tokens_output == 8


async def test_a_segunda_tentativa_enxerga_a_mensagem_de_correcao(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["saida ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="saida ruim", reason="json ausente"),
            _CRITERIOS_VALIDOS,
        ]
    )

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    assert "saida ruim" in llm.texts_of(1)
    assert any("json ausente" in texto for texto in llm.texts_of(1))


async def test_saidas_recusadas_e_corrigidas_ficam_expostas_no_resultado(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["primeira ruim", "segunda ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="primeira ruim", reason="json ausente"),
            PhaseParsingError(phase=_FASE, raw_output="segunda ruim", reason="campo faltando"),
            _CRITERIOS_VALIDOS,
        ]
    )

    resultado = await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=_janela(), variables={}
    )

    assert resultado.invalid_outputs == (
        InvalidOutput(raw_output="primeira ruim", reason="json ausente"),
        InvalidOutput(raw_output="segunda ruim", reason="campo faltando"),
    )


async def test_falha_de_parsing_alem_do_limite_repropaga_o_erro(recorder: SessionRecorderAdapter) -> None:
    erros = [
        PhaseParsingError(phase=_FASE, raw_output="ruim", reason=f"falha {indice}") for indice in range(3)
    ]
    llm = ScriptedLLMCompletions(responses=["ruim", "ruim", "ruim"])
    settings = FakeSettings(ralph_json_parse_max_retries=2)

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            parser=FakeStructuredParser(outcomes=list(erros)),
            settings=settings,
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 3


async def test_sem_retentativa_configurada_a_primeira_falha_ja_e_fatal(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim"])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha")]
    )

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            parser=parser,
            settings=FakeSettings(ralph_json_parse_max_retries=0),
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 1


# ── Contexto de validação ────────────────────────────────────────────────────


async def test_repassa_o_contexto_de_validacao_ao_parser(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    parser = FakeStructuredParser(outcomes=[_CRITERIOS_VALIDOS])
    validacao = ValidationContext(expected_criteria_ids=("AC1",), max_tasks=3)

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=_janela(), variables={}, validation=validacao
    )

    assert parser.validations == [validacao]


async def test_sem_contexto_de_validacao_o_parser_recebe_none(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    parser = FakeStructuredParser(outcomes=[_CRITERIOS_VALIDOS])

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    assert parser.validations == [None]


def _verificacao(*avaliacoes: tuple[str, bool]) -> str:
    falhas = [criterion_id for criterion_id, met in avaliacoes if not met]
    return json.dumps(
        {
            "decision": "reproved" if falhas else "approved",
            "criteria_evaluation": [
                {"criterion_id": criterion_id, "met": met, "justification": "porque"}
                for criterion_id, met in avaliacoes
            ],
            "unmet_criteria_ids": falhas,
        }
    )


async def test_relatorio_que_nao_cobre_os_criterios_pede_correcao_ao_verificador(
    recorder: SessionRecorderAdapter,
) -> None:
    """Um relatório incompleto é corrigido pelo verificador, sem aprovar nem abortar a fase."""
    llm = ScriptedLLMCompletions(
        responses=[_verificacao(("T1-AC1", True)), _verificacao(("T1-AC1", True), ("T1-AC2", True))]
    )
    guardiao = FakeCostGuard()
    fase = TaskVerificationPhase(
        llm_completions=llm,
        template_provider=FakePromptTemplateProvider(),
        parser=_parser_real(),
        cost_guard=guardiao,
        session_recorder=recorder,
        clock=FakeClock(monotonic_values=[0, 5, 10, 20]),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )
    janela = ContextWindow(context_id="ctx-v", phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION)

    resultado = await fase.execute(
        context=janela,
        variables={},
        validation=ValidationContext(expected_criteria_ids=("T1-AC1", "T1-AC2")),
    )

    assert llm.call_count == 2
    assert any("T1-AC2" in texto for texto in llm.texts_of(1))
    assert len(resultado.parsed["criteria_evaluation"]) == 2
    assert [saida.reason for saida in resultado.invalid_outputs] == [
        "Faltam avaliações para os critérios: T1-AC2."
    ]
    assert len(guardiao.started_calls) == 2


async def test_relatorio_sem_o_contexto_de_validacao_e_um_erro_de_programacao(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_verificacao(("T1-AC1", True))])
    fase = TaskVerificationPhase(
        llm_completions=llm,
        template_provider=FakePromptTemplateProvider(),
        parser=_parser_real(),
        cost_guard=FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )

    with pytest.raises(ValueError, match="contexto de validação"):
        await fase.execute(
            context=ContextWindow(context_id="ctx-v", phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION),
            variables={},
        )


# ── Completion vazia ─────────────────────────────────────────────────────────
#
# Modelos de raciocínio às vezes gastam todo o `max_tokens` pensando e devolvem `content`
# nulo — de forma intermitente, na mesma pergunta. Como não há saída para corrigir, a fase
# só repete a chamada; o que não pode é a sessão inteira morrer numa falha passageira, nem a
# chamada perdida sumir da contabilidade.

async def test_completion_vazia_seguida_de_sucesso_e_recuperada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA],
        tokens_input=10,
        tokens_output=4,
    )
    clock = FakeClock(monotonic_values=[100, 912])

    resultado = await _fase(llm_completions=llm, recorder=recorder, clock=clock).execute(
        context=_janela(), variables={}
    )

    assert llm.call_count == 2
    assert resultado.parsed["general_acceptance_criteria"][0]["id"] == "AC1"


async def test_completion_vazia_nao_suja_a_janela_e_a_retentativa_ve_o_contexto_original(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA],
        tokens_input=10,
        tokens_output=4,
    )
    janela = _janela()
    provider = FakePromptTemplateProvider(templates={_FASE: "prompt da fase"})
    clock = FakeClock(monotonic_values=[100, 912])

    await _fase(llm_completions=llm, recorder=recorder, template_provider=provider, clock=clock).execute(
        context=janela, variables={}
    )

    assert llm.texts_of(1) == ["prompt da fase"]
    assert janela.context_size == 14


async def test_completion_vazia_preserva_consumo_e_tempo_no_resultado_da_fase(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length", tokens_input=100, tokens_output=40), _SAIDA_VALIDA],
        tokens_input=10,
        tokens_output=4,
    )
    clock = FakeClock(monotonic_values=[0, 30, 30, 40])

    resultado = await _fase(llm_completions=llm, recorder=recorder, clock=clock).execute(
        context=_janela(), variables={}
    )

    assert resultado.tokens.tokens_input == 110
    assert resultado.tokens.tokens_output == 44
    assert resultado.inference_time_ms == 40


async def test_completion_vazia_registra_uma_invocacao_com_o_consumo_do_provedor(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(
        responses=[
            EmptyCompletionError(finish_reason="length", tokens_input=100, tokens_output=40, response_id="gen-1"),
            _SAIDA_VALIDA,
        ],
        tokens_input=10,
        tokens_output=4,
    )
    guardiao = FakeCostGuard()
    clock = FakeClock(monotonic_values=[0, 30, 30, 40])

    await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao, clock=clock).execute(
        context=_janela(), variables={}
    )

    vazia, boa = recorder.session.invocations
    assert vazia.outcome is InvocationOutcomeEnum.EMPTY_COMPLETION
    assert (vazia.tokens_input, vazia.tokens_output) == (100, 40)
    assert vazia.finish_reason == "length"
    assert vazia.provider_response_id == "gen-1"
    assert vazia.duration_ms == 30
    assert boa.outcome is InvocationOutcomeEnum.SUCCESS
    assert guardiao.registered_usages == [(100, 40), (10, 4)]
    assert recorder.session.totals.total_llm_calls == 2
    assert recorder.session.totals.total_tokens == 154


async def test_completion_vazia_sem_consumo_informado_conta_como_chamada_com_consumo_desconhecido(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[EmptyCompletionError(finish_reason="stop"), _SAIDA_VALIDA])
    guardiao = FakeCostGuard()

    await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao).execute(
        context=_janela(), variables={}
    )

    vazia = recorder.session.invocations[0]
    assert (vazia.tokens_input, vazia.tokens_output) == (None, None)
    assert vazia.usage_known is False
    assert recorder.session.totals.total_llm_calls == 2
    assert guardiao.registered_usages[0] == (0, 0)


async def test_completion_vazia_alem_do_limite_repropaga_o_erro_e_nao_perde_nenhuma_chamada(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(
        responses=[EmptyCompletionError(finish_reason="length", tokens_input=3, tokens_output=2) for _ in range(3)]
    )

    with pytest.raises(EmptyCompletionError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            settings=FakeSettings(ralph_json_parse_max_retries=2),
        ).execute(context=_janela(), variables={})

    assert llm.call_count == 3
    assert recorder.session.totals.total_llm_calls == 3
    assert recorder.session.totals.total_tokens == 15


async def test_a_retentativa_tambem_pede_autorizacao_e_contabiliza_o_custo(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha"),
            _CRITERIOS_VALIDOS,
        ]
    )
    guardiao = FakeCostGuard()

    await _fase(llm_completions=llm, recorder=recorder, parser=parser, cost_guard=guardiao).execute(
        context=_janela(), variables={}
    )

    assert [fase for fase, _ in guardiao.started_calls] == [_FASE, _FASE]
    assert len(guardiao.registered_usages) == 2


# ── Registro por invocação ───────────────────────────────────────────────────


async def test_cada_chamada_gera_uma_invocacao_com_fase_contexto_modelo_e_desfecho(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=40, tokens_output=12)
    fase = _fase(llm_completions=llm, recorder=recorder, clock=FakeClock(monotonic_values=[100, 912]))
    fase.configure(model_name="vendor/outro", max_tokens=1200, temperature=0.3, provider=ModelProviderEnum.OPENAI)

    await fase.execute(context=ContextWindow(context_id="ctx-9", phase=_FASE, task_id="T4"), variables={})

    (invocacao,) = recorder.session.invocations
    assert invocacao.phase is _FASE
    assert invocacao.task_id == "T4"
    assert invocacao.context_id == "ctx-9"
    assert invocacao.model_name == "vendor/outro"
    assert invocacao.provider is ModelProviderEnum.OPENAI
    assert invocacao.outcome is InvocationOutcomeEnum.SUCCESS
    assert (invocacao.tokens_input, invocacao.tokens_output) == (40, 12)
    assert invocacao.duration_ms == 812
    assert invocacao.finish_reason == "stop"


async def test_sem_configure_a_invocacao_registra_o_modelo_e_o_provedor_padrao(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])

    await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    invocacao = recorder.session.invocations[0]
    assert invocacao.model_name == "vendor/modelo-padrao"
    assert invocacao.provider is ModelProviderEnum.OPEN_ROUTER


async def test_a_invocacao_ja_consta_na_sessao_quando_a_chamada_e_enviada(recorder: SessionRecorderAdapter) -> None:
    vistas: list[tuple[int, InvocationOutcomeEnum]] = []

    class _EspiaoLLM(ScriptedLLMCompletions):
        async def send_conversation(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            vistas.append((recorder.session.totals.total_llm_calls, recorder.session.invocations[-1].outcome))
            return await super().send_conversation(*args, **kwargs)

    llm = _EspiaoLLM(responses=[_SAIDA_VALIDA])

    await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert vistas == [(1, InvocationOutcomeEnum.STARTED)]


async def test_falha_de_parsing_nao_apaga_o_custo_das_chamadas_feitas(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", "ruim", "ruim"], tokens_input=10, tokens_output=5)
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason=f"falha {i}") for i in range(3)]
    )

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            parser=parser,
            settings=FakeSettings(ralph_json_parse_max_retries=2),
        ).execute(context=_janela(), variables={})

    assert recorder.session.totals.total_llm_calls == 3
    assert recorder.session.totals.total_tokens == 45
    assert [i.outcome for i in recorder.session.invocations] == [InvocationOutcomeEnum.SUCCESS] * 3


async def test_erro_do_provedor_registra_a_invocacao_com_consumo_desconhecido_e_repropaga(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[RuntimeError("provedor fora do ar")])

    with pytest.raises(RuntimeError, match="provedor fora do ar"):
        await _fase(
            llm_completions=llm, recorder=recorder, clock=FakeClock(monotonic_values=[0, 77])
        ).execute(context=_janela(), variables={})

    (invocacao,) = recorder.session.invocations
    assert invocacao.outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert invocacao.usage_known is False
    assert invocacao.duration_ms == 77
    assert recorder.session.totals.total_llm_calls == 1
    assert recorder.session.totals.total_tokens == 0


async def test_resposta_sem_consumo_informado_conta_a_chamada_sem_inventar_custo_zero(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=None, tokens_output=None)

    resultado = await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    (invocacao,) = recorder.session.invocations
    assert invocacao.outcome is InvocationOutcomeEnum.SUCCESS
    assert (invocacao.tokens_input, invocacao.tokens_output) == (None, None)
    assert recorder.session.totals.total_llm_calls == 1
    assert (resultado.tokens.input_known, resultado.tokens.output_known) == (False, False)


async def test_o_resultado_da_fase_agrega_sem_duplicar_o_que_a_sessao_soma(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA], tokens_input=10, tokens_output=4)
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha"), _CRITERIOS_VALIDOS]
    )

    resultado = await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=_janela(), variables={}
    )

    assert resultado.tokens.tokens_input + resultado.tokens.tokens_output == 28
    assert recorder.session.totals.total_tokens == 28
    assert recorder.session.totals.total_llm_calls == 2


# ── Auditoria das saídas inválidas ───────────────────────────────────────────


def _auditorias(recorder: SessionRecorderAdapter) -> list:
    return [
        mensagem
        for mensagem in recorder.session.messages
        if mensagem.source is MessageSourceEnum.SYSTEM and "Saída inválida" in mensagem.content
    ]


async def test_saidas_invalidas_ficam_na_sessao_mesmo_quando_as_correcoes_se_esgotam(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim 1", "ruim 2", "ruim 3"])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="x", reason=f"falha {indice}") for indice in range(3)]
    )

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            parser=parser,
            settings=FakeSettings(ralph_json_parse_max_retries=2),
        ).execute(context=_janela(), variables={})

    auditorias = _auditorias(recorder)
    assert len(auditorias) == 3
    for indice, mensagem in enumerate(auditorias, start=1):
        assert f"ruim {indice}" in mensagem.content
        assert f"falha {indice - 1}" in mensagem.content
        assert mensagem.phase is _FASE
        assert mensagem.context_id == "ctx-1"
        assert mensagem.tokens_input == 0
        assert mensagem.tokens_output == 0
    assert recorder.session.totals.total_llm_calls == 3
    assert recorder.session.totals.total_tokens == 45


async def test_saida_invalida_corrigida_tambem_fica_na_sessao(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="json ausente"), _CRITERIOS_VALIDOS]
    )

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    (auditoria,) = _auditorias(recorder)
    assert "ruim" in auditoria.content
    assert "json ausente" in auditoria.content


async def test_saida_invalida_sem_retentativa_ja_fica_registrada_antes_da_falha(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim"])
    parser = FakeStructuredParser(outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha")])

    with pytest.raises(PhaseParsingError):
        await _fase(
            llm_completions=llm,
            recorder=recorder,
            parser=parser,
            settings=FakeSettings(ralph_json_parse_max_retries=0),
        ).execute(context=_janela(), variables={})

    assert len(_auditorias(recorder)) == 1


async def test_completion_vazia_nao_gera_auditoria_de_saida_invalida(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA])

    await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert _auditorias(recorder) == []


async def test_resposta_com_consumo_parcial_preserva_o_contador_ausente_como_desconhecido(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], tokens_input=10, tokens_output=None)

    resultado = await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    (invocacao,) = recorder.session.invocations
    assert (invocacao.tokens_input, invocacao.tokens_output) == (10, None)
    assert invocacao.usage_known is True
    assert recorder.session.totals.tokens_input == 10
    assert recorder.session.totals.tokens_output == 0
    assert (resultado.tokens.input_known, resultado.tokens.output_known) == (True, False)


async def test_consumo_parcial_de_uma_chamada_torna_desconhecido_o_contador_agregado_da_fase(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA], tokens_input=10, tokens_output=None)
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="falha"), _CRITERIOS_VALIDOS]
    )

    resultado = await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=_janela(), variables={}
    )

    assert resultado.tokens.tokens_input == 20
    assert resultado.tokens.input_known is True
    assert resultado.tokens.output_known is False


# ── Recusa local anterior ao envio ───────────────────────────────────────────


async def test_recusa_local_nao_gera_invocacao_nem_conta_chamada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], validation_error=ValueError("Missing OpenRouter settings."))
    guardiao = FakeCostGuard()

    with pytest.raises(ValueError, match="Missing OpenRouter settings"):
        await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao).execute(
            context=_janela(), variables={}
        )

    assert llm.call_count == 0
    assert recorder.session.invocations == []
    assert recorder.session.totals.total_llm_calls == 0
    assert guardiao.started_calls == []
    assert guardiao.registered_usages == []


async def test_a_validacao_local_recebe_a_mesma_conversa_e_os_mesmos_parametros_do_envio(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    fase = _fase(
        llm_completions=llm,
        recorder=recorder,
        template_provider=FakePromptTemplateProvider(templates={_FASE: "prompt da fase"}),
    )
    fase.configure(model_name="vendor/modelo", max_tokens=777, temperature=0.0, provider=ModelProviderEnum.OPENAI)

    await fase.execute(context=_janela(), variables={})

    assert llm.validations == [
        {
            "texts": ["prompt da fase"],
            "model_name": "vendor/modelo",
            "max_tokens": 777,
            "temperature": 0.0,
            "provider": ModelProviderEnum.OPENAI,
        }
    ]


async def test_a_validacao_local_vem_antes_da_autorizacao_de_custo(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], validation_error=ValueError("modelo inválido"))
    guardiao = FakeCostGuard(authorized=False, denied_limit=BudgetLimitEnum.LLM_CALLS_PER_SESSION)

    with pytest.raises(ValueError, match="modelo inválido"):
        await _fase(llm_completions=llm, recorder=recorder, cost_guard=guardiao).execute(
            context=_janela(), variables={}
        )

    assert guardiao.started_calls == []


async def test_erro_do_provedor_depois_do_envio_continua_contando_como_chamada(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(error=RuntimeError("HTTP 500"))

    with pytest.raises(RuntimeError):
        await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    (invocacao,) = recorder.session.invocations
    assert invocacao.outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert recorder.session.totals.total_llm_calls == 1


# ── Prompt de entrada ────────────────────────────────────────────────────────


async def test_o_resultado_carrega_a_conversa_enviada_ao_modelo(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])
    provider = FakePromptTemplateProvider(templates={_FASE: "prompt da fase"})

    resultado = await _fase(llm_completions=llm, recorder=recorder, template_provider=provider).execute(
        context=_janela(), variables={}
    )

    assert [mensagem.text for mensagem in resultado.prompt_input] == llm.texts_of(0) == ["prompt da fase"]
    assert resultado.prompt_input[0].source is MessageSourceEnum.USER


async def test_apos_correcao_o_prompt_de_entrada_e_o_da_chamada_que_produziu_a_saida_valida(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["saida ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="saida ruim", reason="json ausente"),
            _CRITERIOS_VALIDOS,
        ]
    )

    resultado = await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(
        context=_janela(), variables={}
    )

    assert [mensagem.text for mensagem in resultado.prompt_input] == llm.texts_of(1)
    assert _SAIDA_VALIDA not in [mensagem.text for mensagem in resultado.prompt_input]


async def test_a_auditoria_da_saida_invalida_guarda_o_prompt_que_a_produziu(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="json ausente"), _CRITERIOS_VALIDOS]
    )

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    (auditoria,) = _auditorias(recorder)
    assert [mensagem.text for mensagem in auditoria.prompt_input] == llm.texts_of(0)


# ── Temperatura das retentativas ─────────────────────────────────────────────
#
# Uma retentativa repete um pedido que acabou de falhar. Com a temperatura do usuário — em
# geral baixa —, o modelo tende a devolver a mesma saída e a falhar do mesmo jeito até esgotar
# as tentativas. Por isso toda chamada de retentativa sai com temperatura 1, e a temperatura do
# usuário volta a valer assim que as retentativas acabam.

_TEMPERATURA_DO_USUARIO = 0.3
_TEMPERATURA_DE_RETENTATIVA = 1.0


def _fase_configurada(
    llm: ScriptedLLMCompletions,
    recorder: SessionRecorderAdapter,
    parser: IStructuredResponseParser | None = None,
    retentativas: int = 2,
) -> GeneralCriteriaPhase:
    fase = _fase(
        llm_completions=llm,
        recorder=recorder,
        parser=parser,
        settings=FakeSettings(ralph_json_parse_max_retries=retentativas),
    )
    fase.configure(
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=_TEMPERATURA_DO_USUARIO,
        provider=ModelProviderEnum.OPENAI,
    )
    return fase


def _temperaturas(llm: ScriptedLLMCompletions) -> list[object]:
    return [chamada["temperature"] for chamada in llm.calls]


async def test_a_correcao_de_saida_invalida_e_pedida_com_temperatura_1(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [_TEMPERATURA_DO_USUARIO, _TEMPERATURA_DE_RETENTATIVA]


async def test_todas_as_correcoes_seguidas_usam_temperatura_1(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim 1", "ruim 2", _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [
        _TEMPERATURA_DO_USUARIO,
        _TEMPERATURA_DE_RETENTATIVA,
        _TEMPERATURA_DE_RETENTATIVA,
    ]


async def test_saida_que_contradiz_a_validacao_tambem_e_corrigida_com_temperatura_1(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["relatorio incoerente", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[
            PhaseParsingError(phase=_FASE, raw_output="relatorio incoerente", reason="faltam avaliações"),
            _CRITERIOS_VALIDOS,
        ]
    )

    await _fase_configurada(llm=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [_TEMPERATURA_DO_USUARIO, _TEMPERATURA_DE_RETENTATIVA]


async def test_a_repeticao_depois_de_completion_vazia_usa_temperatura_1(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [_TEMPERATURA_DO_USUARIO, _TEMPERATURA_DE_RETENTATIVA]


async def test_a_validacao_local_da_retentativa_recebe_a_temperatura_1(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert [validacao["temperature"] for validacao in llm.validations] == [
        _TEMPERATURA_DO_USUARIO,
        _TEMPERATURA_DE_RETENTATIVA,
    ]


async def test_a_temperatura_do_usuario_volta_na_execucao_seguinte_a_das_retentativas(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA, _SAIDA_VALIDA])
    fase = _fase_configurada(llm=llm, recorder=recorder)

    await fase.execute(context=_janela(), variables={})
    await fase.execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [_TEMPERATURA_DO_USUARIO, _TEMPERATURA_DE_RETENTATIVA, _TEMPERATURA_DO_USUARIO]
    assert fase.temperature == _TEMPERATURA_DO_USUARIO


async def test_execucao_sem_falha_nunca_usa_a_temperatura_de_retentativa(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [_TEMPERATURA_DO_USUARIO]


async def test_execucao_marcada_como_retentativa_ja_comeca_com_temperatura_1(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={}, is_retry=True)

    assert _temperaturas(llm) == [_TEMPERATURA_DE_RETENTATIVA, _TEMPERATURA_DE_RETENTATIVA]


async def test_a_invocacao_registra_a_temperatura_efetiva_de_cada_chamada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])

    await _fase_configurada(llm=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert [invocacao.temperature for invocacao in recorder.session.invocations] == [
        _TEMPERATURA_DO_USUARIO,
        _TEMPERATURA_DE_RETENTATIVA,
    ]


async def test_sem_configure_a_invocacao_registra_a_temperatura_padrao_das_configuracoes(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["isto nao e json", _SAIDA_VALIDA])

    await _fase(
        llm_completions=llm, recorder=recorder, settings=FakeSettings(ralph_json_parse_max_retries=1)
    ).execute(context=_janela(), variables={})

    assert _temperaturas(llm) == [None, _TEMPERATURA_DE_RETENTATIVA]
    assert [invocacao.temperature for invocacao in recorder.session.invocations] == [0.7, _TEMPERATURA_DE_RETENTATIVA]


# ── Reparo automático de JSON incompleto ─────────────────────────────────────
#
# Toda fase que espera JSON passa a saída pelo parser junto com o motivo de término da chamada:
# é ele que decide se faltam só fechamentos (reparáveis) ou conteúdo (corte por limite de tokens).


async def test_repassa_ao_parser_o_motivo_de_termino_da_chamada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], finish_reason="stop")
    parser = FakeStructuredParser(outcomes=[_CRITERIOS_VALIDOS])

    await _fase(llm_completions=llm, recorder=recorder, parser=parser).execute(context=_janela(), variables={})

    assert parser.finish_reasons == ["stop"]


async def test_json_sem_o_fechamento_final_e_aceito_sem_retentativa(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA[:-1]], finish_reason="stop")

    resultado = await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert llm.call_count == 1
    assert resultado.parsed == json.loads(_SAIDA_VALIDA)
    assert resultado.raw_output == _SAIDA_VALIDA[:-1]
    assert resultado.invalid_outputs == ()


async def test_json_cortado_pelo_limite_de_tokens_ainda_pede_retentativa(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA[:-1], _SAIDA_VALIDA], finish_reason="length")

    resultado = await _fase(llm_completions=llm, recorder=recorder).execute(context=_janela(), variables={})

    assert llm.call_count == 2
    assert resultado.parsed == json.loads(_SAIDA_VALIDA)
    assert [saida.raw_output for saida in resultado.invalid_outputs] == [_SAIDA_VALIDA[:-1]]
