from dataclasses import dataclass, field, replace
from datetime import datetime

from src.domain.enums.user_role_enum import UserRoleEnum


@dataclass(frozen=True)
class User:
    """Conta de usuário.

    Attributes:
        id: Identificador estável, usado como proprietário dos dados no backend.
        email: E-mail normalizado e único.
        password_hash: Hash Argon2id (formato PHC); nunca a senha.
        role: Perfil da conta.
        created_at: Instante do cadastro, em UTC.
    """

    id: str
    email: str
    password_hash: str = field(repr=False)
    role: UserRoleEnum
    created_at: datetime

    def with_password_hash(self, password_hash: str) -> "User":
        """Cópia da conta com outro hash de senha (rehash após mudança de parâmetros)."""
        return replace(self, password_hash=password_hash)

    def promoted_to_admin(self) -> "User":
        """Cópia da conta com perfil de administrador."""
        return replace(self, role=UserRoleEnum.ADMIN)
