"""Recuperação integral: a conversa enviada, não apenas o registro de auditoria.

As respostas são roteirizadas. Preservar o conteúdo e pedir cobertura não prova que um modelo
real produzirá um plano semanticamente suficiente.
"""
import asyncio
import json
import logging

import pytest

from src.application.phases.additional_planning_phase import AdditionalPlanningPhase
from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.application.phases.task_decomposition_phase import TaskDecompositionPhase
from src.application.phases.task_resolution_phase import TaskResolutionPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_defect_enum import OutputDefectEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.interfaces.cost_guard_interface import ICostGuard
from src.infra.adapters.cost_guard_adapter import CostGuardAdapter
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scripts import tarefa
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_A2 = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
_C2 = ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING
_B1 = ThinkingPhaseEnum.B1_TASK_RESOLUTION
_LONGO = "Explain each relation and its assumptions. " * 40
_DADO_FINAL = "Apply the final relation to determine the requested period in months."
_VALIDA = json.dumps({"result": "complete corrected result", "conclusion": "corrected conclusion"})


def _plano() -> dict:
    plano = {"tasks": [tarefa(task_id) for task_id in ("T1", "T2", "T3")]}
    plano["tasks"][0]["description"] = _LONGO
    plano["tasks"][2]["description"] = _DADO_FINAL
    return plano


def _fase(
    classe: type[BaseThinkingPhase], llm: ScriptedLLMCompletions, recorder: SessionRecorderAdapter,
    retentativas: int = 2, guardiao: ICostGuard | None = None,
) -> BaseThinkingPhase:
    fase = classe(
        llm_completions=llm,
        template_provider=FakePromptTemplateProvider(),
        parser=StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser")),
        cost_guard=guardiao or FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(monotonic_values=list(range(0, 100, 7))),
        settings=FakeSettings(ralph_json_parse_max_retries=retentativas),
        logger=logging.getLogger("teste.fase"),
    )
    fase.configure(model_name="vendor/modelo", max_tokens=1200, temperature=0.3, provider=ModelProviderEnum.OPENAI)
    return fase


def _janela(phase: ThinkingPhaseEnum = _B1) -> ContextWindow:
    return ContextWindow(context_id=f"ctx-{phase.value}", phase=phase)


def _auditorias(recorder: SessionRecorderAdapter) -> list:
    return [m for m in recorder.session.messages if "Saída inválida" in m.content]


@pytest.mark.parametrize("classe,phase", [(TaskDecompositionPhase, _A2), (AdditionalPlanningPhase, _C2)])
async def test_plano_longo_sem_titulo_chega_inteiro_a_correcao(
    recorder: SessionRecorderAdapter, classe: type[BaseThinkingPhase], phase: ThinkingPhaseEnum,
) -> None:
    completo = _plano()
    corrigida = json.dumps(completo)
    del completo["tasks"][2]["title"]
    recusada = json.dumps(completo)
    assert recusada.index('"id": "T2"') > 1000
    llm = ScriptedLLMCompletions(responses=[recusada, corrigida])

    resultado = await _fase(classe, llm, recorder).execute(context=_janela(phase), variables={})

    template, anterior, correcao = llm.conversations[1]
    assert anterior.text == recusada
    assert anterior.source is MessageSourceEnum.LLM_AGENT
    assert _DADO_FINAL in anterior.text
    assert '"T2"' in anterior.text and '"T3"' in anterior.text
    assert llm.texts_of(1).count(template.text) == 1
    assert llm.texts_of(0) == [template.text]
    assert correcao.source is MessageSourceEnum.USER
    assert "title" in correcao.text and resultado.invalid_outputs[0].reason in correcao.text
    assert tuple(llm.conversations[1]) == resultado.prompt_input
    assert resultado.raw_output == corrigida
    assert resultado.parsed == json.loads(corrigida)
    assert [t["id"] for t in resultado.parsed["tasks"]] == ["T1", "T2", "T3"]
    assert resultado.invalid_outputs[0].raw_output == recusada
    assert recusada in _auditorias(recorder)[0].content
    original, recuperacao = recorder.session.invocations
    assert original.output_diagnostic.problem.field == "tasks[].title"
    assert original.output_diagnostic.problem.affected_ids == ("T3",)
    assert original.content_accepted is False and recuperacao.content_accepted is True
    assert recuperacao.recovers_invocation_id == original.id
    assert original.recovery.resolved_by_invocation_id == recuperacao.id


@pytest.mark.parametrize("classe,phase", [(TaskDecompositionPhase, _A2), (AdditionalPlanningPhase, _C2)])
@pytest.mark.parametrize("defeito", ["contract", "syntax", "truncated"])
async def test_recuperacao_do_planejamento_orienta_cobertura_sem_congelar_o_lote(
    recorder: SessionRecorderAdapter, classe: type[BaseThinkingPhase], phase: ThinkingPhaseEnum,
    defeito: str,
) -> None:
    plano = _plano()
    del plano["tasks"][2]["title"]
    recusada = json.dumps(plano) if defeito == "contract" else '{"tasks": [{"id": "T1", "description": "' + _LONGO
    llm = ScriptedLLMCompletions(
        responses=[recusada, json.dumps(_plano())], finish_reason="length" if defeito == "truncated" else "stop",
    )

    await _fase(classe, llm, recorder).execute(context=_janela(phase), variables={})

    correcao = llm.texts_of(1)[-1].lower()
    # Conceitos do contrato, sem fixar o parágrafo inteiro ou um exemplo de Física.
    for conceito in ("complete", "unaffected", "necessary", "requested determination", "final steps", "title"):
        assert conceito in correcao
    assert "remaining gaps" in correcao and "approved results" in correcao
    assert "defect requires" in correcao
    assert "task limit" in correcao and "duplicate ids" in correcao
    assert correcao.startswith("## ")


async def test_outra_fase_preserva_todas_as_recusas_e_feedbacks_sem_concatenar_saidas(
    recorder: SessionRecorderAdapter,
) -> None:
    primeira = json.dumps({"result": _LONGO + "first tail", "rejected_only": "not an accepted field"})
    segunda = json.dumps({"result": _LONGO + "second tail"})
    llm = ScriptedLLMCompletions(responses=[primeira, segunda, _VALIDA])
    guardiao = FakeCostGuard()

    resultado = await _fase(TaskResolutionPhase, llm, recorder, guardiao=guardiao).execute(
        context=_janela(), variables={},
    )

    prompt, recusada1, correcao1, recusada2, correcao2 = llm.conversations[2]
    assert [m.text for m in (recusada1, recusada2)] == [primeira, segunda]
    assert llm.conversations[1] == [prompt, recusada1, correcao1]
    assert "conclusion" in correcao1.text and "conclusion" in correcao2.text
    assert "unaffected" in correcao1.text.lower()
    assert "necessary" in correcao1.text.lower()
    assert tuple(llm.conversations[2]) == resultado.prompt_input
    assert resultado.raw_output == _VALIDA
    assert resultado.parsed == json.loads(_VALIDA)
    assert [s.raw_output for s in resultado.invalid_outputs] == [primeira, segunda]
    assert guardiao.registered_usages == [(10, 5)] * 3
    assert len(guardiao.started_calls) == 3
    assert [c["temperature"] for c in llm.calls] == [0.3, 1.0, 1.0]
    invocacoes = recorder.session.invocations
    assert [i.temperature for i in invocacoes] == [0.3, 1.0, 1.0]
    assert [(i.tokens_input, i.tokens_output, i.duration_ms) for i in invocacoes] == [(10, 5, 7)] * 3
    assert [i.content_accepted for i in invocacoes] == [False, False, True]
    assert [i.recovers_invocation_id for i in invocacoes] == [None, "inv_1", "inv_1"]
    assert all(i.recovery.resolved_by_invocation_id == "inv_3" for i in invocacoes[:2])
    assert (resultado.tokens.tokens_input, resultado.tokens.tokens_output) == (30, 15)
    assert recorder.session.totals.total_tokens == 45
    assert resultado.inference_time_ms == recorder.session.totals.inference_time_ms == 21


@pytest.mark.parametrize(
    "contrato,finish_reason,defeito,corte",
    [
        (True, "stop", OutputDefectEnum.CONTRACT, LengthInterruptionEnum.NOT_DETECTED),
        (True, "length", OutputDefectEnum.CONTRACT, LengthInterruptionEnum.CONFIRMED),
        (False, "stop", OutputDefectEnum.SYNTAX, LengthInterruptionEnum.NOT_DETECTED),
        (False, None, OutputDefectEnum.SYNTAX, LengthInterruptionEnum.SUSPECTED),
        (False, "length", OutputDefectEnum.TRUNCATED, LengthInterruptionEnum.CONFIRMED),
    ],
)
async def test_defeitos_recebem_instrucoes_distintas_sem_perder_a_saida_longa(
    recorder: SessionRecorderAdapter, contrato: bool, finish_reason: str | None,
    defeito: OutputDefectEnum, corte: LengthInterruptionEnum,
) -> None:
    recusada = json.dumps({"result": _LONGO}) if contrato else '{"result": "' + _LONGO
    llm = ScriptedLLMCompletions(responses=[recusada, _VALIDA], finish_reason=finish_reason)

    resultado = await _fase(TaskResolutionPhase, llm, recorder).execute(context=_janela(), variables={})

    assert llm.texts_of(1)[1] == recusada
    assert resultado.raw_output == _VALIDA
    assert resultado.parsed == json.loads(_VALIDA)
    invalida = resultado.invalid_outputs[0]
    assert invalida.defect is defeito
    diagnostico = invalida.diagnostic
    assert diagnostico.finish_reason == finish_reason
    assert diagnostico.length_interruption is corte
    assert diagnostico.syntax_status is (OutputSyntaxStatusEnum.VALID if contrato else OutputSyntaxStatusEnum.INVALID)
    assert diagnostico.contract_status is (
        OutputContractStatusEnum.INVALID if contrato else OutputContractStatusEnum.NOT_EVALUATED
    )
    assert diagnostico.problem.code is (
        OutputProblemCodeEnum.MISSING_FIELD if contrato else OutputProblemCodeEnum.JSON_SYNTAX
    )
    correcao = llm.texts_of(1)[-1].lower()
    assert invalida.reason.lower() in correcao
    assert correcao.startswith("## ")
    if defeito is OutputDefectEnum.CONTRACT:
        assert "complete corrected output" in correcao and "unaffected" in correcao
        assert "do not redo the resolution" not in correcao
    elif defeito is OutputDefectEnum.SYNTAX:
        assert "same content" in correcao and "do not redo the resolution" in correcao
        assert "do not continue" not in correcao
    else:
        assert "new, complete" in correcao and "concise" in correcao and "do not continue" in correcao
        assert "same content" not in correcao


@pytest.mark.parametrize("defeito", ["task_limit", "duplicate_id"])
async def test_correcao_pode_alterar_quantidade_ids_e_conteudo_quando_o_defeito_exige(
    recorder: SessionRecorderAdapter, defeito: str,
) -> None:
    plano = _plano()
    if defeito == "duplicate_id":
        plano["tasks"][2]["id"] = "T2"
    nova = tarefa("T4")
    nova["description"] = "Revised autonomous task covering the required determination."
    corrigida = json.dumps({"tasks": [nova]})
    llm = ScriptedLLMCompletions(responses=[json.dumps(plano), corrigida])

    resultado = await _fase(AdditionalPlanningPhase, llm, recorder).execute(
        context=_janela(_C2), variables={}, validation=ValidationContext(max_tasks=1 if defeito == "task_limit" else 3),
    )

    assert resultado.parsed == json.loads(corrigida)
    assert resultado.invalid_outputs[0].diagnostic.problem.code.value == defeito
    correcao = llm.texts_of(1)[-1].lower()
    assert "defect requires" in correcao
    assert "task limit" in correcao and "duplicate ids" in correcao


async def test_esgotamento_preserva_recusas_inteiras_e_persiste_falha_sem_aceite_parcial(
    recorder: SessionRecorderAdapter,
) -> None:
    recusadas = [json.dumps({"result": _LONGO + str(i)}) for i in range(2)]
    llm = ScriptedLLMCompletions(responses=recusadas)
    janela = _janela()

    with pytest.raises(PhaseParsingError):
        await _fase(TaskResolutionPhase, llm, recorder, retentativas=1).execute(context=janela, variables={})

    assert llm.call_count == 2
    assert llm.texts_of(1)[1] == recusadas[0]
    assert [m.text for m in janela.messages if m.source is MessageSourceEnum.LLM_AGENT] == recusadas
    persistida = await recorder.repository.find_by_id(session_id=recorder.session.id)
    assert [i.recovery.strategy for i in persistida.invocations] == [
        RecoveryStrategyEnum.CORRECTION_PROMPT, RecoveryStrategyEnum.NONE,
    ]
    assert all(i.recovery.result is RecoveryResultEnum.FAILED for i in persistida.invocations)
    assert all(i.content_accepted is False for i in persistida.invocations)
    assert persistida.totals.total_llm_calls == 2 and persistida.totals.total_tokens == 30
    assert all(raw in audit.content for raw, audit in zip(recusadas, _auditorias(recorder)))


async def test_orcamento_esgotado_nao_encurta_a_janela_para_tentar_novamente(
    recorder: SessionRecorderAdapter, budget_factory,
) -> None:
    recusada = json.dumps({"result": _LONGO + "indispensable tail"})
    llm = ScriptedLLMCompletions(responses=[recusada, _VALIDA], tokens_input=750, tokens_output=50)
    guardiao = CostGuardAdapter(budget=budget_factory(), clock=FakeClock(), logger=logging.getLogger("teste.custo"))
    janela = _janela()

    with pytest.raises(BudgetExceededError) as erro:
        await _fase(TaskResolutionPhase, llm, recorder, guardiao=guardiao).execute(context=janela, variables={})

    assert erro.value.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert llm.call_count == 1
    assert llm.validations[1]["texts"] == [m.text for m in janela.messages]
    assert llm.validations[1]["texts"][1] == recusada
    assert janela.messages[-1].source is MessageSourceEnum.USER
    persistida = await recorder.repository.find_by_id(session_id=recorder.session.id)
    assert persistida.totals.total_tokens == 800 and persistida.totals.total_llm_calls == 1
    assert persistida.invocations[0].recovery.result is RecoveryResultEnum.FAILED


async def test_cancelamento_durante_recuperacao_integral_persiste_falha_e_propaga(
    recorder: SessionRecorderAdapter,
) -> None:
    enviada = asyncio.Event()
    recusada = json.dumps({"result": _LONGO + "indispensable tail"})
    capturada = []

    class _LLMBloqueado(ScriptedLLMCompletions):
        async def send_conversation(self, **kwargs):
            if not self.responses:
                capturada.extend(kwargs["conversation"])
                enviada.set()
                await asyncio.Event().wait()
            return await super().send_conversation(**kwargs)

    llm = _LLMBloqueado(responses=[recusada])
    execucao = asyncio.create_task(_fase(TaskResolutionPhase, llm, recorder).execute(context=_janela(), variables={}))
    try:
        await asyncio.wait_for(enviada.wait(), timeout=2)
        execucao.cancel("controlled cancellation")
        with pytest.raises(asyncio.CancelledError, match="controlled cancellation"):
            await execucao
    finally:
        if not execucao.done():
            execucao.cancel()
            with pytest.raises(asyncio.CancelledError):
                await execucao

    assert capturada[1].text == recusada
    persistida = await recorder.repository.find_by_id(session_id=recorder.session.id)
    original, em_andamento = persistida.invocations
    assert original.recovery.result is RecoveryResultEnum.FAILED
    assert em_andamento.recovers_invocation_id == original.id
    assert em_andamento.output_diagnostic is None
    assert persistida.totals.total_llm_calls == 2 and persistida.totals.total_tokens == 15
