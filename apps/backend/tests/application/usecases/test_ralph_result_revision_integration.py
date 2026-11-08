"""Revisão auditável de resultados aprovados e aprendizados vigentes (thinking 05), com prompts reais.

Fases, provider de arquivos, parser, fila, livro de resultados, memória e persistência são reais;
as saídas do LLM — inclusive vereditos de B.2 e C.1 e propostas de revisão de B.1 — são roteirizadas.
Os testes provam protocolo, transições e gestão de estado: que uma revisão só muda o estado vigente
pela referência estruturada aprovada em B.2, e o que cada fase recebe depois disso. Não provam que
um modelo real reconhece a contradição ou decide corretamente qual resultado está errado.
"""
import json
import logging
import re

import pytest

from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import aprendizados, relatorio, resposta_final

_PERGUNTA = (
    "Um carro freia uma vez com os pneus travados no asfalto e outra vez com blocos de freio, "
    "partindo de 20 m/s até parar. Compare a força média de frenagem e a energia dissipada."
)
_A3 = "O carro parte de 20 m/s e para nos dois casos de frenagem."
_T1 = "MARCA_T1: a força média é maior nos pneus travados, porque o tempo de parada é menor."
_T2 = "MARCA_T2: a energia dissipada é igual nos dois casos, pois a variação de energia cinética é a mesma."
_T3 = "MARCA_T3: a força média é maior nos blocos e a energia dissipada é maior nos blocos."
_T4 = "MARCA_T4: a força média é maior nos pneus; a afirmação de T3 sobre a força trocou o tempo de parada."
_L_T1 = "A força média de frenagem é maior com pneus travados: F = m·Δv/Δt com Δt menor."
_L_COMPARTILHADO = "A variação de energia cinética do carro é a mesma nos dois casos: mesma massa e Δv."
_L_T3 = "A força média de frenagem é maior com blocos de freio: atribuída ao contato prolongado."
_L_T4 = "A força média de frenagem é maior com pneus travados: Δt menor para o mesmo impulso."
_MOTIVO = "T3 afirma força maior nos blocos, incompatível com T1 para o mesmo carro e as mesmas condições."
_CONTRADICAO = "T1 e T3 fazem afirmações incompatíveis sobre a força média; investigar a força, sem decidir antes."
_JUSTIFICATIVA_SUBSTITUI = "O tempo de parada de T3 foi trocado; com Δt correto, a força é maior nos pneus."
_APROVACAO_REVISAO = "A investigação demonstra o tempo trocado em T3; o veredito superseded está sustentado."
_SEM_REVISAO = "None: this task does not review stored results."


def _json(**value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _criterios() -> str:
    return _json(general_acceptance_criteria=[
        {"id": "AC1", "description": "Comparar força média e energia dissipada com justificativa consistente."},
        {"id": "AC2", "description": "Responder em português."},
    ])


def _tarefa(task_id: str, descricao: str, **extra: object) -> dict:
    return {"id": task_id, "title": f"Investigação {task_id}", "description": descricao,
            "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "Resultado explicado."}], **extra}


def _plano(*tarefas: dict) -> str:
    return _json(tasks=list(tarefas))


def _resolucao(task_id: str, texto: str, *vereditos: tuple[str, str, str]) -> str:
    extra = {"revision": [{"task_id": alvo, "verdict": verdict, "justification": justificativa}
                          for alvo, verdict, justificativa in vereditos]} if vereditos else {}
    return _json(task_id=task_id, result=texto, conclusion=texto, **extra)


def _relatorio_revisao(task_id: str, aprovado: bool, justificativa: str = _APROVACAO_REVISAO) -> str:
    return _json(
        criteria_evaluation=[
            {"criterion_id": f"{task_id}-AC1", "met": True, "justification": "Resultado explicado."},
            {"criterion_id": f"{task_id}-REV", "met": aprovado, "justification": justificativa},
        ],
        unmet_criteria_ids=[] if aprovado else [f"{task_id}-REV"],
        decision="approved" if aprovado else "reproved",
    )


def _global(aprovado: bool, justificativa: str = _CONTRADICAO) -> str:
    return _json(
        criteria_evaluation=[{"criterion_id": "AC1", "met": aprovado, "justification": justificativa},
                             {"criterion_id": "AC2", "met": True, "justification": "Português."}],
        unmet_criteria_ids=[] if aprovado else ["AC1"], decision="approved" if aprovado else "reproved",
    )


def _tarefa_executada(task_id: str, texto: str, *fatos: str) -> list[str]:
    return [_resolucao(task_id, texto), relatorio((f"{task_id}-AC1", True)), aprendizados(*fatos)]


def _ate_a_contradicao() -> list[str]:
    """A.1–A.3, T1–T3 aprovadas e C.1 reprovando AC1 pela contradição entre T1 e T3."""
    return [
        _criterios(),
        _plano(_tarefa("T1", "Determine onde a força média é maior, explicando."),
               _tarefa("T2", "Determine onde a energia dissipada é maior, explicando."),
               _tarefa("T3", "Compare força e energia dissipada nos dois casos, explicando.")),
        aprendizados(_A3),
        *_tarefa_executada("T1", _T1, _L_T1),
        *_tarefa_executada("T2", _T2, _L_COMPARTILHADO),
        *_tarefa_executada("T3", _T3, _L_T3, _L_COMPARTILHADO),
        _global(False),
    ]


def _revisora(task_id: str = "T4", alvos: tuple[str, ...] = ("T3",), **extra: object) -> dict:
    return _tarefa(task_id, "Investigue a força média nos dois casos de frenagem e explique qual afirmação "
                   "registrada ela confirma ou corrige.", review={"task_ids": list(alvos), "reason": _MOTIVO}, **extra)


def _cenario(responses: list[str], cost_guard: FakeCostGuard | None = None) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(responses=responses, settings=settings, cost_guard=cost_guard,
                         template_provider=FilePromptTemplateProvider(
                             settings=settings, logger=logging.getLogger("test.revision.templates")))


def _fases(cenario: RalphScenario) -> list[Phase]:
    return [invocation.phase for invocation in cenario.session.invocations]


def _prompts(cenario: RalphScenario, fase: Phase) -> list[str]:
    return [cenario.llm.texts_of(index)[0] for index, invocation in enumerate(cenario.session.invocations)
            if invocation.phase is fase and invocation.recovers_invocation_id is None]


def _area(prompt: str, titulo: str) -> str:
    conteudo = prompt.split(f"## {titulo}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", conteudo, maxsplit=1)[0].strip()


def _blocos(area: str) -> list[str]:
    return re.findall(r"^## (T\d+) —", area, flags=re.MULTILINE)


_CICLO = [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION]
_PLANEJAMENTO = [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_PLANNING_LEARNINGS]


# ── Contradição → investigação → substituição aprovada ─────────────────────


async def test_contradicao_vira_revisao_aprovada_e_c1_c3_recebem_so_os_resultados_vigentes() -> None:
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_revisora()),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)),
        _relatorio_revisao("T4", True),
        aprendizados(_L_T4),
        _global(True, "Os resultados vigentes T1, T2 e T4 são consistentes."),
        resposta_final("Força maior com pneus travados; energia dissipada igual."),
    ])

    eventos = await cenario.run(question=_PERGUNTA)

    assert _fases(cenario) == [*_PLANEJAMENTO, *_CICLO * 3, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C2_ADDITIONAL_PLANNING, *_CICLO, Phase.C1_GLOBAL_VERIFICATION,
                               Phase.C3_FINAL_ANSWER]
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count == 19

    # C.2 recebe a contradição como diagnóstico e planeja a revisão por referência estruturada.
    c2 = _prompts(cenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    assert _CONTRADICAO in _area(c2, "Global verification feedback")
    assert _area(c2, "Revision record").endswith("\n\nNo stored result has been revised or suspended.")
    assert '"review"' in _area(c2, "Output format")

    # B.1 recebe o resultado sob investigação; B.2 recebe a proposta explícita e o critério de revisão.
    b1 = _prompts(cenario, Phase.B1_TASK_RESOLUTION)[-1]
    sob_revisao = _area(b1, "Results under review")
    assert _MOTIVO in sob_revisao and _T3 in sob_revisao and _T1 not in sob_revisao
    b2 = _prompts(cenario, Phase.B2_TASK_VERIFICATION)[-1]
    proposta = _area(b2, "Proposed revision")
    assert "`T3`" in proposta and "`superseded`" in proposta and _JUSTIFICATIVA_SUBSTITUI in proposta
    assert "`T4-REV`" in _area(b2, "Acceptance criteria for this task")
    assert _area(_prompts(cenario, Phase.B2_TASK_VERIFICATION)[0], "Proposed revision").endswith(_SEM_REVISAO)

    # B.4 da revisora já vê a memória atualizada: o fato exclusivo de T3 saiu, o compartilhado ficou.
    b4 = _area(_prompts(cenario, Phase.B4_LEARNINGS_EXTRACTION)[-1], "Key Learnings")
    assert _L_T3 not in b4 and _L_COMPARTILHADO in b4 and _A3 in b4 and _L_T1 in b4

    # A nova C.1 e C.3 recebem exatamente os resultados vigentes; a aprovação global é sobre eles.
    primeira_c1, segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)
    c3 = _prompts(cenario, Phase.C3_FINAL_ANSWER)[0]
    assert _blocos(_area(primeira_c1, "Stored results")) == ["T1", "T2", "T3"]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2", "T4"]
    assert _area(segunda_c1, "Stored results") == _area(c3, "Stored results")
    assert _T3 not in _area(segunda_c1, "Stored results")
    registro = _area(segunda_c1, "Revision record")
    assert "`T3`" in registro and "superseded by `T4`" in registro and _T3 not in registro
    for prompt in (segunda_c1, c3):
        memoria = _area(prompt, "Key Learnings")
        assert _L_T3 not in memoria
        assert all(fato in memoria for fato in (_A3, _L_T1, _L_COMPARTILHADO, _L_T4))

    # Auditoria: a conclusão antiga continua no histórico; a revisão aprovada fica registrada.
    [revisao] = cenario.session.result_revisions
    assert revisao.revising_task_id == "T4" and revisao.reason == _MOTIVO
    assert revisao.superseded_task_ids == ("T3",) and revisao.confirmed_task_ids == ()
    assert revisao.verdicts[0].justification == _JUSTIFICATIVA_SUBSTITUI
    assert revisao.approval_justification == _APROVACAO_REVISAO
    assert revisao.withdrawn_learnings == (_L_T3,)
    assert revisao.current_task_ids == ("T1", "T2", "T4")
    historico = [m.content for m in cenario.session.messages]
    assert _T3 in historico
    armazenamento = [m.content for m in cenario.session.messages if m.phase is Phase.B3_RESULT_STORAGE]
    assert any("Superseded results: `T3`" in conteudo for conteudo in armazenamento)
    assert any("**Reviews:** `T3`" in conteudo and _MOTIVO in conteudo for conteudo in historico)
    assert cenario.session.final_answer == eventos[-1].content
    assert cenario.session.status is SessionStatusEnum.COMPLETED


# ── Sem aprovação da correção ───────────────────────────────────────────────


async def test_correcao_reprovada_sem_tentativas_nao_substitui_nem_remove_aprendizados() -> None:
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_revisora()),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)),
        _relatorio_revisao("T4", False, "A investigação não demonstra o erro de T3."),
    ], cost_guard=FakeCostGuard(max_task_attempts=1))

    eventos = await _consumir(cenario)

    assert cenario.session.status is SessionStatusEnum.FAILED
    assert cenario.session.final_answer is None and eventos[-1].type.value == "error"
    assert Phase.C3_FINAL_ANSWER not in _fases(cenario)
    assert cenario.session.result_revisions == []
    assert _L_T3 in [learning.content for learning in cenario.learnings_memory.all()]
    assert cenario.session.failure.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count


async def test_tentativa_reprovada_nao_muda_estado_e_investigacao_que_confirma_mantem_o_resultado() -> None:
    confirmacao = "MARCA_T4C: a afirmação de T3 sobre a força se mantém sob as condições declaradas em T3."
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_revisora()),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)),
        _relatorio_revisao("T4", False, "A substituição não está demonstrada."),
        _resolucao("T4", confirmacao, ("T3", "confirmed", "As condições de T3 diferem das de T1.")),
        _relatorio_revisao("T4", True, "A confirmação está sustentada."),
        aprendizados(),
        _global(True, "As condições distintas foram explicadas."),
        resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2", "T3", "T4"]
    assert _L_T3 in _area(segunda_c1, "Key Learnings")
    assert _T4 not in _area(segunda_c1, "Stored results")
    [revisao] = cenario.session.result_revisions
    assert revisao.confirmed_task_ids == ("T3",) and revisao.superseded_task_ids == ()
    assert revisao.withdrawn_learnings == () and revisao.approval_justification == "A confirmação está sustentada."
    retentativa = _area(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[-1], "Previous attempts at this task")
    assert "`superseded`" in retentativa
    temperaturas = [i.temperature for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION]
    assert temperaturas[-2:] == [cenario.temperature, 1.0]


async def test_hipotese_diferente_sem_referencia_de_revisao_nao_substitui_por_ser_mais_recente() -> None:
    hipotese = "MARCA_T4H: com atrito de rolamento incluído, a força média nos blocos também é estimada."
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_tarefa("T4", "Estime a força média nos blocos incluindo o atrito de rolamento, explicando.")),
        *_tarefa_executada("T4", hipotese),
        _global(True, "Hipóteses distintas e explicitadas."),
        resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2", "T3", "T4"]
    assert _area(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[-1], "Results under review").endswith(_SEM_REVISAO)
    assert cenario.session.result_revisions == []
    assert _L_T3 in _area(segunda_c1, "Key Learnings")


async def test_tarefa_normal_que_propoe_revisao_e_recusada_pelo_contrato_e_corrigida_sem_mutacao() -> None:
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_tarefa("T4", "Investigue a força média, explicando.")),
        _resolucao("T4", _T4, ("T3", "superseded", "mais recente")),
        _resolucao("T4", _T4),
        relatorio(("T4-AC1", True)), aprendizados(),
        _global(True, "ok"), resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    recusada = [i for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION][-2]
    assert recusada.output_diagnostic.problem.code is OutputProblemCodeEnum.TASK_REFERENCES
    assert recusada.recovery.result is RecoveryResultEnum.RECOVERED
    assert cenario.session.result_revisions == []
    assert "T3" in _blocos(_area(_prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1], "Stored results"))


# ── Contrato de C.2: referências inválidas recusadas sem mutação parcial ───


@pytest.mark.parametrize(("invalido", "afetados"), [
    (_plano(_revisora(alvos=("T9",))), ("T9",)),
    (_plano(_revisora(alvos=("T4",))), ("T4",)),
    (_plano(_revisora(alvos=("T3", "T3"))), ("T3",)),
    (_plano(_revisora(depends_on=["T5"]), _tarefa("T5", "Outra investigação, explicando.")), ("T5",)),
    (_plano(_revisora(depends_on=["T3"])), ("T3",)),
], ids=["inexistente", "autorreferencia", "repetida", "dependencia_futura", "depende_do_alvo"])
async def test_c2_com_referencia_invalida_e_corrigida_antes_de_tocar_a_fila(invalido: str, afetados: tuple) -> None:
    cenario = _cenario([
        *_ate_a_contradicao(), invalido, _plano(_revisora()),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)), _relatorio_revisao("T4", True),
        aprendizados(), _global(True, "ok"), resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    recusada, corrigida = [i for i in cenario.session.invocations if i.phase is Phase.C2_ADDITIONAL_PLANNING]
    assert recusada.output_diagnostic.problem.affected_ids == afetados
    assert recusada.content_accepted is False and corrigida.recovers_invocation_id == recusada.id
    assert [i.task_id for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION][-1] == "T4"
    assert _fases(cenario).count(Phase.B1_TASK_RESOLUTION) == 4
    assert [r.superseded_task_ids for r in cenario.session.result_revisions] == [("T3",)]


# ── Dependências explícitas ────────────────────────────────────────────────


async def test_dependente_explicito_do_revisado_aguarda_revalidacao_e_independente_nao_e_refeito() -> None:
    l_t2 = "A força média sobre o motorista segue a força média de frenagem do carro com pneus travados."
    t2 = "MARCA_DEP_T2: o cinto exerce a maior força média no caso dos pneus travados, como derivado de T1."
    t3 = "MARCA_IND_T3: a energia dissipada é igual nos dois casos."
    t4 = "MARCA_DEP_T4: a força média é maior nos blocos; T1 usou um tempo de parada trocado."
    t5 = "MARCA_DEP_T5: o cinto exerce a maior força média no caso dos blocos, a partir de T4."
    cenario = _cenario([
        _criterios(),
        _plano(_tarefa("T1", "Determine onde a força média é maior, explicando."),
               _tarefa("T2", "Use a força de T1 para comparar a força do cinto, explicando.", depends_on=["T1"]),
               _tarefa("T3", "Determine a energia dissipada, explicando.")),
        aprendizados(_A3),
        *_tarefa_executada("T1", _T1, _L_T1),
        *_tarefa_executada("T2", t2, l_t2),
        *_tarefa_executada("T3", t3, _L_COMPARTILHADO),
        _global(False, "O tempo de parada de T1 contradiz os dados; investigar a força média."),
        _plano(_revisora(alvos=("T1",))),
        _resolucao("T4", t4, ("T1", "superseded", "Tempo de parada trocado em T1.")),
        _relatorio_revisao("T4", True), aprendizados(),
        _global(False, "T2 aguarda revalidação; a força do cinto não está vigente."),
        _plano(_tarefa("T5", "Revalide a força do cinto a partir do resultado vigente de T4, explicando.",
                       review={"task_ids": ["T2"], "reason": "T2 dependia de T1, substituído por T4."},
                       depends_on=["T4"])),
        _resolucao("T5", t5, ("T2", "superseded", "A força do cinto muda com a força corrigida.")),
        _relatorio_revisao("T5", True), aprendizados(),
        _global(True, "ok"), resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    assert [i.task_id for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION] == [
        "T1", "T2", "T3", "T4", "T5"]
    primeira, segunda, terceira = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)
    assert _blocos(_area(segunda, "Stored results")) == ["T3", "T4"]
    registro = _area(segunda, "Revision record")
    assert "`T2`" in registro and "depends on `T1`" in registro and t2 not in registro
    c2 = _prompts(cenario, Phase.C2_ADDITIONAL_PLANNING)[1]
    assert t2 in _area(c2, "Revision record") and t2 not in _area(c2, "Results already stored")
    assert l_t2 not in _area(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[-1], "Key Learnings")
    assert _blocos(_area(terceira, "Stored results")) == ["T3", "T4", "T5"]
    assert _area(terceira, "Stored results") == _area(_prompts(cenario, Phase.C3_FINAL_ANSWER)[0], "Stored results")
    primeira_revisao, segunda_revisao = cenario.session.result_revisions
    assert primeira_revisao.suspended_task_ids == ("T2",)
    assert set(primeira_revisao.withdrawn_learnings) == {_L_T1, l_t2}
    assert segunda_revisao.superseded_task_ids == ("T2",) and segunda_revisao.current_task_ids == ("T3", "T4", "T5")
    assert _blocos(_area(primeira, "Stored results")) == ["T1", "T2", "T3"]


async def test_revalidacao_que_confirma_o_dependente_o_restaura_com_seus_aprendizados() -> None:
    l_t2 = "A energia dissipada pelo cinto não depende do tempo de parada: só da variação de energia cinética."
    t2 = "MARCA_REST_T2: a energia dissipada pelo cinto é a mesma nos dois casos, independentemente de T1."
    cenario = _cenario([
        _criterios(),
        _plano(_tarefa("T1", "Determine onde a força média é maior, explicando."),
               _tarefa("T2", "Use T1 para analisar a energia dissipada pelo cinto, explicando.", depends_on=["T1"])),
        aprendizados(_A3),
        *_tarefa_executada("T1", _T1, _L_T1),
        *_tarefa_executada("T2", t2, l_t2),
        _global(False, "O tempo de parada de T1 contradiz os dados."),
        _plano(_revisora(task_id="T3", alvos=("T1",))),
        _resolucao("T3", _T4, ("T1", "superseded", "Tempo de parada trocado em T1.")),
        _relatorio_revisao("T3", True), aprendizados(_L_T4),
        _global(False, "T2 aguarda revalidação."),
        _plano(_tarefa("T4", "Revalide a energia dissipada pelo cinto, explicando.",
                       review={"task_ids": ["T2"], "reason": "T2 dependia de T1, substituído por T3."})),
        _resolucao("T4", "MARCA_REST_T4: a conclusão de T2 não usa a força de T1.",
                   ("T2", "confirmed", "A energia dissipada não depende do tempo de parada.")),
        _relatorio_revisao("T4", True, "A confirmação está demonstrada."), aprendizados(),
        _global(True, "ok"), resposta_final("ok"),
    ])

    await cenario.run(question=_PERGUNTA)

    terceira_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[2]
    assert _blocos(_area(terceira_c1, "Stored results")) == ["T2", "T3", "T4"]
    assert l_t2 in _area(terceira_c1, "Key Learnings") and _L_T1 not in _area(terceira_c1, "Key Learnings")
    registro = _area(terceira_c1, "Revision record")
    assert "`T1`" in registro and "Results awaiting revalidation" not in registro
    primeira, segunda = cenario.session.result_revisions
    assert primeira.suspended_task_ids == ("T2",) and set(primeira.withdrawn_learnings) == {_L_T1, l_t2}
    assert segunda.reinstated_task_ids == ("T2",) and segunda.restored_learnings == (l_t2,)
    armazenamento = [m.content for m in cenario.session.messages if m.phase is Phase.B3_RESULT_STORAGE]
    assert any("Reinstated results: `T2`" in c and "Learnings restored to the current view: 1." in c
               for c in armazenamento)


async def test_tarefa_planejada_sobre_resultado_substituido_no_mesmo_lote_nao_entra_na_sintese() -> None:
    t5 = "MARCA_T5_PENDENTE: o trabalho do atrito nos blocos segue a força de T3."
    fato_t5 = "O trabalho do atrito nos blocos é calculado com a força registrada para os blocos."
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_revisora(), _tarefa("T5", "Use a força de T3 para obter o trabalho do atrito, explicando.",
                                    depends_on=["T3"])),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)), _relatorio_revisao("T4", True),
        aprendizados(_L_T4),
        *_tarefa_executada("T5", t5, fato_t5),
        _global(True, "Os resultados vigentes bastam."), resposta_final("ok"),
    ])

    eventos = await cenario.run(question=_PERGUNTA)

    segunda_c1 = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)[1]
    assert _blocos(_area(segunda_c1, "Stored results")) == ["T1", "T2", "T4"]
    assert "`T5`" in _area(segunda_c1, "Revision record")
    assert _L_T3 not in _area(_prompts(cenario, Phase.B1_TASK_RESOLUTION)[-1], "Key Learnings")
    for prompt in (segunda_c1, _prompts(cenario, Phase.C3_FINAL_ANSWER)[0]):
        assert fato_t5 not in prompt and t5 not in _area(prompt, "Stored results")
    armazenamento = [e.content for e in eventos if e.subtype.value == "store" and e.task == "T5"]
    assert "Results awaiting revalidation: `T5`" in armazenamento[0]
    retido = [e.content for e in eventos if e.subtype.value == "learn" and e.task == "T5"][0]
    assert "withheld" in retido and fato_t5 in retido


# ── Limites e interrupção controlada ───────────────────────────────────────


async def test_sem_planejamento_adicional_a_contradicao_interrompe_sem_sintese_e_sem_revisao() -> None:
    cenario = _cenario(_ate_a_contradicao(), cost_guard=FakeCostGuard(additional_planning_allowed=False))

    await _consumir(cenario)

    assert cenario.session.status is SessionStatusEnum.FAILED and cenario.session.final_answer is None
    assert _fases(cenario)[-1] is Phase.C1_GLOBAL_VERIFICATION
    assert cenario.session.result_revisions == []
    assert cenario.session.failure.pending_criteria_ids == ("AC1",)
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count


async def test_interrupcao_depois_da_revisao_preserva_a_auditoria_e_nao_sintetiza() -> None:
    cost_guard = FakeCostGuard()
    cenario = _cenario([
        *_ate_a_contradicao(),
        _plano(_revisora(), _tarefa("T5", "Determine a energia dissipada de novo, explicando.")),
        _resolucao("T4", _T4, ("T3", "superseded", _JUSTIFICATIVA_SUBSTITUI)), _relatorio_revisao("T4", True),
        aprendizados(_L_T4),
    ], cost_guard=cost_guard)

    eventos = []
    with pytest.raises(ExecutionInterruptedError):
        async for evento in cenario.stream(question=_PERGUNTA):
            eventos.append(evento)
            if evento.subtype.value == "learn" and evento.task == "T4":
                cost_guard.authorized = False

    assert cenario.session.status is SessionStatusEnum.FAILED and cenario.session.final_answer is None
    assert [r.superseded_task_ids for r in cenario.session.result_revisions] == [("T3",)]
    assert "`T5`" in cenario.session.failure.description
    assert _fases(cenario).count(Phase.C1_GLOBAL_VERIFICATION) == 1
    assert cenario.session.totals.total_llm_calls == cenario.llm.call_count
    assert eventos[-1].type.value == "error"


async def _consumir(cenario: RalphScenario) -> list:
    eventos = []
    with pytest.raises(Exception):
        async for evento in cenario.stream(question=_PERGUNTA):
            eventos.append(evento)
    return eventos


def test_veredito_de_revisao_usa_somente_os_valores_do_contrato() -> None:
    assert {v.value for v in RevisionVerdictEnum} == {"confirmed", "superseded"}
