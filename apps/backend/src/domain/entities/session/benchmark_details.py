from dataclasses import dataclass, fields

from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum


@dataclass(frozen=True)
class BenchmarkDetails:
    """Metadados de avaliação, separados do enunciado enviado ao modelo.

    Os nomes is_banchmark, corret_answer e providade_answer preservam o contrato
    solicitado. A resposta fornecida é o texto bruto; as letras ficam em campos próprios.
    Uma sessão comum tem somente is_banchmark=false, com os demais campos nulos.
    """

    is_banchmark: bool = False
    question_name: str | None = None
    corret_answer: str | None = None
    providade_answer: str | None = None
    inference_mode: BenchmarkInferenceModeEnum | None = None
    run_id: str | None = None
    expected_alternative: str | None = None
    selected_alternative: str | None = None
    is_correct: bool | None = None
    duration_seconds: float | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Impede flags ambíguas e metadados residuais em sessões comuns."""
        if type(self.is_banchmark) is not bool:
            raise ValueError("is_banchmark deve ser booleano.")
        if not self.is_banchmark and any(
            getattr(self, item.name) is not None for item in fields(self) if item.name != "is_banchmark"
        ):
            raise ValueError("Sessões comuns devem ter todos os detalhes de benchmark nulos.")
