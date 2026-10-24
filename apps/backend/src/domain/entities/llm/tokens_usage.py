from dataclasses import dataclass

from src.domain.entities.llm.genai_model import GenaiModel


@dataclass(frozen=True)
class TokensUsage:
    """Representa o consumo de tokens por interação com um modelo de LLM.

    Cada contador é informado, ou não, de forma independente pelo provedor. Um contador não
    informado fica em zero para poder ser somado, mas é marcado como desconhecido: zero conhecido
    e zero por falta de informação são coisas diferentes, e só o primeiro é custo nulo.

    Attributes:
        tokens_input: Quantidade de tokens enviados no input; zero quando desconhecida.
        tokens_output: Quantidade de tokens retornados no output; zero quando desconhecida.
        llm_model: Modelo GenAI associado ao consumo.
        input_known: `False` quando o provedor não informou os tokens de entrada.
        output_known: `False` quando o provedor não informou os tokens de saída.
    """

    tokens_input: int
    tokens_output: int
    llm_model: GenaiModel
    input_known: bool = True
    output_known: bool = True

    @classmethod
    def from_reported(
        cls,
        tokens_input: int | None,
        tokens_output: int | None,
        llm_model: GenaiModel,
    ) -> "TokensUsage":
        """Cria o consumo a partir do que o provedor informou, contador a contador.

        Args:
            tokens_input: Tokens de entrada informados, ou `None` se o provedor não os informou.
            tokens_output: Tokens de saída informados, ou `None` se o provedor não os informou.
            llm_model: Modelo GenAI associado ao consumo.

        Returns:
            TokensUsage: Consumo com cada contador marcado como conhecido ou desconhecido.
        """
        return cls(
            tokens_input=tokens_input or 0,
            tokens_output=tokens_output or 0,
            llm_model=llm_model,
            input_known=tokens_input is not None,
            output_known=tokens_output is not None,
        )

    @property
    def known_input(self) -> int | None:
        """Tokens de entrada como o provedor informou.

        Returns:
            int | None: O contador, ou `None` quando desconhecido.
        """
        return self.tokens_input if self.input_known else None

    @property
    def known_output(self) -> int | None:
        """Tokens de saída como o provedor informou.

        Returns:
            int | None: O contador, ou `None` quando desconhecido.
        """
        return self.tokens_output if self.output_known else None
