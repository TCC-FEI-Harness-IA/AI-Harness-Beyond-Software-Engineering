from datetime import timedelta

import pytest

from src.domain.errors.invalid_credentials_error import InvalidCredentialsError
from src.domain.errors.session_invalid_error import SessionInvalidError
from src.domain.errors.too_many_attempts_error import TooManyAttemptsError
from src.infra.adapters.argon2_password_hasher import Argon2PasswordHasher
from tests.application.conftest import TTL_24H, AuthWorld

_SENHA = "senha muito boa 1"


async def _cadastrar(world: AuthWorld, email: str = "ana@exemplo.com") -> None:
    await world.register.execute(email=email, password=_SENHA)


async def test_login_valido_cria_sessao_de_24h_sem_guardar_o_token(world: AuthWorld) -> None:
    await _cadastrar(world)

    result = await world.login.execute(email="ANA@exemplo.com", password=_SENHA, client_key="ip:1")

    assert result.user.email == "ana@exemplo.com"
    assert result.session.expires_at == world.clock.now() + timedelta(seconds=TTL_24H)
    assert result.session.created_at == world.clock.now()
    stored = list(world.sessions.sessions.values())
    assert len(stored) == 1
    assert stored[0].token_hash != result.token
    assert result.token not in repr(stored[0])
    assert result.session.csrf_token


async def test_login_com_senha_errada_ou_email_inexistente_tem_a_mesma_falha(world: AuthWorld) -> None:
    await _cadastrar(world)

    with pytest.raises(InvalidCredentialsError) as senha_errada:
        await world.login.execute(email="ana@exemplo.com", password="senha errada 99", client_key="ip:1")
    with pytest.raises(InvalidCredentialsError) as inexistente:
        await world.login.execute(email="outra@exemplo.com", password=_SENHA, client_key="ip:1")

    assert str(senha_errada.value) == str(inexistente.value)
    assert world.sessions.sessions == {}


async def test_email_malformado_no_login_vira_credencial_invalida(world: AuthWorld) -> None:
    with pytest.raises(InvalidCredentialsError):
        await world.login.execute(email="sem-arroba", password=_SENHA, client_key="ip:1")


async def test_tentativas_excessivas_bloqueiam_inclusive_a_senha_certa(world: AuthWorld) -> None:
    await _cadastrar(world)
    for _ in range(3):
        with pytest.raises(InvalidCredentialsError):
            await world.login.execute(email="ana@exemplo.com", password="senha errada 99", client_key="ip:1")

    with pytest.raises(TooManyAttemptsError) as bloqueio:
        await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:2")
    assert bloqueio.value.retry_after_seconds > 0

    world.clock.advance(seconds=601)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:2")
    assert result.user.email == "ana@exemplo.com"


async def test_login_bem_sucedido_zera_o_contador_do_email(world: AuthWorld) -> None:
    await _cadastrar(world)
    for _ in range(2):
        with pytest.raises(InvalidCredentialsError):
            await world.login.execute(email="ana@exemplo.com", password="senha errada 99", client_key="ip:1")
    await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:9")

    assert "email:ana@exemplo.com" not in world.limiter.counters


async def test_login_regrava_hash_com_parametros_desatualizados(world: AuthWorld) -> None:
    user = await world.register.execute(email="ana@exemplo.com", password=_SENHA)
    antigo = Argon2PasswordHasher(time_cost=1, memory_cost_kib=16, parallelism=2).hash(_SENHA)
    await world.users.update(user.with_password_hash(antigo))

    await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")

    assert world.users.users[user.id].password_hash != antigo


async def test_sessao_vale_ate_um_instante_antes_das_24h(world: AuthWorld) -> None:
    await _cadastrar(world)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")

    world.clock.advance(seconds=TTL_24H - 1)
    current = await world.resolve.execute(token=result.token)
    assert current.user.id == result.user.id
    assert current.session.id == result.session.id


async def test_sessao_expira_exatamente_nas_24h(world: AuthWorld) -> None:
    await _cadastrar(world)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")

    world.clock.advance(seconds=TTL_24H)

    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token=result.token)


async def test_atividade_nao_renova_a_sessao(world: AuthWorld) -> None:
    await _cadastrar(world)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")
    for _ in range(23):
        world.clock.advance(hours=1)
        await world.resolve.execute(token=result.token)

    world.clock.advance(hours=1)
    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token=result.token)


async def test_token_desconhecido_ou_vazio_e_recusado(world: AuthWorld) -> None:
    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token="token-que-nao-existe")
    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token="")


async def test_logout_revoga_e_copia_antiga_do_cookie_continua_recusada(world: AuthWorld) -> None:
    await _cadastrar(world)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")

    assert await world.logout.execute(token=result.token) is True

    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token=result.token)
    world.clock.advance(minutes=5)
    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token=result.token)
    assert await world.logout.execute(token=result.token) is False


async def test_logout_de_uma_sessao_nao_afeta_outra_do_mesmo_usuario(world: AuthWorld) -> None:
    await _cadastrar(world)
    primeira = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")
    segunda = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")

    await world.logout.execute(token=primeira.token)

    assert (await world.resolve.execute(token=segunda.token)).session.id == segunda.session.id


async def test_logout_sem_token_nao_falha(world: AuthWorld) -> None:
    assert await world.logout.execute(token="") is False


async def test_sessao_de_usuario_removido_e_recusada(world: AuthWorld) -> None:
    await _cadastrar(world)
    result = await world.login.execute(email="ana@exemplo.com", password=_SENHA, client_key="ip:1")
    world.users.users.clear()

    with pytest.raises(SessionInvalidError):
        await world.resolve.execute(token=result.token)
