from collections.abc import Awaitable, Callable

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.entities.llm.llm_credential import LLMCredential
from src.domain.errors.execution_not_authorized_error import ExecutionNotAuthorizedError
from src.domain.interfaces.clock_interface import IClock

_EXPIRED = "A sessão de autenticação expirou. Faça login novamente."


class ExecutionAuthorization:
    """Autorização de uma requisição ou execução para chamar o LLM em nome de uma conta.

    Junta a identidade validada e a credencial decifrada, que precisam ser da mesma conta e da
    mesma sessão. É consultada antes de cada chamada ao provedor: depois do fim da sessão (ou da
    credencial) ou de uma revogação detectada durante a execução, nenhuma chamada nova sai.
    Cada execução tem a sua instância; nada é global, então execuções simultâneas nunca misturam
    credenciais.
    """

    def __init__(
        self, identity: AuthenticatedUser, credential: LLMCredential, clock: IClock,
        session_validator: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Inicializa a autorização.

        Args:
            identity: Identidade validada da requisição.
            credential: Credencial decifrada do cookie.
            clock: Fonte de tempo.
            session_validator: Revalida a sessão no auth antes de cada envio LLM.

        Raises:
            ValueError: Quando a credencial pertence a outra conta ou a outra sessão.
        """
        if credential.owner_id != identity.user_id or credential.session_id != identity.session_id:
            raise ValueError("A credencial pertence a outra conta ou sessão.")
        self.identity = identity
        self.__credential = credential
        self.clock = clock
        self.__revoked_reason: str | None = None
        self.__deadline = min(identity.session_expires_at, credential.expires_at)
        self.__session_validator = session_validator

    async def revalidate(self) -> None:
        """Revalida a sessão e o prazo antes de enviar uma chamada ao provedor.

        Uma recusa do auth revoga também a autorização local, impedindo que outras chamadas da
        mesma execução continuem. O prazo é conferido novamente depois do I/O de validação.
        """
        self.ensure_active()
        if self.__session_validator is not None:
            try:
                await self.__session_validator()
            except ExecutionNotAuthorizedError as exc:
                self.revoke(str(exc))
                raise
        self.ensure_active()

    @property
    def credential(self) -> LLMCredential:
        """Credencial a usar na chamada."""
        return self.__credential

    @property
    def owner_id(self) -> str:
        """Conta dona da execução."""
        return self.identity.user_id

    @property
    def is_active(self) -> bool:
        """Informa se novas chamadas ainda podem sair."""
        return self.__revoked_reason is None and self.clock.now() < self.__deadline

    def revoke(self, reason: str) -> None:
        """Bloqueia novas chamadas (sessão revogada, expirada ou validação indisponível).

        Args:
            reason: Motivo exibido no erro das chamadas seguintes.
        """
        self.__revoked_reason = reason

    def ensure_active(self) -> None:
        """Recusa a chamada quando a autorização deixou de valer.

        Raises:
            ExecutionNotAuthorizedError: Depois do prazo ou de uma revogação.
        """
        if self.__revoked_reason is not None:
            raise ExecutionNotAuthorizedError(self.__revoked_reason)
        if self.clock.now() >= self.__deadline:
            raise ExecutionNotAuthorizedError(_EXPIRED)
