import pytest
from motor.motor_asyncio import AsyncIOMotorCollection

from src.infra.adapters import mongo_client_adapter
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from tests.doubles.fake_settings import FakeSettings


def _build_adapter(**settings_overrides: object) -> MongoClientAdapter:
    return MongoClientAdapter(settings=FakeSettings(**settings_overrides))


def test_sessions_collection_usa_o_banco_e_a_colecao_configurados() -> None:
    adapter = _build_adapter(mongodb_database="banco_de_teste", mongodb_sessions_collection="colecao_de_teste")

    colecao = adapter.sessions_collection

    assert isinstance(colecao, AsyncIOMotorCollection)
    assert colecao.name == "colecao_de_teste"
    assert colecao.database.name == "banco_de_teste"


def test_cliente_e_construido_com_a_uri_configurada(monkeypatch: pytest.MonkeyPatch) -> None:
    uris_recebidas: list[str] = []

    class _ClienteFalso:
        def __init__(self, uri: str) -> None:
            uris_recebidas.append(uri)

        def __getitem__(self, database_name: str) -> object:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", _ClienteFalso)

    _build_adapter(mongodb_uri="mongodb://mongo-de-teste:27017")

    assert uris_recebidas == ["mongodb://mongo-de-teste:27017"]


def test_close_encerra_o_cliente_sem_levantar_excecao() -> None:
    adapter = _build_adapter()

    adapter.close()
