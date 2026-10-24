import json
import logging

import pytest

from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    aprendizados as _aprendizados,
    aprovado as _aprovado,
    criterios as _criterios,
    global_aprovado as _global_aprovado,
    global_reprovado as _global_reprovado,
    relatorio as _relatorio,
    reprovado as _reprovado,
    resolucao as _resolucao,
    resposta_final as _resposta_final,
    roteiro_feliz as _roteiro_feliz,
    tarefa_aprovada as _tarefa_aprovada,
    tarefas as _tarefas,
)

_TIPO = ThinkingEventTypeEnum
_SUB = ThinkingEventSubtypeEnum
_FASE = ThinkingPhaseEnum


def _cenario_feliz() -> RalphScenario:
    return RalphScenario(responses=_roteiro_feliz())


def _assinaturas(eventos: list) -> list[tuple[str, str]]:
    return [(evento.type.value, evento.subtype.value) for evento in eventos]


async def _executar_ate_falhar(cenario: RalphScenario, excecao: type[Exception]) -> list:
    """Executa o fluxo esperando que ele termine na exceção dada, devolvendo os eventos emitidos."""
    eventos = []
    with pytest.raises(excecao):
        async for evento in cenario.stream():
            eventos.append(evento)
    return eventos


# ── Fluxo feliz ──────────────────────────────────────────────────────────────


async def test_emite_os_eventos_do_fluxo_na_ordem_do_paper() -> None:
    eventos = await _cenario_feliz().run()

    por_tarefa = [("thinking", "reset"), ("thinking", "execute"), ("thinking", "reasoning"),
                  ("thinking", "verify_pass"), ("thinking", "store"), ("thinking", "learn")]
    assert _assinaturas(eventos) == [
        ("thinking", "setup"),
        ("thinking", "tasks"),
        *por_tarefa * 3,
        ("thinking", "compile"),
        ("thinking", "compile"),
        ("result", "compile"),
    ]


async def test_as_fases_sao_chamadas_na_sequencia_do_paper() -> None:
    cenario = _cenario_feliz()

    eventos = await cenario.run()

    fases_com_modelo = [evento.phase.value for evento in eventos if evento.inference_time_ms > 0]
    assert fases_com_modelo == ["A1", "A2", "B1", "B2", "B4", "B1", "B2", "B4", "B1", "B2", "B4", "C1", "C3", "C3"]
    assert cenario.llm.call_count == 13


async def test_o_ultimo_evento_traz_a_resposta_final() -> None:
    eventos = await _cenario_feliz().run()

    assert eventos[-1].type is _TIPO.RESULT
    assert eventos[-1].content == "D) Nenhuma das anteriores"


async def test_o_total_de_tokens_nunca_decresce() -> None:
    eventos = await _cenario_feliz().run()

    totais = [evento.total_tokens for evento in eventos]
    assert totais == sorted(totais)
    assert totais[-1] > 0


async def test_a_sessao_persistida_registra_o_pensamento_completo() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    sessao = cenario.session
    assert sessao.status is SessionStatusEnum.COMPLETED
    assert sessao.final_answer == "D) Nenhuma das anteriores"
    assert [mensagem.phase.value for mensagem in sessao.messages] == [
        "A1", "A1", "A2",
        *["B1", "B1", "B2", "B3", "B4"] * 3,
        "C1", "C3",
    ]
    assert sessao.degradations == []


async def test_toda_mensagem_de_tarefa_carrega_fase_tarefa_contexto_tokens_e_tempo() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    resolucoes = [m for m in cenario.session.messages if m.phase is _FASE.B1_TASK_RESOLUTION and m.total_tokens]
    assert len(resolucoes) == 3
    for mensagem in resolucoes:
        assert mensagem.task_id
        assert mensagem.context_id
        assert mensagem.inference_time_ms > 0


async def test_a_selecao_da_tarefa_e_o_armazenamento_nao_chamam_o_modelo() -> None:
    cenario = _cenario_feliz()

    eventos = await cenario.run()

    programaticos = [e for e in eventos if e.subtype in (_SUB.RESET, _SUB.EXECUTE, _SUB.STORE)]
    assert len(programaticos) == 9
    assert all(evento.inference_time_ms == 0 for evento in programaticos)


async def test_os_parametros_do_modelo_chegam_a_todas_as_chamadas() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    assert all(chamada["model_name"] == "vendor/modelo-padrao" for chamada in cenario.llm.calls)
    assert all(chamada["max_tokens"] == 1200 for chamada in cenario.llm.calls)
    assert all(chamada["temperature"] == 0.3 for chamada in cenario.llm.calls)


# ── I1 — Fresh Context por tarefa ────────────────────────────────────────────


async def test_invariante_i1_cada_tarefa_recebe_uma_janela_de_contexto_nova() -> None:
    eventos = await _cenario_feliz().run()

    resets = [evento for evento in eventos if evento.subtype is _SUB.RESET]
    assert len(resets) == 3
    assert len({evento.context_id for evento in resets}) == 3
    assert all(evento.context_size == 0 for evento in resets)
    assert all(evento.phase is _FASE.B1_TASK_RESOLUTION for evento in resets)


async def test_invariante_i1_a_janela_da_tarefa_seguinte_nao_carrega_a_conversa_anterior() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    conversa_da_segunda_tarefa = cenario.llm.texts_of(5)
    assert all("2 e primo" not in texto for texto in conversa_da_segunda_tarefa)


# ── I2 — Injeção de aprendizados ─────────────────────────────────────────────


async def test_invariante_i2_a_primeira_tarefa_nao_recebe_aprendizados() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    primeira_conversa = cenario.llm.texts_of(2)
    assert len(primeira_conversa) == 1
    assert "Aprendizados acumulados" not in primeira_conversa[0]


async def test_invariante_i2_as_tarefas_seguintes_recebem_os_aprendizados_no_inicio() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    segunda_conversa = cenario.llm.texts_of(5)
    terceira_conversa = cenario.llm.texts_of(8)
    assert segunda_conversa[0].startswith("## Aprendizados acumulados")
    assert "Um numero primo so e divisivel por 1 e por ele mesmo." in segunda_conversa[0]
    assert segunda_conversa[1].startswith("TEMPLATE B1")
    assert terceira_conversa[0].startswith("## Aprendizados acumulados")
    assert "Todo numero par e divisivel por 2." in terceira_conversa[0]


# ── I3 — Contexto preservado entre tentativas da mesma tarefa ────────────────


def _roteiro_com_reprovacao() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2"),
        *_tarefa_aprovada("T1", "2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        _resolucao("primeira tentativa incompleta"),
        _reprovado("T2"),
        _resolucao("segunda tentativa completa"),
        _aprovado("T2"),
        _aprendizados("Todo numero par e divisivel por 2."),
        _global_aprovado(),
        _resposta_final(),
    ]


async def test_invariante_i3_as_tentativas_da_mesma_tarefa_usam_a_mesma_janela() -> None:
    eventos = await RalphScenario(responses=_roteiro_com_reprovacao()).run()

    raciocinios_da_t2 = [e for e in eventos if e.subtype is _SUB.REASONING and e.task == "T2"]
    assert len(raciocinios_da_t2) == 2
    assert raciocinios_da_t2[0].context_id == raciocinios_da_t2[1].context_id


async def test_invariante_i3_a_segunda_tentativa_enxerga_a_reprovacao_da_primeira() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    segunda_tentativa = cenario.llm.texts_of(7)
    assert any("primeira tentativa incompleta" in texto for texto in segunda_tentativa)
    assert any("T2-AC1" in texto for texto in segunda_tentativa)


async def test_invariante_i3_nao_ha_reset_entre_tentativas_da_mesma_tarefa() -> None:
    eventos = await RalphScenario(responses=_roteiro_com_reprovacao()).run()

    assinaturas_da_t2 = [
        evento.subtype.value for evento in eventos if evento.task == "T2"
    ]
    assert assinaturas_da_t2 == [
        "reset", "execute", "reasoning", "verify_fail", "reasoning", "verify_pass", "store", "learn"
    ]
    assert assinaturas_da_t2.count("reset") == 1


# ── I4 — Verificação isolada ────────────────────────────────────────────────


async def test_invariante_i4_a_verificacao_usa_janela_diferente_da_resolucao() -> None:
    eventos = await _cenario_feliz().run()

    for tarefa in ("T1", "T2", "T3"):
        raciocinio = next(e for e in eventos if e.subtype is _SUB.REASONING and e.task == tarefa)
        verificacao = next(e for e in eventos if e.subtype is _SUB.VERIFY_PASS and e.task == tarefa)
        assert raciocinio.context_id != verificacao.context_id


async def test_invariante_i4_a_conversa_da_verificacao_traz_apenas_o_proprio_prompt() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    conversa_da_verificacao = cenario.llm.texts_of(6)
    assert len(conversa_da_verificacao) == 1
    assert conversa_da_verificacao[0].startswith("TEMPLATE B2")
    assert "Aprendizados acumulados" not in conversa_da_verificacao[0]
    assert "2 e primo" not in conversa_da_verificacao[0]


async def test_invariante_i4_a_verificacao_recebe_resultado_preliminar_e_criterios() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    variaveis = cenario.template_provider.variables_of(_FASE.B2_TASK_VERIFICATION)[0]
    assert variaveis["preliminary_result"] == "2 e primo"
    assert "T1-AC1" in variaveis["task_acceptance_criteria"]


# ── I5 — Só o aprovado é armazenado ─────────────────────────────────────────


async def test_invariante_i5_armazena_apenas_a_tentativa_aprovada() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    resultados = cenario.template_provider.variables_of(_FASE.C1_GLOBAL_VERIFICATION)[0]["stored_results"]
    assert "segunda tentativa completa" in resultados
    assert "primeira tentativa incompleta" not in resultados


async def test_invariante_i5_o_armazenamento_nao_chama_o_modelo() -> None:
    cenario = _cenario_feliz()

    eventos = await cenario.run()

    armazenamentos = [evento for evento in eventos if evento.subtype is _SUB.STORE]
    assert len(armazenamentos) == 3
    assert all(evento.inference_time_ms == 0 for evento in armazenamentos)
    assert all(evento.phase is _FASE.B3_RESULT_STORAGE for evento in armazenamentos)


# ── I6 — Separação entre resultado e aprendizado ────────────────────────────


async def test_invariante_i6_a_fase_c_nao_enxerga_nenhum_aprendizado() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    for fase in (_FASE.C1_GLOBAL_VERIFICATION, _FASE.C3_FINAL_ANSWER):
        resultados = cenario.template_provider.variables_of(fase)[0]["stored_results"]
        assert "2 e primo" in resultados
        assert "Um numero primo so e divisivel" not in resultados
        assert "Aprendizados acumulados" not in resultados


async def test_invariante_i6_o_loop_b_nao_enxerga_nenhum_resultado_armazenado() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    conversa_da_terceira_tarefa = " ".join(cenario.llm.texts_of(8))
    assert "Aprendizados acumulados" in conversa_da_terceira_tarefa
    assert "2 e primo" not in conversa_da_terceira_tarefa
    assert "2, 4 e 6 sao pares" not in conversa_da_terceira_tarefa


# ── I7 — C.2 insere no topo e a seleção é programática ──────────────────────


def _roteiro_com_replanejamento() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1"),
        *_tarefa_aprovada("T1", "2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        _global_reprovado("AC2"),
        _tarefas("T4", "T5"),
        *_tarefa_aprovada("T4", "4 e par", "Todo numero par e divisivel por 2."),
        *_tarefa_aprovada("T5", "6 e maior que 2", "O unico primo par e o 2."),
        _global_aprovado(),
        _resposta_final(),
    ]


async def test_invariante_i7_as_tarefas_de_c2_entram_no_topo_e_na_ordem() -> None:
    eventos = await RalphScenario(responses=_roteiro_com_replanejamento()).run()

    ordem = [evento.task for evento in eventos if evento.subtype is _SUB.RESET]
    assert ordem == ["T1", "T4", "T5"]


async def test_invariante_i7_a_selecao_da_proxima_tarefa_nao_chama_o_modelo() -> None:
    cenario = RalphScenario(responses=_roteiro_com_replanejamento())

    eventos = await cenario.run()

    chamadas_por_evento = [e for e in eventos if e.inference_time_ms > 0]
    assert cenario.llm.call_count == len(chamadas_por_evento) - 1
    resets = [evento for evento in eventos if evento.subtype is _SUB.RESET]
    assert all(evento.inference_time_ms == 0 for evento in resets)


async def test_c2_recebe_as_pendencias_os_resultados_e_a_proxima_numeracao() -> None:
    cenario = RalphScenario(responses=_roteiro_com_replanejamento())

    await cenario.run()

    variaveis = cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)[0]
    assert "AC2" in variaveis["unmet_criteria"]
    assert "2 e primo" in variaveis["stored_results"]
    assert variaveis["next_task_number"] == "2"


async def test_c2_recebe_o_teto_de_tarefas_que_a_sessao_ainda_comporta() -> None:
    cenario = RalphScenario(responses=_roteiro_com_replanejamento(), cost_guard=FakeCostGuard(task_slots=9))

    await cenario.run()

    assert cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)[0]["max_tasks"] == "9"
    assert cenario.template_provider.variables_of(_FASE.A2_TASK_DECOMPOSITION)[0]["max_tasks"] == "9"


# ── Ciclo de planejamento adicional ─────────────────────────────────────────


async def test_duas_rodadas_de_planejamento_adicional() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            _global_reprovado("AC2"),
            _tarefas("T4"),
            *_tarefa_aprovada("T4", "4 e par", "fato dois"),
            _global_reprovado("AC2"),
            _tarefas("T5"),
            *_tarefa_aprovada("T5", "6 e maior que 2", "fato tres"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    assert len([evento for evento in eventos if evento.subtype is _SUB.REPLAN]) == 2
    assert cenario.cost_guard.additional_rounds == 2
    resultados = cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)[0]["stored_results"]
    assert "4 e par" in resultados
    assert "6 e maior que 2" in resultados


async def test_c1_aprovando_de_primeira_nao_gera_replanejamento() -> None:
    eventos = await _cenario_feliz().run()

    assert not [evento for evento in eventos if evento.subtype is _SUB.REPLAN]


async def test_as_tarefas_de_c2_recebem_os_aprendizados_acumulados_de_todas_as_anteriores() -> None:
    cenario = RalphScenario(responses=_roteiro_com_replanejamento())

    await cenario.run()

    # chamadas: 0 A1, 1 A2, 2-4 T1, 5 C1, 6 C2, 7 B1 de T4
    primeira_conversa_da_t4 = cenario.llm.texts_of(7)
    assert primeira_conversa_da_t4[0].startswith("## Aprendizados acumulados")
    assert "Um numero primo so e divisivel por 1 e por ele mesmo." in primeira_conversa_da_t4[0]


async def test_a_sintese_so_recebe_os_resultados_que_a_verificacao_global_aprovou() -> None:
    cenario = RalphScenario(responses=_roteiro_com_replanejamento())

    await cenario.run()

    por_c1 = cenario.template_provider.variables_of(_FASE.C1_GLOBAL_VERIFICATION)
    por_c3 = cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)[0]["stored_results"]
    assert "4 e par" not in por_c1[0]["stored_results"]
    assert "4 e par" in por_c1[1]["stored_results"]
    assert por_c3 == por_c1[1]["stored_results"]


# ── Relatórios incompletos ou contraditórios nunca aprovam ───────────────────


async def test_relatorio_local_vazio_e_corrigido_pelo_verificador_sem_gastar_tentativa_de_resolucao() -> None:
    relatorio_vazio = json.dumps({"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []})
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            _resolucao("2 e primo"),
            relatorio_vazio,
            _aprovado("T1"),
            _aprendizados("fato"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    assert cenario.cost_guard.attempts_by_task == {"T1": 1}
    assert len([e for e in eventos if e.subtype is _SUB.VERIFY_PASS]) == 1
    assert eventos[-1].type is _TIPO.RESULT
    # a segunda conversa do verificador mostra a correção pedida, na mesma janela
    assert any("T1-AC1" in texto and "Faltam avaliações" in texto for texto in cenario.llm.texts_of(4))


async def test_relatorio_local_com_id_inexistente_marcado_como_nao_atendido_nao_aprova() -> None:
    contraditorio = json.dumps(
        {
            "decision": "approved",
            "criteria_evaluation": [{"criterion_id": "INEXISTENTE", "met": False, "justification": "x"}],
            "unmet_criteria_ids": [],
        }
    )
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            _resolucao("2 e primo"),
            contraditorio,
            _aprovado("T1"),
            _aprendizados(),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    await cenario.run()

    assert cenario.llm.call_count == 8


async def test_relatorio_global_incompleto_e_corrigido_antes_de_decidir_pela_sintese() -> None:
    incompleto = _relatorio(("AC1", True))
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato"),
            incompleto,
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    assert eventos[-1].type is _TIPO.RESULT
    assert len([e for e in eventos if e.phase is _FASE.C1_GLOBAL_VERIFICATION]) == 1
    assert cenario.llm.call_count == 8


async def test_relatorio_global_que_reprova_um_id_desconhecido_e_corrigido_e_nao_zera_as_pendencias_do_c2() -> None:
    desconhecido = _relatorio(("AC1", True), ("AC2", True), ("FANTASMA", False))
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            desconhecido,
            _global_reprovado("AC2"),
            _tarefas("T4"),
            *_tarefa_aprovada("T4", "4 e par", "fato dois"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    await cenario.run()

    variaveis = cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)[0]
    assert "AC2" in variaveis["unmet_criteria"]
    assert variaveis["unmet_criteria"] != "—"


async def test_verificador_que_nunca_corrige_o_relatorio_encerra_sem_armazenar_nem_sintetizar() -> None:
    vazio = json.dumps({"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []})
    cenario = RalphScenario(
        responses=[_criterios(), _tarefas("T1"), _resolucao("2 e primo"), vazio, vazio, vazio],
        settings=FakeSettings(ralph_json_parse_max_retries=2),
    )

    eventos = await _executar_ate_falhar(cenario, PhaseParsingError)

    assert not [e for e in eventos if e.subtype is _SUB.STORE]
    assert eventos[-1].type is _TIPO.ERROR
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.failure.phase is _FASE.B2_TASK_VERIFICATION


# ── B.3: só o resultado aprovado é armazenado ────────────────────────────────


def _roteiro_com_tarefa_reprovada_em_todas_as_tentativas() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2"),
        _resolucao("primeira tentativa ruim"),
        _reprovado("T1"),
        _resolucao("RESULTADO_REPROVADO"),
        _reprovado("T1"),
    ]


async def test_tarefa_reprovada_em_todas_as_tentativas_interrompe_a_execucao() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.B2_TASK_VERIFICATION
    assert "task_attempts" in eventos[-1].content
    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1"]


async def test_resultado_reprovado_nunca_e_armazenado_nem_chega_a_sintese() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert not [e for e in eventos if e.subtype is _SUB.STORE]
    assert not [e for e in eventos if e.phase is _FASE.B3_RESULT_STORAGE]
    assert not cenario.template_provider.variables_of(_FASE.C1_GLOBAL_VERIFICATION)
    assert not cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)
    assert not [e for e in eventos if e.type is _TIPO.RESULT]
    assert cenario.llm.call_count == 6


async def test_tarefa_reprovada_em_todas_as_tentativas_nao_extrai_aprendizados_nem_segue_o_loop() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert not [e for e in eventos if e.subtype is _SUB.LEARN]
    assert cenario.learnings_memory.is_empty()
    assert cenario.task_queue.is_empty()


async def test_interrupcao_por_tentativas_registra_tarefa_causa_e_ultimo_relatorio_na_sessao() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    sessao = cenario.session
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None
    assert sessao.degradations == []
    assert sessao.failure.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert sessao.failure.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert sessao.failure.task_id == "T1"
    assert sessao.failure.phase is _FASE.B2_TASK_VERIFICATION
    assert "`T2`" in sessao.failure.description
    ultimo_veredito = [m for m in sessao.messages if m.phase is _FASE.B2_TASK_VERIFICATION][-1]
    assert "nao atende" in ultimo_veredito.content


async def test_a_tarefa_reprovada_fica_marcada_como_falha_e_as_demais_como_descartadas() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert cenario.task_queue.total_created() == 2
    assert cenario.task_queue.is_empty()


async def test_se_a_segunda_tentativa_e_aprovada_so_ela_e_armazenada() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    resultados = cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)[0]["stored_results"]
    assert "segunda tentativa completa" in resultados
    assert "primeira tentativa incompleta" not in resultados


# ── C.3 exige aprovação global ───────────────────────────────────────────────


def _roteiro_ate_a_primeira_reprovacao_global() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1"),
        *_tarefa_aprovada("T1", "2 e primo", "fato um"),
        _global_reprovado("AC2"),
    ]


async def test_reprovacao_global_sem_recursos_para_replanejar_nao_chama_a_sintese() -> None:
    cenario = RalphScenario(
        responses=_roteiro_ate_a_primeira_reprovacao_global(),
        cost_guard=FakeCostGuard(additional_planning_allowed=False),
    )

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert not cenario.template_provider.variables_of(_FASE.C3_FINAL_ANSWER)
    assert not [e for e in eventos if e.type is _TIPO.RESULT]
    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.C2_ADDITIONAL_PLANNING
    assert cenario.llm.call_count == 6


@pytest.mark.parametrize(
    "limite",
    [
        BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS,
        BudgetLimitEnum.TASKS_PER_SESSION,
        BudgetLimitEnum.SESSION_TOKEN_BUDGET,
        BudgetLimitEnum.LLM_CALLS_PER_SESSION,
        BudgetLimitEnum.SESSION_TIMEOUT,
    ],
)
async def test_o_limite_registrado_e_o_que_o_guardiao_apontou_para_negar_o_replanejamento(
    limite: BudgetLimitEnum,
) -> None:
    cenario = RalphScenario(
        responses=_roteiro_ate_a_primeira_reprovacao_global(),
        cost_guard=FakeCostGuard(additional_planning_allowed=False, additional_planning_denied_limit=limite),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert cenario.session.failure.limit is limite
    assert cenario.session.failure.reason is SessionFailureReasonEnum.RESOURCE_LIMIT


async def test_reprovacao_global_sem_recursos_registra_os_criterios_pendentes_e_nao_conclui() -> None:
    cenario = RalphScenario(
        responses=_roteiro_ate_a_primeira_reprovacao_global(),
        cost_guard=FakeCostGuard(additional_planning_allowed=False),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    sessao = cenario.session
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None
    assert sessao.failure.pending_criteria_ids == ("AC2",)
    assert "`AC2`" in sessao.failure.description
    assert sessao.degradations == []


async def test_duas_reprovacoes_globais_seguidas_nunca_conduzem_a_c3() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            _global_reprovado("AC2"),
            _tarefas("T4"),
            *_tarefa_aprovada("T4", "4 e par", "fato dois"),
            _global_reprovado("AC2"),
        ],
        cost_guard=guardiao,
    )

    eventos = []
    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream():
            eventos.append(evento)
            if evento.subtype is _SUB.REPLAN:
                guardiao.additional_planning_allowed = False

    assert [e.phase.value for e in eventos if e.phase in (_FASE.C1_GLOBAL_VERIFICATION, _FASE.C3_FINAL_ANSWER)] == [
        "C1",
        "C1",
    ]
    assert eventos[-1].type is _TIPO.ERROR
    assert cenario.session.final_answer is None
    assert cenario.session.failure.pending_criteria_ids == ("AC2",)


async def test_aprovacao_global_seguida_de_falha_na_sintese_nao_gera_sucesso() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato"),
            _global_aprovado(),
            "isto nao e json",
        ],
        settings=FakeSettings(ralph_json_parse_max_retries=0),
    )

    eventos = await _executar_ate_falhar(cenario, PhaseParsingError)

    assert not [e for e in eventos if e.type is _TIPO.RESULT]
    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.C3_FINAL_ANSWER
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None


async def test_aprovacao_global_seguida_de_sintese_valida_gera_uma_unica_conclusao_persistida() -> None:
    cenario = _cenario_feliz()
    persistida_ao_receber_o_resultado: list[SessionStatusEnum] = []

    eventos = []
    async for evento in cenario.stream():
        eventos.append(evento)
        if evento.type is _TIPO.RESULT:
            persistida_ao_receber_o_resultado.append(cenario.session.status)

    assert persistida_ao_receber_o_resultado == [SessionStatusEnum.COMPLETED]
    assert len([e for e in eventos if e.type is _TIPO.RESULT]) == 1
    assert cenario.session.final_answer == "D) Nenhuma das anteriores"
    assert cenario.session.failure is None


# ── Interrupção por orçamento: causa, diagnóstico e fim único ────────────────


def _roteiro_interrompido() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2", "T3"),
        *_tarefa_aprovada("T1", "2 e primo", "fato um"),
    ]


async def test_orcamento_esgotado_no_loop_interrompe_descartando_as_tarefas_restantes() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    eventos = []
    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream():
            eventos.append(evento)
            if evento.subtype is _SUB.LEARN:
                guardiao.authorized = False

    assert eventos[-1].type is _TIPO.ERROR
    assert "session_token_budget" in eventos[-1].content
    assert "`T2`, `T3`" in eventos[-1].content
    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1"]
    assert not [e for e in eventos if e.type is _TIPO.RESULT]
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.failure.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert cenario.session.failure.phase is _FASE.B1_TASK_RESOLUTION


async def test_o_limite_registrado_e_o_do_veredito_que_negou_o_loop() -> None:
    guardiao = FakeCostGuard(denied_limit=BudgetLimitEnum.SESSION_TIMEOUT)
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream():
            if evento.subtype is _SUB.LEARN:
                guardiao.authorized = False

    assert cenario.session.failure.limit is BudgetLimitEnum.SESSION_TIMEOUT


async def test_tarefas_descartadas_pela_interrupcao_saem_da_fila() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream():
            if evento.subtype is _SUB.LEARN:
                guardiao.authorized = False

    assert cenario.task_queue.is_empty() is True
    assert cenario.task_queue.total_created() == 3


async def test_orcamento_esgotado_dentro_de_uma_fase_interrompe_com_a_fase_e_a_tarefa_reais() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    eventos = []
    with pytest.raises(BudgetExceededError):
        async for evento in cenario.stream():
            eventos.append(evento)
            if evento.subtype is _SUB.EXECUTE and evento.task == "T2":
                guardiao.authorized = False

    # T2 só chega a executar porque o veredito de consulta ainda autorizava; a chamada é que foi negada
    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.B1_TASK_RESOLUTION
    assert cenario.session.failure.task_id == "T2"
    assert cenario.session.failure.phase is _FASE.B1_TASK_RESOLUTION


async def test_orcamento_esgotado_em_c3_encerra_a_sessao_sem_resposta_final() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_feliz(), cost_guard=guardiao)

    eventos = []
    with pytest.raises(BudgetExceededError):
        async for evento in cenario.stream():
            eventos.append(evento)
            if evento.phase is _FASE.C1_GLOBAL_VERIFICATION:
                guardiao.authorized = False

    assert eventos[-1].type is _TIPO.ERROR
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.failure.phase is _FASE.C3_FINAL_ANSWER
    assert not [e for e in eventos if e.type is _TIPO.RESULT]


async def test_toda_interrupcao_emite_um_unico_evento_de_erro_e_encerra_a_sessao_uma_unica_vez() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert len([e for e in eventos if e.type is _TIPO.ERROR]) == 1
    assert eventos[-1].type is _TIPO.ERROR
    assert not [e for e in eventos if e.type is _TIPO.DEGRADED]
    assert cenario.repository.save_calls.count(cenario.session.id) > 0


async def test_o_diagnostico_da_interrupcao_traz_o_consumo_conhecido_da_sessao() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    totais = cenario.session.totals
    assert totais.total_llm_calls == 6
    assert f"{totais.total_tokens} tokens em {totais.total_llm_calls} chamadas" in cenario.session.failure.description


# ── Teto de tarefas vale para o plano inicial e para o adicional ─────────────


async def test_plano_inicial_acima_do_teto_e_devolvido_ao_planejador_e_nunca_truncado() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1", "T2"),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato"),
            _global_aprovado(),
            _resposta_final(),
        ],
        cost_guard=FakeCostGuard(task_slots=1),
    )

    eventos = await cenario.run()

    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1"]
    assert cenario.task_queue.total_created() == 1
    assert any("no máximo 1" in texto for texto in cenario.llm.texts_of(2))
    assert eventos[-1].type is _TIPO.RESULT


async def test_plano_inicial_que_nunca_cabe_no_teto_interrompe_sem_mutar_a_fila_nem_os_contadores() -> None:
    guardiao = FakeCostGuard(task_slots=1)
    cenario = RalphScenario(
        responses=[_criterios(), _tarefas("T1", "T2"), _tarefas("T1", "T2"), _tarefas("T1", "T2")],
        cost_guard=guardiao,
        settings=FakeSettings(ralph_json_parse_max_retries=2),
    )

    eventos = await _executar_ate_falhar(cenario, PhaseParsingError)

    assert eventos[-1].type is _TIPO.ERROR
    assert cenario.task_queue.total_created() == 0
    assert cenario.task_queue.known_task_ids() == frozenset()
    assert guardiao.tasks_created == []
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.failure.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert cenario.session.failure.limit is BudgetLimitEnum.TASKS_PER_SESSION
    assert cenario.session.failure.phase is _FASE.A2_TASK_DECOMPOSITION


async def test_c2_acima_do_teto_e_devolvido_ao_planejador_e_nao_e_truncado() -> None:
    guardiao = FakeCostGuard(task_slots=2)
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            _global_reprovado("AC2"),
            _tarefas("T4", "T5", "T6", "T7", "T8"),
            _tarefas("T4", "T5"),
            *_tarefa_aprovada("T4", "4 e par", "fato dois"),
            *_tarefa_aprovada("T5", "6 e maior que 2", "fato tres"),
            _global_aprovado(),
            _resposta_final(),
        ],
        cost_guard=guardiao,
    )

    eventos = await cenario.run()

    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1", "T4", "T5"]
    assert guardiao.tasks_created == [1, 2]


async def test_c2_que_reutiliza_o_id_de_uma_tarefa_ja_criada_e_devolvido_para_correcao() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            _global_reprovado("AC2"),
            _tarefas("T1"),
            _tarefas("T4"),
            *_tarefa_aprovada("T4", "4 e par", "fato dois"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1", "T4"]
    assert cenario.task_queue.known_task_ids() == frozenset({"T1", "T4"})


async def test_c2_sem_slot_de_tarefa_nao_chama_o_planejador_e_aponta_o_limite_de_tarefas() -> None:
    cenario = RalphScenario(
        responses=_roteiro_ate_a_primeira_reprovacao_global(),
        cost_guard=FakeCostGuard(
            additional_planning_allowed=False, additional_planning_denied_limit=BudgetLimitEnum.TASKS_PER_SESSION
        ),
    )

    await _executar_ate_falhar(cenario, ExecutionInterruptedError)

    assert not cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)
    assert cenario.session.failure.limit is BudgetLimitEnum.TASKS_PER_SESSION


# ── Erros técnicos ──────────────────────────────────────────────────────────


async def test_falha_de_parsing_irrecuperavel_encerra_a_sessao_como_falha() -> None:
    cenario = RalphScenario(
        responses=[_criterios(), "isso nao e json"],
        settings=FakeSettings(ralph_json_parse_max_retries=0),
    )

    eventos = []
    with pytest.raises(PhaseParsingError):
        async for evento in cenario.stream():
            eventos.append(evento)

    assert eventos[-1].type is _TIPO.ERROR
    assert eventos[-1].phase is _FASE.A2_TASK_DECOMPOSITION
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.failure.limit is None


async def test_excecao_inesperada_do_provedor_e_registrada_e_repropagada(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cenario = RalphScenario(responses=[], error=RuntimeError("provedor fora do ar"))

    eventos = []
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="provedor fora do ar"):
            async for evento in cenario.stream():
                eventos.append(evento)

    assert eventos[-1].type is _TIPO.ERROR
    assert "provedor fora do ar" in eventos[-1].content
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert "provedor fora do ar" in cenario.session.failure.description
    assert any(registro.exc_info for registro in caplog.records)
    assert cenario.session.invocations[0].outcome is InvocationOutcomeEnum.PROVIDER_ERROR


async def test_a_sessao_registra_o_provedor_efetivo_e_a_temperatura_pedida() -> None:
    cenario = RalphScenario(responses=_roteiro_feliz(), temperature=0.0)

    await cenario.run()

    assert cenario.session.provider.value == "open_router"
    assert cenario.session.temperature == 0.0
    assert all(chamada["temperature"] == 0.0 for chamada in cenario.llm.calls)


# ── Casos de borda ──────────────────────────────────────────────────────────


async def test_uma_unica_tarefa_percorre_o_fluxo_completo() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato um"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    assert _assinaturas(eventos) == [
        ("thinking", "setup"),
        ("thinking", "tasks"),
        ("thinking", "reset"),
        ("thinking", "execute"),
        ("thinking", "reasoning"),
        ("thinking", "verify_pass"),
        ("thinking", "store"),
        ("thinking", "learn"),
        ("thinking", "compile"),
        ("thinking", "compile"),
        ("result", "compile"),
    ]
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_tarefa_sem_aprendizado_nao_injeta_bloco_na_tarefa_seguinte() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1", "T2"),
            *_tarefa_aprovada("T1", "2 e primo"),
            *_tarefa_aprovada("T2", "4 e par"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    segunda_conversa = cenario.llm.texts_of(5)
    assert len(segunda_conversa) == 1
    assert segunda_conversa[0].startswith("TEMPLATE B1")
    assert [e.content for e in eventos if e.subtype is _SUB.LEARN][0] == "Nenhum aprendizado foi extraído desta tarefa."


# ── I3/I4 — Veredito do validador e histórico completo da tarefa (B.4) ───────


async def test_invariante_i3_a_segunda_tentativa_enxerga_o_veredito_do_validador() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    segunda_tentativa = " ".join(cenario.llm.texts_of(7))
    assert "nao atende" in segunda_tentativa
    assert "reproved" in segunda_tentativa


async def test_a_instrucao_de_refazer_so_aparece_quando_ha_nova_tentativa() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    segunda_tentativa = cenario.llm.texts_of(7)
    assert sum("Refaça a resolução da tarefa" in texto for texto in segunda_tentativa) == 1
    historico_de_b4 = cenario.llm.texts_of(9)
    assert sum("Refaça a resolução da tarefa" in texto for texto in historico_de_b4) == 1


async def test_a_resposta_reprovada_nao_e_duplicada_na_mensagem_de_correcao() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    segunda_tentativa = cenario.llm.texts_of(7)
    assert sum("primeira tentativa incompleta" in texto for texto in segunda_tentativa) == 1


async def test_b4_recebe_o_veredito_de_aprovacao_mesmo_quando_aprovado_de_primeira() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    contexto_de_b4 = " ".join(cenario.llm.texts_of(4))
    assert "Veredito do validador (tentativa 1)" in contexto_de_b4
    assert "`approved`" in contexto_de_b4
    assert "atende" in contexto_de_b4


async def test_b4_recebe_a_reprovacao_e_tambem_a_aprovacao_de_uma_tarefa_com_retry() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    contexto_de_b4 = cenario.llm.texts_of(9)
    vereditos = [texto for texto in contexto_de_b4 if texto.startswith("## Veredito do validador")]
    assert len(vereditos) == 2
    assert "tentativa 1" in vereditos[0] and "`reproved`" in vereditos[0]
    assert "tentativa 2" in vereditos[1] and "`approved`" in vereditos[1]


async def test_b4_recebe_a_correcao_de_saida_estruturada_do_validador_identificada_como_invalida() -> None:
    saida_invalida_do_validador = json.dumps(
        {"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []}
    )
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            _resolucao("2 e primo"),
            saida_invalida_do_validador,
            _aprovado("T1"),
            _aprendizados("fato"),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    await cenario.run()

    contexto_de_b4 = cenario.llm.texts_of(5)
    indice_da_invalida = next(i for i, texto in enumerate(contexto_de_b4) if "saída inválida" in texto)
    indice_do_veredito = next(i for i, texto in enumerate(contexto_de_b4) if texto.startswith("## Veredito"))
    assert indice_da_invalida < indice_do_veredito
    assert "Faltam avaliações" in contexto_de_b4[indice_da_invalida]


async def test_a_janela_do_validador_continua_isolada_da_da_tarefa() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    conversa_do_validador = cenario.llm.texts_of(8)
    assert len(conversa_do_validador) == 1
    assert "Veredito do validador" not in conversa_do_validador[0]
    assert "primeira tentativa incompleta" not in conversa_do_validador[0]


async def test_a_tarefa_seguinte_recebe_so_os_aprendizados_e_nao_o_historico_ampliado() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    primeira_conversa_da_t2 = " ".join(cenario.llm.texts_of(5))
    assert "Veredito do validador" not in primeira_conversa_da_t2
    assert "Aprendizados acumulados" in primeira_conversa_da_t2


async def test_a_fase_c_nao_enxerga_vereditos_locais_nem_historico_de_tentativas() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    for fase in (_FASE.C1_GLOBAL_VERIFICATION, _FASE.C3_FINAL_ANSWER):
        variaveis = cenario.template_provider.variables_of(fase)[0]
        assert "Veredito do validador" not in " ".join(variaveis.values())
        assert "primeira tentativa incompleta" not in " ".join(variaveis.values())
        assert "Aprendizados acumulados" not in " ".join(variaveis.values())


# ── Registro por invocação ──────────────────────────────────────────────────


async def test_a_sessao_registra_uma_invocacao_por_chamada_ao_modelo() -> None:
    cenario = _cenario_feliz()

    await cenario.run()

    sessao = cenario.session
    assert len(sessao.invocations) == cenario.llm.call_count == 13
    assert sessao.totals.total_llm_calls == 13
    assert sessao.totals.total_tokens == 13 * 15
    assert all(i.outcome is InvocationOutcomeEnum.SUCCESS for i in sessao.invocations)


async def test_chamadas_de_correcao_de_saida_contam_como_chamadas_da_sessao() -> None:
    cenario = RalphScenario(
        responses=["isto nao e json", *_roteiro_feliz()],
        settings=FakeSettings(ralph_json_parse_max_retries=2),
    )

    await cenario.run()

    assert cenario.session.totals.total_llm_calls == 14 == cenario.llm.call_count
    assert cenario.session.totals.total_tokens == 14 * 15


async def test_o_total_de_tokens_dos_eventos_acompanha_as_invocacoes_e_nunca_decresce() -> None:
    cenario = RalphScenario(
        responses=["isto nao e json", *_roteiro_feliz()],
        settings=FakeSettings(ralph_json_parse_max_retries=2),
    )

    eventos = await cenario.run()

    totais = [evento.total_tokens for evento in eventos]
    assert totais == sorted(totais)
    assert totais[-1] == 14 * 15


async def test_falha_de_fase_preserva_chamadas_e_tokens_na_sessao_falha() -> None:
    cenario = RalphScenario(
        responses=["ruim", "ruim", "ruim"],
        settings=FakeSettings(ralph_json_parse_max_retries=2),
        tokens_input=10,
        tokens_output=5,
    )

    await _executar_ate_falhar(cenario, PhaseParsingError)

    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.totals.total_llm_calls == 3
    assert cenario.session.totals.total_tokens == 45


async def test_a_falha_e_persistida_antes_de_o_evento_terminal_de_erro_ser_emitido() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_reprovada_em_todas_as_tentativas(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )
    persistida_ao_receber_o_erro: list[SessionStatusEnum] = []

    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream():
            if evento.type is _TIPO.ERROR:
                persistida_ao_receber_o_erro.append(cenario.session.status)
                assert cenario.session.failure is not None

    assert persistida_ao_receber_o_erro == [SessionStatusEnum.FAILED]


# ── Persistência do encerramento e atribuição da fase ───────────────────────


async def test_falha_ao_gravar_a_conclusao_encerra_a_sessao_como_falha_sem_resposta_final() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.COMPLETED: 1})
    cenario = RalphScenario(responses=_roteiro_feliz(), repository=repositorio)
    eventos = []

    with pytest.raises(OSError, match="persistência indisponível"):
        async for evento in cenario.stream():
            eventos.append(evento)

    assert not any(evento.type is _TIPO.RESULT for evento in eventos)
    assert eventos[-1].type is _TIPO.ERROR
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.failure.phase is _FASE.C3_FINAL_ANSWER


async def test_falha_persistente_ao_encerrar_propaga_a_falha_de_gravacao_e_nao_o_estado_da_sessao() -> None:
    repositorio = InMemorySessionRepository(
        failing_saves={SessionStatusEnum.COMPLETED: 1, SessionStatusEnum.FAILED: 1}
    )
    cenario = RalphScenario(responses=_roteiro_feliz(), repository=repositorio)

    with pytest.raises(OSError, match="persistência indisponível"):
        await cenario.run()

    assert cenario.recorder.session.status is SessionStatusEnum.RUNNING
    assert cenario.session.status is SessionStatusEnum.RUNNING


async def test_erro_tecnico_na_verificacao_da_tarefa_e_atribuido_a_b2() -> None:
    cenario = RalphScenario(
        responses=[_criterios(), _tarefas("T1"), _resolucao("2 e primo"), RuntimeError("provedor caiu")]
    )
    eventos = []

    with pytest.raises(RuntimeError, match="provedor caiu"):
        async for evento in cenario.stream():
            eventos.append(evento)

    invocacao = cenario.session.invocations[-1]
    assert invocacao.phase is _FASE.B2_TASK_VERIFICATION
    assert cenario.session.failure.phase is _FASE.B2_TASK_VERIFICATION
    assert eventos[-1].phase is _FASE.B2_TASK_VERIFICATION
    assert eventos[-1].context_id == invocacao.context_id
    assert cenario.session.failure.task_id == "T1"


async def test_erro_tecnico_na_extracao_de_aprendizados_e_atribuido_a_b4() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            _resolucao("2 e primo"),
            _aprovado("T1"),
            RuntimeError("provedor caiu"),
        ]
    )
    eventos = []

    with pytest.raises(RuntimeError):
        async for evento in cenario.stream():
            eventos.append(evento)

    assert cenario.session.invocations[-1].phase is _FASE.B4_LEARNINGS_EXTRACTION
    assert cenario.session.failure.phase is _FASE.B4_LEARNINGS_EXTRACTION
    assert eventos[-1].phase is _FASE.B4_LEARNINGS_EXTRACTION


async def test_erro_tecnico_na_verificacao_global_e_atribuido_a_c1() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("T1", "2 e primo", "fato"),
            RuntimeError("provedor caiu"),
        ]
    )

    with pytest.raises(RuntimeError):
        await cenario.run()

    assert cenario.session.failure.phase is _FASE.C1_GLOBAL_VERIFICATION
    assert cenario.session.failure.task_id is None


async def test_saidas_invalidas_do_verificador_ficam_na_sessao_quando_as_correcoes_se_esgotam() -> None:
    cenario = RalphScenario(
        responses=[_criterios(), _tarefas("T1"), _resolucao("2 e primo"), "invalida 1", "invalida 2", "invalida 3"],
        settings=FakeSettings(ralph_json_parse_max_retries=2),
    )

    await _executar_ate_falhar(cenario, PhaseParsingError)

    auditorias = [
        mensagem.content
        for mensagem in cenario.session.messages
        if mensagem.phase is _FASE.B2_TASK_VERIFICATION and "Saída inválida" in mensagem.content
    ]
    assert len(auditorias) == 3
    assert all(f"invalida {indice}" in auditorias[indice - 1] for indice in (1, 2, 3))
    assert cenario.session.totals.total_llm_calls == 6
    assert cenario.session.failure.phase is _FASE.B2_TASK_VERIFICATION


async def test_falha_ao_gravar_a_pergunta_do_usuario_encerra_a_sessao_como_falha() -> None:
    repositorio = InMemorySessionRepository(failing_save_calls={2})
    cenario = RalphScenario(responses=_roteiro_feliz(), repository=repositorio)
    eventos = []

    with pytest.raises(OSError, match=r"gravação 2"):
        async for evento in cenario.stream():
            eventos.append(evento)

    assert [evento.type for evento in eventos] == [_TIPO.ERROR]
    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.failure.reason is SessionFailureReasonEnum.TECHNICAL_ERROR
    assert cenario.session.invocations == []
    assert cenario.llm.call_count == 0
