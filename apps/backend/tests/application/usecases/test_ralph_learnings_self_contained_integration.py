"""Preservação e transporte com extrações roteirizadas, sem garantia semântica do LLM.

Somente texto genérico entra no harness. Os dados completos das fixtures são respostas falsas de
A.3/B.4, não um extrator alternativo nem evidência de que um modelo real nunca omitirá dados.
"""
import json
import logging
import re

import pytest

from src.domain.entities.thinking.learning import Learning
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import aprendizados, aprovado, relatorio, reprovado, resposta_final


_CASES = [
    pytest.param(
        "SLA significa Acordo de Nível de Serviço. A Bomba Alfa entrega 12 L/min; a Bomba Alfa II, "
        "8 L/min. O relatório SLR vence 2 dias após o ensaio. Determine o volume em litros entregue "
        "pela Bomba Alfa em 3 min, mantendo vazão constante.",
        (
            "SLA significa Acordo de Nível de Serviço.",
            "A Bomba Alfa entrega 12 L/min; a Bomba Alfa II, 8 L/min.",
            "O relatório SLR vence 2 dias após o ensaio.",
            "Determine o volume em litros entregue pela Bomba Alfa em 3 min, mantendo vazão constante.",
        ),
        "Para a Bomba Alfa, V = 12 L/min × 3 min = 36 L sob vazão constante.",
        ("O volume da Bomba Alfa em 3 min é 36 L sob vazão constante: V = vazão × tempo.",),
        None, id="pergunta-aberta-sigla-nomes-unidades-prazo",
    ),
    pytest.param(
        "Testes e parâmetros: 1-Cálcio, 2-Cloreto, 3-Turbidez, 4-Coliformes totais, "
        "5-Sólidos sedimentáveis. Qual teste identifica cálcio? A) 1, B) 2, C) 3, D) 4, E) 5.",
        (
            "Testes e parâmetros: 1-Cálcio, 2-Cloreto, 3-Turbidez, 4-Coliformes totais, 5-Sólidos sedimentáveis.",
            "Alternativas: A) 1, B) 2, C) 3, D) 4, E) 5.",
            "Qual teste identifica cálcio?",
        ),
        "O teste 1 identifica cálcio, conforme a associação 1-Cálcio da tabela.",
        ("O teste que identifica cálcio é o 1: a tabela associa o código 1 ao parâmetro Cálcio.",),
        None, id="tabela-e-alternativas-somente-no-texto",
    ),
    pytest.param(
        "No microscópio, a imagem intermediária está a 130 mm da objetiva, cuja distância focal é "
        "34,5 mm. Sob a hipótese de lentes delgadas, determine a distância do objeto à objetiva. "
        "Alternativas: A) 44 mm; B) 60 mm. Escolha a mais próxima do cálculo aproximado.",
        (
            "A imagem intermediária está a 130 mm da objetiva.",
            "A distância focal da objetiva é 34,5 mm.",
            "Hipótese: lentes delgadas.",
            "Determine a distância do objeto à objetiva.",
            "Alternativas: A) 44 mm; B) 60 mm. Escolha a mais próxima do cálculo aproximado.",
        ),
        "A referência de 130 mm é a objetiva. Sob lentes delgadas, p = (1/34,5 − 1/130)⁻¹ mm ≈ 47 mm "
        "é a distância do objeto à objetiva; A) 44 mm é o melhor ajuste, com diferença aproximada de 3 mm.",
        (
            "Sob lentes delgadas, a distância calculada do objeto à objetiva é aproximadamente 47 mm: "
            "equação 1/f = 1/p + 1/p', com f = 34,5 mm e imagem a 130 mm da objetiva.",
            "A opção A) 44 mm é o melhor ajuste para a distância calculada de aproximadamente 47 mm "
            "do objeto à objetiva: diferença aproximada de 3 mm, sem igualdade entre os valores.",
        ),
        "A imagem intermediária está a 130 mm da ocular; a distância é exatamente 44 mm.",
        id="referencia-espacial-aproximacao-e-melhor-ajuste",
    ),
    pytest.param(
        "O gás A passa de 300 K a 600 K sob pressão constante; o gás B passa de 300 K a 600 K "
        "em recipiente rígido. Ambos são ideais. Determine a razão entre volumes finais e iniciais de cada gás.",
        (
            "O gás A passa de 300 K a 600 K sob pressão constante.",
            "O gás B passa de 300 K a 600 K em recipiente rígido.",
            "Ambos são ideais.",
            "Determine a razão entre volumes finais e iniciais de cada gás.",
        ),
        "Para o gás A ideal a pressão constante, Vfinal/Vinicial = 600/300 = 2. "
        "Para o gás B ideal no recipiente rígido, Vfinal/Vinicial = 1 pela restrição de volume.",
        (
            "Sob pressão constante, o volume do gás A ideal dobra: V/T constante.",
            "Em recipiente rígido, o volume do gás B ideal permanece constante: a rigidez fixa o volume.",
        ),
        None, id="objetos-e-hipoteses-distintos",
    ),
]


def _task(task_id: str) -> str:
    return json.dumps({"tasks": [{
        "id": task_id, "title": f"Objetivo de {task_id}",
        "description": "Determine e explique o resultado solicitado usando os dados disponíveis.",
        "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "Resultado fundamentado."}],
    }]})


def _result(text: str) -> str:
    return json.dumps({"result": text, "conclusion": text})


def _area(prompt: str, heading: str) -> str:
    return re.split(r"\n## (?!T\d+\b)", prompt.split(f"## {heading}\n", 1)[1], maxsplit=1)[0]


def _check_memory_role(phase: Phase, memory: str) -> None:
    obligations = {
        Phase.B2_TASK_VERIFICATION: "are not criteria",
        Phase.C1_GLOBAL_VERIFICATION: "do not count as coverage",
        Phase.C3_FINAL_ANSWER: "do not replace the stored results",
    }
    if phase in obligations:
        assert obligations[phase] in memory


@pytest.mark.parametrize(("question", "given", "approved", "derived", "refuted"), _CASES)
async def test_notas_autossuficientes_chegam_a_todos_os_destinos_inclusive_tarefa_adicional(
    question: str, given: tuple[str, ...], approved: str, derived: tuple[str, ...], refuted: str | None,
) -> None:
    settings = FakeSettings()
    responses = [
        json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "Responder ao pedido."}]}),
        _task("T1"), aprendizados(*given, "  " + given[0] + "  ", "   "),
    ]
    if refuted:
        responses.extend([_result(refuted), reprovado("T1")])
    additional_result = "A verificação adicional confirma o conteúdo: " + approved
    responses.extend([
        _result(approved), aprovado("T1"), aprendizados(*derived),
        relatorio(("AC1", False)), _task("T2"), _result(additional_result), aprovado("T2"),
        aprendizados(), relatorio(("AC1", True)), resposta_final("Síntese roteirizada."),
    ])
    scenario = RalphScenario(responses=responses, settings=settings, template_provider=FilePromptTemplateProvider(
        settings=settings, logger=logging.getLogger("test.self_contained"),
    ))

    events = await scenario.run(question=question)

    assert scenario.session.status is SessionStatusEnum.COMPLETED
    assert scenario.learnings_memory.all() == (
        *(Learning(content=fact) for fact in given),
        *(Learning(content=fact, source_task_id="T1") for fact in derived),
    )
    contexts = [invocation.context_id for invocation in scenario.session.invocations]
    assert len(contexts) == len(set(contexts))
    destinations = set()
    for index, invocation in enumerate(scenario.session.invocations):
        conversation = scenario.llm.texts_of(index)
        assert len(conversation) == 1  # Nenhuma conversa de outra fase é restaurada.
        prompt = conversation[0]
        assert "{{" not in prompt
        if invocation.phase is Phase.A3_PLANNING_LEARNINGS:
            assert question in _area(prompt, "Question")
            assert "T1-AC1" not in prompt and "## Key Learnings" not in prompt
        if invocation.phase.value.startswith(("B", "C")):
            destinations.add(invocation.phase)
            memory = _area(prompt, "Key Learnings")
            facts = given if invocation.task_id == "T1" else (*given, *derived)
            offsets = [memory.index(f"- {fact}") for fact in facts]
            assert offsets == sorted(offsets)
            assert approved not in memory and additional_result not in memory
            if refuted:
                assert refuted not in memory
            if invocation.task_id == "T2" and invocation.phase is Phase.B1_TASK_RESOLUTION:
                assert approved not in prompt and "# B.4" not in prompt
            if invocation.phase in (Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER):
                stored = _area(prompt, "Stored results")
                assert approved in stored
                assert all(fact not in stored for fact in (*given, *derived))
                if refuted:
                    assert refuted not in stored
            _check_memory_role(invocation.phase, memory)
    assert destinations == {
        Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
        Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, Phase.C3_FINAL_ANSWER,
    }
    a3_event = next(event for event in events if event.phase is Phase.A3_PLANNING_LEARNINGS)
    assert "## Repeated learnings already recorded (not stored again)" in a3_event.content
    assert given[0] in a3_event.content
    b4_events = [event for event in events if event.phase is Phase.B4_LEARNINGS_EXTRACTION]
    assert all(fact in b4_events[0].content for fact in derived)
    assert b4_events[-1].content == "No learnings were extracted from this task."
    for event in (a3_event, *b4_events):
        assert any(message.content == event.content for message in scenario.session.messages)
