import io

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.enums.user_role_enum import UserRoleEnum
from src.infra.cli import admin_cli
from src.infra.config.settings import Settings
from src.infra.startups.auth_container import AuthContainer
from tests.doubles.fakes import FakeClock, fast_hasher

_TOKEN = "segredo-interno-de-teste-com-mais-de-32-caracteres"


@pytest.fixture
def container(monkeypatch: pytest.MonkeyPatch) -> AuthContainer:
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    monkeypatch.delenv("APP_ENV", raising=False)
    return AuthContainer(
        settings=Settings(), mongo_client=AsyncMongoMockClient(tz_aware=True), clock=FakeClock(), hasher=fast_hasher()
    )


async def test_cria_admin_lendo_senha_da_entrada_padrao(container: AuthContainer, capsys) -> None:
    codigo = await admin_cli.run(
        ["create-admin", "--email", "Admin@Exemplo.com", "--password-stdin"],
        container=container,
        stdin=io.StringIO("senha de admin forte\n"),
    )

    assert codigo == 0
    admin = await container.users.find_by_email("admin@exemplo.com")
    assert admin is not None and admin.role is UserRoleEnum.ADMIN
    saida = capsys.readouterr().out
    assert admin.id in saida
    assert "senha de admin forte" not in saida


async def test_senha_interativa_precisa_ser_confirmada(container: AuthContainer, capsys) -> None:
    respostas = iter(["senha de admin forte", "outra senha diferente"])

    codigo = await admin_cli.run(
        ["create-admin", "--email", "admin@exemplo.com"], container=container, prompt=lambda _: next(respostas)
    )

    assert codigo == 2
    assert "não conferem" in capsys.readouterr().err
    assert await container.users.find_by_email("admin@exemplo.com") is None


async def test_senha_interativa_confirmada(container: AuthContainer) -> None:
    codigo = await admin_cli.run(
        ["create-admin", "--email", "admin@exemplo.com"], container=container, prompt=lambda _: "senha de admin forte"
    )

    assert codigo == 0


async def test_promove_conta_existente_so_com_flag(container: AuthContainer, capsys) -> None:
    await container.register_user.execute(email="ana@exemplo.com", password="senha muito boa 1")

    sem_flag = await admin_cli.run(
        ["create-admin", "--email", "ana@exemplo.com"], container=container, prompt=lambda _: "senha de admin forte"
    )
    com_flag = await admin_cli.run(["create-admin", "--email", "ana@exemplo.com", "--promote"], container=container)

    assert sem_flag == 2
    assert com_flag == 0
    assert (await container.users.find_by_email("ana@exemplo.com")).role is UserRoleEnum.ADMIN


async def test_senha_fraca_e_recusada(container: AuthContainer, capsys) -> None:
    codigo = await admin_cli.run(
        ["create-admin", "--email", "admin@exemplo.com", "--password-stdin"], container=container,
        stdin=io.StringIO("curta\n"),
    )

    assert codigo == 2
    assert "12" in capsys.readouterr().err


def test_senha_nunca_e_aceita_como_argumento() -> None:
    with pytest.raises(SystemExit):
        admin_cli.build_parser().parse_args(["create-admin", "--email", "a@b.co", "--password", "x"])


def test_main_monta_o_container_real(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[list[str]] = []

    async def _run(argv: list[str], container: object, **_: object) -> int:
        chamadas.append(argv)
        assert isinstance(container, AuthContainer)
        return 0

    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", _TOKEN)
    monkeypatch.setattr(admin_cli, "run", _run)

    assert admin_cli.main(["create-admin", "--email", "a@b.co"]) == 0
    assert chamadas == [["create-admin", "--email", "a@b.co"]]
