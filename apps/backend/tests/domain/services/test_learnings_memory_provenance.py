"""Proveniência dos aprendizados: retirar uma fonte só remove o que não tem outra fonte vigente.

A deduplicação continua textual (espaços normalizados). Uma repetição não entra de novo na área
"Aprendizados Pontuais", mas acrescenta a sua fonte ao fato já registrado. Nenhuma comparação
semântica é usada para retirar fatos.
"""
from src.domain.entities.thinking.learning import Learning
from src.domain.services.learnings_memory import LearningsMemory

_A3 = Learning(content="A massa do bloco é 2 kg.", source_task_id=None)
_T1 = Learning(content="A força média nos pneus é maior.", source_task_id="T1")
_T3 = Learning(content="A força média nos blocos é maior.", source_task_id="T3")
_T3_DISSIPACAO = Learning(content="A dissipação é igual nos dois casos.", source_task_id="T3")


def _memoria(*aprendizados: Learning) -> LearningsMemory:
    memoria = LearningsMemory()
    memoria.append(learnings=list(aprendizados))
    return memoria


def test_retirar_fonte_remove_da_visao_vigente_so_os_fatos_exclusivos_dela() -> None:
    memoria = _memoria(_A3, _T1, _T3, _T3_DISSIPACAO)

    retirados = memoria.withdraw(task_ids=("T3",))

    assert retirados == (_T3, _T3_DISSIPACAO)
    assert memoria.all() == (_A3, _T1)
    assert _T3.content not in memoria.render()


def test_fato_repetido_por_outra_fonte_continua_vigente_quando_a_primeira_e_retirada() -> None:
    repetido = Learning(content="  A força média nos   pneus é maior. ", source_task_id="T2")
    memoria = _memoria(_T1)

    assert memoria.append(learnings=[repetido]) == ()
    retirados = memoria.withdraw(task_ids=("T1",))

    assert retirados == ()
    assert memoria.all() == (_T1,)


def test_fato_do_enunciado_nunca_e_retirado_por_revisao_de_tarefa() -> None:
    copia_da_tarefa = Learning(content=_A3.content, source_task_id="T3")
    memoria = _memoria(_A3)
    memoria.append(learnings=[copia_da_tarefa])

    assert memoria.withdraw(task_ids=("T3",)) == ()
    assert memoria.all() == (_A3,)


def test_restaurar_fonte_devolve_os_fatos_a_visao_vigente_na_ordem_original() -> None:
    memoria = _memoria(_A3, _T3, _T1)
    memoria.withdraw(task_ids=("T3",))

    restaurados = memoria.restore(task_ids=("T3",))

    assert restaurados == (_T3,)
    assert memoria.all() == (_A3, _T3, _T1)
    assert memoria.restore(task_ids=("T3",)) == ()


def test_aprendizado_de_fonte_retirada_e_registrado_mas_nao_fica_vigente() -> None:
    memoria = _memoria(_A3)
    memoria.withdraw(task_ids=("T5",))

    aceitos = memoria.append(learnings=[Learning(content="Fato de T5.", source_task_id="T5")])

    assert aceitos == ()
    assert memoria.all() == (_A3,)
    assert memoria.restore(task_ids=("T5",)) == (Learning(content="Fato de T5.", source_task_id="T5"),)


def test_fato_retirado_volta_a_visao_quando_uma_fonte_vigente_o_registra_de_novo() -> None:
    memoria = _memoria(_T3)
    memoria.withdraw(task_ids=("T3",))
    nova_fonte = Learning(content=_T3.content, source_task_id="T4")

    aceitos = memoria.append(learnings=[nova_fonte])

    assert aceitos == (nova_fonte,)
    assert memoria.all() == (_T3,)
    assert memoria.withdraw(task_ids=("T3",)) == ()


def test_memoria_so_com_fatos_retirados_fica_vazia_na_visao_vigente() -> None:
    memoria = _memoria(_T3)

    memoria.withdraw(task_ids=("T3",))

    assert memoria.is_empty() is True
    assert memoria.render() == "No key learnings recorded so far."
