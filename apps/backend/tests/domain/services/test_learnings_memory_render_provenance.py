"""Procedência visível na área Key Learnings (refinamentos 03, mudança 4).

`render()` mostra a origem de cada nota a partir dos metadados já existentes — o enunciado e as tarefas
vigentes que a registraram —, sem alterar o conteúdo armazenado, a chave de deduplicação, a ordem nem a
política de retirada e restauração. O rótulo indica origem, não veracidade: nenhuma nota é classificada
como hipótese ou como fato demonstrado.
"""
from src.domain.entities.thinking.learning import Learning
from src.domain.services.learnings_memory import LearningsMemory

_PRAZO = Learning(content="Prazo máximo: 10 dias.", source_task_id=None)
_ESTIMATIVA = Learning(
    content="Duração estimada de 8 dias, supondo disponibilidade integral da equipe.", source_task_id="T1"
)


def _memoria(*aprendizados: Learning) -> LearningsMemory:
    memoria = LearningsMemory()
    memoria.append(learnings=list(aprendizados))
    return memoria


def test_nota_do_enunciado_e_nota_de_tarefa_trazem_rotulos_de_origem_distintos() -> None:
    memoria = _memoria(_PRAZO, _ESTIMATIVA)

    assert memoria.render() == (
        "- [Question] Prazo máximo: 10 dias.\n"
        "- [Task T1] Duração estimada de 8 dias, supondo disponibilidade integral da equipe."
    )


def test_rotulo_nao_contamina_o_conteudo_armazenado_nem_a_visao_vigente() -> None:
    memoria = _memoria(_PRAZO, _ESTIMATIVA)
    memoria.render()

    assert memoria.all() == (_PRAZO, _ESTIMATIVA)
    assert [aprendizado.content for aprendizado in memoria.all()] == [_PRAZO.content, _ESTIMATIVA.content]
    assert all("[" not in aprendizado.content for aprendizado in memoria.all())


def test_nota_com_varias_fontes_vigentes_mostra_todas_na_ordem_de_registro() -> None:
    memoria = _memoria(_ESTIMATIVA)
    memoria.append(learnings=[Learning(content=_ESTIMATIVA.content, source_task_id="T3")])

    assert memoria.render() == f"- [Tasks T1, T3] {_ESTIMATIVA.content}"


def test_nota_do_enunciado_reestabelecida_por_tarefa_mostra_as_duas_origens() -> None:
    memoria = _memoria(_PRAZO)
    memoria.append(learnings=[Learning(content=_PRAZO.content, source_task_id="T2")])

    assert memoria.render() == f"- [Question; Task T2] {_PRAZO.content}"


def test_retirar_a_primeira_fonte_mantem_a_nota_com_a_fonte_vigente_e_sem_a_retirada() -> None:
    memoria = _memoria(_ESTIMATIVA)
    memoria.append(learnings=[Learning(content=_ESTIMATIVA.content, source_task_id="T4")])

    memoria.withdraw(task_ids=("T1",))

    # O objeto `Learning` conserva o identificador inicial, mas a procedência exibida é só a vigente.
    assert memoria.all() == (_ESTIMATIVA,) and memoria.all()[0].source_task_id == "T1"
    assert memoria.render() == f"- [Task T4] {_ESTIMATIVA.content}"


def test_retirar_todas_as_fontes_de_tarefa_some_e_restaurar_devolve_com_a_procedencia() -> None:
    memoria = _memoria(_PRAZO, _ESTIMATIVA)
    memoria.append(learnings=[Learning(content=_ESTIMATIVA.content, source_task_id="T3")])

    memoria.withdraw(task_ids=("T1", "T3"))
    assert memoria.render() == f"- [Question] {_PRAZO.content}"

    memoria.restore(task_ids=("T3",))
    assert memoria.render() == f"- [Question] {_PRAZO.content}\n- [Task T3] {_ESTIMATIVA.content}"

    memoria.restore(task_ids=("T1",))
    assert memoria.render() == f"- [Question] {_PRAZO.content}\n- [Tasks T1, T3] {_ESTIMATIVA.content}"


def test_fonte_do_enunciado_e_preservada_quando_a_copia_da_tarefa_e_retirada() -> None:
    memoria = _memoria(_PRAZO)
    memoria.append(learnings=[Learning(content=_PRAZO.content, source_task_id="T2")])

    memoria.withdraw(task_ids=("T2",))

    assert memoria.render() == f"- [Question] {_PRAZO.content}"
    memoria.restore(task_ids=("T2",))
    assert memoria.render() == f"- [Question; Task T2] {_PRAZO.content}"


def test_deduplicacao_continua_textual_e_independente_dos_rotulos() -> None:
    memoria = _memoria(_ESTIMATIVA)

    repetido = Learning(content=f"  {_ESTIMATIVA.content}  ", source_task_id="T2")
    rotulado = Learning(content=f"[Task T1] {_ESTIMATIVA.content}", source_task_id="T2")

    assert memoria.append(learnings=[repetido]) == ()
    # Um texto que copia o rótulo não é o mesmo conteúdo: a memória não interpreta nem remove prefixos.
    assert memoria.append(learnings=[rotulado]) == (rotulado,)
    assert memoria.render().splitlines()[0] == f"- [Tasks T1, T2] {_ESTIMATIVA.content}"


def test_hipoteses_qualificadores_e_associacoes_sobrevivem_a_renderizacao() -> None:
    notas = (
        Learning(content="Velocidade média ≈ 20,8 m/s (75 km/h), supondo trajeto sem paradas.", source_task_id="T1"),
        Learning(content="Alternativas: A) 12 kΩ; B) 4 kΩ; C) 3 kΩ.", source_task_id=None),
        Learning(
            content="Sob pressão constante, o volume final é 2,0 L (melhor ajuste: opção B).", source_task_id="T2"
        ),
    )
    memoria = _memoria(*notas)

    renderizado = memoria.render()

    for nota in notas:
        assert nota.content in renderizado


def test_sem_notas_vigentes_o_aviso_permanece_sem_rotulo() -> None:
    memoria = _memoria(_ESTIMATIVA)
    memoria.withdraw(task_ids=("T1",))

    assert memoria.render() == "No key learnings recorded so far."
