from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from src.domain.interfaces.password_hasher_interface import IPasswordHasher


class Argon2PasswordHasher(IPasswordHasher):
    """Hash de senhas com Argon2id, via `argon2-cffi`.

    Os parâmetros vêm da configuração (padrão: perfil de baixa memória da RFC 9106, acima do mínimo
    recomendado pela OWASP). O sal é aleatório por hash e fica embutido na string PHC devolvida.
    """

    def __init__(self, time_cost: int, memory_cost_kib: int, parallelism: int) -> None:
        """Inicializa o hasher.

        Args:
            time_cost: Número de iterações.
            memory_cost_kib: Memória usada por hash, em KiB.
            parallelism: Número de faixas paralelas.

        Raises:
            ValueError: Quando algum parâmetro não é positivo.
        """
        if min(time_cost, memory_cost_kib, parallelism) < 1:
            raise ValueError("Parâmetros do Argon2 precisam ser positivos.")
        self.__hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
            type=Type.ID,
        )
        self.__dummy_hash = self.__hasher.hash("verificacao-ficticia-de-tempo-constante")

    def hash(self, password: str) -> str:
        """Gera o hash Argon2id da senha."""
        return self.__hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        """Verifica a senha; qualquer divergência ou hash inválido resulta em `False`."""
        try:
            return self.__hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """Informa se o hash usa parâmetros diferentes dos configurados."""
        return self.__hasher.check_needs_rehash(password_hash)

    def burn_verification(self, password: str) -> None:
        """Verifica contra um hash fictício, gastando o mesmo tempo de uma conta existente."""
        self.verify(self.__dummy_hash, password)
