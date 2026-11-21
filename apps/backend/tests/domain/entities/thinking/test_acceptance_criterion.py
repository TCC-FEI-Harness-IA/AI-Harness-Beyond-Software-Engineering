import dataclasses

import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion


def test_carrega_id_e_descricao() -> None:
    criterio = AcceptanceCriterion(id="c1", description="resposta em portugues")

    assert criterio.id == "c1"
    assert criterio.description == "resposta em portugues"


def test_e_imutavel() -> None:
    criterio = AcceptanceCriterion(id="c1", description="resposta em portugues")

    with pytest.raises(dataclasses.FrozenInstanceError):
        criterio.id = "outro"
