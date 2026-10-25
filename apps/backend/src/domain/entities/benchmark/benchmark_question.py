from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkQuestion:
    """Questão de múltipla escolha do benchmark e o seu gabarito.

    O gabarito é metadado de avaliação: nunca entra no prompt enviado aos fluxos.

    Attributes:
        id: Identificador da questão (nome da pasta no dataset).
        statement: Enunciado completo, com as alternativas.
        options: Texto de cada alternativa, indexado pela letra.
        expected_alternative: Letra da alternativa correta.
    """

    id: str
    statement: str
    options: dict[str, str]
    expected_alternative: str

    def __post_init__(self) -> None:
        """Garante que o gabarito aponta para uma alternativa existente.

        Raises:
            ValueError: Quando a letra esperada não está entre as alternativas.
        """
        if self.expected_alternative not in self.options:
            raise ValueError(f"Gabarito '{self.expected_alternative}' não é alternativa da questão '{self.id}'.")

    @property
    def expected_answer(self) -> str:
        """Alternativa correta completa, com letra e texto.

        Returns:
            str: Alternativa no formato `LETRA) texto`.
        """
        return f"{self.expected_alternative}) {self.options[self.expected_alternative]}"
