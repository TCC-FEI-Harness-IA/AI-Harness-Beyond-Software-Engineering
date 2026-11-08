"""Livro dos resultados de B.3: estado vigente derivado só de referências estruturadas aprovadas.

Ordem temporal, palavras como "correção" e semelhança textual nunca mudam o estado. Um resultado
só deixa de ser vigente por um veredito `superseded` aprovado ou por depender, explicitamente, de
um resultado que deixou de ser vigente.
"""
import pytest

from src.domain.entities.thinking.revision_verdict import RevisionVerdict
from src.domain.entities.thinking.task_result import TaskResult
from src.domain.enums.result_status_enum import ResultStatusEnum
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
from src.domain.services.results_ledger import ResultsLedger

_SUBSTITUI = RevisionVerdictEnum.SUPERSEDED
_CONFIRMA = RevisionVerdictEnum.CONFIRMED


def _resultado(
    task_id: str, *depends_on: str, verdicts: tuple[tuple[str, RevisionVerdictEnum], ...] = (),
) -> TaskResult:
    return TaskResult(
        task_id=task_id, task_title=f"titulo {task_id}", task_description=f"enunciado {task_id}",
        content=f"conteudo {task_id}", conclusion=f"conclusao {task_id}", depends_on=depends_on,
        revision_verdicts=tuple(
            RevisionVerdict(task_id=target, verdict=verdict, justification=f"motivo {target}")
            for target, verdict in verdicts
        ),
    )


def _livro(*resultados: TaskResult) -> ResultsLedger:
    livro = ResultsLedger()
    for resultado in resultados:
        livro.store(result=resultado)
    return livro


def _ids(resultados: tuple[TaskResult, ...]) -> tuple[str, ...]:
    return tuple(resultado.task_id for resultado in resultados)


def test_resultados_normais_ficam_vigentes_na_ordem_de_armazenamento() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2"))

    assert _ids(livro.current()) == ("T1", "T2") == livro.current_task_ids()
    assert livro.status_of(task_id="T2") is ResultStatusEnum.CURRENT
    assert livro.get(task_id="T1").content == "conteudo T1"
    assert livro.reviewable_task_ids() == frozenset({"T1", "T2"})
    assert livro.superseded() == () and livro.awaiting_revalidation() == ()


def test_resultado_mais_recente_e_divergente_sem_veredito_nao_substitui_nada() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2"))

    mudanca = livro.store(result=_resultado("T3"))

    assert _ids(livro.current()) == ("T1", "T2", "T3")
    assert mudanca.is_empty()


def test_veredito_superseded_aprovado_tira_o_alvo_do_estado_vigente_sem_apaga_lo() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2"), _resultado("T3"))

    mudanca = livro.store(result=_resultado("T4", verdicts=(("T3", _SUBSTITUI),)))

    assert _ids(livro.current()) == ("T1", "T2", "T4")
    assert _ids(livro.superseded()) == ("T3",)
    assert livro.get(task_id="T3").content == "conteudo T3"
    assert livro.superseded_by(task_id="T3") == "T4"
    assert livro.superseded_by(task_id="T1") is None
    assert mudanca.superseded_task_ids == ("T3",)
    assert mudanca.withdrawn_task_ids == ("T3",)
    assert livro.reviewable_task_ids() == frozenset({"T1", "T2", "T4"})


def test_veredito_confirmed_mantem_o_alvo_vigente() -> None:
    livro = _livro(_resultado("T1"), _resultado("T3"))

    mudanca = livro.store(result=_resultado("T4", verdicts=(("T3", _CONFIRMA),)))

    assert _ids(livro.current()) == ("T1", "T3", "T4")
    assert mudanca.confirmed_task_ids == ("T3",)
    assert mudanca.withdrawn_task_ids == () and mudanca.reinstated_task_ids == ()


def test_dependente_explicito_do_substituido_aguarda_revalidacao_e_independente_continua() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"), _resultado("T3", "T2"), _resultado("T4"))

    mudanca = livro.store(result=_resultado("T5", verdicts=(("T1", _SUBSTITUI),)))

    assert _ids(livro.current()) == ("T4", "T5")
    assert _ids(livro.awaiting_revalidation()) == ("T2", "T3")
    assert mudanca.suspended_task_ids == ("T2", "T3")
    assert mudanca.withdrawn_task_ids == ("T1", "T2", "T3")
    assert livro.reviewable_task_ids() == frozenset({"T2", "T3", "T4", "T5"})


def test_confirmacao_de_resultado_em_revalidacao_o_restaura_sem_restaurar_dependentes_transitivos() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"), _resultado("T3", "T2"))
    livro.store(result=_resultado("T4", verdicts=(("T1", _SUBSTITUI),)))

    mudanca = livro.store(result=_resultado("T5", verdicts=(("T2", _CONFIRMA),)))

    assert _ids(livro.current()) == ("T2", "T4", "T5")
    assert _ids(livro.awaiting_revalidation()) == ("T3",)
    assert mudanca.reinstated_task_ids == ("T2",)
    assert mudanca.withdrawn_task_ids == ()

    livro.store(result=_resultado("T6"))
    assert livro.status_of(task_id="T2") is ResultStatusEnum.CURRENT


def test_substituir_e_confirmar_na_mesma_revisao_aplica_a_substituicao_antes_da_confirmacao() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"))

    mudanca = livro.store(result=_resultado("T3", verdicts=(("T2", _CONFIRMA), ("T1", _SUBSTITUI))))

    assert _ids(livro.current()) == ("T2", "T3")
    assert mudanca.superseded_task_ids == ("T1",) and mudanca.confirmed_task_ids == ("T2",)
    assert mudanca.suspended_task_ids == ()


def test_resultado_novo_que_depende_de_resultado_nao_vigente_entra_aguardando_revalidacao() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", verdicts=(("T1", _SUBSTITUI),)))

    mudanca = livro.store(result=_resultado("T3", "T1"))

    assert livro.status_of(task_id="T3") is ResultStatusEnum.AWAITING_REVALIDATION
    assert mudanca.suspended_task_ids == ("T3",)


def test_revisora_que_depende_de_dependente_do_alvo_tambem_aguarda_revalidacao() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"))

    mudanca = livro.store(result=_resultado("T3", "T2", verdicts=(("T1", _SUBSTITUI),)))

    assert mudanca.suspended_task_ids == ("T2", "T3")
    assert livro.current() == ()


def test_revisao_de_resultado_em_revalidacao_pode_substitui_lo() -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"))
    livro.store(result=_resultado("T3", verdicts=(("T1", _SUBSTITUI),)))

    livro.store(result=_resultado("T4", verdicts=(("T2", _SUBSTITUI),)))

    assert _ids(livro.superseded()) == ("T1", "T2")
    assert livro.superseded_by(task_id="T2") == "T4"


@pytest.mark.parametrize(("resultado", "motivo"), [
    (_resultado("T1"), "já foi armazenado"),
    (_resultado("T9", verdicts=(("T8", _SUBSTITUI),)), "não é um resultado"),
    (_resultado("T9", verdicts=(("T3", _SUBSTITUI),)), "não pode ser revisado"),
    (_resultado("T9", verdicts=(("T9", _SUBSTITUI),)), "não pode revisar a si"),
    (_resultado("T9", verdicts=(("T2", _SUBSTITUI), ("T2", _CONFIRMA))), "mais de um veredito"),
    (_resultado("T9", "T8"), "não é um resultado"),
    (_resultado("T9", "T9"), "não pode depender de si"),
    (_resultado("T9", "T2", verdicts=(("T2", _SUBSTITUI),)), "não pode depender de um resultado que revisa"),
])
def test_referencias_invalidas_sao_recusadas_sem_mutacao_parcial(resultado: TaskResult, motivo: str) -> None:
    livro = _livro(_resultado("T1"), _resultado("T2"), _resultado("T3"),
                   _resultado("T4", verdicts=(("T3", _SUBSTITUI),)))
    antes = (_ids(livro.current()), _ids(livro.superseded()), _ids(livro.awaiting_revalidation()))

    with pytest.raises(ValueError, match=motivo):
        livro.store(result=resultado)

    assert (_ids(livro.current()), _ids(livro.superseded()), _ids(livro.awaiting_revalidation())) == antes


def test_consulta_de_resultado_inexistente_e_recusada() -> None:
    with pytest.raises(KeyError):
        ResultsLedger().get(task_id="T1")


@pytest.mark.parametrize("ordem", [("T2", "T3"), ("T3", "T2")])
def test_confirmacoes_encadeadas_na_mesma_revisao_preservam_a_dependencia_qualquer_que_seja_a_ordem(
    ordem: tuple[str, str],
) -> None:
    livro = _livro(_resultado("T1"), _resultado("T2", "T1"), _resultado("T3", "T2"))
    livro.store(result=_resultado("T4", verdicts=(("T1", _SUBSTITUI),)))

    mudanca = livro.store(result=_resultado("T5", verdicts=tuple((alvo, _CONFIRMA) for alvo in ordem)))

    assert _ids(livro.current()) == ("T2", "T3", "T4", "T5")
    assert set(mudanca.reinstated_task_ids) == {"T2", "T3"}

    substituicao = livro.store(result=_resultado("T6", verdicts=(("T2", _SUBSTITUI),)))

    assert substituicao.suspended_task_ids == ("T3",)
    assert _ids(livro.awaiting_revalidation()) == ("T3",)
