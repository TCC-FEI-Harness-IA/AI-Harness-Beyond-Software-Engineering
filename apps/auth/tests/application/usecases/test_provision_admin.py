import pytest

from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from tests.application.conftest import AuthWorld


async def test_cria_administrador_novo(world: AuthWorld) -> None:
    admin = await world.provision_admin.execute(
        email="Admin@Exemplo.com", password="senha de admin forte", promote=False
    )

    assert admin.role is UserRoleEnum.ADMIN
    assert admin.email == "admin@exemplo.com"
    assert admin.password_hash.startswith("$argon2id$")


async def test_nao_promove_conta_existente_sem_pedido_explicito(world: AuthWorld) -> None:
    await world.register.execute(email="ana@exemplo.com", password="senha muito boa 1")

    with pytest.raises(EmailAlreadyRegisteredError):
        await world.provision_admin.execute(email="ana@exemplo.com", password=None, promote=False)


async def test_promove_conta_existente_mantendo_senha_e_identificador(world: AuthWorld) -> None:
    user = await world.register.execute(email="ana@exemplo.com", password="senha muito boa 1")

    admin = await world.provision_admin.execute(email="ana@exemplo.com", password=None, promote=True)

    assert admin.id == user.id
    assert admin.role is UserRoleEnum.ADMIN
    assert admin.password_hash == user.password_hash


async def test_criacao_exige_senha_valida(world: AuthWorld) -> None:
    with pytest.raises(InvalidRegistrationError):
        await world.provision_admin.execute(email="admin@exemplo.com", password=None, promote=False)
    with pytest.raises(InvalidRegistrationError):
        await world.provision_admin.execute(email="admin@exemplo.com", password="curta", promote=True)
    assert world.users.users == {}
