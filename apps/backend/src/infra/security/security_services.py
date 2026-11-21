import logging
from dataclasses import dataclass

from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.execution_limiter_interface import IExecutionLimiter
from src.domain.interfaces.identity_provider_interface import IIdentityProvider
from src.domain.interfaces.llm_key_validator_interface import ILLMKeyValidator
from src.infra.config.security_settings import SecuritySettings
from src.infra.security.auth_service_identity_provider import AuthServiceIdentityProvider
from src.infra.security.in_memory_execution_limiter import InMemoryExecutionLimiter
from src.infra.security.jwe_credential_cookie_codec import JweCredentialCookieCodec
from src.infra.security.openrouter_key_validator import OpenRouterKeyValidator


@dataclass(frozen=True)
class SecurityServices:
    """Serviços de segurança compartilhados pelo processo (ficam em `app.state.security`).

    O limitador precisa ser único por processo; os demais são sem estado. Em produção são sempre
    os reais (`from_settings`); os testes trocam apenas identidade e validação de chave.
    """

    settings: SecuritySettings
    clock: IClock
    identity_provider: IIdentityProvider
    key_validator: ILLMKeyValidator
    credential_codec: JweCredentialCookieCodec
    execution_limiter: IExecutionLimiter

    @classmethod
    def build(
        cls,
        settings: SecuritySettings,
        clock: IClock,
        identity_provider: IIdentityProvider,
        key_validator: ILLMKeyValidator,
    ) -> "SecurityServices":
        """Monta os serviços a partir de identidade e validação já escolhidas."""
        return cls(
            settings=settings,
            clock=clock,
            identity_provider=identity_provider,
            key_validator=key_validator,
            credential_codec=JweCredentialCookieCodec(encryption_key=settings.credential_encryption_key, clock=clock),
            execution_limiter=InMemoryExecutionLimiter(
                clock=clock,
                max_concurrent=settings.max_concurrent_runs_per_user,
                max_starts=settings.max_run_starts_per_window,
                window_seconds=settings.run_starts_window_seconds,
            ),
        )

    @classmethod
    def from_settings(cls, settings: SecuritySettings, clock: IClock, logger: logging.Logger) -> "SecurityServices":
        """Serviços reais: serviço de autenticação e OpenRouter."""
        return cls.build(
            settings=settings,
            clock=clock,
            identity_provider=AuthServiceIdentityProvider(
                base_url=settings.auth_service_url, internal_token=settings.internal_token, logger=logger
            ),
            key_validator=OpenRouterKeyValidator(validation_url=settings.key_validation_url, logger=logger),
        )
