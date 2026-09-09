from src.infra.adapters.id_generator_adapter import IdGeneratorAdapter
from tests.doubles.fake_settings import FakeSettings


def _build_adapter(prefix: str = "sess") -> IdGeneratorAdapter:
    return IdGeneratorAdapter(settings=FakeSettings(ralph_session_id_prefix=prefix))


def test_id_de_sessao_usa_o_prefixo_das_configuracoes() -> None:
    identificador = _build_adapter(prefix="tcc").new_session_id()

    assert identificador.startswith("tcc_")
    assert len(identificador) > len("tcc_")


def test_ids_de_sessao_sucessivos_sao_distintos() -> None:
    gerador = _build_adapter()

    assert gerador.new_session_id() != gerador.new_session_id()


def test_id_de_mensagem_e_nao_vazio_e_distinto_a_cada_chamada() -> None:
    gerador = _build_adapter()

    primeiro = gerador.new_message_id()
    segundo = gerador.new_message_id()

    assert primeiro
    assert primeiro != segundo


def test_id_de_contexto_tem_sete_caracteres() -> None:
    assert len(_build_adapter().new_context_id()) == 7


def test_ids_de_contexto_sucessivos_sao_distintos() -> None:
    gerador = _build_adapter()

    assert gerador.new_context_id() != gerador.new_context_id()
