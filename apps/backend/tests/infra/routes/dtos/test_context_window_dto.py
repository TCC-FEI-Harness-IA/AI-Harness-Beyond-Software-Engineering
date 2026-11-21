from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO


def test_carrega_o_id_e_o_tamanho_da_janela() -> None:
    dto = ContextWindowDTO(context_id="3a7f2b1", context_size=182)

    assert dto.context_id == "3a7f2b1"
    assert dto.context_size == 182
