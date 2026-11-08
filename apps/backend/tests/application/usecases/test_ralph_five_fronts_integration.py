"""Matriz de regressões integradas das cinco frentes do thinking (etapa 07), com prompts reais.

Caso de uso, fases, provider de arquivos, parser, fila, livro de resultados, memória, gravador e
repositório são reais; só a porta do modelo é falsa. As perguntas vêm da fixture versionada
`integration_regressions_v1.json`, cujo oráculo pertence ao avaliador e não é usado aqui.

O que estes testes provam: mensagens preservadas, transições, contratos, estado vigente, auditoria,
contabilização e o material que cada fase recebe (`prompt_input` e conversas capturadas). O que não
provam: que um modelo real chega às respostas certas. As saídas do modelo são roteirizadas — inclusive
as corretas —, logo nenhum destes cenários é evidência de acurácia semântica.
"""
import asyncio
import io
import json
import logging
import re
import zipfile
from pathlib import Path

import pytest

from src.domain.entities.benchmark.benchmark_ralph_error import BenchmarkRalphError
from src.domain.entities.resilience.cost_budget import CostBudget
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.result_status_enum import ResultStatusEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from src.infra.services.benchmark_ralph_errors_archive_builder import BenchmarkRalphErrorsArchiveBuilder
from tests.doubles.benchmark_factories import desfecho, questao
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import plano_aprovado
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_MATRIZ = json.loads(
    (Path(__file__).resolve().parents[2] / "fixtures" / "integration_regressions_v1.json").read_text(encoding="utf-8")
)
_CASOS = {caso["name"]: caso for caso in _MATRIZ["cases"]}
_PLANEJAMENTO = [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
                 Phase.A4_PLANNING_LEARNINGS]
_CICLO = [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION]
_SEM_REVISOES = "No stored result has been revised or suspended."


# ── Roteiros ────────────────────────────────────────────────────────────────


def _pergunta(caso: str) -> str:
    return _CASOS[caso]["question"]


def _json(**valor: object) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _criterios(*descricoes: str) -> str:
    return _json(general_acceptance_criteria=[
        {"id": f"AC{indice}", "description": descricao} for indice, descricao in enumerate(descricoes, start=1)
    ])


def _tarefa(task_id: str, titulo: str, descricao: str, **extra: object) -> dict:
    return {"id": task_id, "title": titulo, "description": descricao,
            "acceptance_criteria": [{"id": f"{task_id}-AC1",
                                     "description": "Resultado determinado e justificado a partir dos dados."}],
            **extra}


def _plano(*tarefas: dict) -> str:
    return _json(tasks=list(tarefas))


def _notas(*fatos: str) -> str:
    return _json(learnings=list(fatos))


def _resolucao(task_id: str, resultado: str, *vereditos: tuple[str, str, str]) -> str:
    extra = {"revision": [{"task_id": alvo, "verdict": verdict, "justification": justificativa}
                          for alvo, verdict, justificativa in vereditos]} if vereditos else {}
    return _json(task_id=task_id, result=resultado, conclusion=resultado, **extra)


def _local(task_id: str, aprovado: bool = True, justificativa: str = "Atende.", revisao: bool | None = None) -> str:
    avaliacoes = [{"criterion_id": f"{task_id}-AC1", "met": aprovado, "justification": justificativa}]
    if revisao is not None:
        avaliacoes.append({"criterion_id": f"{task_id}-REV", "met": revisao,
                           "justification": "A investigação demonstra o veredito." if revisao else
                           "O veredito não está demonstrado."})
    pendentes = [a["criterion_id"] for a in avaliacoes if not a["met"]]
    return _json(criteria_evaluation=avaliacoes, unmet_criteria_ids=pendentes,
                 decision="reproved" if pendentes else "approved")


def _global(justificativa_ac1: str = "Coberto pelos resultados vigentes.", aprovado: bool = True) -> str:
    return _json(
        criteria_evaluation=[{"criterion_id": "AC1", "met": aprovado, "justification": justificativa_ac1},
                             {"criterion_id": "AC2", "met": True, "justification": "C.3 aplica o idioma."}],
        unmet_criteria_ids=[] if aprovado else ["AC1"], decision="approved" if aprovado else "reproved",
    )


def _final(texto: str) -> str:
    return _json(final_answer=texto)


def _tarefa_executada(task_id: str, resultado: str, *fatos: str) -> list[str]:
    return [_resolucao(task_id, resultado), _local(task_id), _notas(*fatos)]


def _cenario(respostas: list[str], **extra: object) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(
        responses=respostas, settings=settings,
        template_provider=FilePromptTemplateProvider(settings=settings, logger=logging.getLogger("teste.07")),
        **extra,
    )


# ── Inspeção ────────────────────────────────────────────────────────────────


def _fases(cenario: RalphScenario) -> list[Phase]:
    return [invocacao.phase for invocacao in cenario.session.invocations]


def _indices(cenario: RalphScenario, fase: Phase, task_id: str | None = None) -> list[int]:
    return [indice for indice, invocacao in enumerate(cenario.session.invocations)
            if invocacao.phase is fase and invocacao.recovers_invocation_id is None
            and (task_id is None or invocacao.task_id == task_id)]


def _prompts(cenario: RalphScenario, fase: Phase, task_id: str | None = None) -> list[str]:
    return [cenario.llm.texts_of(indice)[0] for indice in _indices(cenario, fase, task_id)]


def _area(prompt: str, titulo: str) -> str:
    conteudo = prompt.split(f"## {titulo}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", conteudo, maxsplit=1)[0].strip()


def _blocos(area: str) -> list[str]:
    return re.findall(r"^## (T\d+) —", area, flags=re.MULTILINE)


def _memoria(prompt: str) -> list[str]:
    return [linha for linha in _area(prompt, "Key Learnings").splitlines() if linha.startswith("- ")]


def _sem_espacos(texto: str) -> str:
    return " ".join(texto.split())


def _contabilizacao_integral(cenario: RalphScenario) -> None:
    """Toda chamada enviada vira uma invocação concluída e entra nos totais da sessão."""
    invocacoes = cenario.session.invocations
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == len(invocacoes)
    assert all(invocacao.outcome is InvocationOutcomeEnum.SUCCESS for invocacao in invocacoes)


def _c3_recebe_exatamente_a_ultima_c1(cenario: RalphScenario) -> str:
    """C.3 roda uma vez, por último, numa janela nova, sobre o que a última C.1 aprovou."""
    [indice_c3] = _indices(cenario, Phase.C3_FINAL_ANSWER)
    assert indice_c3 == cenario.llm.call_count - 1
    assert len(cenario.llm.texts_of(indice_c3)) == 1
    c3 = cenario.llm.texts_of(indice_c3)[0]
    ultima_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[-1]
    for area in ("Stored results", "General acceptance criteria"):
        assert _area(c3, area) == _area(ultima_c1, area), area
    # A descrição da área é de cada template; a memória renderizada é a mesma que a última C.1 viu.
    assert _memoria(c3) == _memoria(ultima_c1)
    mensagem_c3 = [m for m in cenario.session.messages if m.phase is Phase.C3_FINAL_ANSWER][-1]
    assert [m.text for m in mensagem_c3.prompt_input] == [c3]
    return c3


def _concluida(cenario: RalphScenario, eventos: list, resposta: str) -> None:
    assert cenario.session.status is SessionStatusEnum.COMPLETED
    assert cenario.session.final_answer == resposta
    assert eventos[-1].type is ThinkingEventTypeEnum.RESULT and eventos[-1].content == resposta
    _contabilizacao_integral(cenario)


def _harness_nao_injeta(cenario: RalphScenario, pergunta: str, *proibidos: str) -> None:
    """Antes da primeira saída do modelo, os prompts só trazem template e pergunta: nenhum oráculo."""
    for fase in _PLANEJAMENTO:
        for prompt in _prompts(cenario, fase):
            sem_pergunta = prompt.replace(pergunta, "")
            for proibido in proibidos:
                assert proibido not in sem_pergunta, (fase, proibido)


# ── Casos de Marte: recuperação integral e cobertura ───────────────────────

_MARTE_A3 = [
    "Razão entre a maior e a menor distância Terra–Marte: aproximadamente 7,7, na configuração considerada.",
    "Órbitas supostas circulares, coplanares e concêntricas ao Sol; período terrestre: 12 meses.",
    "Alternativas, em meses: A) 12, B) 15, C) 18, D) 22, E) 27.",
    "Determinação pedida: período orbital de Marte, em meses.",
]
_MARTE_CRITERIOS = _criterios("Determinar o período orbital de Marte em meses e indicar a alternativa sustentada.",
                              "Responder em português.")
_DETALHE = (" Preserve os dados literais: razão aproximada de 7,7 entre a maior e a menor distância Terra–Marte; "
            "órbitas circulares, coplanares e concêntricas; período terrestre de 12 meses. Explique as relações "
            "usadas, as hipóteses e as convenções adotadas, com substituição e unidades.")
_MARTE_T1 = _tarefa("T1", "Relacionar as distâncias extremas aos raios orbitais",
                    "Relacione a maior e a menor distância Terra–Marte aos raios orbitais R (Marte) e r (Terra)."
                    + _DETALHE)
_MARTE_T2 = _tarefa("T2", "Obter a razão dos raios orbitais",
                    "Use a relação de distâncias registrada em Key Learnings para obter R/r." + _DETALHE,
                    depends_on=["T1"])
_MARTE_T3_SEM_TITULO = {key: value for key, value in _tarefa(
    "T3", "Determinar o período de Marte em meses",
    "Aplique a terceira lei de Kepler à razão R/r registrada em Key Learnings, determine o período de Marte em "
    "meses e justifique a alternativa escolhida, distinguindo valor obtido e opção." + _DETALHE,
    depends_on=["T2"]).items() if key != "title"}
_MARTE_T3 = {**_MARTE_T3_SEM_TITULO, "title": "Determinar o período de Marte em meses"}
_MARTE_PERIODO = ("MARCA_PERIODO: T = 12·(R/r)^(3/2) = 12·(1,2985)^(3/2) ≈ 17,76 meses. C) 18 meses é o melhor "
                  "ajuste (diferença de 0,24 mês, compatível com a precisão de 7,7); não há igualdade.")


async def test_marte_recuperacao_preserva_o_plano_integral_e_executa_as_tres_tarefas() -> None:
    recusada = _plano(_MARTE_T1, _MARTE_T2, _MARTE_T3_SEM_TITULO)
    corrigida = _plano(_MARTE_T1, _MARTE_T2, _MARTE_T3)
    pergunta = _pergunta("mars_recovery")
    cenario = _cenario([
        _MARTE_CRITERIOS, recusada, corrigida, plano_aprovado(), _notas(*_MARTE_A3),
        *_tarefa_executada("T1", "MARCA_T1: d_max = R + r e d_min = R − r, logo (R + r)/(R − r) ≈ 7,7.",
                           "As distâncias extremas Terra–Marte valem R + r e R − r: órbitas circulares concêntricas."),
        *_tarefa_executada("T2", "MARCA_T2: R/r = (7,7 + 1)/(7,7 − 1) ≈ 1,2985.",
                           "A razão dos raios orbitais de Marte e da Terra é R/r ≈ 1,2985: (7,7 + 1)/(7,7 − 1)."),
        *_tarefa_executada("T3", _MARTE_PERIODO,
                           "O período de Marte é ≈ 17,76 meses e C) 18 é o melhor ajuste: T ∝ R^(3/2)."),
        _global("T3 determina o período e fundamenta C) 18 como melhor ajuste."),
        _final("C) 18 meses — melhor ajuste para o período obtido, de cerca de 17,8 meses."),
    ])

    eventos = await cenario.run(question=pergunta)

    # A saída recusada volta inteira na mesma janela: T2 e T3 estão depois dos 1.000 primeiros caracteres.
    assert len(recusada) > 1_000 and recusada.index('"id": "T3"') > 1_000
    [chamada_original] = _indices(cenario, Phase.A2_TASK_DECOMPOSITION)
    template_a2, recusa_na_janela, correcao = cenario.llm.texts_of(chamada_original + 1)
    assert recusa_na_janela == recusada and [template_a2] == cenario.llm.texts_of(chamada_original)
    assert correcao.startswith("## Phase contract correction") and "### Planning coverage" in correcao
    assert "title" in correcao
    original, recuperada = cenario.session.invocations[1:3]
    assert original.content_accepted is False and recuperada.recovers_invocation_id == original.id
    assert original.output_diagnostic.problem.affected_ids == ("T3",)
    assert recuperada.temperature == 1.0
    assert cenario.session.invocations[3].temperature == cenario.temperature

    # O plano corrigido inteiro é executado, com as dependências declaradas levadas ao domínio.
    assert _fases(cenario) == [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A2_TASK_DECOMPOSITION,
                               Phase.A3_DECOMPOSITION_VALIDATION, Phase.A4_PLANNING_LEARNINGS, *_CICLO * 3,
                               Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C3_FINAL_ANSWER]
    b1_t3 = _prompts(cenario, Phase.B1_TASK_RESOLUTION, "T3")[0]
    assert "### T3 — Determinar o período de Marte em meses" in _area(b1_t3, "Task")
    assert cenario.results_ledger.get(task_id="T3").depends_on == ("T2",)
    assert cenario.results_ledger.get(task_id="T2").depends_on == ("T1",)

    # As anotações de A.3 chegam a todas as fases B e C; o planejamento não recebe resultados antecipados.
    for fase in (*_CICLO, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER):
        for prompt in _prompts(cenario, fase):
            assert all(nota in _area(prompt, "Key Learnings") for nota in _MARTE_A3), fase
    _harness_nao_injeta(cenario, pergunta, "17,76", "1,2985")
    _c3_recebe_exatamente_a_ultima_c1(cenario)
    _concluida(cenario, eventos, "C) 18 meses — melhor ajuste para o período obtido, de cerca de 17,8 meses.")


async def test_cobertura_de_marte_encaminha_a_c2_completa_a_analise_e_reverifica_antes_de_c3() -> None:
    lacuna = ("Os resultados vigentes trazem só a razão adimensional R/r ≈ 1,2985 (T1); o período em meses pedido "
              "não foi determinado. Investigar o período a partir de T1.")
    cenario = _cenario([
        _MARTE_CRITERIOS,
        _plano(_MARTE_T1, _MARTE_T2, _MARTE_T3_SEM_TITULO),
        _plano(_tarefa("T1", "Obter a razão dos raios orbitais", "Obtenha R/r a partir da razão 7,7." + _DETALHE)),
        plano_aprovado(), _notas(*_MARTE_A3),
        *_tarefa_executada("T1", "MARCA_RAZAO: R/r = (7,7 + 1)/(7,7 − 1) ≈ 1,2985.",
                           "A razão dos raios orbitais de Marte e da Terra é R/r ≈ 1,2985: (7,7 + 1)/(7,7 − 1)."),
        _global(lacuna, aprovado=False),
        _plano(_tarefa("T2", "Determinar o período de Marte em meses",
                       "Aplique a terceira lei de Kepler à razão R/r registrada em Key Learnings e determine o "
                       "período de Marte em meses, justificando a alternativa." + _DETALHE, depends_on=["T1"])),
        *_tarefa_executada("T2", _MARTE_PERIODO, "O período de Marte é ≈ 17,76 meses: T ∝ R^(3/2)."),
        _global("T2 determina o período; C) 18 é o melhor ajuste fundamentado."),
        _final("C"),
    ])

    eventos = await cenario.run(question=_pergunta("mars_coverage"))

    assert _fases(cenario) == [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A2_TASK_DECOMPOSITION,
                               Phase.A3_DECOMPOSITION_VALIDATION, Phase.A4_PLANNING_LEARNINGS, *_CICLO,
                               Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C2_ADDITIONAL_PLANNING, *_CICLO, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C3_FINAL_ANSWER]
    assert cenario.llm.call_count == 15
    c2 = _prompts(cenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert lacuna in _area(c2, "Global verification feedback")
    assert "MARCA_RAZAO" in _area(c2, "Results already stored")
    assert _pergunta("mars_coverage") in _area(c2, "Original Prompt")
    assert _area(c2, "Revision record").endswith(_SEM_REVISOES)
    assert cenario.results_ledger.get(task_id="T2").depends_on == ("T1",)
    primeira_c1, segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)
    assert _blocos(_area(primeira_c1, "Stored results")) == ["T1"]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2"]
    assert "MARCA_PERIODO" in _area(_c3_recebe_exatamente_a_ultima_c1(cenario), "Stored results")
    _concluida(cenario, eventos, "C")


# ── Colisões: contradição, revisão aprovada, memória vigente e auditoria ────

_COLISOES_A3 = [
    "Carros iguais: massa m, velocidade inicial v e o mesmo intervalo de tempo de colisão nos dois casos.",
    "Barreira de pneus: o carro retorna com velocidade de módulo u > 0.",
    "Blocos de concreto: o carro para.",
    "Pedido: comparar a força média sobre cada carro e a energia mecânica dissipada em cada colisão.",
]
_COLISOES_CRITERIOS = _criterios("Comparar força média e energia dissipada com justificativa consistente.",
                                 "Responder em português.")
_C_T1 = "MARCA_C1: |Δp| = m(v + u) nos pneus e mv nos blocos; com o mesmo intervalo, a força média é maior nos pneus."
_C_T2 = "MARCA_C2: dissipa-se ½m(v² − u²) nos pneus e ½mv² nos blocos; a dissipação é maior nos blocos."
_C_T3 = "MARCA_C3: a força média é maior nos blocos e a dissipação é maior nos pneus."
_C_L1 = "A força média sobre o carro é maior na barreira de pneus: impulso m(v + u) contra mv, no mesmo intervalo."
_C_L2 = "A energia mecânica dissipada é maior nos blocos: ½mv² contra ½m(v² − u²) nos pneus."
_C_LDV = "A variação de velocidade do carro nos pneus tem módulo v + u: o carro inverte o sentido."
_C_L3 = "A força média é maior nos blocos de concreto: atribuída à parada total do carro."
_C_MOTIVO = "T3 afirma força maior nos blocos e dissipação maior nos pneus, incompatível com T1 e T2."
_C_CONTRADICAO = ("T3 contradiz T1 e T2 sobre os mesmos carros e condições (força média e dissipação); "
                  "investigar as afirmações de T3 sem decidir antes qual está errada.")


def _colisoes_ate_a_contradicao(t3: str = _C_T3, *notas_t3: str) -> list[str]:
    return [
        _COLISOES_CRITERIOS,
        _plano(_tarefa("T1", "Comparar a força média", "Compare a força média sobre cada carro, com impulso."),
               _tarefa("T2", "Comparar a energia dissipada", "Compare a energia mecânica dissipada em cada caso."),
               _tarefa("T3", "Relacionar força e energia", "Relacione força média e energia dissipada nos dois "
                       "casos, usando os achados registrados.", depends_on=["T1", "T2"])),
        plano_aprovado(), _notas(*_COLISOES_A3),
        *_tarefa_executada("T1", _C_T1, _C_L1, _C_LDV),
        *_tarefa_executada("T2", _C_T2, _C_L2),
        *_tarefa_executada("T3", t3, *(notas_t3 or (_C_L3, _C_LDV))),
        _global(_C_CONTRADICAO, aprovado=False),
    ]


def _revisora(task_id: str = "T4", alvos: tuple[str, ...] = ("T3",), motivo: str = _C_MOTIVO) -> dict:
    return _tarefa(task_id, "Investigar as afirmações conflitantes",
                   "Investigue a força média e a energia dissipada nos dois casos e explique qual afirmação "
                   "registrada a investigação confirma ou corrige.",
                   review={"task_ids": list(alvos), "reason": motivo})


_C_T4 = ("MARCA_C4: com o mesmo intervalo, o impulso m(v + u) nos pneus supera mv nos blocos, então a força média "
         "é maior nos pneus; a dissipação é maior nos blocos. T3 tratou a parada total como a maior variação de "
         "momento e inverteu as duas comparações.")
_C_L4 = "Com o mesmo intervalo de colisão, a inversão do sentido nos pneus torna o impulso maior: força média maior."


async def test_colisoes_revisao_aprovada_atualiza_resultados_e_memoria_vigentes_com_historico_auditado() -> None:
    final = "A força média é maior na barreira de pneus; a energia dissipada é maior nos blocos de concreto."
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(),
        _plano(_revisora()),
        _resolucao("T4", _C_T4, ("T3", "superseded", "T3 inverteu o impulso: a parada total não é o maior Δp.")),
        _local("T4", revisao=True),
        _notas(_C_L4),
        _global("Os resultados vigentes T1, T2 e T4 são consistentes."),
        _final(final),
    ])

    eventos = await cenario.run(question=_pergunta("collisions_revision"))

    assert _fases(cenario) == [*_PLANEJAMENTO, *_CICLO * 3, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C2_ADDITIONAL_PLANNING, *_CICLO, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C3_FINAL_ANSWER]
    # Estado vigente: só a referência estruturada aprovada substituiu T3; T1/T2 continuam vigentes.
    livro = cenario.results_ledger
    assert livro.status_of(task_id="T3") is ResultStatusEnum.SUPERSEDED and livro.superseded_by(task_id="T3") == "T4"
    assert livro.current_task_ids() == ("T1", "T2", "T4")
    # Memória vigente: sai só o fato exclusivo de T3; dados de A.3 e o fato com fonte independente ficam.
    memoria = [learning.content for learning in cenario.learnings_memory.all()]
    assert _C_L3 not in memoria
    assert all(fato in memoria for fato in (*_COLISOES_A3, _C_L1, _C_L2, _C_LDV, _C_L4))
    # Auditoria: a conclusão antiga continua nas mensagens e a revisão vira registro estruturado.
    assert any(_C_T3 in mensagem.content for mensagem in cenario.session.messages
               if mensagem.phase is Phase.B1_TASK_RESOLUTION)
    [revisao] = cenario.session.result_revisions
    assert revisao.superseded_task_ids == ("T3",) and revisao.withdrawn_learnings == (_C_L3,)
    assert revisao.current_task_ids == ("T1", "T2", "T4") and revisao.reason == _C_MOTIVO
    armazenamento = [m.content for m in cenario.session.messages if m.phase is Phase.B3_RESULT_STORAGE]
    assert "Superseded results: `T3`." in armazenamento[-1]
    # A nova C.1 e C.3 recebem só os vigentes; C.3 não recebe registro de revisão nem o fato retirado.
    segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2", "T4"]
    assert "superseded by `T4`" in _area(segunda_c1, "Revision record") and _C_T3 not in segunda_c1
    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    assert _C_T3 not in c3 and _C_L3 not in c3 and "## Revision record" not in c3
    _concluida(cenario, eventos, final)

    # Consulta e exportação levam a revisão; uma sessão antiga, sem a chave, é lida sem revisões.
    mapper = SessionDocumentMapper()
    documento = mapper.to_document(session=cenario.session)
    assert documento["result_revisions"][0]["superseded_task_ids"] == ["T3"]
    assert mapper.from_document(document=documento).result_revisions == cenario.session.result_revisions
    antigo = {chave: valor for chave, valor in documento.items() if chave != "result_revisions"}
    assert mapper.from_document(document=antigo).result_revisions == []
    erro = BenchmarkRalphError(
        question_id="COLISOES", expected_alternative="A", question=questao("COLISOES"), session=cenario.session,
        outcome=desfecho(mode=BenchmarkInferenceModeEnum.RALPH, correto=False, session_id=cenario.session.id),
    )
    arquivo = BenchmarkRalphErrorsArchiveBuilder(session_mapper=mapper).build("bench_07", [erro])
    with zipfile.ZipFile(io.BytesIO(arquivo.content)) as zip_:
        exportada = json.loads(zip_.read("questao-COLISOES/execucao-ralph-loop.json").decode("utf-8"))
    assert exportada["session"]["result_revisions"][0]["withdrawn_learnings"] == [_C_L3]


async def test_revisao_confirmatoria_nao_substitui_por_recencia_e_e_registrada_para_c1() -> None:
    hipotese = ("MARCA_HIP: sob a hipótese explícita de contato três vezes mais longo nos pneus, a força média nos "
                "pneus seria menor que nos blocos.")
    l_hipotese = "Com contato três vezes mais longo nos pneus (hipótese), a força média nos pneus seria a menor."
    confirmacao = "As afirmações tratam de intervalos diferentes; a hipótese de T3 é explícita e não contradiz T1."
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(hipotese, l_hipotese),
        _plano(_revisora(motivo="T3 parece contradizer T1 sobre a força média; verificar as condições de T3.")),
        _resolucao("T4", "MARCA_CONF: T3 usa um intervalo três vezes maior, declarado como hipótese; sob o mesmo "
                   "intervalo vale T1. Não há contradição.", ("T3", "confirmed", confirmacao)),
        _local("T4", revisao=True),
        _notas(),
        _global("T3 e T1 tratam de hipóteses diferentes, como a revisão confirmada explica."),
        _final("Com o mesmo intervalo, a força média é maior nos pneus e a dissipação é maior nos blocos."),
    ])

    eventos = await cenario.run(question=_pergunta("confirmatory_review"))

    livro = cenario.results_ledger
    assert livro.status_of(task_id="T3") is ResultStatusEnum.CURRENT and livro.superseded() == ()
    assert livro.current_task_ids() == ("T1", "T2", "T3", "T4")
    memoria = [learning.content for learning in cenario.learnings_memory.all()]
    assert all(fato in memoria for fato in (*_COLISOES_A3, _C_L1, _C_L2, _C_LDV, l_hipotese))
    [revisao] = cenario.session.result_revisions
    assert revisao.confirmed_task_ids == ("T3",) and revisao.superseded_task_ids == ()
    assert revisao.withdrawn_learnings == () and revisao.restored_learnings == ()
    # A confirmação aprovada aparece no registro que C.1 recebe: o resultado continua vigente por ela,
    # não pela ordem; o registro não pode dizer que nada foi revisado.
    registro = _area(_prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1], "Revision record")
    assert "`T3`" in registro and "confirmed by `T4`" in registro and confirmacao in registro
    assert _SEM_REVISOES not in registro
    assert _blocos(_area(_c3_recebe_exatamente_a_ultima_c1(cenario), "Stored results")) == ["T1", "T2", "T3", "T4"]
    _concluida(cenario, eventos, "Com o mesmo intervalo, a força média é maior nos pneus e a dissipação é maior "
                                 "nos blocos.")


async def test_revisao_rejeitada_ate_esgotar_as_tentativas_nao_muda_estado_e_contabiliza_tudo() -> None:
    proposta = _resolucao("T4", "MARCA_REJ: T3 está errado por ser anterior.", ("T3", "superseded", "mais recente"))
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(), _plano(_revisora()),
        proposta, _local("T4", revisao=False), proposta, _local("T4", revisao=False),
        proposta, _local("T4", revisao=False),
    ])

    with pytest.raises(ExecutionInterruptedError):
        await cenario.run(question=_pergunta("collisions_revision"))

    assert cenario.results_ledger.status_of(task_id="T3") is ResultStatusEnum.CURRENT
    assert cenario.results_ledger.current_task_ids() == ("T1", "T2", "T3")
    assert cenario.session.result_revisions == []
    assert _C_L3 in [learning.content for learning in cenario.learnings_memory.all()]
    falha = cenario.session.failure
    assert falha.reason is SessionFailureReasonEnum.RESOURCE_LIMIT and falha.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert falha.task_id == "T4" and cenario.session.final_answer is None
    assert Phase.C3_FINAL_ANSWER not in _fases(cenario)
    tentativas = [i for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION and i.task_id == "T4"]
    assert [i.temperature for i in tentativas] == [cenario.temperature, 1.0, 1.0]
    assert len({i.context_id for i in tentativas}) == 3
    _contabilizacao_integral(cenario)


async def test_recuperacao_de_c2_com_referencia_invalida_corrige_a_referencia_sem_abandonar_a_investigacao() -> None:
    recusada = _plano(_revisora(alvos=("T9",)))
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(), recusada, _plano(_revisora()),
        _resolucao("T4", _C_T4, ("T3", "superseded", "T3 inverteu o impulso.")), _local("T4", revisao=True),
        _notas(_C_L4), _global(), _final("ok"),
    ])

    eventos = await cenario.run(question=_pergunta("collisions_revision"))

    original, recuperacao = [i for i in cenario.session.invocations if i.phase is Phase.C2_ADDITIONAL_PLANNING]
    assert original.output_diagnostic.problem.code is OutputProblemCodeEnum.TASK_REFERENCES
    assert recuperacao.recovers_invocation_id == original.id
    indice = cenario.session.invocations.index(recuperacao)
    template_c2, recusa_na_janela, correcao = cenario.llm.texts_of(indice)
    assert recusa_na_janela == recusada and "{{" not in template_c2
    assert "does not exist in the session" in correcao and "### Planning coverage" in correcao
    normalizada = _sem_espacos(correcao)
    assert "`review` or `depends_on`" in normalizada
    assert "do not drop the targeted investigation of a flagged defect" in normalizada
    assert "current approved results" in normalizada
    # Nada do lote recusado entrou na fila ou no livro; a revisão aprovada vem do lote corrigido.
    assert cenario.task_queue.known_task_ids() == frozenset({"T1", "T2", "T3", "T4"})
    assert [r.superseded_task_ids for r in cenario.session.result_revisions] == [("T3",)]
    _concluida(cenario, eventos, "ok")


@pytest.mark.parametrize("respostas_extras,revisao_aplicada", [(0, False), (3, True)],
                         ids=["durante_a_revisora", "depois_da_revisao_aplicada"])
async def test_cancelamento_propaga_sem_sintese_e_sem_chamada_fora_da_contabilizacao(
    respostas_extras: int, revisao_aplicada: bool,
) -> None:
    roteiro = [*_colisoes_ate_a_contradicao(), _plano(_revisora()),
               _resolucao("T4", _C_T4, ("T3", "superseded", "T3 inverteu o impulso.")), _local("T4", revisao=True),
               _notas(_C_L4)][:15 + respostas_extras]
    enviada = asyncio.Event()

    class _LLMBloqueado(ScriptedLLMCompletions):
        async def send_conversation(self, **kwargs):
            if not self.responses:
                self.conversations.append(list(kwargs["conversation"]))
                enviada.set()
                await asyncio.Event().wait()
            return await super().send_conversation(**kwargs)

    cenario = _cenario([], llm=_LLMBloqueado(responses=roteiro))
    execucao = asyncio.create_task(cenario.run(question=_pergunta("collisions_revision")))
    await asyncio.wait_for(enviada.wait(), timeout=2)
    execucao.cancel("cancelamento controlado")
    with pytest.raises(asyncio.CancelledError):
        await execucao

    invocacoes = cenario.session.invocations
    assert cenario.session.totals.total_llm_calls == len(invocacoes) == cenario.llm.call_count
    assert [i.outcome for i in invocacoes[:-1]] == [InvocationOutcomeEnum.SUCCESS] * (len(invocacoes) - 1)
    assert invocacoes[-1].outcome is InvocationOutcomeEnum.STARTED
    assert Phase.C3_FINAL_ANSWER not in _fases(cenario) and cenario.session.final_answer is None
    status_t3 = ResultStatusEnum.SUPERSEDED if revisao_aplicada else ResultStatusEnum.CURRENT
    assert cenario.results_ledger.status_of(task_id="T3") is status_t3
    assert [r.superseded_task_ids for r in cenario.session.result_revisions] == ([("T3",)] if revisao_aplicada else [])


# ── Tacho: planejamento sem conclusão prescrita ──────────────────────────────

_TACHO_A3 = [
    "Vapor d'água entra na camisa do tacho a 120 °C e sai como água líquida a 100 °C.",
    "O produto no interior do tacho aquece e parte da sua água evapora.",
    "Pedido: explicar de onde vem a energia que aquece o produto e qual efeito essa energia produz no produto.",
]


async def test_tacho_planejamento_separa_origem_e_efeito_sem_transformar_hipotese_em_obrigacao() -> None:
    pergunta = _pergunta("steam_kettle_planning")
    l_origem = ("A energia que aquece o produto provém do vapor na camisa: resfriamento de 120 °C a 100 °C e "
                "mudança de fase liberam calor.")
    cenario = _cenario([
        _criterios("Explicar a origem da energia e o efeito no produto, com justificativa.", "Responder em português."),
        _plano(_tarefa("T1", "Origem da energia transferida ao produto",
                       "Com os processos fornecidos (vapor que entra na camisa a 120 °C e sai líquido a 100 °C; "
                       "produto que aquece e tem parte da água evaporada), determine e justifique de qual processo "
                       "provém a energia transferida ao produto. A análise restringe-se à origem da energia."),
               _tarefa("T2", "Efeito da energia no produto",
                       "Usando a origem da energia registrada em Key Learnings, determine e justifique o efeito da "
                       "energia recebida pelo produto. A análise restringe-se ao efeito no produto.",
                       depends_on=["T1"])),
        plano_aprovado(), _notas(*_TACHO_A3),
        *_tarefa_executada("T1", "MARCA_ORIGEM: análise completa do balanço na camisa (resolução extensa).", l_origem),
        *_tarefa_executada("T2", "MARCA_EFEITO: o produto aquece e parte da sua água evapora.",
                           "A energia recebida pelo produto o aquece e evapora parte da sua água."),
        _global(), _final("A energia vem do vapor na camisa; no produto, aquece e evapora parte da água."),
    ])

    eventos = await cenario.run(question=pergunta)

    a2 = _sem_espacos(_prompts(cenario, Phase.A2_TASK_DECOMPOSITION)[0])
    # A.2 simplificada mantém a regra geral; a auditoria de neutralidade é da rubrica fixa de A.3.
    assert "must remain open, including in titles and criteria" in a2
    assert "Never present a convenient condition as a supplied fact" in a2
    a3 = _sem_espacos(_prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION)[0])
    assert "**Neutrality:**" in a3 and "**Applicability:**" in a3 and pergunta in _prompts(
        cenario, Phase.A3_DECOMPOSITION_VALIDATION)[0]
    _harness_nao_injeta(cenario, pergunta, "condens", "MARCA_ORIGEM")
    b1_t1, b1_t2 = _prompts(cenario, Phase.B1_TASK_RESOLUTION)
    assert "condens" not in _area(b1_t1, "Acceptance criteria for this task")
    assert all(nota in _area(b1_t1, "Key Learnings") for nota in _TACHO_A3)
    # A tarefa dependente recebe a conclusão anterior pela memória, nunca a resolução completa.
    assert l_origem in _area(b1_t2, "Key Learnings") and "MARCA_ORIGEM" not in b1_t2
    assert cenario.results_ledger.get(task_id="T2").depends_on == ("T1",)
    b2 = _sem_espacos(_prompts(cenario, Phase.B2_TASK_VERIFICATION)[0])
    assert "A planning anticipation is not the standard of correctness" in b2
    _c3_recebe_exatamente_a_ultima_c1(cenario)
    _concluida(cenario, eventos, "A energia vem do vapor na camisa; no produto, aquece e evapora parte da água.")


# ── Microscópio: referências, grandeza linear e retentativa isolada ─────────

_MICRO_A3 = [
    "Objetiva: distância focal 5 mm; o objeto está a 5,2 mm da objetiva.",
    "Ocular: distância focal 70 mm.",
    "Separação entre a objetiva e a ocular: 190 mm.",
    "Pedido: posição da imagem final em relação à ocular e aumento linear total.",
]
_MICRO_ANGULAR = "MARCA_ANGULAR: aumento angular 250/70 ≈ 3,6; total ≈ 25 × 3,6 ≈ 89, imagem final no infinito."
_MICRO_LINEAR = "MARCA_LINEAR: m = m1·m2 = (−25)·(7) = −175; módulo do aumento linear total 175."
_MICRO_VEREDITO = ("O pedido é aumento linear; o resultado usou aumento angular e imagem no infinito, contrariando a "
                   "imagem final a −420 mm da ocular registrada.")


async def test_microscopio_preserva_referencias_e_grandeza_linear_com_retentativa_em_janela_nova() -> None:
    l_obj = ("A imagem formada pela objetiva está a 130 mm da objetiva, real, com aumento linear m1 = −25: "
             "1/f = 1/p + 1/p'.")
    l_ocu = "O objeto da ocular está a 60 mm da ocular e a imagem final a −420 mm da ocular (virtual): m2 = 7."
    l_tot = "O aumento linear total do microscópio tem módulo 175: produto dos aumentos lineares 25 e 7."
    cenario = _cenario([
        _criterios("Determinar a posição da imagem final em relação à ocular e o aumento linear total.",
                   "Responder em português."),
        _plano(_tarefa("T1", "Imagem da objetiva", "Determine a posição da imagem formada pela objetiva em relação "
                       "à objetiva e seu aumento linear (focal 5 mm, objeto a 5,2 mm da objetiva)."),
               _tarefa("T2", "Imagem final pela ocular", "Com a imagem da objetiva registrada em Key Learnings e a "
                       "separação de 190 mm, determine a posição da imagem final em relação à ocular (focal 70 mm).",
                       depends_on=["T1"]),
               _tarefa("T3", "Aumento linear total", "Determine o aumento linear total a partir dos aumentos "
                       "registrados em Key Learnings.", depends_on=["T1", "T2"])),
        plano_aprovado(), _notas(*_MICRO_A3),
        *_tarefa_executada("T1", "MARCA_OBJ: 1/p' = 1/5 − 1/5,2 ⇒ p' = 130 mm da objetiva; m1 = −25.", l_obj),
        *_tarefa_executada("T2", "MARCA_OCU: p = 190 − 130 = 60 mm da ocular; p'' = −420 mm; m2 = 7.", l_ocu),
        _resolucao("T3", _MICRO_ANGULAR), _local("T3", aprovado=False, justificativa=_MICRO_VEREDITO),
        _resolucao("T3", _MICRO_LINEAR), _local("T3"), _notas(l_tot),
        _global("T2 e T3 determinam a posição e o aumento linear pedidos."),
        _final("Imagem final virtual a 420 mm da ocular, do lado do objeto; aumento linear total de módulo 175."),
    ])

    eventos = await cenario.run(question=_pergunta("microscope_quantities"))

    primeira, retentativa = [i for i in cenario.session.invocations
                             if i.phase is Phase.B1_TASK_RESOLUTION and i.task_id == "T3"]
    assert primeira.context_id != retentativa.context_id and retentativa.temperature == 1.0
    indice = cenario.session.invocations.index(retentativa)
    [prompt_retentativa] = cenario.llm.texts_of(indice)
    anteriores = _area(prompt_retentativa, "Previous attempts at this task")
    assert _MICRO_ANGULAR in anteriores and _MICRO_VEREDITO in anteriores and "`T3-AC1`" in anteriores
    # B.4 recebe o histórico completo; memória, C.1 e C.3 recebem só o resultado aprovado.
    b4_t3 = _prompts(cenario, Phase.B4_LEARNINGS_EXTRACTION, "T3")[0]
    assert _MICRO_ANGULAR in _area(b4_t3, "Task history") and _MICRO_LINEAR in _area(b4_t3, "Approved result")
    assert cenario.results_ledger.get(task_id="T3").content == _MICRO_LINEAR
    memoria = cenario.learnings_memory.render()
    assert "MARCA_ANGULAR" not in memoria and "infinito" not in memoria
    for fase in (Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER):
        prompt = _prompts(cenario, fase)[-1]
        assert _MICRO_LINEAR in _area(prompt, "Stored results") and "MARCA_ANGULAR" not in prompt
        # Cada distância chega com o seu referente, sem troca entre objetiva e ocular.
        assert all(nota in _area(prompt, "Key Learnings") for nota in (*_MICRO_A3, l_obj, l_ocu, l_tot))
    a2 = _sem_espacos(_prompts(cenario, Phase.A2_TASK_DECOMPOSITION)[0])
    # A referência de cada distância é regra de geração de A.2 e item de fidelidade da rubrica de A.3.
    assert "keeping each value attached to its referent" in a2
    a3 = _sem_espacos(_prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION)[0])
    assert "**Fidelity:**" in a3 and "changed referent" in a3
    _c3_recebe_exatamente_a_ultima_c1(cenario)
    _concluida(cenario, eventos, "Imagem final virtual a 420 mm da ocular, do lado do objeto; aumento linear total "
                                 "de módulo 175.")


# ── Geografia: conteúdo implícito com o mesmo padrão para as opções ─────────


async def test_geografia_retentativa_explicita_o_vinculo_sem_trocar_a_conclusao_sustentada() -> None:
    primeira = "MARCA_GEO_1: D, pois o rito de pedir chuva expressa a relação com o ciclo das chuvas; A, B, C e E não."
    veredito = "Falta explicitar o vínculo entre pedir chuva antes da colheita e o ciclo das chuvas."
    segunda = ("MARCA_GEO_2: D. Pedir chuva antes da colheita vincula o rito ao ciclo das chuvas e da colheita; "
               "A, B, C e E não são sustentadas pelo trecho.")
    cenario = _cenario([
        _criterios("Indicar a alternativa que interpreta o trecho, com fundamento.", "Responder em português."),
        _plano(_tarefa("T1", "Interpretar o trecho", "Compare as alternativas com o trecho e escolha a mais "
                       "sustentada, por eliminação, aplicando o mesmo padrão a todas.")),
        plano_aprovado(),
        _notas("Trecho: \"Na comunidade, os moradores se reúnem antes da colheita para um rito em que pedem chuva.\"",
               "Alternativas copiadas literalmente: A) A comunidade depende de irrigação artificial. B) O trecho "
               "descreve um conflito por terras. C) O rito é uma atividade comercial. D) O rito expressa a relação "
               "da comunidade com o ciclo das chuvas e da colheita. E) A colheita ocorre na estação seca."),
        _resolucao("T1", primeira), _local("T1", aprovado=False, justificativa=veredito),
        _resolucao("T1", segunda), _local("T1"), _notas("A alternativa D interpreta o trecho: o rito liga a "
                                                        "comunidade ao ciclo das chuvas e da colheita."),
        _global(), _final("D"),
    ])

    eventos = await cenario.run(question=_pergunta("geography_interpretation"))

    retentativa = _sem_espacos(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[1])
    assert primeira in retentativa and veredito in retentativa
    assert "Keep the conclusions that the verdict did not refute" in retentativa
    assert "make the supporting link explicit instead of switching to another conclusion" in retentativa
    for prompt in _prompts(cenario, Phase.B2_TASK_VERIFICATION):
        assert "Apply the same standard of implicit content to every option compared" in _sem_espacos(prompt)
    assert cenario.results_ledger.get(task_id="T1").content == segunda
    _c3_recebe_exatamente_a_ultima_c1(cenario)
    _concluida(cenario, eventos, "D")


# ── Probabilidade: revisão pelas fases previstas, nunca na síntese ──────────


async def test_probabilidade_revisao_percorre_as_fases_e_nao_acontece_na_sintese() -> None:
    l_t1 = "A probabilidade de A vencer a série dado que venceu a primeira é 21/64: soma por duração vezes 1/2."
    l_t2 = "A alternativa mais próxima de 21/64 é A) 11/32: diferença de cerca de 0,016."
    l_t3 = "Dada a vitória na primeira partida, A vence a série com probabilidade 42/64 = 21/32: soma por duração."
    cenario = _cenario([
        _criterios("Determinar a probabilidade condicionada e indicar a alternativa sustentada.",
                   "Responder em português."),
        _plano(_tarefa("T1", "Probabilidade condicionada", "Calcule a probabilidade de A vencer a série melhor de "
                       "sete, dado que A venceu a primeira partida, com partidas independentes de probabilidade 1/2."),
               _tarefa("T2", "Escolha da alternativa", "Com a probabilidade registrada em Key Learnings, escolha a "
                       "alternativa sustentada, justificando.", depends_on=["T1"])),
        plano_aprovado(),
        _notas("Série melhor de sete; partidas independentes; cada equipe vence uma partida com probabilidade 1/2.",
               "Condição dada: a equipe A venceu a primeira partida.",
               "Alternativas: A) 11/32, B) 35/64, C) 21/32, D) 1/2, E) 11/16."),
        *_tarefa_executada("T1", "MARCA_P1: 1/8 + 3/16 + 6/32 + 10/64 = 42/64; multiplicando pela primeira vitória "
                           "(1/2), 21/64.", l_t1),
        *_tarefa_executada("T2", "MARCA_P2: 21/64 ≈ 0,328; A) 11/32 ≈ 0,344 é o melhor ajuste.", l_t2),
        _global("T1 multiplica por 1/2 a primeira vitória, já dada pela condição (dupla contagem); a escolha de T2 "
                "apoia-se nesse valor. Investigar o condicionamento de T1 e a escolha de T2.", aprovado=False),
        _plano(_tarefa("T3", "Investigar o condicionamento", "Refaça a probabilidade condicionada com a condição "
                       "aplicada uma única vez e explique quais afirmações registradas ela confirma ou corrige.",
                       review={"task_ids": ["T1", "T2"],
                               "reason": "Dupla contagem da condição em T1; a escolha de T2 usa esse valor."})),
        _resolucao("T3", "MARCA_P3: dada a primeira vitória, faltam três vitórias de A antes de quatro de B: "
                   "1/8 + 3/16 + 6/32 + 10/64 = 42/64 = 21/32, logo C. O fator 1/2 contava de novo a primeira "
                   "partida; a escolha de A) 11/32 decorria desse valor.",
                   ("T1", "superseded", "O fator 1/2 conta de novo a partida já dada pela condição."),
                   ("T2", "superseded", "A escolha usava o valor com a dupla contagem.")),
        _local("T3", revisao=True), _notas(l_t3),
        _global("T3 determina 42/64 = 21/32 com a condição aplicada uma vez; C é sustentada."),
        _final("C) 21/32"),
    ])

    eventos = await cenario.run(question=_pergunta("probability_conditioning"))

    assert _fases(cenario) == [*_PLANEJAMENTO, *_CICLO * 2, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C2_ADDITIONAL_PLANNING, *_CICLO, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C3_FINAL_ANSWER]
    [revisao] = cenario.session.result_revisions
    assert revisao.superseded_task_ids == ("T1", "T2") and set(revisao.withdrawn_learnings) == {l_t1, l_t2}
    assert cenario.results_ledger.current_task_ids() == ("T3",)
    # A síntese não recebe o valor errado em lugar nenhum: nem resultado, nem memória, nem registro.
    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    assert _blocos(_area(c3, "Stored results")) == ["T3"]
    assert "21/64" not in c3 and "MARCA_P1" not in c3 and "MARCA_P2" not in c3
    assert "Do not repair, recalculate or reconcile results here" in _sem_espacos(c3)
    _concluida(cenario, eventos, "C) 21/32")


# ── Contagem: definição preservada e igualdade falsa investigada ────────────

_LISTAS_A3 = [
    "Listas ordenadas de cinco números inteiros positivos.",
    "Condições simultâneas: mediana, média, amplitude e moda todas iguais a 23.",
    "Alternativas: A) 8, B) 12, C) 36, D) 44, E) 47.",
    "Pedido: quantidade de listas que satisfazem simultaneamente as condições.",
]


async def test_contagem_preserva_definicao_e_igualdade_falsa_vira_investigacao() -> None:
    l_errado = "Há 47 listas que satisfazem as condições, o que corresponde exatamente a 44: contagem por casos."
    igualdade = "T1 afirma que 47 corresponde exatamente a 44: igualdade falsa. Investigar a contagem e as condições."
    cenario = _cenario([
        _criterios("Determinar a quantidade de listas e indicar a alternativa sustentada.", "Responder em português."),
        _plano(_tarefa("T1", "Contar as listas", "Conte as listas ordenadas de cinco inteiros positivos com mediana, "
                       "média, amplitude e moda iguais a 23, justificando a contagem por casos.")),
        plano_aprovado(), _notas(*_LISTAS_A3),
        *_tarefa_executada("T1", "MARCA_L47: 47 listas, o que corresponde exatamente à alternativa D) 44.", l_errado),
        _global(igualdade, aprovado=False),
        _plano(_tarefa("T2", "Investigar a contagem", "Refaça a contagem com todas as condições simultâneas e "
                       "explique qual afirmação registrada ela confirma ou corrige.",
                       review={"task_ids": ["T1"], "reason": "Igualdade falsa entre 47 e 44 e contagem a verificar."})),
        _resolucao("T2", "MARCA_L8: com moda 23 e as demais condições, há 8 listas; T1 admitiu listas sem moda 23.",
                   ("T1", "superseded", "T1 contou listas sem moda 23 e afirmou 47 = 44.")),
        _local("T2", revisao=True), _notas("Há 8 listas com moda 23 que satisfazem todas as condições."),
        _global("T2 determina 8 com as condições simultâneas; A é sustentada."), _final("A"),
    ])

    eventos = await cenario.run(question=_pergunta("integer_lists_count"))

    # A definição e as condições chegam íntegras, literalmente, a todas as fases que resolvem ou verificam.
    for fase in (*_CICLO, Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, Phase.C3_FINAL_ANSWER):
        for prompt in _prompts(cenario, fase):
            assert all(nota in _area(prompt, "Key Learnings") for nota in _LISTAS_A3), fase
    c2 = _prompts(cenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert igualdade in _area(c2, "Global verification feedback")
    assert _pergunta("integer_lists_count") in _area(c2, "Original Prompt")
    c1 = _sem_espacos(_prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[0])
    assert "never write that they correspond exactly" in c1
    assert "If the results had instead selected 8 cm explicitly as the best fit for 8.4 cm" in c1
    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    assert l_errado not in c3 and "MARCA_L47" not in c3
    _concluida(cenario, eventos, "A")


# ── Química: tabela e alternativas preservadas para o pareamento literal ────


async def test_quimica_tabela_e_alternativas_chegam_a_c1_e_c3_para_pareamento_literal() -> None:
    tabela = ("Testes da estação, código e parâmetro: 1-Cálcio, 2-Cloreto, 3-Turbidez, 4-Coliformes totais, "
              "5-Sólidos sedimentáveis.")
    alternativas = "Alternativas copiadas literalmente: A) 1, B) 2, C) 3, D) 4, E) 5."
    cenario = _cenario([
        _criterios("Indicar a alternativa do teste que identifica a espécie, com fundamento.",
                   "Responder em português."),
        _plano(_tarefa("T1", "Identificar a espécie e o teste", "Identifique a espécie que forma precipitado "
                       "branco com oxalato de amônio e o teste correspondente da tabela, justificando.")),
        plano_aprovado(),
        _notas(tabela, alternativas, "Observação: a amostra forma precipitado branco com oxalato de amônio."),
        *_tarefa_executada("T1", "MARCA_CA: o precipitado branco com oxalato indica cálcio; teste 1 — Cálcio.",
                           "O teste 1 (Cálcio) identifica a espécie: oxalato de cálcio é precipitado branco."),
        _global("T1 determina o teste 1; as notas copiam que a alternativa cujo texto é 1 é A."), _final("A"),
    ])

    eventos = await cenario.run(question=_pergunta("chemistry_table"))

    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    for prompt in (_prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[0], c3):
        assert tabela in _area(prompt, "Key Learnings") and alternativas in _area(prompt, "Key Learnings")
    assert "## Fidelity check before answering" in c3
    assert "Literal pairing is not analytical selection" in _sem_espacos(c3)
    _concluida(cenario, eventos, "A")


# ── Aproximação legítima e pergunta aberta ──────────────────────────────────


async def test_aproximacao_legitima_e_aceita_sem_c2_e_apresentada_como_melhor_ajuste() -> None:
    estimativa = ("MARCA_AJUSTE: t = 2.000 L / 37 L/min ≈ 54 min; C) 55 min é o melhor ajuste (diferença de cerca "
                  "de 1 min, dentro da precisão da vazão aproximada); não há igualdade.")
    final = "C) 55 min — melhor ajuste para o tempo estimado de cerca de 54 min."
    cenario = _cenario([
        _criterios("Determinar o tempo aproximado e indicar a alternativa sustentada.", "Responder em português."),
        _plano(_tarefa("T1", "Estimar o tempo de enchimento", "Estime o tempo para encher 2.000 L com vazão "
                       "aproximada de 37 L/min e escolha a alternativa por melhor ajuste, justificando.")),
        plano_aprovado(),
        _notas("Caixa d'água: 2.000 L.", "Vazão da bomba: aproximadamente 37 L/min.",
               "Alternativas: A) 30 min, B) 45 min, C) 55 min, D) 70 min, E) 90 min."),
        *_tarefa_executada("T1", estimativa, "O tempo de enchimento é ≈ 54 min e C) 55 min é o melhor ajuste."),
        _global("A escolha de C é fundamentada por comparação e precisão; a diferença não é lacuna."), _final(final),
    ])

    eventos = await cenario.run(question=_pergunta("legitimate_approximation"))

    assert Phase.C2_ADDITIONAL_PLANNING not in _fases(cenario)
    c1 = _sem_espacos(_prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[0])
    assert "a numerical difference alone is not a defect and does not call for extra proof" in c1
    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    assert estimativa in _area(c3, "Stored results")
    assert "never turn a best fit into an exact equality" in _sem_espacos(c3)
    _concluida(cenario, eventos, final)


async def test_pergunta_aberta_preserva_siglas_nomes_unidades_e_condicoes_sem_alternativas() -> None:
    pergunta = _pergunta("open_question")
    notas = ["SLA significa Acordo de Nível de Serviço (definição fornecida no contrato).",
             "Bomba Alfa: 12 L/min. Bomba Alfa II: 8 L/min.",
             "Condição: vazão constante.",
             "Pedido: volume, em litros, entregue pela Bomba Alfa em 3 minutos, com breve explicação."]
    final = "A Bomba Alfa entrega 36 L em 3 minutos, mantida a vazão constante: 12 L/min × 3 min."
    cenario = _cenario([
        _criterios("Determinar o volume, em litros, da Bomba Alfa em 3 minutos, com breve explicação.",
                   "Responder em português."),
        _plano(_tarefa("T1", "Volume da Bomba Alfa", "Determine o volume entregue pela Bomba Alfa (12 L/min) em "
                       "3 minutos, sob vazão constante, explicando.")),
        plano_aprovado(), _notas(*notas),
        *_tarefa_executada("T1", "MARCA_VOL: V = 12 L/min × 3 min = 36 L (Bomba Alfa, vazão constante).",
                           "O volume entregue pela Bomba Alfa em 3 min é 36 L sob vazão constante: V = vazão × tempo."),
        _global(), _final(final),
    ])

    eventos = await cenario.run(question=pergunta)

    assert all(pergunta in _prompts(cenario, fase)[0] for fase in _PLANEJAMENTO)
    for fase in (*_CICLO, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER):
        for prompt in _prompts(cenario, fase):
            area = _area(prompt, "Key Learnings")
            assert all(nota in area for nota in notas), fase
            assert "Alternativas" not in area and "RESPOSTA_FINAL" not in area and "FINAL_ANSWER" not in area
    assert cenario.session.benchmark_details.is_banchmark is False
    c3 = _c3_recebe_exatamente_a_ultima_c1(cenario)
    assert "MARCA_VOL" in _area(c3, "Stored results")
    _concluida(cenario, eventos, final)


async def test_confirmacao_vencida_por_nova_evidencia_sai_do_registro_de_confirmados() -> None:
    hipotese = "MARCA_HIP2: sob contato mais longo nos pneus, a força média nos pneus seria a menor."
    novo_motivo = "Nova evidência: T3 usa um intervalo que contraria o mesmo intervalo de colisão dado no pedido."
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(hipotese, "Com contato mais longo nos pneus (hipótese), a força seria menor."),
        _plano(_revisora(motivo="T3 parece contradizer T1; verificar as condições de T3.")),
        _resolucao("T4", "MARCA_CONF2: T3 declara hipótese própria.", ("T3", "confirmed", "Hipótese explícita.")),
        _local("T4", revisao=True), _notas(),
        _global(novo_motivo, aprovado=False),
        _plano(_revisora(task_id="T5", motivo=novo_motivo)),
        _resolucao("T5", _C_T4, ("T3", "superseded", "O pedido fixa o mesmo intervalo; a hipótese de T3 o contraria.")),
        _local("T5", revisao=True), _notas(_C_L4),
        _global(), _final("ok"),
    ])

    eventos = await cenario.run(question=_pergunta("confirmatory_review"))

    segunda_c1, terceira_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1:]
    assert "confirmed by `T4`" in _area(segunda_c1, "Revision record")
    registro = _area(terceira_c1, "Revision record")
    assert "superseded by `T5`" in registro and "confirmed by `T4`" not in registro
    c2 = _prompts(cenario, Phase.C2_ADDITIONAL_PLANNING)[1]
    assert "confirmed by `T4`" in _area(c2, "Revision record") and novo_motivo in c2
    assert [(r.confirmed_task_ids, r.superseded_task_ids) for r in cenario.session.result_revisions] == [
        (("T3",), ()), ((), ("T3",)),
    ]
    assert cenario.results_ledger.current_task_ids() == ("T1", "T2", "T4", "T5")
    _c3_recebe_exatamente_a_ultima_c1(cenario)
    _concluida(cenario, eventos, "ok")


async def test_orcamento_real_esgotado_depois_da_revisao_aplicada_encerra_sem_sintese_e_com_auditoria() -> None:
    orcamento = CostBudget(max_task_attempts=3, max_planning_attempts=5, max_additional_planning_rounds=2,
                           max_tasks_per_session=12,
                           max_llm_calls_per_session=17, session_token_budget=100_000,
                           final_answer_token_reserve=1_000, session_timeout_seconds=600)
    cenario = _cenario([
        *_colisoes_ate_a_contradicao(), _plano(_revisora()),
        _resolucao("T4", _C_T4, ("T3", "superseded", "T3 inverteu o impulso.")), _local("T4", revisao=True),
    ], budget=orcamento)

    with pytest.raises(Exception):
        await cenario.run(question=_pergunta("collisions_revision"))

    # A 18ª chamada (B.4 da revisora) é negada antes do envio. O teto do cenário acompanha a chamada de A.3
    # acrescentada ao planejamento, para continuar negando exatamente o mesmo ponto do fluxo.
    falha = cenario.session.failure
    assert falha.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert falha.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION and falha.phase is Phase.B4_LEARNINGS_EXTRACTION
    assert cenario.llm.call_count == 17 and Phase.C3_FINAL_ANSWER not in _fases(cenario)
    assert cenario.session.final_answer is None
    # A revisão aprovada em B.2 e aplicada em B.3 permanece auditada; não houve nova C.1 nem síntese.
    assert [r.superseded_task_ids for r in cenario.session.result_revisions] == [("T3",)]
    assert cenario.results_ledger.current_task_ids() == ("T1", "T2", "T4")
    _contabilizacao_integral(cenario)
