import pytest

from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from tests.application.conftest import AuthWorld


async def test_cadastro_cria_usuario_comum_com_hash(world: AuthWorld) -> None:
    user = await world.register.execute(email=" Ana@Exemplo.com ", password="senha muito boa 1")

    assert user.id.startswith("usr_")
    assert user.email == "ana@exemplo.com"
    assert user.role is UserRoleEnum.USER
    assert user.password_hash.startswith("$argon2id$")
    assert "senha muito boa 1" not in user.password_hash
    assert world.users.users[user.id] == user


async def test_email_ja_cadastrado_com_outra_grafia_e_recusado(world: AuthWorld) -> None:
    await world.register.execute(email="ana@exemplo.com", password="senha muito boa 1")

    with pytest.raises(EmailAlreadyRegisteredError):
        await world.register.execute(email="ANA@exemplo.com", password="outra senha boa 2")
    assert len(world.users.users) == 1


async def test_senha_fraca_nao_cria_conta(world: AuthWorld) -> None:
    with pytest.raises(InvalidRegistrationError):
        await world.register.execute(email="ana@exemplo.com", password="curta")
    assert world.users.users == {}
