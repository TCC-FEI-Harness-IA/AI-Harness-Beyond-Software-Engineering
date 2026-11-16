from src.domain.errors.invalid_registration_error import InvalidRegistrationError


class PasswordPolicy:
    """Regras de aceitação de senhas no cadastro.

    Segue a orientação da OWASP/NIST: comprimento mínimo, teto alto para permitir frases-senha e
    nenhuma regra de composição. A senha nunca é alterada (sem `strip`), apenas validada.
    """

    def __init__(self, min_length: int, max_length: int) -> None:
        """Inicializa a política.

        Args:
            min_length: Comprimento mínimo aceito.
            max_length: Comprimento máximo aceito.

        Raises:
            ValueError: Quando os limites são incoerentes.
        """
        if min_length < 1 or max_length < min_length:
            raise ValueError("Limites de senha incoerentes.")
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, password: str) -> None:
        """Valida uma senha candidata.

        Args:
            password: Senha informada.

        Raises:
            InvalidRegistrationError: Quando a senha está fora dos limites ou é só espaço em branco.
        """
        if len(password) < self.min_length:
            raise InvalidRegistrationError(f"A senha precisa ter pelo menos {self.min_length} caracteres.")
        if len(password) > self.max_length:
            raise InvalidRegistrationError(f"A senha pode ter no máximo {self.max_length} caracteres.")
        if not password.strip():
            raise InvalidRegistrationError("A senha não pode conter apenas espaços.")
