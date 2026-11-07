"""A memória não interpreta símbolos, unidades, referentes ou condições."""
import pytest

from src.domain.entities.thinking.learning import Learning
from src.domain.services.learnings_memory import LearningsMemory


@pytest.mark.parametrize("contents", [
    ("A = 1.", "a = 1."),
    ("Distância da imagem: 130 mm da objetiva.", "Distância da imagem: 130 mm da ocular."),
    ("Comprimento da haste: 1 m.", "Comprimento da haste: 1 mm."),
    ("O volume dobra sob pressão constante.", "O volume dobra sob temperatura constante."),
    ("O volume do gás A dobra.", "O volume do gás B dobra."),
    ("Distância: aproximadamente 47 mm.", "Distância: exatamente 47 mm."),
])
def test_diferencas_de_significado_nao_sao_deduplicadas(contents: tuple[str, str]) -> None:
    memory = LearningsMemory()
    given = Learning(content=contents[0])
    derived = Learning(content=contents[1], source_task_id="T1")

    assert memory.append(learnings=[given]) == (given,)
    assert memory.append(learnings=[Learning(content=" \t" + contents[0] + "\n", source_task_id="T1"),
                                    derived, derived, Learning(content=" \t\n")]) == (derived,)
    assert memory.append(learnings=[]) == ()
    assert memory.all() == (given, derived)  # A primeira origem permanece após duplicatas.
    assert memory.render() == f"- {contents[0]}\n- {contents[1]}"


def test_conteudo_multilinha_preserva_associacoes_e_apenas_compara_espacos() -> None:
    memory = LearningsMemory()
    literal = "Tabela:\n1 — cálcio\n2 — cloreto\nAlternativas: A) 1; B) 2."
    note = Learning(content=literal)

    assert memory.append(learnings=[note]) == (note,)
    assert memory.append(learnings=[Learning(content=" ".join(literal.split()), source_task_id="T1")]) == ()
    assert memory.all() == (note,)
    assert memory.render() == f"- {literal}"
