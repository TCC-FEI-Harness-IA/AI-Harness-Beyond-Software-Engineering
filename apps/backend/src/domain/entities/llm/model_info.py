from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Modelo cadastrado no catálogo, com as características que ajudam a escolher entre eles.

    Todo campo numérico é opcional: um dado ainda desconhecido fica vazio sem impedir que o
    modelo seja cadastrado e escolhido.

    Attributes:
        model_name: Identificador do modelo no provedor (ex.: `vendor/modelo`).
        display_name: Nome amigável exibido na lista de escolha.
        input_price_per_million_tokens: Preço em USD por 1 milhão de tokens de entrada.
        output_price_per_million_tokens: Preço em USD por 1 milhão de tokens de saída.
        context_length: Tamanho máximo do contexto, em tokens.
        throughput_tokens_per_second: Vazão típica, em tokens por segundo.

    Raises:
        ValueError: Quando o identificador é vazio ou algum número está fora da faixa válida.
    """

    model_name: str
    display_name: str | None = None
    input_price_per_million_tokens: float | None = None
    output_price_per_million_tokens: float | None = None
    context_length: int | None = None
    throughput_tokens_per_second: float | None = None

    def __post_init__(self) -> None:
        """Valida o identificador e as faixas dos campos numéricos."""
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty.")

        for field_name in ("input_price_per_million_tokens", "output_price_per_million_tokens"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must not be negative.")

        for field_name in ("context_length", "throughput_tokens_per_second"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"{field_name} must be positive.")
