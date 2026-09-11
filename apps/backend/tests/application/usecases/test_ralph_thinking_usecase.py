import json
import logging

import pytest

from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.phase_parsing_error import PhaseParsingError
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario

_TIPO = ThinkingEventTypeEnum
_SUB = ThinkingEventSubtypeEnum
_FASE = ThinkingPhaseEnum


def _criterios() -> str:
    return json.dumps(
        {
            "general_acceptance_criteria": [
                {"id": "AC1", "description": "responder em portugues"},
                {"id": "AC2", "description": "selecionar uma das alternativas"},
            ]
        }
    )


def _tarefa(task_id: str) -> dict[str, object]:
    return {
        "id": task_id,
        "title": f"titulo de {task_id}",
        "description": f"descricao de {task_id}",
        "expected_input": "entrada esperada",
        "expected_output": "saida esperada",
        "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": f"criterio de {task_id}"}],
    }


def _tarefas(*ids: str) -> str:
    return json.dumps({"tasks": [_tarefa(task_id) for task_id in ids]})


def _resolucao(texto: str) -> str:
    return json.dumps({"task_id": "T1", "result": texto})


def _aprovado(criterion_id: str = "T1-AC1") -> str:
    return json.dumps(
        {
            "decision": "approved",
            "criteria_evaluation": [{"criterion_id": criterion_id, "met": True, "justification": "atende"}],
            "unmet_criteria_ids": [],
        }
    )


def _reprovado(criterion_id: str = "T1-AC1") -> str:
    return json.dumps(
        {
            "decision": "reproved",
            "criteria_evaluation": [{"criterion_id": criterion_id, "met": False, "justification": "nao atende"}],
            "unmet_criteria_ids": [criterion_id],
        }
    )


def _aprendizados(*fatos: str) -> str:
    return json.dumps({"learnings": list(fatos)})


def _resposta_final(texto: str = "D) Nenhuma das anteriores") -> str:
    return json.dumps({"final_answer": texto})


def _tarefa_aprovada(resultado: str, *aprendizados: str) -> list[str]:
    return [_resolucao(resultado), _aprovado(), _aprendizados(*aprendizados)]


def _roteiro_feliz() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2", "T3"),
        *_tarefa_aprovada("2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        *_tarefa_aprovada("2, 4 e 6 sao pares", "Todo numero par e divisivel por 2."),
        *_tarefa_aprovada("apenas 4 e 6 sao maiores que 2", "O unico primo par e o 2."),
        _aprovado("AC1"),
        _resposta_final(),
    ]


def _cenario_feliz() -> RalphScenario:
    return RalphScenario(responses=_roteiro_feliz())


def _assinaturas(eventos: list) -> list[tuple[str, str]]:
    return [(evento.type.value, evento.subtype.value) for evento in eventos]


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
        *_tarefa_aprovada("2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        _resolucao("primeira tentativa incompleta"),
        _reprovado("T2-AC1"),
        _resolucao("segunda tentativa completa"),
        _aprovado("T2-AC1"),
        _aprendizados("Todo numero par e divisivel por 2."),
        _aprovado("AC1"),
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
        *_tarefa_aprovada("2 e primo", "Um numero primo so e divisivel por 1 e por ele mesmo."),
        _reprovado("AC2"),
        _tarefas("T4", "T5"),
        *_tarefa_aprovada("4 e par", "Todo numero par e divisivel por 2."),
        *_tarefa_aprovada("6 e maior que 2", "O unico primo par e o 2."),
        _aprovado("AC1"),
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


# ── Ciclo de planejamento adicional ─────────────────────────────────────────


async def test_duas_rodadas_de_planejamento_adicional() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _reprovado("AC2"),
            _tarefas("T4"),
            *_tarefa_aprovada("4 e par", "fato dois"),
            _reprovado("AC2"),
            _tarefas("T5"),
            *_tarefa_aprovada("6 e maior que 2", "fato tres"),
            _aprovado("AC1"),
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


# ── Degradação — tentativas esgotadas ───────────────────────────────────────


def _roteiro_com_tarefa_degradada() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2"),
        _resolucao("primeira tentativa ruim"),
        _reprovado("T1-AC1"),
        _resolucao("segunda tentativa ainda ruim"),
        _reprovado("T1-AC1"),
        _aprendizados("fato descoberto mesmo na reprovacao"),
        *_tarefa_aprovada("T2 resolvida", "outro fato"),
        _aprovado("AC1"),
        _resposta_final(),
    ]


async def test_degradacao_por_tentativas_esgotadas_aceita_a_ultima_tentativa() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_degradada(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await cenario.run()

    degradados = [evento for evento in eventos if evento.type is _TIPO.DEGRADED]
    assert len(degradados) == 1
    assert "task_attempts" in degradados[0].content
    assert degradados[0].task == "T1"
    resultados = cenario.template_provider.variables_of(_FASE.C1_GLOBAL_VERIFICATION)[0]["stored_results"]
    assert "segunda tentativa ainda ruim" in resultados


async def test_degradacao_por_tentativas_esgotadas_nao_interrompe_o_fluxo() -> None:
    cenario = RalphScenario(
        responses=_roteiro_com_tarefa_degradada(),
        cost_guard=FakeCostGuard(max_task_attempts=2),
    )

    eventos = await cenario.run()

    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1", "T2"]
    assert eventos[-1].type is _TIPO.RESULT
    assert cenario.session.status is SessionStatusEnum.DEGRADED
    assert [degradacao.limit.value for degradacao in cenario.session.degradations] == ["task_attempts"]
    assert cenario.session.degradations[0].task_id == "T1"


# ── Degradação — planejamento adicional esgotado ────────────────────────────


async def test_degradacao_por_planejamento_adicional_esgotado() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _reprovado("AC2"),
            _tarefas("T4"),
            *_tarefa_aprovada("4 e par", "fato dois"),
            _reprovado("AC2"),
            _resposta_final(),
        ],
        cost_guard=guardiao,
    )

    eventos = []
    async for evento in cenario.stream():
        eventos.append(evento)
        if evento.subtype is _SUB.REPLAN:
            guardiao.additional_planning_allowed = False

    degradados = [evento for evento in eventos if evento.type is _TIPO.DEGRADED]
    assert len(degradados) == 1
    assert "additional_planning_rounds" in degradados[0].content
    assert [evento.subtype.value for evento in eventos[-3:]] == ["replan", "compile", "compile"]
    assert eventos[-1].type is _TIPO.RESULT
    assert cenario.session.status is SessionStatusEnum.DEGRADED


async def test_degradacao_por_falta_de_slot_de_tarefa_aponta_o_limite_de_tarefas() -> None:
    guardiao = FakeCostGuard(additional_planning_allowed=False, task_slots=0)
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _reprovado("AC2"),
            _resposta_final(),
        ],
        cost_guard=guardiao,
    )

    eventos = await cenario.run()

    degradados = [evento for evento in eventos if evento.type is _TIPO.DEGRADED]
    assert "tasks_per_session" in degradados[0].content


# ── Degradação — orçamento da sessão ────────────────────────────────────────


def _roteiro_interrompido() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1", "T2", "T3"),
        *_tarefa_aprovada("2 e primo", "fato um"),
        _aprovado("AC1"),
        _resposta_final(),
    ]


async def test_degradacao_por_orcamento_de_tokens_descarta_as_tarefas_restantes() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    eventos = []
    async for evento in cenario.stream():
        eventos.append(evento)
        if evento.subtype is _SUB.LEARN:
            guardiao.tokens_left = 0

    degradados = [evento for evento in eventos if evento.type is _TIPO.DEGRADED]
    assert len(degradados) == 1
    assert "session_token_budget" in degradados[0].content
    assert "`T2`, `T3`" in degradados[0].content
    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1"]
    assert eventos[-1].type is _TIPO.RESULT
    assert eventos[-1].content == "D) Nenhuma das anteriores"
    assert cenario.session.status is SessionStatusEnum.DEGRADED


async def test_degradacao_por_veredito_negado_no_loop_aponta_o_limite_do_veredito() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    eventos = []
    async for evento in cenario.stream():
        eventos.append(evento)
        if evento.subtype is _SUB.LEARN:
            guardiao.authorized = False
            guardiao.denied_limit = BudgetLimitEnum.SESSION_TIMEOUT
        if evento.type is _TIPO.DEGRADED:
            guardiao.authorized = True

    degradados = [evento for evento in eventos if evento.type is _TIPO.DEGRADED]
    assert "session_timeout" in degradados[0].content
    assert eventos[-1].type is _TIPO.RESULT
    assert cenario.session.status is SessionStatusEnum.DEGRADED


async def test_as_tarefas_descartadas_ficam_marcadas_como_descartadas() -> None:
    guardiao = FakeCostGuard()
    cenario = RalphScenario(responses=_roteiro_interrompido(), cost_guard=guardiao)

    async for evento in cenario.stream():
        if evento.subtype is _SUB.LEARN:
            guardiao.tokens_left = 0

    assert cenario.task_queue.is_empty() is True
    assert cenario.task_queue.total_created() == 3


# ── Degradação — limite de tarefas em C.2 ───────────────────────────────────


async def test_c2_trunca_as_novas_tarefas_ao_numero_de_slots_disponiveis() -> None:
    guardiao = FakeCostGuard(task_slots=2)
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _reprovado("AC2"),
            _tarefas("T4", "T5", "T6", "T7", "T8"),
            *_tarefa_aprovada("4 e par", "fato dois"),
            *_tarefa_aprovada("6 e maior que 2", "fato tres"),
            _aprovado("AC1"),
            _resposta_final(),
        ],
        cost_guard=guardiao,
    )

    eventos = await cenario.run()

    assert [evento.task for evento in eventos if evento.subtype is _SUB.RESET] == ["T1", "T4", "T5"]
    assert guardiao.tasks_created == [1, 2]


# ── Erros ───────────────────────────────────────────────────────────────────


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


async def test_orcamento_esgotado_em_c3_encerra_a_sessao_como_falha() -> None:
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
    assert any(registro.exc_info for registro in caplog.records)


# ── Casos de borda ──────────────────────────────────────────────────────────


async def test_uma_unica_tarefa_percorre_o_fluxo_completo() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _aprovado("AC1"),
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
            *_tarefa_aprovada("2 e primo"),
            *_tarefa_aprovada("4 e par"),
            _aprovado("AC1"),
            _resposta_final(),
        ]
    )

    eventos = await cenario.run()

    segunda_conversa = cenario.llm.texts_of(5)
    assert len(segunda_conversa) == 1
    assert segunda_conversa[0].startswith("TEMPLATE B1")
    assert [e.content for e in eventos if e.subtype is _SUB.LEARN][0] == "Nenhum aprendizado foi extraído desta tarefa."


async def test_pendencia_sem_criterio_geral_correspondente_vira_lista_vazia_em_c2() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas("T1"),
            *_tarefa_aprovada("2 e primo", "fato um"),
            _reprovado("criterio-desconhecido"),
            _tarefas("T4"),
            *_tarefa_aprovada("4 e par", "fato dois"),
            _aprovado("AC1"),
            _resposta_final(),
        ]
    )

    await cenario.run()

    variaveis = cenario.template_provider.variables_of(_FASE.C2_ADDITIONAL_PLANNING)[0]
    assert variaveis["unmet_criteria"] == "—"


async def test_invariante_i3_a_segunda_tentativa_enxerga_o_veredito_do_validador() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    segunda_tentativa = " ".join(cenario.llm.texts_of(7))
    assert "nao atende" in segunda_tentativa
    assert "reproved" in segunda_tentativa


async def test_o_contexto_da_tarefa_leva_a_interacao_com_o_validador_ate_b4() -> None:
    cenario = RalphScenario(responses=_roteiro_com_reprovacao())

    await cenario.run()

    contexto_completo_em_b4 = " ".join(cenario.llm.texts_of(9))
    assert "primeira tentativa incompleta" in contexto_completo_em_b4
    assert "nao atende" in contexto_completo_em_b4
