"""Fidelidade da síntese final (thinking 06) com templates, fases, parser e persistência reais.

As saídas do LLM são roteirizadas. Estes testes provam três coisas distintas:

- **preservação das entradas**: C.3 recebe exatamente os resultados vigentes e a memória que a
  última C.1 aprovou, com pareamentos, unidades e qualificações intactos;
- **contrato de prompt**: a conferência de fidelidade chega a C.3 na mesma chamada, e C.1 recebe a
  regra sobre o vínculo entre item e identificador;
- **transições**: lacunas de análise ou de vínculo percorrem C.2 antes de uma nova C.1/C.3.

Não provam a qualidade semântica da saída de um modelo real: a resposta fiel é roteirizada.
"""
import json
import logging
import re

import pytest

from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import plano_aprovado
from tests.doubles.ralph_scripts import aprendizados, relatorio, resposta_final

_PLANNING = [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
             Phase.A4_PLANNING_LEARNINGS]
_CYCLE = [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION]
_FIDELITY_HEADING = "Fidelity check before answering"

_QUIMICA = (
    "Cinco testes foram feitos com uma amostra. O teste 1 forma precipitado branco com oxalato. "
    "Qual teste identifica o cálcio? A) 1 B) 2 C) 3 D) 4 E) 5"
)
_PAREAMENTO = "Alternativas copiadas literalmente: A) 1, B) 2, C) 3, D) 4, E) 5."
_SEM_PAREAMENTO = "O teste 1 forma precipitado branco com oxalato."
_CALCIO = "teste 1 — cálcio: o precipitado branco com oxalato identifica Ca²⁺; os demais testes não."


def _json(**value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _criteria(*descriptions: str) -> str:
    return _json(general_acceptance_criteria=[
        {"id": f"AC{index}", "description": text} for index, text in enumerate(descriptions, 1)
    ])


def _task(task_id: str, description: str, **extra: object) -> dict:
    return {"id": task_id, "title": f"Tarefa {task_id}", "description": description,
            "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "Resultado explicado."}], **extra}


def _plan(*tasks: dict) -> str:
    return _json(tasks=list(tasks))


def _result(task_id: str, text: str, *verdicts: tuple[str, str, str]) -> str:
    extra = {"revision": [{"task_id": target, "verdict": verdict, "justification": why}
                          for target, verdict, why in verdicts]} if verdicts else {}
    return _json(task_id=task_id, result=text, conclusion=text, **extra)


def _executed(task_id: str, text: str, *facts: str) -> list[str]:
    return [_result(task_id, text), relatorio((f"{task_id}-AC1", True), (f"{task_id}-TECH", True)),
            aprendizados(*facts)]


def _global(*evaluations: tuple[str, bool, str]) -> str:
    unmet = [criterion_id for criterion_id, met, _ in evaluations if not met]
    return _json(
        criteria_evaluation=[{"criterion_id": criterion_id, "met": met, "justification": why}
                             for criterion_id, met, why in evaluations],
        unmet_criteria_ids=unmet, decision="reproved" if unmet else "approved",
    )


def _scenario(responses: list[str], cost_guard: FakeCostGuard | None = None) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(responses=responses, settings=settings, cost_guard=cost_guard,
                         template_provider=FilePromptTemplateProvider(
                             settings=settings, logger=logging.getLogger("test.fidelity.templates")))


def _phases(scenario: RalphScenario) -> list[Phase]:
    return [invocation.phase for invocation in scenario.session.invocations]


def _prompts(scenario: RalphScenario, phase: Phase) -> list[str]:
    return [scenario.llm.texts_of(index)[0] for index, invocation in enumerate(scenario.session.invocations)
            if invocation.phase is phase and invocation.recovers_invocation_id is None]


def _area(prompt: str, heading: str) -> str:
    content = prompt.split(f"## {heading}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", content, maxsplit=1)[0].strip()


def _synthesis_inputs_match_last_c1(scenario: RalphScenario) -> str:
    """Confere que C.3 recebeu o conjunto e a memória da última C.1, numa janela própria."""
    last_c1 = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[-1]
    [c3] = _prompts(scenario, Phase.C3_FINAL_ANSWER)
    for heading in ("Stored results", "General acceptance criteria"):
        assert _area(c3, heading) == _area(last_c1, heading), heading
    memory = scenario.learnings_memory.render()
    assert _area(c3, "Key Learnings").endswith(memory) and _area(last_c1, "Key Learnings").endswith(memory)
    c3_index = _phases(scenario).index(Phase.C3_FINAL_ANSWER)
    assert len(scenario.llm.conversations[c3_index]) == 1
    assert _FIDELITY_HEADING in c3
    return c3


def _finished(scenario: RalphScenario, events: list, final: str) -> None:
    assert scenario.session.status is SessionStatusEnum.COMPLETED
    assert scenario.session.final_answer == final
    assert events[-1].type is ThinkingEventTypeEnum.RESULT and events[-1].content == final
    assert _phases(scenario)[-1] is Phase.C3_FINAL_ANSWER
    assert _phases(scenario).count(Phase.C3_FINAL_ANSWER) == 1
    assert scenario.session.totals.total_llm_calls == scenario.llm.call_count


# ── Identificadores: pareamento literal disponível ───────────────────────────


async def test_pareamento_completo_nas_notas_chega_a_c3_e_a_resposta_fiel_entrega_a_letra() -> None:
    marker = "Terminar com a linha RESPOSTA_FINAL: LETRA."
    scenario = _scenario([
        _criteria("Identificar a alternativa do teste que identifica o cálcio.", marker),
        _plan(_task("T1", "Determine qual dos cinco testes identifica o cálcio, explicando.")),
        plano_aprovado(), aprendizados(_PAREAMENTO, _SEM_PAREAMENTO),
        *_executed("T1", _CALCIO, "O cálcio é identificado pelo teste 1."),
        _global(("AC1", True, "T1 determina o teste 1; as notas rotulam o teste 1 como A."),
                ("AC2", True, "C.3 aplica a linha final.")),
        resposta_final("RESPOSTA_FINAL: A"),
    ])

    events = await scenario.run(question=_QUIMICA)

    # Conteúdo suficiente sem marcador final segue diretamente de C.1 a C.3.
    assert _phases(scenario) == [*_PLANNING, *_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert _PAREAMENTO in _area(c3, "Key Learnings")
    assert _CALCIO in _area(c3, "Stored results")
    assert "RESPOSTA_FINAL: A" not in _area(c3, "Stored results")
    assert "must label the very object the results determined" in " ".join(c3.split())
    _finished(scenario, events, "RESPOSTA_FINAL: A")


async def test_vinculo_ausente_entre_item_e_identificador_percorre_c2_antes_da_sintese() -> None:
    gap = ("T1 determina o teste 1, mas nem os resultados nem as notas registram qual letra rotula o "
           "teste 1; estabelecer esse vínculo a partir do enunciado.")
    link = "As alternativas do enunciado são A) 1, B) 2, C) 3, D) 4, E) 5; o teste 1 é rotulado pela letra A."
    scenario = _scenario([
        _criteria("Responder com a letra da alternativa do teste que identifica o cálcio."),
        _plan(_task("T1", "Determine qual dos cinco testes identifica o cálcio, explicando.")),
        plano_aprovado(), aprendizados(_SEM_PAREAMENTO),
        *_executed("T1", _CALCIO),
        _global(("AC1", False, gap)),
        _plan(_task("T2", "Copie literalmente as alternativas do enunciado e identifique a letra que rotula o "
                          "teste 1, explicando o pareamento.")),
        *_executed("T2", link),
        _global(("AC1", True, "T1 determina o teste 1 e T2 registra que A rotula o teste 1.")),
        resposta_final("A"),
    ])

    events = await scenario.run(question=_QUIMICA)

    assert _phases(scenario) == [*_PLANNING, *_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING,
                                 *_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    first_c1 = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0]
    assert "## Identifiers and faithful presentation" in first_c1
    assert "A) 1" not in _area(first_c1, "Stored results") + _area(first_c1, "Key Learnings")
    c2 = _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert gap in _area(c2, "Global verification feedback")
    assert "A) 1 B) 2 C) 3 D) 4 E) 5" in _area(c2, "Original Prompt")
    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert link in _area(c3, "Stored results") and _CALCIO in _area(c3, "Stored results")
    _finished(scenario, events, "A")


# ── Pergunta aberta, unidade, condição e tradução ────────────────────────────


async def test_pergunta_aberta_preserva_entidade_numero_unidade_e_condicao_ate_a_resposta_traduzida() -> None:
    approved = ("The Lisbon plant consumed 3.2 MWh in March, assuming 8-hour shifts on 22 working days; "
                "the Porto plant is not included.")
    final = ("A planta de Lisboa consumiu 3,2 MWh em março, supondo turnos de 8 horas em 22 dias úteis; "
             "a planta do Porto não está incluída.")
    scenario = _scenario([
        _criteria("Informar o consumo de energia da planta de Lisboa em março, com unidade.",
                  "Responder em português."),
        _plan(_task("T1", "Determine the March energy consumption of the Lisbon plant, explaining.")),
        plano_aprovado(),
        aprendizados("Lisbon plant: 400 kW average load; shifts of 8 hours; 22 working days in March."),
        *_executed("T1", approved),
        _global(("AC1", True, "T1 determina 3.2 MWh sob a hipótese de turnos de 8 horas."),
                ("AC2", True, "C.3 traduz.")),
        resposta_final(final),
    ])

    events = await scenario.run(question="Quanto a planta de Lisboa consumiu em março? Responda em português.")

    assert Phase.C2_ADDITIONAL_PLANNING not in _phases(scenario)
    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert approved in _area(c3, "Stored results")
    check = " ".join(_area(c3, _FIDELITY_HEADING).split())
    assert "Translation and concision change the wording, never these aspects." in check
    for kept in ("Lisboa", "3,2 MWh", "março", "8 horas", "Porto"):
        assert kept in scenario.session.final_answer
    _finished(scenario, events, final)


# ── Aproximação e melhor ajuste já aprovados ─────────────────────────────────


async def test_escolha_por_melhor_ajuste_aprovada_chega_a_c3_com_sua_natureza_sem_replanejamento() -> None:
    approved = ("O comprimento estimado é ≈ 47 mm. A) 44 mm é o melhor ajuste: difere 3 mm, contra mais de "
                "13 mm das demais opções; não há igualdade entre 47 e 44.")
    final = "A) 44 mm — melhor ajuste para o valor estimado de cerca de 47 mm."
    scenario = _scenario([
        _criteria("Selecionar a alternativa mais sustentada para o comprimento.", "Pode justificar brevemente."),
        _plan(_task("T1", "Estime o comprimento e compare com A) 44 mm B) 60 mm C) 75 mm, explicando.")),
        plano_aprovado(), aprendizados("Opções: A) 44 mm, B) 60 mm, C) 75 mm."),
        *_executed("T1", approved),
        _global(("AC1", True, "T1 seleciona A como melhor ajuste para ≈ 47 mm, com comparação."),
                ("AC2", True, "Justificativa opcional.")),
        resposta_final(final),
    ])

    events = await scenario.run(question="Qual o comprimento? A) 44 mm B) 60 mm C) 75 mm. Pode justificar.")

    assert _phases(scenario) == [*_PLANNING, *_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert approved in _area(c3, "Stored results")
    check = " ".join(_area(c3, _FIDELITY_HEADING).split())
    assert "even without numerical equality and without a calculation that produces the chosen value" in check
    assert "never write that they are equal" in check
    assert "exatamente" not in scenario.session.final_answer and "=" not in scenario.session.final_answer
    _finished(scenario, events, final)


# ── Comparação direcional ────────────────────────────────────────────────────


async def test_comparacao_direcional_aprovada_chega_com_orientacao_contra_texto_contraditorio() -> None:
    force = "A força média de frenagem é maior com pneus travados: F = m·Δv/Δt e Δt é menor nesse caso."
    energy = "A energia dissipada é igual nos dois casos: a variação de energia cinética é a mesma."
    final = ("C — a força média é maior nos pneus travados (Δt menor para o mesmo Δv) e a energia "
             "dissipada é igual nos dois casos.")
    scenario = _scenario([
        _criteria("Comparar força média e energia dissipada, selecionando a alternativa.", "Justificar."),
        _plan(_task("T1", "Compare a força média nos dois casos, explicando."),
              _task("T2", "Compare a energia dissipada nos dois casos, explicando.")),
        plano_aprovado(), aprendizados("O carro parte de 20 m/s e para nos dois casos."),
        *_executed("T1", force), *_executed("T2", energy),
        _global(("AC1", True, "T1 e T2 sustentam C."), ("AC2", True, "T1 e T2 fundamentam.")),
        resposta_final(final),
    ])

    events = await scenario.run(question="Compare força média e energia dissipada nas duas frenagens. Justifique.")

    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert force in _area(c3, "Stored results") and energy in _area(c3, "Stored results")
    check = " ".join(_area(c3, _FIDELITY_HEADING).split())
    assert "direction of every comparison" in check
    assert "every formula, comparison and explanation you present points in the same direction" in check
    _finished(scenario, events, final)


# ── Resultado revisado ───────────────────────────────────────────────────────


async def test_apos_revisao_a_sintese_recebe_so_a_versao_vigente_e_a_memoria_vigente() -> None:
    old = "MARCA_ANTIGA: a força média é maior com blocos de freio."
    old_fact = "FATO_OBSOLETO: a força média é maior com blocos de freio."
    new = "MARCA_NOVA: a força média é maior com pneus travados; T2 trocou o tempo de parada."
    reason = "T2 afirma força maior nos blocos, incompatível com T1 para as mesmas condições."
    scenario = _scenario([
        _criteria("Comparar a força média de frenagem com justificativa consistente."),
        _plan(_task("T1", "Determine o tempo de parada em cada caso, explicando."),
              _task("T2", "Compare a força média nos dois casos, explicando.")),
        plano_aprovado(), aprendizados("O carro parte de 20 m/s."),
        *_executed("T1", "Δt é menor com pneus travados.", "Δt é menor com pneus travados."),
        *_executed("T2", old, old_fact),
        _global(("AC1", False, "T1 e T2 são incompatíveis quanto ao tempo de parada; investigar.")),
        _plan(_task("T3", "Investigue a força média nos dois casos e explique se confirma ou corrige T2.",
                    review={"task_ids": ["T2"], "reason": reason})),
        _result("T3", new, ("T2", "superseded", "O tempo de parada foi trocado em T2.")),
        _json(criteria_evaluation=[{"criterion_id": "T3-AC1", "met": True, "justification": "ok"},
                                   {"criterion_id": "T3-TECH", "met": True, "justification": "fundamentado"},
                                   {"criterion_id": "T3-REV", "met": True, "justification": "sustentado"}],
              unmet_criteria_ids=[], decision="approved"),
        aprendizados("A força média é maior com pneus travados."),
        _global(("AC1", True, "T1 e T3 são consistentes.")),
        resposta_final("A força média é maior com pneus travados, porque o tempo de parada é menor."),
    ])

    events = await scenario.run(question="Compare a força média de frenagem com pneus travados e com blocos.")

    c3 = _synthesis_inputs_match_last_c1(scenario)
    for prompt_area in (_area(c3, "Stored results"), _area(c3, "Key Learnings")):
        assert old not in prompt_area and old_fact not in prompt_area
    assert new in _area(c3, "Stored results")
    assert old not in c3 and old_fact not in c3 and "Previous attempts" not in c3
    assert "{{result_revisions}}" not in c3 and "## Revision record" not in c3
    _finished(scenario, events, "A força média é maior com pneus travados, porque o tempo de parada é menor.")


# ── Apresentação conforme o pedido ───────────────────────────────────────────


@pytest.mark.parametrize(("presentation", "final"), [
    ("Responder somente com o resultado.", "A"),
    ("Pode justificar, se quiser.", "A — o teste 1 identifica o cálcio."),
    ("Justificar a resposta.", "A. O teste 1 identifica o cálcio: forma precipitado branco com oxalato."),
], ids=["somente_resultado", "justificativa_opcional", "justificativa_obrigatoria"])
async def test_mesmo_conteudo_interno_admite_apresentacoes_distintas(presentation: str, final: str) -> None:
    scenario = _scenario([
        _criteria("Identificar a alternativa do teste que identifica o cálcio.", presentation),
        _plan(_task("T1", "Determine qual dos cinco testes identifica o cálcio, explicando.")),
        plano_aprovado(), aprendizados(_PAREAMENTO),
        *_executed("T1", _CALCIO),
        _global(("AC1", True, "T1 determina o teste 1, rotulado A."), ("AC2", True, "C.3 apresenta.")),
        resposta_final(final),
    ])

    events = await scenario.run(question=f"{_QUIMICA} {presentation}")

    c3 = _synthesis_inputs_match_last_c1(scenario)
    assert _area(c3, "Stored results").endswith(_CALCIO)
    assert presentation in _area(c3, "General acceptance criteria")
    flat = " ".join(c3.split())
    assert "optional does not mean mandatory" in flat
    assert "do not mention stages, tasks, criteria, learnings or other internal details of the process" in flat
    _finished(scenario, events, final)


# ── Contratos preservados: recuperação, guarda da aprovação e limites ────────


async def test_saida_invalida_de_c3_e_recuperada_sem_fase_nova_nem_verificador_posterior() -> None:
    scenario = _scenario([
        _criteria("Identificar a alternativa do teste que identifica o cálcio."),
        _plan(_task("T1", "Determine qual dos cinco testes identifica o cálcio, explicando.")),
        plano_aprovado(), aprendizados(_PAREAMENTO),
        *_executed("T1", _CALCIO),
        _global(("AC1", True, "T1 determina o teste 1, rotulado A.")),
        _json(answer="A"),
        resposta_final("A"),
    ])

    events = await scenario.run(question=_QUIMICA)

    invocations = scenario.session.invocations
    assert _phases(scenario)[-2:] == [Phase.C3_FINAL_ANSWER, Phase.C3_FINAL_ANSWER]
    assert invocations[-1].recovers_invocation_id == invocations[-2].id
    assert invocations[-2].output_diagnostic is not None and invocations[-2].recovery is not None
    assert scenario.session.totals.total_llm_calls == scenario.llm.call_count == 10
    assert scenario.session.status is SessionStatusEnum.COMPLETED and scenario.session.final_answer == "A"
    assert events[-1].type is ThinkingEventTypeEnum.RESULT
    assert [e.type for e in events].count(ThinkingEventTypeEnum.RESULT) == 1


async def test_sintese_nao_roda_sobre_aprovacao_desatualizada() -> None:
    scenario = _scenario([
        _criteria("Identificar a alternativa do teste que identifica o cálcio."),
        _plan(_task("T1", "Determine qual dos cinco testes identifica o cálcio, explicando.")),
        plano_aprovado(), aprendizados(_PAREAMENTO),
        *_executed("T1", _CALCIO),
        _global(("AC1", True, "T1 determina o teste 1, rotulado A.")),
        resposta_final("A"),
    ])

    events = []
    with pytest.raises(ValueError, match="nova verificação global"):
        async for event in scenario.stream(question=_QUIMICA):
            events.append(event)
            if event.phase is Phase.C1_GLOBAL_VERIFICATION:
                scenario.results_ledger.current_task_ids = lambda: ("T9",)

    assert Phase.C3_FINAL_ANSWER not in _phases(scenario)
    assert scenario.session.status is SessionStatusEnum.FAILED and scenario.session.final_answer is None
    assert scenario.session.failure.phase is Phase.C3_FINAL_ANSWER
    assert events[-1].type is ThinkingEventTypeEnum.ERROR
    assert not [e for e in events if e.type is ThinkingEventTypeEnum.RESULT]
