"""Escala de temperatura das revisões semânticas de A.2 (refinamentos 03, mudança 5.2).

Uma revisão é a nova geração de A.2 depois de um relatório estruturalmente válido de A.3 com
`approved: false`. Candidato 1 usa a temperatura da sessão; candidato 2, `0.5`; candidatos 3 a 5, `1.0`.
A.3 usa sempre a temperatura da sessão. Recuperações de saída inválida ou vazia continuam a `1.0`, na
janela da mesma execução, e não criam candidato nem avançam a escala. Os testes usam parser, fila,
memória e recorder reais com saídas roteirizadas: provam os parâmetros enviados e auditados, não a
qualidade das revisões de um modelo real.
"""
import json

import pytest

from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    aprendizados,
    criterios,
    global_aprovado,
    plano_aprovado,
    plano_reprovado,
    problema_do_plano,
    reprovado,
    resolucao,
    resposta_final,
    tarefa_aprovada,
    tarefas,
    aprovado,
)

_SESSAO = 0.2
_PRIMEIRA_REVISAO = 0.5
_RETENTATIVA = 1.0
_REPROVACAO = plano_reprovado(problema_do_plano(task_id="T1", problem="Condicao omitida.", adjustment="Preservar."))


def _cenario(roteiro: list, **kwargs) -> RalphScenario:
    return RalphScenario(responses=roteiro, temperature=_SESSAO, **kwargs)


def _execucao_t1() -> list[str]:
    return [*tarefa_aprovada("T1", "resultado", "fato"), global_aprovado(), resposta_final()]


def _temperaturas(cenario: RalphScenario, fase: Phase) -> list[float]:
    return [i.temperature for i in cenario.session.invocations if i.phase is fase]


def _primeiras_chamadas(cenario: RalphScenario, fase: Phase) -> list[float]:
    """Temperatura da primeira chamada de cada execução da fase (sem as recuperações)."""
    return [
        i.temperature for i in cenario.session.invocations
        if i.phase is fase and i.recovers_invocation_id is None
    ]


def _enviadas_coincidem_com_registradas(cenario: RalphScenario) -> bool:
    enviadas = [chamada["temperature"] for chamada in cenario.llm.calls]
    return enviadas == [i.temperature for i in cenario.session.invocations]


async def test_primeiro_candidato_aprovado_usa_a_temperatura_da_sessao_sem_revisao() -> None:
    cenario = _cenario([criterios(), tarefas("T1"), plano_aprovado(), anotacoes_do_enunciado(), *_execucao_t1()])

    await cenario.run()

    assert _temperaturas(cenario, Phase.A2_TASK_DECOMPOSITION) == [_SESSAO]
    assert _temperaturas(cenario, Phase.A3_DECOMPOSITION_VALIDATION) == [_SESSAO]
    assert _PRIMEIRA_REVISAO not in [i.temperature for i in cenario.session.invocations]
    assert cenario.cost_guard.planning_attempts == 1
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_reprovacoes_sucessivas_seguem_sessao_meio_e_um_e_a3_fica_na_sessao() -> None:
    roteiro = [criterios()]
    for _ in range(4):
        roteiro += [tarefas("T1"), _REPROVACAO]
    roteiro += [tarefas("T1"), plano_aprovado(), anotacoes_do_enunciado(), *_execucao_t1()]
    cenario = _cenario(roteiro, cost_guard=FakeCostGuard())

    await cenario.run()

    assert _temperaturas(cenario, Phase.A2_TASK_DECOMPOSITION) == [
        _SESSAO, _PRIMEIRA_REVISAO, _RETENTATIVA, _RETENTATIVA, _RETENTATIVA,
    ]
    assert _temperaturas(cenario, Phase.A3_DECOMPOSITION_VALIDATION) == [_SESSAO] * 5
    assert _temperaturas(cenario, Phase.A4_PLANNING_LEARNINGS) == [_SESSAO]
    assert cenario.session.temperature == _SESSAO
    assert cenario.session.status is SessionStatusEnum.COMPLETED
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_esgotamento_no_quinto_candidato_preserva_falha_sem_sexto_candidato() -> None:
    roteiro = [criterios()]
    for _ in range(5):
        roteiro += [tarefas("T1"), _REPROVACAO]
    cenario = _cenario(roteiro, cost_guard=FakeCostGuard())

    with pytest.raises(Exception, match="planning_attempts"):
        await cenario.run()

    assert _temperaturas(cenario, Phase.A2_TASK_DECOMPOSITION) == [
        _SESSAO, _PRIMEIRA_REVISAO, _RETENTATIVA, _RETENTATIVA, _RETENTATIVA,
    ]
    assert cenario.llm.call_count == 11
    assert cenario.task_queue.total_created() == 0
    assert cenario.session.temperature == _SESSAO
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_exemplo_da_especificacao_correcoes_de_json_nao_avancam_a_escala() -> None:
    # candidato 1 em 0.2 → correção em 1.0 → A.3 em 0.2 reprova → candidato 2 em 0.5 → correção em 1.0 →
    # A.3 em 0.2 reprova → candidato 3 em 1.0.
    cenario = _cenario([
        criterios(),
        "isto nao e json", tarefas("T1"), _REPROVACAO,
        "isto tambem nao e json", tarefas("T1"), _REPROVACAO,
        tarefas("T1"), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao_t1(),
    ], cost_guard=FakeCostGuard())

    await cenario.run()

    planejamento = [
        (i.phase, i.temperature) for i in cenario.session.invocations
        if i.phase in (Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION)
    ]
    assert planejamento == [
        (Phase.A2_TASK_DECOMPOSITION, _SESSAO), (Phase.A2_TASK_DECOMPOSITION, _RETENTATIVA),
        (Phase.A3_DECOMPOSITION_VALIDATION, _SESSAO),
        (Phase.A2_TASK_DECOMPOSITION, _PRIMEIRA_REVISAO), (Phase.A2_TASK_DECOMPOSITION, _RETENTATIVA),
        (Phase.A3_DECOMPOSITION_VALIDATION, _SESSAO),
        (Phase.A2_TASK_DECOMPOSITION, _RETENTATIVA),
        (Phase.A3_DECOMPOSITION_VALIDATION, _SESSAO),
    ]
    assert cenario.cost_guard.planning_attempts == 3
    assert _primeiras_chamadas(cenario, Phase.A2_TASK_DECOMPOSITION) == [_SESSAO, _PRIMEIRA_REVISAO, _RETENTATIVA]
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_relatorio_invalido_de_a3_e_corrigido_antes_de_qualquer_revisao_de_a2() -> None:
    invalido = json.dumps({"approved": "false", "issues": []})
    cenario = _cenario([
        criterios(),
        tarefas("T1"), invalido, _REPROVACAO,
        tarefas("T1"), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao_t1(),
    ], cost_guard=FakeCostGuard())

    await cenario.run()

    fases = [(i.phase, i.temperature) for i in cenario.session.invocations][1:6]
    assert fases == [
        (Phase.A2_TASK_DECOMPOSITION, _SESSAO),
        (Phase.A3_DECOMPOSITION_VALIDATION, _SESSAO), (Phase.A3_DECOMPOSITION_VALIDATION, _RETENTATIVA),
        (Phase.A2_TASK_DECOMPOSITION, _PRIMEIRA_REVISAO),
        (Phase.A3_DECOMPOSITION_VALIDATION, _SESSAO),
    ]
    assert cenario.cost_guard.planning_attempts == 2
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_resposta_vazia_na_primeira_revisao_recupera_a_1_sem_novo_candidato() -> None:
    cenario = _cenario([
        criterios(),
        tarefas("T1"), _REPROVACAO,
        EmptyCompletionError(finish_reason="stop"), tarefas("T1"), _REPROVACAO,
        tarefas("T1"), plano_aprovado(),
        anotacoes_do_enunciado(), *_execucao_t1(),
    ], cost_guard=FakeCostGuard())

    await cenario.run()

    a2 = [i for i in cenario.session.invocations if i.phase is Phase.A2_TASK_DECOMPOSITION]
    assert [(i.outcome, i.temperature) for i in a2] == [
        (InvocationOutcomeEnum.SUCCESS, _SESSAO),
        (InvocationOutcomeEnum.EMPTY_COMPLETION, _PRIMEIRA_REVISAO),
        (InvocationOutcomeEnum.SUCCESS, _RETENTATIVA),  # repetição da resposta vazia, mesma execução
        (InvocationOutcomeEnum.SUCCESS, _RETENTATIVA),  # terceiro candidato
    ]
    assert a2[1].context_id == a2[2].context_id != a2[3].context_id
    assert cenario.cost_guard.planning_attempts == 3
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_retentativa_de_b1_continua_a_1_e_b2_e_c_voltam_a_sessao_depois_das_revisoes_do_plano() -> None:
    cenario = _cenario([
        criterios(),
        tarefas("T1"), _REPROVACAO, tarefas("T1"), plano_aprovado(),
        anotacoes_do_enunciado(),
        resolucao("primeira"), reprovado("T1"),
        resolucao("segunda"), aprovado("T1"), aprendizados("fato"),
        global_aprovado(), resposta_final(),
    ], cost_guard=FakeCostGuard())

    await cenario.run()

    assert _temperaturas(cenario, Phase.B1_TASK_RESOLUTION) == [_SESSAO, _RETENTATIVA]
    assert _temperaturas(cenario, Phase.B2_TASK_VERIFICATION) == [_SESSAO, _SESSAO]
    for fase in (Phase.B4_LEARNINGS_EXTRACTION, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER):
        assert _temperaturas(cenario, fase) == [_SESSAO], fase
    assert _enviadas_coincidem_com_registradas(cenario)


async def test_sessoes_sucessivas_nao_compartilham_o_indice_de_revisao() -> None:
    primeira = _cenario([
        criterios(), tarefas("T1"), _REPROVACAO, tarefas("T1"), _REPROVACAO,
        tarefas("T1"), plano_aprovado(), anotacoes_do_enunciado(), *_execucao_t1(),
    ])
    segunda = _cenario([criterios(), tarefas("T1"), _REPROVACAO, tarefas("T1"), plano_aprovado(),
                        anotacoes_do_enunciado(), *_execucao_t1()])

    await primeira.run()
    await segunda.run()

    assert _temperaturas(primeira, Phase.A2_TASK_DECOMPOSITION) == [_SESSAO, _PRIMEIRA_REVISAO, _RETENTATIVA]
    assert _temperaturas(segunda, Phase.A2_TASK_DECOMPOSITION) == [_SESSAO, _PRIMEIRA_REVISAO]


def test_cada_sessao_do_startup_tem_o_seu_proprio_contador_de_candidatos(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome, valor in {
        "LLM_MODEL": "vendor/modelo", "OPENROUTER_API_KEY": "chave-de-teste",
        "GENAI_AVAILABLE_MODELS": "vendor/modelo", "GENAI_AVAILABLE_PROVIDERS": "open_router,openai",
        "LLM_MAX_TOKENS": "120000", "RALPH_FINAL_ANSWER_TOKEN_RESERVE": "4000",
    }.items():
        monkeypatch.setenv(nome, valor)

    primeira, segunda = RalphThinkingStartup(), RalphThinkingStartup()
    primeira.cost_guard.register_planning_attempt()
    primeira.cost_guard.register_planning_attempt()

    assert primeira.cost_guard is not segunda.cost_guard
    assert segunda.cost_guard.register_planning_attempt() == 1
