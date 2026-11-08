"""Contratos dos prompts reais e transições; os vereditos do LLM são roteirizados.

Estes testes não medem a qualidade semântica de um modelo real. Exercitam renderização,
parser, fila, memória, persistência e isolamento com decisões representativas do contrato.
"""
import json
import logging
import re

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import plano_aprovado
from tests.doubles.ralph_scripts import aprendizados, relatorio, resposta_final


def _json(**value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _criteria(*descriptions: str) -> str:
    return _json(general_acceptance_criteria=[
        {"id": f"AC{index}", "description": text} for index, text in enumerate(descriptions, 1)
    ])


def _task(task_id: str, description: str, *criteria: str) -> str:
    return _json(tasks=[{
        "id": task_id, "title": description, "description": description,
        "acceptance_criteria": [
            {"id": f"{task_id}-AC{index}", "description": text} for index, text in enumerate(criteria, 1)
        ],
    }])


def _result(task_id: str, text: str) -> str:
    return _json(task_id=task_id, result=text, conclusion=text)


def _scenario(responses: list[str]) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(responses=responses, settings=settings, template_provider=FilePromptTemplateProvider(
        settings=settings, logger=logging.getLogger("test.scope.templates"),
    ))


def _prompts(scenario: RalphScenario, phase: Phase) -> list[str]:
    return [scenario.llm.texts_of(index)[0] for index, invocation in enumerate(scenario.session.invocations)
            if invocation.phase is phase]


def _area(prompt: str, heading: str) -> str:
    content = prompt.split(f"## {heading}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", content, maxsplit=1)[0].strip()


def _isolated_inputs(scenario: RalphScenario) -> None:
    isolated = {Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
                Phase.A4_PLANNING_LEARNINGS,
                Phase.B2_TASK_VERIFICATION, Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING,
                Phase.C3_FINAL_ANSWER}
    ids = []
    for index, invocation in enumerate(scenario.session.invocations):
        assert "{{" not in "\n".join(scenario.llm.texts_of(index))
        if invocation.phase in isolated:
            assert len(scenario.llm.conversations[index]) == 1
            ids.append(invocation.context_id)
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(("format_criterion", "final"), [
    ("Terminar com a linha RESPOSTA_FINAL: LETRA para a alternativa identificada.", "RESPOSTA_FINAL: C"),
    ("Responder apenas com a letra, sem explicação.", "C"),
])
async def test_conteudo_explicado_sem_linha_final_segue_de_c1_a_c3(format_criterion: str, final: str) -> None:
    content = "A alternativa C corresponde ao valor calculado: 6 g / 2 = 3 g. A e B não correspondem a 3 g."
    memory = "ANOTACAO_TRANSVERSAL: dados do enunciado."
    scenario = _scenario([
        _criteria("Identificar a alternativa sustentada pelo cálculo.", format_criterion),
        _task("T1", "Calcule 6 g / 2 e compare A) 1 g B) 2 g C) 3 g, explicando.", "Resultado explicado."),
        plano_aprovado(), aprendizados(memory), _result("T1", content), relatorio(("T1-AC1", True)), aprendizados(),
        relatorio(("AC1", True), ("AC2", True)), resposta_final(final),
    ])

    events = await scenario.run(question="Calcule 6 g / 2. A) 1 g B) 2 g C) 3 g. " + format_criterion)

    phases = [invocation.phase for invocation in scenario.session.invocations]
    assert phases[-2:] == [Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    assert Phase.C2_ADDITIONAL_PLANNING not in phases
    assert scenario.session.final_answer == final == events[-1].content
    _isolated_inputs(scenario)
    c1 = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0]
    c3 = _prompts(scenario, Phase.C3_FINAL_ANSWER)[0]
    assert _area(c1, "Stored results") == _area(c3, "Stored results")
    assert content in _area(c1, "Stored results")
    assert "RESPOSTA_FINAL:" not in _area(c1, "Stored results")
    for prompt in (c1, c3):
        assert memory in _area(prompt, "Key Learnings")
        assert memory not in _area(prompt, "Stored results")
        assert format_criterion in _area(prompt, "General acceptance criteria")
    assert "FINAL_ANSWER: C" in c1
    assert "joint analysis" in c1
    assert "optional justification" in _prompts(scenario, Phase.A1_GENERAL_CRITERIA)[0]
    assert "arbitrary line or word limits" in _prompts(scenario, Phase.A1_GENERAL_CRITERIA)[0]
    assert "without new analytical reasoning" in c3


async def test_analise_conjunta_ausente_exige_c2_e_resultado_explicado_antes_de_c3() -> None:
    content = "Primos: [2]; pares: [2, 4, 6]; maiores que 2: [4, 6]. Cada lista verifica uma condição."
    joint = "Interseção vazia: 2 não é maior que 2; 4 e 6 não são primos. Logo D) Nenhuma das anteriores."
    gap = "Sustentar a resposta com análise conjunta explícita das três condições."
    memory = "MEMORIA_NAO_E_RESULTADO: a interseção é vazia."
    scenario = _scenario([
        _criteria("Responder apenas com a letra.", gap),
        _task("T1", "Verifique separadamente primalidade, paridade e >2 em [2,4,6], explicando.",
              "Listas com explicação."),
        plano_aprovado(), aprendizados(memory), _result("T1", content), relatorio(("T1-AC1", True)), aprendizados(),
        relatorio(("AC1", True), ("AC2", False)),
        _task("T2", "Determine e explique a interseção de primos [2], pares [2,4,6] e >2 [4,6].",
              "Interseção correta e explicada.", "Não redigir a resposta final ao usuário."),
        _result("T2", joint), relatorio(("T2-AC1", True), ("T2-AC2", True)), aprendizados(),
        relatorio(("AC1", True), ("AC2", True)), resposta_final("D"),
    ])

    await scenario.run(question="Primo, par e >2 entre 2,4,6? D) NDA. Apenas a letra; análise conjunta explícita.")

    assert [i.phase for i in scenario.session.invocations][7:] == [
        Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING,
        Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
        Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER,
    ]
    _isolated_inputs(scenario)
    c2 = _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert gap in _area(c2, "General criteria not yet met")
    assert "Responder apenas com a letra." not in _area(c2, "General criteria not yet met")
    assert content in _area(c2, "Results already stored")
    assert "content gaps" in c2 and "FINAL_ANSWER: C" in c2
    b1 = _prompts(scenario, Phase.B1_TASK_RESOLUTION)
    assert "Interseção correta e explicada." in b1[1]
    assert "Listas com explicação." not in b1[1]
    b1_ids = [i.context_id for i in scenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION]
    assert len(set(b1_ids)) == 2
    first, second = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)
    assert joint not in _area(first, "Stored results")
    assert joint in _area(second, "Stored results")
    assert memory not in _area(second, "Stored results")
    assert _area(second, "Stored results") == _area(
        _prompts(scenario, Phase.C3_FINAL_ANSWER)[0], "Stored results",
    )
    assert scenario.session.final_answer == "D"


@pytest.mark.parametrize(("question", "inconsistent", "investigation", "corrected", "letter"), [
    (
        "A urna A tem P(preta)=20%. A urna B tem 4 pretas e P(preta)=25%. "
        "Quantas brancas adicionar para P(voucher)<=1%? A) 20 B) 60 C) 64 D) 68 E) 80.",
        "P(voucher)=0,20*4/(4+x)<=0,01; x>=76. Nenhuma alternativa corresponde ao mínimo 76.",
        "Investigue se o total inicial da urna B foi considerado na modelagem e determine "
        "o mínimo de brancas adicionais, explicando a correção e comparando com as opções.",
        "Correção de T1: 4/0,25=16 bolinhas iniciais, incluindo 12 brancas. "
        "O denominador 4+x estava incorreto: 0,20*4/(16+x)<=0,01 implica x>=64. "
        "O mínimo é 64, correspondente a C.",
        "C",
    ),
    (
        "Pacote básico: 2.000 gemas e 100.000 moedas. O especial terá 6.000 gemas a mais "
        "que dois básicos. Quantas moedas inserir para manter a proporção? "
        "A) 50.000 B) 100.000 C) 200.000 D) 300.000 E) 400.000.",
        "O especial tem 10.000 gemas e deve conter 500.000 moedas. "
        "Nenhuma alternativa corresponde ao total calculado.",
        "Investigue a diferença entre o total de moedas do especial e o acréscimo sobre "
        "o pacote básico, determinando a quantidade pedida e explicando a correção.",
        "Correção de T1: 500.000 é o total de moedas, mas falta determinar o acréscimo "
        "sobre as 100.000 do básico: 500.000-100.000=400.000 moedas adicionais, alternativa E.",
        "E",
    ),
], ids=["urnas_sem_bolinhas_iniciais", "moedas_total_em_vez_de_acrescimo"])
async def test_resultado_sem_alternativa_sustentada_encaminha_ac2_a_investigacao_em_c2(
    question: str, inconsistent: str, investigation: str, corrected: str, letter: str,
) -> None:
    selection = "Selecionar exatamente uma alternativa disponível, preservando sua letra original."
    final = f"RESPOSTA_FINAL: {letter}"
    scenario = _scenario([
        _criteria("Terminar com RESPOSTA_FINAL: LETRA.", selection),
        _task("T1", "Determine a quantidade pedida com explicação.", "Cálculo explicado."),
        plano_aprovado(), aprendizados(question),
        _result("T1", inconsistent), relatorio(("T1-AC1", True)), aprendizados(inconsistent),
        relatorio(("AC1", True), ("AC2", False)),
        _task("T2", investigation, "Investiga a incompatibilidade e explica a correção de T1."),
        _result("T2", corrected), relatorio(("T2-AC1", True)), aprendizados(corrected),
        relatorio(("AC1", True), ("AC2", True)), resposta_final(final),
    ])

    events = await scenario.run(question=question)

    assert [i.phase for i in scenario.session.invocations][7:] == [
        Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING,
        Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
        Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER,
    ]
    _isolated_inputs(scenario)
    c2 = _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert _area(c2, "General criteria not yet met") == f"- `AC2`: {selection}"
    assert _area(c2, "Original Prompt").endswith(f"\n\n{question}")
    assert inconsistent in _area(c2, "Results already stored")
    assert question in _area(c2, "Key Learnings")
    assert investigation in _area(_prompts(scenario, Phase.B1_TASK_RESOLUTION)[1], "Task")
    first, second = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)
    assert corrected not in _area(first, "Stored results")
    assert corrected in _area(second, "Stored results")
    assert corrected in _area(_prompts(scenario, Phase.C3_FINAL_ANSWER)[0], "Stored results")
    assert scenario.session.final_answer == final == events[-1].content


@pytest.mark.parametrize(("outside_scope", "scope_criterion"), [
    (False, "Não calcular a massa por colher."),
    (True, "Não calcular a massa por colher."),
    (True, "Não mencionar colheres."),
])
async def test_b2_distingue_mencao_contextual_de_calculo_fora_do_escopo(
    outside_scope: bool, scope_criterion: str,
) -> None:
    context = "O enunciado cita colheres; aqui calculo apenas a massa total: 2 g + 4 g = 6 g."
    overreach = context + " A massa por colher é 6 g / 2 = 3 g; a resposta final é C."
    rejected = overreach if "calcular" in scope_criterion else context
    approved = context if "calcular" in scope_criterion else "A massa total é 2 g + 4 g = 6 g."
    responses = [
        _criteria("Obter a massa total.", "Resposta objetiva."),
        _task("T1", "Calcule a massa total de 2 g + 4 g com explicação; o enunciado menciona colheres.",
              "Massa total correta e explicada.", scope_criterion),
        plano_aprovado(), aprendizados("Dado de contexto: duas colheres."),
        _result("T1", rejected if outside_scope else approved),
        relatorio(("T1-AC1", True), ("T1-AC2", not outside_scope)),
    ]
    if outside_scope:
        responses.extend([_result("T1", approved), relatorio(("T1-AC1", True), ("T1-AC2", True))])
    responses.extend([aprendizados(), relatorio(("AC1", True), ("AC2", True)), resposta_final("6 g")])
    scenario = _scenario(responses)

    await scenario.run(question="Some 2 g e 4 g. Contexto: duas colheres. Responda objetivamente.")

    _isolated_inputs(scenario)
    b2 = _prompts(scenario, Phase.B2_TASK_VERIFICATION)
    assert len(b2) == (2 if outside_scope else 1)
    for prompt in b2:
        assert scope_criterion in _area(prompt, "Acceptance criteria for this task")
        assert "Massa total correta e explicada." in _area(prompt, "Acceptance criteria for this task")
        assert "contextual reference" in prompt
        assert "Do not ignore, rewrite or waive" in prompt
    assert "do not mention spoons" in _prompts(scenario, Phase.A2_TASK_DECOMPOSITION)[0]
    stored = _area(_prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0], "Stored results")
    assert approved in stored and overreach not in stored
    if outside_scope:
        assert rejected not in stored
    b1_invocations = [i for i in scenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION]
    assert len({i.context_id for i in b1_invocations}) == len(b1_invocations)
    if outside_scope:
        retry = scenario.llm.texts_of(6)
        assert len(retry) == 1
        assert retry[0].count("# B.1") == 1
        assert rejected in _area(retry[0], "Previous attempts at this task")
        assert "T1-AC2" in retry[-1]
    assert scenario.session.final_answer == "6 g"
