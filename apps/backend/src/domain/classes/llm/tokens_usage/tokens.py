from dataclasses import dataclass

from src.domain.classes.llm.models.genai_model import GenaiModel


@dataclass
class TokensUsage:
    """Representa o consumo de tokens por interação com um modelo de LLM.

    Attributes:
        tokens_input: Quantidade de tokens enviados no input.
        tokens_output: Quantidade de tokens retornados no output.
        llm_model: Modelo GenAI associado ao consumo.
    """

    tokens_input: int
    tokens_output: int
    llm_model: GenaiModel
