import dataclasses
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_INICIO = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _iniciada() -> LLMInvocation:
    return LLMInvocation(
        id="inv-1",
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id="T1",
        context_id="ctx-1",
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
        started_at=_INICIO,
    )


def test_uma_invocacao_nova_esta_iniciada_e_sem_consumo_conhecido() -> None:
    invocacao = _iniciada()

    assert invocacao.outcome is InvocationOutcomeEnum.STARTED
    assert invocacao.duration_ms == 0
    assert invocacao.tokens_input is None
    assert invocacao.tokens_output is None
    assert invocacao.finish_reason is None
    assert invocacao.provider_response_id is None
    assert invocacao.usage_known is False


def test_complete_devolve_uma_copia_com_o_desfecho_e_o_consumo() -> None:
    inicial = _iniciada()

    concluida = inicial.complete(
        outcome=InvocationOutcomeEnum.SUCCESS,
        duration_ms=812,
        tokens_input=40,
        tokens_output=12,
        finish_reason="stop",
        provider_response_id="resp-1",
    )

    assert concluida is not inicial
    assert inicial.outcome is InvocationOutcomeEnum.STARTED
    assert concluida.outcome is InvocationOutcomeEnum.SUCCESS
    assert concluida.duration_ms == 812
    assert concluida.tokens_input == 40
    assert concluida.tokens_output == 12
    assert concluida.finish_reason == "stop"
    assert concluida.provider_response_id == "resp-1"
    assert concluida.id == "inv-1"
    assert concluida.usage_known is True


def test_consumo_ausente_continua_desconhecido_e_nao_vira_zero() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.PROVIDER_ERROR,
        duration_ms=30,
        tokens_input=None,
        tokens_output=None,
    )

    assert concluida.tokens_input is None
    assert concluida.tokens_output is None
    assert concluida.usage_known is False


def test_so_o_consumo_de_saida_conhecido_ja_conta_como_conhecido() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.EMPTY_COMPLETION,
        duration_ms=30,
        tokens_input=None,
        tokens_output=140,
    )

    assert concluida.usage_known is True


def test_nao_se_completa_uma_invocacao_para_o_desfecho_iniciada() -> None:
    with pytest.raises(ValueError, match="started"):
        _iniciada().complete(
            outcome=InvocationOutcomeEnum.STARTED, duration_ms=0, tokens_input=None, tokens_output=None
        )


def test_nao_se_completa_duas_vezes() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1, tokens_output=1
    )

    with pytest.raises(ValueError, match="já foi concluída"):
        concluida.complete(outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1, tokens_output=1)


def test_e_imutavel() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _iniciada().duration_ms = 5


# ── Diagnóstico da saída e recuperação ───────────────────────────────────────


_ACEITA = OutputDiagnostic.accepted(finish_reason="stop", length_interruption=LengthInterruptionEnum.NOT_DETECTED)
_RECUSADA = OutputDiagnostic(
    syntax_status=OutputSyntaxStatusEnum.INVALID,
    contract_status=OutputContractStatusEnum.NOT_EVALUATED,
    finish_reason="length",
    length_interruption=LengthInterruptionEnum.CONFIRMED,
    problem=OutputProblem(code=OutputProblemCodeEnum.JSON_SYNTAX, reason="string não terminada"),
)
_PENDENTE = OutputRecovery(strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.PENDING)


def _sucesso() -> LLMInvocation:
    return _iniciada().complete(
        outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1, tokens_output=1, finish_reason="length"
    )


def test_invocacao_nova_nao_tem_diagnostico_recuperacao_nem_vinculo() -> None:
    invocacao = _iniciada()

    assert invocacao.output_diagnostic is None
    assert invocacao.recovery is None
    assert invocacao.recovers_invocation_id is None
    assert invocacao.content_accepted is None


def test_sucesso_do_provedor_com_conteudo_recusado_preserva_o_desfecho_do_provedor() -> None:
    diagnosticada = _sucesso().with_output_diagnostic(diagnostic=_RECUSADA)

    assert diagnosticada.outcome is InvocationOutcomeEnum.SUCCESS
    assert diagnosticada.finish_reason == "length"
    assert diagnosticada.output_diagnostic == _RECUSADA
    assert diagnosticada.content_accepted is False


def test_conteudo_aceito_fica_registrado_separado_do_desfecho() -> None:
    assert _sucesso().with_output_diagnostic(diagnostic=_ACEITA).content_accepted is True


@pytest.mark.parametrize(
    "outcome",
    [InvocationOutcomeEnum.EMPTY_COMPLETION, InvocationOutcomeEnum.PROVIDER_ERROR],
)
def test_so_uma_resposta_com_conteudo_recebe_diagnostico(outcome: InvocationOutcomeEnum) -> None:
    concluida = _iniciada().complete(outcome=outcome, duration_ms=1, tokens_input=None, tokens_output=None)

    with pytest.raises(ValueError, match="success"):
        concluida.with_output_diagnostic(diagnostic=_RECUSADA)


def test_invocacao_em_andamento_nao_recebe_diagnostico() -> None:
    with pytest.raises(ValueError, match="success"):
        _iniciada().with_output_diagnostic(diagnostic=_ACEITA)


def test_o_diagnostico_de_uma_saida_e_unico() -> None:
    diagnosticada = _sucesso().with_output_diagnostic(diagnostic=_RECUSADA)

    with pytest.raises(ValueError, match="já tem diagnóstico"):
        diagnosticada.with_output_diagnostic(diagnostic=_ACEITA)


def test_recuperacao_so_se_aplica_a_conteudo_recusado() -> None:
    with pytest.raises(ValueError, match="recusad"):
        _sucesso().with_recovery(recovery=_PENDENTE)
    with pytest.raises(ValueError, match="recusad"):
        _sucesso().with_output_diagnostic(diagnostic=_ACEITA).with_recovery(recovery=_PENDENTE)


def test_recuperacao_pendente_evolui_para_o_resultado_final() -> None:
    recusada = _sucesso().with_output_diagnostic(diagnostic=_RECUSADA)
    final = OutputRecovery(
        strategy=RecoveryStrategyEnum.CORRECTION_PROMPT,
        result=RecoveryResultEnum.RECOVERED,
        resolved_by_invocation_id="inv-2",
    )

    recuperada = recusada.with_recovery(recovery=_PENDENTE).with_recovery(recovery=final)

    assert recuperada.recovery == final


def test_resultado_final_da_recuperacao_nao_e_reescrito() -> None:
    falhou = (
        _sucesso()
        .with_output_diagnostic(diagnostic=_RECUSADA)
        .with_recovery(recovery=OutputRecovery(strategy=RecoveryStrategyEnum.NONE, result=RecoveryResultEnum.FAILED))
    )

    with pytest.raises(ValueError, match="final"):
        falhou.with_recovery(recovery=_PENDENTE)


def test_vinculo_a_invocacao_original_e_um_campo_proprio() -> None:
    retentativa = dataclasses.replace(_iniciada(), id="inv-2", recovers_invocation_id="inv-1")

    assert retentativa.recovers_invocation_id == "inv-1"
