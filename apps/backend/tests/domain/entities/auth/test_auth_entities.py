from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.entities.llm.llm_credential import LLMCredential
from src.domain.errors.execution_not_authorized_error import ExecutionNotAuthorizedError
from src.domain.services.execution_authorization import ExecutionAuthorization
from tests.doubles.controllable_clock import ControllableClock as FakeClock

_AGORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
_CHAVE = "sk-or-v1-chave-ficticia-de-teste"


def _usuario(expira_em: datetime = _AGORA + timedelta(hours=24)) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="usr_1", role="user", session_id="ses_1", session_expires_at=expira_em, csrf_token="csrf"
    )


def _credencial(expira_em: datetime = _AGORA + timedelta(hours=24)) -> LLMCredential:
    return LLMCredential(api_key=_CHAVE, owner_id="usr_1", session_id="ses_1", expires_at=expira_em)


def test_representacoes_nunca_mostram_segredos() -> None:
    assert _CHAVE not in repr(_credencial())
    assert _CHAVE not in str(_credencial())
    assert "csrf" not in repr(_usuario())


def test_credencial_redige_a_chave_em_textos() -> None:
    assert _credencial().redact(f"erro com {_CHAVE} no corpo") == "erro com [REDACTED] no corpo"


def test_credencial_vazia_e_recusada() -> None:
    with pytest.raises(ValueError):
        LLMCredential(api_key="  ", owner_id="usr_1", session_id="ses_1", expires_at=_AGORA)


def test_admin_e_identificado_pelo_perfil() -> None:
    assert _usuario().is_admin is False
    assert AuthenticatedUser("usr_2", "admin", "ses_2", _AGORA, "c").is_admin is True


def test_autorizacao_vale_ate_o_menor_prazo_entre_sessao_e_credencial() -> None:
    clock = FakeClock(_AGORA)
    autorizacao = ExecutionAuthorization(
        identity=_usuario(), credential=_credencial(expira_em=_AGORA + timedelta(hours=1)), clock=clock
    )

    clock.advance(seconds=3599)
    autorizacao.ensure_active()
    assert autorizacao.owner_id == "usr_1"
    assert autorizacao.credential.api_key == _CHAVE

    clock.advance(seconds=1)
    with pytest.raises(ExecutionNotAuthorizedError):
        autorizacao.ensure_active()
    assert autorizacao.is_active is False


def test_revogacao_bloqueia_novas_chamadas() -> None:
    autorizacao = ExecutionAuthorization(identity=_usuario(), credential=_credencial(), clock=FakeClock(_AGORA))

    autorizacao.revoke("Sessão revogada.")

    with pytest.raises(ExecutionNotAuthorizedError, match="revogada"):
        autorizacao.ensure_active()
    assert isinstance(ExecutionNotAuthorizedError("x"), ValueError)


def test_credencial_de_outra_conta_ou_sessao_e_recusada() -> None:
    with pytest.raises(ValueError):
        ExecutionAuthorization(
            identity=_usuario(),
            credential=LLMCredential(api_key=_CHAVE, owner_id="usr_2", session_id="ses_1", expires_at=_AGORA),
            clock=FakeClock(_AGORA),
        )
    with pytest.raises(ValueError):
        ExecutionAuthorization(
            identity=_usuario(),
            credential=LLMCredential(api_key=_CHAVE, owner_id="usr_1", session_id="ses_9", expires_at=_AGORA),
            clock=FakeClock(_AGORA),
        )
