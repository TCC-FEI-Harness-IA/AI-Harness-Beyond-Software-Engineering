import dataclasses

import pytest

from src.domain.entities.thinking.criterion_evaluation import CriterionEvaluation


def test_carrega_os_campos_informados() -> None:
    avaliacao = CriterionEvaluation(criterion_id="c1", met=True, justification="atende ao critério")

    assert avaliacao.criterion_id == "c1"
    assert avaliacao.met is True
    assert avaliacao.justification == "atende ao critério"


def test_e_imutavel() -> None:
    avaliacao = CriterionEvaluation(criterion_id="c1", met=True, justification="atende ao critério")

    with pytest.raises(dataclasses.FrozenInstanceError):
        avaliacao.met = False
