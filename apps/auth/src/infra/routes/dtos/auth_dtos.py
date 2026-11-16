from pydantic import BaseModel, ConfigDict, Field


class CredentialsInputDTO(BaseModel):
    """Corpo de cadastro e login. Campos extras (como `role`) são ignorados."""

    model_config = ConfigDict(extra="ignore")

    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class VerifyInputDTO(BaseModel):
    """Corpo da verificação interna: o valor do cookie de sessão repassado pelo backend."""

    token: str = Field(max_length=512)
