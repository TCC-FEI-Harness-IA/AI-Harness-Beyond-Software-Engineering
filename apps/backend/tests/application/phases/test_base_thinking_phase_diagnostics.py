"""Associação dos diagnósticos de saída às invocações e registro da recuperação.

O diagnóstico é tratamento operacional: não muda o fluxo analítico nem a política de orçamento.
Cada saída avaliada pelo parser ganha um diagnóstico na invocação que a produziu; uma saída recusada
recebe também o registro da recuperação, e cada nova chamada de correção aponta a invocação original.
"""
import asyncio
import json
import logging

import pytest

from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.application.phases.task_verification_phase import TaskVerificationPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum
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
_CRITERIOS = {"general_acceptance_criteria": [{"id": "AC1", "description": "responder em pt-BR"}]}
_SAIDA_VALIDA = json.dumps(_CRITERIOS)
_CORTADA = '{"general_acceptance_criteria": [{"id": "AC1", "description": "respon'
_SEM_VIRGULA = '{"general_acceptance_criteria": [{"id": "AC1" "description": "x"}]}'
_CORRECAO = OutputRecovery(
    strategy=RecoveryStrategyEnum.CORRECTION_PROMPT,
    result=RecoveryResultEnum.RECOVERED,
    resolved_by_invocation_id="inv_2",
)


class _GuardiaoQueNegaAPartirDe(FakeCostGuard):
    """Guardião que autoriza as primeiras chamadas e nega a partir da informada."""

    def __init__(self, negar_na_chamada: int) -> None:
        super().__init__()
        self.negar_na_chamada = negar_na_chamada
        self.consultas = 0

    def begin_call(self, phase: ThinkingPhaseEnum, reserved_output_tokens: int = 0) -> BudgetVerdict:
        self.consultas += 1
        self.authorized = self.consultas < self.negar_na_chamada
        return super().begin_call(phase=phase, reserved_output_tokens=reserved_output_tokens)


def _fase(
    llm: ScriptedLLMCompletions,
    recorder: SessionRecorderAdapter,
    parser: IStructuredResponseParser | None = None,
    retentativas: int = 2,
    cost_guard: FakeCostGuard | None = None,
) -> GeneralCriteriaPhase:
    return GeneralCriteriaPhase(
        llm_completions=llm,
        template_provider=FakePromptTemplateProvider(),
        parser=parser or StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser")),
        cost_guard=cost_guard or FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(),
        settings=FakeSettings(ralph_json_parse_max_retries=retentativas),
        logger=logging.getLogger("teste.fase"),
    )


def _janela() -> ContextWindow:
    return ContextWindow(context_id="ctx-1", phase=_FASE)


def _invocacoes(recorder: SessionRecorderAdapter) -> list[LLMInvocation]:
    return list(recorder.session.invocations)


def _auditorias(recorder: SessionRecorderAdapter) -> list:
    return [
        mensagem
        for mensagem in recorder.session.messages
        if mensagem.source is MessageSourceEnum.SYSTEM and "Saída inválida" in mensagem.content
    ]


# ── Saídas aceitas ────────────────────────────────────────────────────────────


async def test_saida_aceita_recebe_diagnostico_na_invocacao_que_a_produziu(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], finish_reason="stop")

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    (invocacao,) = _invocacoes(recorder)
    assert invocacao.outcome is InvocationOutcomeEnum.SUCCESS
    assert invocacao.content_accepted is True
    assert invocacao.output_diagnostic == OutputDiagnostic.accepted(
        finish_reason="stop", length_interruption=LengthInterruptionEnum.NOT_DETECTED
    )
    assert invocacao.recovery is None
    assert invocacao.recovers_invocation_id is None


async def test_json_valido_terminado_por_length_e_aceito_sem_retentativa(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA], finish_reason="length")

    resultado = await _fase(llm, recorder).execute(context=_janela(), variables={})

    (invocacao,) = _invocacoes(recorder)
    assert llm.call_count == 1
    assert resultado.parsed == _CRITERIOS
    assert invocacao.finish_reason == "length"
    assert invocacao.content_accepted is True
    assert invocacao.output_diagnostic.length_interruption is LengthInterruptionEnum.CONFIRMED
    assert recorder.session.rejected_output_count == 0


async def test_reparo_local_fica_no_diagnostico_sem_abrir_recuperacao(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_SAIDA_VALIDA[:-1]], finish_reason="stop")

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    (invocacao,) = _invocacoes(recorder)
    assert invocacao.output_diagnostic.syntax_status is OutputSyntaxStatusEnum.REPAIRED
    assert invocacao.output_diagnostic.repaired_closings == "}"
    assert invocacao.content_accepted is True
    assert invocacao.recovery is None


async def test_reprovacao_valida_da_verificacao_e_conteudo_aceito(recorder: SessionRecorderAdapter) -> None:
    relatorio = json.dumps(
        {
            "decision": "reproved",
            "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": False, "justification": "faltou"}],
            "unmet_criteria_ids": ["T1-AC1"],
        }
    )
    fase = TaskVerificationPhase(
        llm_completions=ScriptedLLMCompletions(responses=[relatorio]),
        template_provider=FakePromptTemplateProvider(),
        parser=StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser")),
        cost_guard=FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )

    resultado = await fase.execute(
        context=ContextWindow(context_id="ctx-v", phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION),
        variables={},
        validation=ValidationContext(expected_criteria_ids=("T1-AC1",)),
    )

    assert resultado.parsed["decision"] == "reproved"
    (invocacao,) = _invocacoes(recorder)
    assert invocacao.content_accepted is True
    assert invocacao.recovery is None
    assert recorder.session.rejected_output_count == 0


# ── Recusa seguida de recuperação ────────────────────────────────────────────


async def test_recusa_corrigida_liga_a_retentativa_a_invocacao_original(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, _SAIDA_VALIDA], finish_reason="length")

    resultado = await _fase(llm, recorder).execute(context=_janela(), variables={})

    original, correcao = _invocacoes(recorder)
    assert original.outcome is InvocationOutcomeEnum.SUCCESS
    assert original.content_accepted is False
    assert original.output_diagnostic.problem.code is OutputProblemCodeEnum.JSON_SYNTAX
    assert original.output_diagnostic.length_interruption is LengthInterruptionEnum.CONFIRMED
    assert original.recovery == _CORRECAO
    assert correcao.recovers_invocation_id == original.id
    assert correcao.content_accepted is True
    assert correcao.recovery is None
    (saida_invalida,) = resultado.invalid_outputs
    assert saida_invalida.invocation_id == original.id
    assert saida_invalida.diagnostic == original.output_diagnostic
    assert saida_invalida.raw_output == _CORTADA


async def test_auditoria_da_recusa_aponta_a_invocacao_e_mantem_motivo_e_saida_bruta(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_SEM_VIRGULA, _SAIDA_VALIDA], finish_reason="stop")

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    (auditoria,) = _auditorias(recorder)
    assert auditoria.invocation_id == "inv_1"
    assert _SEM_VIRGULA in auditoria.content
    assert "Nenhum objeto JSON válido" in auditoria.content
    assert "json_syntax" in auditoria.content
    assert "not_detected" in auditoria.content


async def test_cadeia_de_recusas_resolvida_pela_terceira_chamada(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, _SEM_VIRGULA, _SAIDA_VALIDA], finish_reason="stop")

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    primeira, segunda, terceira = _invocacoes(recorder)
    resolvida = OutputRecovery(
        strategy=RecoveryStrategyEnum.CORRECTION_PROMPT,
        result=RecoveryResultEnum.RECOVERED,
        resolved_by_invocation_id="inv_3",
    )
    assert primeira.recovery == resolvida
    assert segunda.recovery == resolvida
    assert segunda.recovers_invocation_id == "inv_1"
    assert terceira.recovers_invocation_id == "inv_1"
    assert recorder.session.rejected_output_count == 2
    assert recorder.session.totals.total_llm_calls == 3


async def test_completion_vazia_no_meio_da_recuperacao_tambem_aponta_a_original(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA])

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    original, vazia, correcao = _invocacoes(recorder)
    assert vazia.outcome is InvocationOutcomeEnum.EMPTY_COMPLETION
    assert vazia.output_diagnostic is None
    assert vazia.content_accepted is None
    assert vazia.recovers_invocation_id == "inv_1"
    assert correcao.recovers_invocation_id == "inv_1"
    assert original.recovery.resolved_by_invocation_id == "inv_3"


async def test_completion_vazia_sem_recusa_anterior_nao_cria_vinculo(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[EmptyCompletionError(finish_reason="length"), _SAIDA_VALIDA])

    await _fase(llm, recorder).execute(context=_janela(), variables={})

    vazia, resposta = _invocacoes(recorder)
    assert vazia.recovers_invocation_id is None
    assert resposta.recovers_invocation_id is None
    assert resposta.content_accepted is True


async def test_recuperacao_fica_pendente_enquanto_a_correcao_nao_volta(recorder: SessionRecorderAdapter) -> None:
    pendencias: list[OutputRecovery | None] = []

    class _Parser(StructuredResponseParserAdapter):
        def parse_output(self, raw_output, phase, validation=None, finish_reason=None):  # type: ignore[override]
            if raw_output == _SAIDA_VALIDA:
                pendencias.append(recorder.session.invocations[0].recovery)
            return super().parse_output(
                raw_output=raw_output, phase=phase, validation=validation, finish_reason=finish_reason
            )

    llm = ScriptedLLMCompletions(responses=[_CORTADA, _SAIDA_VALIDA])

    await _fase(llm, recorder, parser=_Parser(logger=logging.getLogger("teste"))).execute(
        context=_janela(), variables={}
    )

    assert pendencias == [
        OutputRecovery(strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.PENDING)
    ]


# ── Falha terminal ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("recusas", [0, 1, 2])
async def test_cancelamento_persiste_falha_das_recuperacoes_e_propaga(
    recorder: SessionRecorderAdapter, recusas: int,
) -> None:
    chamada_em_andamento = asyncio.Event()

    class _LLMBloqueado(ScriptedLLMCompletions):
        async def send_conversation(self, **kwargs):
            if not self.responses:
                chamada_em_andamento.set()
                await asyncio.Event().wait()
            return await super().send_conversation(**kwargs)

    llm = _LLMBloqueado(responses=[_SEM_VIRGULA] * recusas)
    execucao = asyncio.create_task(_fase(llm, recorder).execute(context=_janela(), variables={}))
    try:
        await asyncio.wait_for(chamada_em_andamento.wait(), timeout=2)
        totais_antes = (
            recorder.session.totals.total_llm_calls, recorder.session.totals.total_tokens,
        )
        assert all(i.recovery.result is RecoveryResultEnum.PENDING for i in _invocacoes(recorder)[:recusas])

        execucao.cancel("cliente desconectou")
        with pytest.raises(asyncio.CancelledError, match="cliente desconectou"):
            await execucao
    finally:
        if not execucao.done():
            execucao.cancel()
            with pytest.raises(asyncio.CancelledError):
                await execucao

    persistida = await recorder.repository.find_by_id(session_id=recorder.session.id)
    assert persistida is not None
    assert persistida.invocations == recorder.session.invocations
    assert len(persistida.invocations) == recusas + 1
    for invocacao in persistida.invocations[:recusas]:
        assert invocacao.recovery == OutputRecovery(
            strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.FAILED,
        )
    assert persistida.invocations[-1].recovery is None
    assert persistida.invocations[-1].recovers_invocation_id == ("inv_1" if recusas else None)
    assert (persistida.totals.total_llm_calls, persistida.totals.total_tokens) == totais_antes
    assert persistida.rejected_output_count == recusas


async def test_falha_terminal_registra_a_recuperacao_como_falha(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, _SEM_VIRGULA], finish_reason="stop")

    with pytest.raises(PhaseParsingError) as erro:
        await _fase(llm, recorder, retentativas=1).execute(context=_janela(), variables={})

    primeira, ultima = _invocacoes(recorder)
    assert primeira.recovery == OutputRecovery(
        strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.FAILED
    )
    assert ultima.recovery == OutputRecovery(strategy=RecoveryStrategyEnum.NONE, result=RecoveryResultEnum.FAILED)
    assert ultima.recovers_invocation_id == "inv_1"
    assert erro.value.diagnostic == ultima.output_diagnostic
    assert recorder.session.rejected_output_count == 2
    assert recorder.session.totals.total_llm_calls == 2


async def test_sem_retentativa_a_unica_recusa_ja_e_falha_terminal(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA])

    with pytest.raises(PhaseParsingError):
        await _fase(llm, recorder, retentativas=0).execute(context=_janela(), variables={})

    (invocacao,) = _invocacoes(recorder)
    assert invocacao.recovery == OutputRecovery(strategy=RecoveryStrategyEnum.NONE, result=RecoveryResultEnum.FAILED)


async def test_orcamento_negado_durante_a_correcao_encerra_a_recuperacao_como_falha(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, _SAIDA_VALIDA])

    with pytest.raises(BudgetExceededError):
        await _fase(llm, recorder, cost_guard=_GuardiaoQueNegaAPartirDe(negar_na_chamada=2)).execute(
            context=_janela(), variables={}
        )

    (original,) = _invocacoes(recorder)
    assert original.recovery == OutputRecovery(
        strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.FAILED
    )


async def test_completions_vazias_esgotando_a_correcao_encerram_a_recuperacao_como_falha(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(
        responses=[_CORTADA, EmptyCompletionError(finish_reason="length"), EmptyCompletionError(finish_reason="length")]
    )

    with pytest.raises(EmptyCompletionError):
        await _fase(llm, recorder, retentativas=2).execute(context=_janela(), variables={})

    original = _invocacoes(recorder)[0]
    assert original.recovery.result is RecoveryResultEnum.FAILED
    assert recorder.session.rejected_output_count == 1
    assert recorder.session.totals.total_llm_calls == 3


async def test_erro_do_provedor_durante_a_correcao_encerra_a_recuperacao_como_falha(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=[_CORTADA, RuntimeError("provedor fora do ar")])

    with pytest.raises(RuntimeError):
        await _fase(llm, recorder).execute(context=_janela(), variables={})

    original, falha = _invocacoes(recorder)
    assert falha.outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert falha.recovers_invocation_id == "inv_1"
    assert original.recovery.result is RecoveryResultEnum.FAILED


async def test_falha_sem_recusa_anterior_nao_registra_recuperacao(recorder: SessionRecorderAdapter) -> None:
    llm = ScriptedLLMCompletions(responses=[RuntimeError("provedor fora do ar")])

    with pytest.raises(RuntimeError):
        await _fase(llm, recorder).execute(context=_janela(), variables={})

    (invocacao,) = _invocacoes(recorder)
    assert invocacao.recovery is None
    assert invocacao.output_diagnostic is None


# ── Diagnóstico vindo de outro parser ────────────────────────────────────────


async def test_recusa_sem_diagnostico_vira_recusa_nao_classificada_com_o_termino_da_chamada(
    recorder: SessionRecorderAdapter,
) -> None:
    llm = ScriptedLLMCompletions(responses=["ruim", _SAIDA_VALIDA], finish_reason="stop")
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="ruim", reason="json ausente"), _CRITERIOS]
    )

    await _fase(llm, recorder, parser=parser).execute(context=_janela(), variables={})

    original = _invocacoes(recorder)[0]
    assert original.output_diagnostic == OutputDiagnostic.unclassified(reason="json ausente", finish_reason="stop")
    assert original.content_accepted is False


async def test_diagnostico_informado_pelo_parser_e_o_registrado(recorder: SessionRecorderAdapter) -> None:
    diagnostico = OutputDiagnostic(
        syntax_status=OutputSyntaxStatusEnum.VALID,
        contract_status=OutputContractStatusEnum.INVALID,
        finish_reason="stop",
        length_interruption=LengthInterruptionEnum.NOT_DETECTED,
        problem=OutputProblem(code=OutputProblemCodeEnum.MISSING_FIELD, reason="falta", field="result"),
    )
    llm = ScriptedLLMCompletions(responses=["{}", _SAIDA_VALIDA])
    parser = FakeStructuredParser(
        outcomes=[PhaseParsingError(phase=_FASE, raw_output="{}", reason="falta", diagnostic=diagnostico), _CRITERIOS]
    )

    await _fase(llm, recorder, parser=parser).execute(context=_janela(), variables={})

    assert _invocacoes(recorder)[0].output_diagnostic is diagnostico


async def test_falha_ao_registrar_a_recuperacao_nao_encobre_o_erro_original(recorder: SessionRecorderAdapter) -> None:
    async def _falhar(**_: object) -> None:
        raise RuntimeError("repositório indisponível")

    llm = ScriptedLLMCompletions(responses=[_CORTADA])
    recorder.record_output_recovery = _falhar  # type: ignore[method-assign]

    with pytest.raises(PhaseParsingError):
        await _fase(llm, recorder, retentativas=0).execute(context=_janela(), variables={})

    assert _invocacoes(recorder)[0].content_accepted is False
