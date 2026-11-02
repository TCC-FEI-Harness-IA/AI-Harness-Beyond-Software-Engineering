import pytest

from src.domain.entities.thinking.learning import Learning
from src.domain.services.learnings_memory import LearningsMemory


_AVISO_SEM_APRENDIZADOS = "Nenhum aprendizado pontual registrado até o momento."


def test_memoria_nova_esta_vazia_e_renderiza_o_aviso_de_que_nao_ha_aprendizados() -> None:
    memoria = LearningsMemory()

    assert memoria.is_empty() is True
    assert memoria.all() == ()
    assert memoria.render() == _AVISO_SEM_APRENDIZADOS


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
    assert memoria.render() == _AVISO_SEM_APRENDIZADOS


def test_render_produz_a_lista_markdown_com_um_item_por_aprendizado_sem_titulo() -> None:
    memoria = LearningsMemory()
    memoria.append(
        learnings=[
            Learning(content="fato um", source_task_id="T1"),
            Learning(content="fato dois", source_task_id="T1"),
        ]
    )

    # O título da área ("## Aprendizados Pontuais") pertence a cada template; a memória entrega só os itens.
    assert memoria.render() == "- fato um\n- fato dois"


# ── Aprendizados repetidos ───────────────────────────────────────────────────


def test_append_devolve_os_aprendizados_efetivamente_acumulados() -> None:
    memoria = LearningsMemory()
    fatos = [Learning(content="fato um", source_task_id="T1"), Learning(content="fato dois", source_task_id="T1")]

    acumulados = memoria.append(learnings=fatos)

    assert acumulados == tuple(fatos)


def test_append_descarta_um_aprendizado_ja_registrado_com_espacos_diferentes() -> None:
    memoria = LearningsMemory()
    original = Learning(content="A afirmação I é verdadeira: C ⊆ A implica A ∩ C = C.", source_task_id="T1")
    memoria.append(learnings=[original])
    novo = Learning(content="A velocidade média é 20 m/s.", source_task_id="T2")

    acumulados = memoria.append(
        learnings=[
            Learning(content="  A afirmação I é   verdadeira: C ⊆ A implica A ∩ C = C. ", source_task_id="T2"),
            novo,
        ]
    )

    assert acumulados == (novo,)
    assert memoria.all() == (original, novo)


def test_append_descarta_repeticoes_dentro_do_mesmo_lote() -> None:
    memoria = LearningsMemory()
    primeiro = Learning(content="fato um", source_task_id="T1")

    acumulados = memoria.append(learnings=[primeiro, Learning(content="fato  um", source_task_id="T1")])

    assert acumulados == (primeiro,)
    assert memoria.render() == "- fato um"


@pytest.mark.parametrize("separar_lotes", [False, True])
@pytest.mark.parametrize("conteudos", [
    ("A concentração de CO é 1 mol/L.", "A concentração de Co é 1 mol/L."),
    ("O comprimento é 1 Mm.", "O comprimento é 1 mm."),
    ("r = 2.", "R = 2."),
])
def test_append_preserva_simbolos_distintos_por_maiusculas(
    conteudos: tuple[str, str], separar_lotes: bool,
) -> None:
    memoria = LearningsMemory()
    fatos = tuple(Learning(content=conteudo, source_task_id=f"T{i}") for i, conteudo in enumerate(conteudos, 1))

    if separar_lotes:
        memoria.append(learnings=[fatos[0]])
        assert memoria.append(learnings=[fatos[1]]) == (fatos[1],)
    else:
        assert memoria.append(learnings=fatos) == fatos

    assert memoria.all() == fatos
    assert memoria.render() == "\n".join(f"- {conteudo}" for conteudo in conteudos)


def test_append_descarta_aprendizados_em_branco() -> None:
    memoria = LearningsMemory()

    acumulados = memoria.append(learnings=[Learning(content="   ", source_task_id="T1")])

    assert acumulados == ()
    assert memoria.is_empty() is True
