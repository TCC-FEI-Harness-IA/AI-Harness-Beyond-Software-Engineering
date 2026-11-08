"""B.4 — Registro dos resultados parciais da tarefa aprovada.

B.4 roda numa janela própria e recebe como entradas explícitas a tarefa, o resultado aprovado, o
histórico das tentativas e os aprendizados já registrados. Os testes usam os templates reais e
inspecionam o prompt efetivamente enviado ao modelo. As respostas do modelo são simuladas: os testes
provam a fiação e o tratamento dos aprendizados, não que um LLM real nunca omitirá uma conclusão.
"""
import json
import logging

from src.domain.entities.thinking.learning import Learning
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado as _anotacoes_do_enunciado,
    plano_aprovado as _plano_aprovado,
    aprendizados as _aprendizados,
    aprovado as _aprovado,
    criterios as _criterios,
    global_aprovado as _global_aprovado,
    reprovado as _reprovado,
    resolucao as _resolucao,
    resposta_final as _resposta_final,
)

_FASE = ThinkingPhaseEnum

# ── Matemática ITA 2024 Q037 (afirmações sobre conjuntos com C ⊆ A) ──────────

_PERGUNTA_Q037 = (
    "Sejam A, B, C ⊆ ℝ tais que C ⊆ A. Considere as afirmações: I. (A ∩ B) ∪ C = A ∩ (B ∪ C). "
    "II. A ∩ B = C ∪ (B ∩ (ℝ − C)). III. A ∩ (B − C) = (A ∩ B) − C. É (São) VERDADEIRA(S): "
    "A) apenas I e II. B) apenas I e III. C) apenas II. D) apenas III. E) I, II e III."
)
_ANOTACOES_Q037 = (
    "Hipótese: A, B, C ⊆ ℝ com C ⊆ A.",
    "Alternativas: A) apenas I e II; B) apenas I e III; C) apenas II; D) apenas III; E) I, II e III.",
)
_TENTATIVA_REFUTADA_T1 = "A afirmação I é falsa, porque a união com C pode acrescentar elementos fora de A."
_RESULTADO_APROVADO_T1 = (
    "Pela distributividade da interseção sobre a união, A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C). "
    "Como C ⊆ A, tem-se A ∩ C = C; logo A ∩ (B ∪ C) = (A ∩ B) ∪ C. Conclusão: a afirmação I é verdadeira."
)
_APRENDIZADO_T1 = "A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade."
_RESULTADO_APROVADO_T2 = (
    "Tomando B = ∅, o lado esquerdo é A ∩ ∅ = ∅ e o lado direito é C ∪ ∅ = C; com C ≠ ∅ a igualdade "
    "falha. Conclusão: a afirmação II é falsa."
)
_APRENDIZADO_T2 = "A afirmação II é falsa: com B = ∅ e C ≠ ∅, A ∩ B = ∅ e o lado direito vale C."


def _tarefa(task_id: str, title: str, description: str) -> dict[str, object]:
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": f"Deve justificar a conclusão de {task_id}."}],
    }


def _tarefas(*tarefas: dict[str, object]) -> str:
    return json.dumps({"tasks": list(tarefas)})


_T1_Q037 = _tarefa("T1", "Avaliar a afirmação I", "Com C ⊆ A, decida se (A ∩ B) ∪ C = A ∩ (B ∪ C), justificando.")
_T2_Q037 = _tarefa("T2", "Avaliar a afirmação II", "Com C ⊆ A, decida se A ∩ B = C ∪ (B ∩ (ℝ − C)), justificando.")


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))


def _cenario_q037(aprendizados_da_t2: tuple[str, ...] = (_APRENDIZADO_T2,)) -> RalphScenario:
    """T1 é reprovada com uma conclusão refutada e aprovada na segunda tentativa; T2 é aprovada de primeira."""
    return RalphScenario(
        responses=[
            _criterios(),
            _tarefas(_T1_Q037, _T2_Q037),
            _plano_aprovado(), _anotacoes_do_enunciado(*_ANOTACOES_Q037),
            _resolucao(_TENTATIVA_REFUTADA_T1),
            _reprovado("T1"),
            _resolucao(_RESULTADO_APROVADO_T1),
            _aprovado("T1"),
            _aprendizados(_APRENDIZADO_T1),
            _resolucao(_RESULTADO_APROVADO_T2),
            _aprovado("T2"),
            _aprendizados(*aprendizados_da_t2),
            _global_aprovado(),
            _resposta_final("B) apenas I e III."),
        ],
        template_provider=_provider(),
    )


def _chamadas(cenario: RalphScenario, fase: ThinkingPhaseEnum, task_id: str | None = None) -> list[int]:
    """Índices das chamadas ao modelo feitas por uma fase, opcionalmente só as de uma tarefa."""
    return [
        indice
        for indice, invocacao in enumerate(cenario.session.invocations)
        if invocacao.phase is fase and (task_id is None or invocacao.task_id == task_id)
    ]


def _conversa(cenario: RalphScenario, fase: ThinkingPhaseEnum, task_id: str, ordem: int = 0) -> list[str]:
    """Mensagens enviadas ao modelo numa chamada da fase para a tarefa."""
    return cenario.llm.texts_of(_chamadas(cenario, fase, task_id)[ordem])


def _evento_learn(eventos: list, task_id: str):
    return next(e for e in eventos if e.phase is _FASE.B4_LEARNINGS_EXTRACTION and e.task == task_id)


# ── Isolamento de contexto: B.4 em janela própria, com entradas explícitas ───


async def test_b4_roda_em_janela_nova_com_um_unico_prompt_e_sem_a_conversa_de_b1() -> None:
    cenario = _cenario_q037()

    eventos = await cenario.run()

    conversa_de_b4 = _conversa(cenario, _FASE.B4_LEARNINGS_EXTRACTION, "T1")
    assert len(conversa_de_b4) == 1
    assert conversa_de_b4[0].startswith("# B.4")
    assert "# B.1" not in conversa_de_b4[0]
    assert "Redo the resolution of the task" not in conversa_de_b4[0]

    invocacoes = cenario.session.invocations
    janela_de_b4 = invocacoes[_chamadas(cenario, _FASE.B4_LEARNINGS_EXTRACTION, "T1")[0]].context_id
    janelas_de_b1 = {invocacoes[i].context_id for i in _chamadas(cenario, _FASE.B1_TASK_RESOLUTION, "T1")}
    assert janela_de_b4 not in janelas_de_b1
    assert _evento_learn(eventos, "T1").context_id == janela_de_b4


async def test_o_prompt_de_b4_traz_tarefa_resultado_aprovado_historico_e_memoria_em_areas_proprias() -> None:
    cenario = _cenario_q037()

    await cenario.run()

    prompt = _conversa(cenario, _FASE.B4_LEARNINGS_EXTRACTION, "T1")[0]
    assert "### T1 — Avaliar a afirmação I" in prompt
    assert f"<approved_result>\n{_RESULTADO_APROVADO_T1}\n</approved_result>" in prompt
    # O resultado aprovado aparece uma única vez: o histórico só aponta para a área própria.
    assert prompt.count(_RESULTADO_APROVADO_T1) == 1

    historico = prompt[prompt.index("<task_history>"):prompt.index("</task_history>")]
    assert historico.index("### Attempt 1 — rejected") < historico.index("### Attempt 2 — approved")
    assert _TENTATIVA_REFUTADA_T1 in historico
    assert "`reproved`" in historico and "`approved`" in historico

    memoria = prompt[prompt.index("## Key Learnings"):prompt.index("## Instructions")]
    assert all(f"- {anotacao}" in memoria for anotacao in _ANOTACOES_Q037)
    assert _TENTATIVA_REFUTADA_T1 not in memoria


async def test_o_historico_de_b4_traz_a_saida_invalida_do_validador_antes_do_veredito() -> None:
    saida_invalida_do_validador = json.dumps(
        {"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []}
    )
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas(_T1_Q037),
            _plano_aprovado(), _anotacoes_do_enunciado(),
            _resolucao(_RESULTADO_APROVADO_T1),
            saida_invalida_do_validador,
            _aprovado("T1"),
            _aprendizados(_APRENDIZADO_T1),
            _global_aprovado(),
            _resposta_final(),
        ]
    )

    await cenario.run()

    historico = cenario.template_provider.variables_of(_FASE.B4_LEARNINGS_EXTRACTION)[0]["task_history"]
    assert historico.index("invalid output") < historico.index("**Validator verdict:**")
    assert "Evaluations are missing" in historico
    assert "### Attempt 1 — approved" in historico


# ── Classificações: o caso da afirmação I (ITA 2024 Q037) ───────────────────


async def test_a_classificacao_aprovada_e_persistida_e_chega_a_proxima_tarefa_sem_vazar_a_conversa() -> None:
    cenario = _cenario_q037()

    eventos = await cenario.run()

    assert Learning(content=_APRENDIZADO_T1, source_task_id="T1") in cenario.learnings_memory.all()
    mensagem_de_b4 = next(
        m for m in cenario.session.messages if m.phase is _FASE.B4_LEARNINGS_EXTRACTION and m.task_id == "T1"
    )
    assert _APRENDIZADO_T1 in mensagem_de_b4.content
    assert _APRENDIZADO_T1 in _evento_learn(eventos, "T1").content

    conversa_da_t2 = _conversa(cenario, _FASE.B1_TASK_RESOLUTION, "T2")
    assert len(conversa_da_t2) == 1
    assert f"- {_APRENDIZADO_T1}" in conversa_da_t2[0]
    for vazamento in (
        _TENTATIVA_REFUTADA_T1,
        _RESULTADO_APROVADO_T1,
        "Veredito do validador",
        "<task_history>",
        "# B.4",
    ):
        assert vazamento not in conversa_da_t2[0], vazamento


async def test_a_extracao_da_tarefa_seguinte_ve_a_classificacao_ja_registrada_e_nao_o_historico_anterior() -> None:
    cenario = _cenario_q037()

    await cenario.run()

    prompt_da_t2 = _conversa(cenario, _FASE.B4_LEARNINGS_EXTRACTION, "T2")[0]
    memoria = prompt_da_t2[prompt_da_t2.index("## Key Learnings"):prompt_da_t2.index("## Instructions")]
    assert f"- {_APRENDIZADO_T1}" in memoria
    assert _TENTATIVA_REFUTADA_T1 not in prompt_da_t2
    assert _RESULTADO_APROVADO_T1 not in prompt_da_t2
    assert f"<approved_result>\n{_RESULTADO_APROVADO_T2}\n</approved_result>" in prompt_da_t2


async def test_os_aprendizados_nao_entram_nos_resultados_armazenados() -> None:
    cenario = _cenario_q037()

    await cenario.run()

    prompt_de_c3 = cenario.llm.texts_of(_chamadas(cenario, _FASE.C3_FINAL_ANSWER)[0])[0]
    resultados = prompt_de_c3[:prompt_de_c3.index("## Key Learnings")]
    assert _RESULTADO_APROVADO_T1 in resultados
    assert _APRENDIZADO_T1 not in resultados


# ── Conclusões numéricas ────────────────────────────────────────────────────

_RESULTADO_NUMERICO = (
    "vₘ = Δs / Δt = 150 km / 2 h = 75 km/h. Dividindo por 3,6: vₘ = 75 / 3,6 ≈ 20,83 m/s. Resultado: 20,83 m/s."
)
_APRENDIZADO_NUMERICO = (
    "A velocidade média do carro no percurso total de 150 km em 2 h é vₘ ≈ 20,83 m/s (75 km/h): "
    "vₘ = Δs/Δt, convertida de km/h para m/s dividindo por 3,6."
)


async def test_a_conclusao_numerica_chega_a_proxima_tarefa_com_grandeza_valor_unidade_e_condicao() -> None:
    cenario = RalphScenario(
        responses=[
            _criterios(),
            _tarefas(
                _tarefa("T1", "Calcular a velocidade média", "Um carro percorre 150 km em 2 h; calcule vₘ em m/s."),
                _tarefa("T2", "Comparar com as alternativas", "Compare a velocidade média com as alternativas."),
            ),
            _plano_aprovado(), _anotacoes_do_enunciado("Distância percorrida: 150 km.", "Tempo de percurso: 2 h."),
            _resolucao(_RESULTADO_NUMERICO),
            _aprovado("T1"),
            _aprendizados(_APRENDIZADO_NUMERICO),
            _resolucao("A alternativa compatível é a de 20,8 m/s."),
            _aprovado("T2"),
            _aprendizados(),
            _global_aprovado(),
            _resposta_final(),
        ],
        template_provider=_provider(),
    )

    await cenario.run()

    assert cenario.learnings_memory.all()[-1] == Learning(content=_APRENDIZADO_NUMERICO, source_task_id="T1")
    conversa_da_t2 = _conversa(cenario, _FASE.B1_TASK_RESOLUTION, "T2")
    assert f"- {_APRENDIZADO_NUMERICO}" in conversa_da_t2[0]
    assert _RESULTADO_NUMERICO not in conversa_da_t2[0]


# ── Duplicatas ──────────────────────────────────────────────────────────────


async def test_aprendizados_ja_registrados_sao_descartados_e_so_o_fato_novo_entra_na_memoria() -> None:
    repetido_com_outra_forma = "  A afirmação I é  verdadeira: C ⊆ A implica A ∩ C = C, pela distributividade. "
    cenario = _cenario_q037(aprendizados_da_t2=(repetido_com_outra_forma, _ANOTACOES_Q037[0], _APRENDIZADO_T2))

    eventos = await cenario.run()

    assert [aprendizado.content for aprendizado in cenario.learnings_memory.all()] == [
        *_ANOTACOES_Q037,
        _APRENDIZADO_T1,
        _APRENDIZADO_T2,
    ]
    conteudo = _evento_learn(eventos, "T2").content
    extraidos, descartados = conteudo.split("## Repeated learnings already recorded (not stored again)")
    assert f"- {_APRENDIZADO_T2}" in extraidos
    assert _ANOTACOES_Q037[0] not in extraidos
    assert repetido_com_outra_forma.strip() in descartados
    assert _ANOTACOES_Q037[0] in descartados


async def test_quando_todos_os_aprendizados_ja_constam_a_tarefa_registra_que_nada_foi_extraido() -> None:
    cenario = _cenario_q037(aprendizados_da_t2=(_APRENDIZADO_T1,))

    eventos = await cenario.run()

    conteudo = _evento_learn(eventos, "T2").content
    assert conteudo.startswith("No learnings were extracted from this task.")
    assert f"## Repeated learnings already recorded (not stored again)\n\n- {_APRENDIZADO_T1}" in conteudo
    assert [a.content for a in cenario.learnings_memory.all()].count(_APRENDIZADO_T1) == 1
    prompt_de_c3 = cenario.llm.texts_of(_chamadas(cenario, _FASE.C3_FINAL_ANSWER)[0])[0]
    assert prompt_de_c3.count(f"- {_APRENDIZADO_T1}") == 1


# ── Ausência legítima de fatos novos ────────────────────────────────────────


async def test_lista_vazia_de_b4_mantem_a_memoria_e_o_fluxo_segue_ate_a_resposta_final() -> None:
    cenario = _cenario_q037(aprendizados_da_t2=())

    eventos = await cenario.run()

    assert _evento_learn(eventos, "T2").content == "No learnings were extracted from this task."
    assert [a.content for a in cenario.learnings_memory.all()] == [*_ANOTACOES_Q037, _APRENDIZADO_T1]
    assert cenario.session.status is SessionStatusEnum.COMPLETED
    prompt_de_c1 = cenario.llm.texts_of(_chamadas(cenario, _FASE.C1_GLOBAL_VERIFICATION)[0])[0]
    assert cenario.learnings_memory.render() in prompt_de_c1


async def test_aprendizado_em_branco_nao_entra_na_memoria_nem_e_listado_como_repetido() -> None:
    cenario = _cenario_q037(aprendizados_da_t2=("   ", _APRENDIZADO_T2))

    eventos = await cenario.run()

    assert _evento_learn(eventos, "T2").content == f"## Extracted learnings\n\n- {_APRENDIZADO_T2}"
    assert cenario.learnings_memory.all()[-1].content == _APRENDIZADO_T2
