import logging

from src.domain.entities.email_address import EmailAddress
from src.domain.entities.user import User
from src.domain.enums.user_role_enum import UserRoleEnum
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.password_hasher_interface import IPasswordHasher
from src.domain.interfaces.token_generator_interface import ITokenGenerator
from src.domain.interfaces.user_repository_interface import IUserRepository
from src.domain.services.password_policy import PasswordPolicy


class RegisterUserUseCase:
    """Cadastro público: cria sempre uma conta comum (nunca administrador)."""

    def __init__(
        self,
        users: IUserRepository,
        hasher: IPasswordHasher,
        tokens: ITokenGenerator,
        clock: IClock,
        policy: PasswordPolicy,
        logger: logging.Logger,
    ) -> None:
        """Inicializa o caso de uso com as portas de persistência, hash, identificadores e tempo."""
        self.users = users
        self.hasher = hasher
        self.tokens = tokens
        self.clock = clock
        self.policy = policy
        self.logger = logger

    async def execute(self, email: str, password: str) -> User:
        """Valida os dados e cria a conta.

        Args:
            email: E-mail como digitado.
            password: Senha em texto claro (só em memória).

        Returns:
            User: Conta criada.

        Raises:
            InvalidRegistrationError: Quando e-mail ou senha são inválidos.
            EmailAlreadyRegisteredError: Quando o e-mail já tem conta.
        """
        address = EmailAddress.parse(email)
        self.policy.validate(password)
        user = User(
            id=self.tokens.user_id(),
            email=address.value,
            password_hash=self.hasher.hash(password),
            role=UserRoleEnum.USER,
            created_at=self.clock.now(),
        )
        await self.users.insert(user)
        self.logger.info("Conta '%s' cadastrada", user.id)
        return user
