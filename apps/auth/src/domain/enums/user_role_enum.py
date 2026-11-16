from enum import StrEnum


class UserRoleEnum(StrEnum):
    """Perfil da conta. Administradores só são criados por provisionamento explícito."""

    USER = "user"
    ADMIN = "admin"
