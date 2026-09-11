from src.domain.entities.thinking.learning import Learning
from src.domain.services.learnings_memory import LearningsMemory


def test_memoria_nova_esta_vazia_e_nao_renderiza_nada() -> None:
    memoria = LearningsMemory()

    assert memoria.is_empty() is True
    assert memoria.all() == ()
    assert memoria.render() == ""


def test_append_acumula_na_ordem_de_descoberta() -> None:
    memoria = LearningsMemory()
    primeiro = Learning(content="fato um", source_task_id="T1")
    segundo = Learning(content="fato dois", source_task_id="T2")

    memoria.append(learnings=[primeiro])
    memoria.append(learnings=[segundo])

    assert memoria.all() == (primeiro, segundo)
    assert memoria.is_empty() is False


def test_all_devolve_uma_tupla_imutavel() -> None:
    memoria = LearningsMemory()
    memoria.append(learnings=[Learning(content="fato um", source_task_id="T1")])

    acumulados = memoria.all()

    assert isinstance(acumulados, tuple)
    assert memoria.all() == acumulados


def test_append_de_lista_vazia_mantem_a_memoria_vazia() -> None:
    memoria = LearningsMemory()

    memoria.append(learnings=[])

    assert memoria.is_empty() is True
    assert memoria.render() == ""


def test_render_produz_bloco_markdown_com_um_item_por_aprendizado() -> None:
    memoria = LearningsMemory()
    memoria.append(
        learnings=[
            Learning(content="fato um", source_task_id="T1"),
            Learning(content="fato dois", source_task_id="T1"),
        ]
    )

    assert memoria.render() == "## Aprendizados acumulados\n\n- fato um\n- fato dois"
