import logging

from src.domain.entities.email_address import EmailAddress
from src.domain.entities.user import User
from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.password_hasher_interface import IPasswordHasher
from src.domain.interfaces.token_generator_interface import ITokenGenerator
from src.domain.interfaces.user_repository_interface import IUserRepository
from src.domain.services.password_policy import PasswordPolicy


class ProvisionAdminUseCase:
    """Provisionamento administrativo, disponível só pela linha de comando do serviço.

    Não existe credencial padrão: a senha de uma conta nova é obrigatória e passa pela mesma
    política do cadastro. Promover uma conta existente exige o pedido explícito (`promote`).
    """

    def __init__(
        self,
        users: IUserRepository,
        hasher: IPasswordHasher,
        tokens: ITokenGenerator,
        clock: IClock,
        policy: PasswordPolicy,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso."""
        self.users = users
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock
        self.policy = policy
        self.logger = logger

    async def execute(self, email: str, password: str | None, promote: bool) -> User:
        """Cria um administrador ou promove uma conta existente.

        Args:
            email: E-mail da conta.
            password: Senha da conta nova; ignorada na promoção.
            promote: Permite promover uma conta já cadastrada.

        Returns:
            User: Conta administradora.

        Raises:
            InvalidRegistrationError: E-mail inválido, ou conta nova sem senha válida.
            EmailAlreadyRegisteredError: A conta existe e `promote` não foi pedido.
        """
        address = EmailAddress.parse(email).value
        existing = await self.users.find_by_email(address)
        if existing is not None:
            if not promote:
                raise EmailAlreadyRegisteredError()
            admin = existing.promoted_to_admin()
            await self.users.update(admin)
            self.logger.info("Conta '%s' promovida a administradora", admin.id)
            return admin

        if password is None:
            raise InvalidRegistrationError("Informe a senha da nova conta administradora.")
        self.policy.validate(password)
        admin = User(
            id=self.tokens.user_id(),
            email=address,
            password_hash=self.hasher.hash(password),
            role=UserRoleEnum.ADMIN,
            created_at=self.clock.now(),
        )
        await self.users.insert(admin)
        self.logger.info("Conta administradora '%s' criada", admin.id)
        return admin
