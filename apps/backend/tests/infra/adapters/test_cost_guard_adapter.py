import logging
from collections.abc import Callable

import pytest

from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.cost_guard_adapter import CostGuardAdapter
from tests.doubles.fake_clock import FakeClock

_LOGGER = logging.getLogger("tests.cost_guard_adapter")
_B1 = ThinkingPhaseEnum.B1_TASK_RESOLUTION


def _gastar(guard: CostGuardAdapter, total: int) -> None:
    """Contabiliza `total` tokens de entrada, sem iniciar nenhuma chamada."""
    guard.register_usage(tokens_input=total, tokens_output=0)


def _chamar(guard: CostGuardAdapter, vezes: int, fase: ThinkingPhaseEnum = _B1) -> None:
    """Inicia `vezes` chamadas autorizadas, sem consumir tokens."""
    for _ in range(vezes):
        assert guard.begin_call(phase=fase).authorized is True


def _guard(budget: CostBudget, clock: FakeClock | None = None) -> CostGuardAdapter:
    """Monta o guardião sob teste com um relógio controlado."""
    return CostGuardAdapter(budget=budget, clock=clock or FakeClock(), logger=_LOGGER)


# ── Autorização: tokens e reserva ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("consumo", "fase", "autorizado"),
    [
        (0, ThinkingPhaseEnum.B1_TASK_RESOLUTION, True),
        (799, ThinkingPhaseEnum.B1_TASK_RESOLUTION, True),
        (800, ThinkingPhaseEnum.B1_TASK_RESOLUTION, False),
        (800, ThinkingPhaseEnum.C3_FINAL_ANSWER, True),
        (999, ThinkingPhaseEnum.C3_FINAL_ANSWER, True),
        (1000, ThinkingPhaseEnum.C3_FINAL_ANSWER, False),
        (800, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION, False),
    ],
)
def test_regra_da_reserva_de_tokens(
    budget_factory: Callable[..., CostBudget],
    consumo: int,
    fase: ThinkingPhaseEnum,
    autorizado: bool,
) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, consumo)

    veredito = guard.authorize(phase=fase)

    assert veredito.authorized is autorizado


def test_negacao_por_tokens_identifica_o_limite(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 800)

    veredito = guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert veredito.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert veredito.reason


# ── Autorização: chamadas ────────────────────────────────────────────────────


def test_autoriza_enquanto_o_teto_de_chamadas_nao_e_atingido(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=3))
    _chamar(guard, 2)

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).authorized is True


def test_nega_quando_o_teto_de_chamadas_e_atingido(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=3))
    _chamar(guard, 3)

    veredito = guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


# ── Autorização: timeout ─────────────────────────────────────────────────────


def test_autoriza_um_milissegundo_antes_do_timeout(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(session_timeout_seconds=10), clock=FakeClock(monotonic_values=[0, 9_999]))

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).authorized is True


def test_nega_exatamente_no_timeout(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(session_timeout_seconds=10), clock=FakeClock(monotonic_values=[0, 10_000]))

    veredito = guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.SESSION_TIMEOUT


def test_o_marco_de_inicio_e_o_instante_da_construcao(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(session_timeout_seconds=10), clock=FakeClock(monotonic_values=[5_000, 14_999]))

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).authorized is True


# ── Precedência ──────────────────────────────────────────────────────────────


def test_timeout_vence_o_limite_de_tokens(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(), clock=FakeClock(monotonic_values=[0, 10_000]))
    _gastar(guard, 900)

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).limit is BudgetLimitEnum.SESSION_TIMEOUT


def test_timeout_vence_quando_todos_os_limites_sao_violados(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=2), clock=FakeClock(monotonic_values=[0, 0, 0, 10_000]))
    _chamar(guard, 2)
    _gastar(guard, 1000)

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).limit is BudgetLimitEnum.SESSION_TIMEOUT


def test_chamadas_vencem_o_limite_de_tokens(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=2))
    _chamar(guard, 2)
    _gastar(guard, 1000)

    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


# ── Tentativas de tarefa ─────────────────────────────────────────────────────


def test_tentativas_sao_numeradas_a_partir_de_um(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())

    assert guard.register_task_attempt(task_id="T1") == 1
    assert guard.register_task_attempt(task_id="T1") == 2


def test_pode_retentar_ate_atingir_o_limite_de_tentativas(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_task_attempts=2))

    assert guard.can_retry_task(task_id="T1") is True
    guard.register_task_attempt(task_id="T1")
    assert guard.can_retry_task(task_id="T1") is True
    guard.register_task_attempt(task_id="T1")
    assert guard.can_retry_task(task_id="T1") is False


def test_contadores_de_tentativa_sao_independentes_por_tarefa(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_task_attempts=2))
    guard.register_task_attempt(task_id="T1")
    guard.register_task_attempt(task_id="T1")

    assert guard.register_task_attempt(task_id="T2") == 1
    assert guard.can_retry_task(task_id="T1") is False
    assert guard.can_retry_task(task_id="T2") is True


def test_tarefa_nunca_vista_pode_ser_tentada(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())

    assert guard.can_retry_task(task_id="jamais-vista") is True


# ── Planejamento adicional ───────────────────────────────────────────────────


def test_autoriza_planejamento_adicional_com_tudo_disponivel(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1))

    assert guard.authorize_additional_planning().authorized is True


def test_nega_planejamento_adicional_apos_a_ultima_rodada_apontando_as_rodadas(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1))
    guard.register_additional_planning_round()

    veredito = guard.authorize_additional_planning()

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS
    assert veredito.reason


def test_nega_planejamento_adicional_sem_slot_de_tarefa_apontando_as_tarefas(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1, max_tasks_per_session=5))
    guard.register_task_created(quantity=5)

    veredito = guard.authorize_additional_planning()

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.TASKS_PER_SESSION


def test_nega_planejamento_adicional_com_orcamento_de_tokens_esgotado_apontando_os_tokens(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1))
    _gastar(guard, 800)

    veredito = guard.authorize_additional_planning()

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET


def test_nega_planejamento_adicional_com_teto_de_chamadas_atingido_apontando_as_chamadas(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1, max_llm_calls_per_session=1))
    _chamar(guard, 1)

    assert guard.authorize_additional_planning().limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


def test_nega_planejamento_adicional_com_timeout_estourado_apontando_o_tempo(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(
        budget_factory(max_additional_planning_rounds=1, session_timeout_seconds=10),
        clock=FakeClock(monotonic_values=[0, 10_000]),
    )

    assert guard.authorize_additional_planning().limit is BudgetLimitEnum.SESSION_TIMEOUT


def test_planejamento_adicional_considera_a_saida_reservada(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1))
    _gastar(guard, 790)

    assert guard.authorize_additional_planning(reserved_output_tokens=10).authorized is True
    assert guard.authorize_additional_planning(reserved_output_tokens=11).authorized is False


def test_rodadas_vencem_slots_na_precedencia_do_planejamento_adicional(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1, max_tasks_per_session=1))
    guard.register_additional_planning_round()
    guard.register_task_created(quantity=1)

    assert guard.authorize_additional_planning().limit is BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS


def test_a_autorizacao_de_planejamento_adicional_nao_conta_chamada(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_additional_planning_rounds=1, max_llm_calls_per_session=1))

    assert guard.authorize_additional_planning().authorized is True
    assert guard.authorize_additional_planning().authorized is True


# ── Slots de tarefa ──────────────────────────────────────────────────────────


def test_slots_de_tarefa_comecam_no_limite_configurado(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_tasks_per_session=5))

    assert guard.remaining_task_slots() == 5


def test_slots_de_tarefa_decrescem_conforme_as_criacoes(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_tasks_per_session=5))
    guard.register_task_created(quantity=3)

    assert guard.remaining_task_slots() == 2


def test_slots_de_tarefa_nunca_ficam_negativos(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_tasks_per_session=5))
    guard.register_task_created(quantity=10)

    assert guard.remaining_task_slots() == 0


# ── Tokens restantes ─────────────────────────────────────────────────────────


def test_tokens_restantes_ja_descontam_a_reserva(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())

    assert guard.remaining_tokens() == 800


def test_tokens_restantes_decrescem_conforme_o_consumo(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    guard.register_usage(tokens_input=100, tokens_output=50)

    assert guard.remaining_tokens() == 650


def test_tokens_restantes_nunca_ficam_negativos(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 1000)

    assert guard.remaining_tokens() == 0


# ── Contabilidade ────────────────────────────────────────────────────────────


def test_registro_de_consumo_soma_entrada_e_saida(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    guard.register_usage(tokens_input=120, tokens_output=80)

    assert guard.remaining_tokens() == 600


def test_chamadas_e_consumos_sao_acumulativos(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=3))
    for total in (100, 200, 300):
        _chamar(guard, 1)
        _gastar(guard, total)

    assert guard.remaining_tokens() == 200
    assert guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION).limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


def test_chamada_sem_consumo_de_tokens_ainda_conta_como_chamada(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=1))
    _chamar(guard, 1)

    veredito = guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert guard.remaining_tokens() == 800
    assert veredito.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


# ── Início de chamada: autorização e contagem numa só operação ───────────────


def test_begin_call_autorizado_ja_conta_a_chamada_sem_esperar_o_consumo(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=2))

    assert guard.begin_call(phase=_B1).authorized is True
    assert guard.begin_call(phase=_B1).authorized is True

    assert guard.begin_call(phase=_B1).limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


def test_begin_call_negado_nao_conta_chamada(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=2, session_token_budget=1000))
    _gastar(guard, 800)

    assert guard.begin_call(phase=_B1).authorized is False
    assert guard.begin_call(phase=_B1).authorized is False

    # Nenhuma das duas negativas consumiu o teto de chamadas: C.3 ainda tem as duas.
    assert guard.begin_call(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).authorized is True
    assert guard.begin_call(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).authorized is True
    assert guard.begin_call(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION


def test_authorize_apenas_consulta_e_nunca_conta_chamada(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory(max_llm_calls_per_session=1))

    for _ in range(5):
        assert guard.authorize(phase=_B1).authorized is True


# ── Saída reservada e motivo da negação ──────────────────────────────────────


def test_a_saida_maxima_pedida_entra_na_conta_do_teto_de_trabalho(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 790)

    assert guard.authorize(phase=_B1, reserved_output_tokens=10).authorized is True
    assert guard.authorize(phase=_B1, reserved_output_tokens=11).authorized is False
    assert guard.begin_call(phase=_B1, reserved_output_tokens=11).limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET


def test_a_saida_maxima_pedida_entra_na_conta_do_teto_total_de_c3(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 990)

    assert guard.authorize(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER, reserved_output_tokens=10).authorized is True
    assert guard.authorize(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER, reserved_output_tokens=11).authorized is False


def test_negacao_do_orcamento_de_trabalho_nao_afirma_que_a_reserva_acabou(
    budget_factory: Callable[..., CostBudget],
) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 800)

    reason = guard.authorize(phase=_B1).reason

    assert "trabalho" in reason
    assert "reserva de 200" in reason
    assert "total" not in reason


def test_negacao_do_orcamento_total_diz_que_o_total_acabou(budget_factory: Callable[..., CostBudget]) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 1000)

    reason = guard.authorize(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).reason

    assert "total" in reason
    assert "trabalho" not in reason


def test_cenario_de_orcamento_100_com_reserva_25_e_consumo_75() -> None:
    """Cinco chamadas de 15 tokens esgotam o trabalho, mas deixam a reserva para C.3."""
    guard = _guard(CostBudget(
        max_task_attempts=2, max_additional_planning_rounds=1, max_tasks_per_session=5,
        max_llm_calls_per_session=60, session_token_budget=100, final_answer_token_reserve=25,
        session_timeout_seconds=10,
    ))
    for fase in (
        ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION,
    ):
        assert guard.begin_call(phase=fase).authorized is True
        guard.register_usage(tokens_input=10, tokens_output=5)

    assert guard.authorize(phase=_B1).limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert guard.authorize(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION).limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert guard.authorize(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER).authorized is True


# ── Logging ──────────────────────────────────────────────────────────────────


def test_negacao_emite_exatamente_um_aviso(
    budget_factory: Callable[..., CostBudget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 800)

    with caplog.at_level(logging.WARNING, logger=_LOGGER.name):
        guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    avisos = [registro for registro in caplog.records if registro.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert BudgetLimitEnum.SESSION_TOKEN_BUDGET.value in caplog.text


def test_aviso_de_negacao_carrega_os_contadores_correntes(
    budget_factory: Callable[..., CostBudget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    guard = _guard(budget_factory())
    _gastar(guard, 800)
    guard.register_task_created(quantity=4)
    guard.register_additional_planning_round()

    with caplog.at_level(logging.WARNING, logger=_LOGGER.name):
        guard.authorize(phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)

    assert "800" in caplog.text
    assert "4" in caplog.text
    assert ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION.value in caplog.text


def test_autorizacao_concedida_nao_emite_aviso(
    budget_factory: Callable[..., CostBudget],
    caplog: pytest.LogCaptureFixture,
) -> None:
    guard = _guard(budget_factory())

    with caplog.at_level(logging.WARNING, logger=_LOGGER.name):
        guard.authorize(phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION)

    assert not [registro for registro in caplog.records if registro.levelno == logging.WARNING]
