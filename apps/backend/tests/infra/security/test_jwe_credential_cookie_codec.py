import base64
import json
import secrets
from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.credential_invalid_error import CredentialInvalidError
from src.infra.security.jwe_credential_cookie_codec import JweCredentialCookieCodec
from tests.doubles.controllable_clock import ControllableClock

_AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
_CHAVE = "sk-or-v1-chave-ficticia-de-teste-0123456789"


def _chave_aplicacao() -> bytes:
    return secrets.token_bytes(32)


def _usuario(user_id: str = "usr_1", session_id: str = "ses_1", horas: int = 24) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id, role="user", session_id=session_id,
        session_expires_at=_AGORA + timedelta(hours=horas), csrf_token="csrf",
    )


def _codec(chave: bytes, clock: ControllableClock | None = None) -> JweCredentialCookieCodec:
    return JweCredentialCookieCodec(encryption_key=chave, clock=clock or ControllableClock(_AGORA))


def test_cookie_e_jwe_compacto_cifrado_sem_a_chave_em_claro() -> None:
    codec = _codec(_chave_aplicacao())

    selado = codec.seal(api_key=_CHAVE, identity=_usuario())

    assert selado.value.count(".") == 4
    assert _CHAVE not in selado.value
    cabecalho = json.loads(base64.urlsafe_b64decode(selado.value.split(".")[0] + "=="))
    assert cabecalho["alg"] == "dir"
    assert cabecalho["enc"] == "A256GCM"
    assert selado.expires_at == _AGORA + timedelta(hours=24)


def test_abre_a_credencial_da_mesma_conta_e_sessao() -> None:
    codec = _codec(_chave_aplicacao())
    selado = codec.seal(api_key=_CHAVE, identity=_usuario())

    credencial = codec.open(value=selado.value, identity=_usuario())

    assert credencial.api_key == _CHAVE
    assert credencial.owner_id == "usr_1"
    assert credencial.session_id == "ses_1"


def test_validade_nunca_ultrapassa_o_fim_da_sessao() -> None:
    clock = ControllableClock(_AGORA)
    codec = _codec(_chave_aplicacao(), clock)
    selado = codec.seal(api_key=_CHAVE, identity=_usuario(horas=2))

    assert selado.expires_at == _AGORA + timedelta(hours=2)
    clock.advance(hours=2)
    with pytest.raises(CredentialInvalidError, match="expirou"):
        codec.open(value=selado.value, identity=_usuario(horas=2))


def test_credencial_de_outra_conta_ou_sessao_e_recusada() -> None:
    codec = _codec(_chave_aplicacao())
    selado = codec.seal(api_key=_CHAVE, identity=_usuario())

    with pytest.raises(CredentialInvalidError, match="outra"):
        codec.open(value=selado.value, identity=_usuario(user_id="usr_2"))
    with pytest.raises(CredentialInvalidError, match="outra"):
        codec.open(value=selado.value, identity=_usuario(session_id="ses_anterior"))


@pytest.mark.parametrize("posicao", [0, 2, 3, 4])
def test_cookie_adulterado_e_recusado(posicao: int) -> None:
    codec = _codec(_chave_aplicacao())
    partes = codec.seal(api_key=_CHAVE, identity=_usuario()).value.split(".")
    alvo = partes[posicao]
    partes[posicao] = alvo[:-2] + ("AA" if alvo[-2:] != "AA" else "BB")

    with pytest.raises(CredentialInvalidError):
        codec.open(value=".".join(partes), identity=_usuario())


def test_cookie_cifrado_com_outra_chave_de_aplicacao_e_recusado() -> None:
    selado = _codec(_chave_aplicacao()).seal(api_key=_CHAVE, identity=_usuario())

    with pytest.raises(CredentialInvalidError):
        _codec(_chave_aplicacao()).open(value=selado.value, identity=_usuario())


@pytest.mark.parametrize("lixo", ["", "abc", "a.b.c.d.e", "x" * 5000])
def test_valores_arbitrarios_sao_recusados(lixo: str) -> None:
    with pytest.raises(CredentialInvalidError):
        _codec(_chave_aplicacao()).open(value=lixo, identity=_usuario())


def test_jwt_apenas_assinado_ou_alg_none_nao_e_aceito() -> None:
    cabecalho = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=").decode()
    corpo = base64.urlsafe_b64encode(json.dumps({"key": _CHAVE}).encode()).rstrip(b"=").decode()

    with pytest.raises(CredentialInvalidError):
        _codec(_chave_aplicacao()).open(value=f"{cabecalho}.{corpo}.", identity=_usuario())


def test_payload_com_campos_faltando_e_recusado() -> None:
    from joserfc import jwe
    from joserfc.jwk import OctKey

    chave = _chave_aplicacao()
    token = jwe.encrypt_compact(
        {"alg": "dir", "enc": "A256GCM"}, json.dumps({"sub": "usr_1"}).encode(), OctKey.import_key(chave)
    )

    with pytest.raises(CredentialInvalidError):
        _codec(chave).open(value=token, identity=_usuario())


def test_chave_de_aplicacao_precisa_ter_256_bits() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        JweCredentialCookieCodec(encryption_key=b"curta", clock=ControllableClock(_AGORA))
