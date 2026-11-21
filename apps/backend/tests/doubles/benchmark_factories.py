"""Construtores de entidades de benchmark usados por vários testes."""
from datetime import UTC, datetime

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_llm_config import BenchmarkLLMConfig
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum

CRIADO_EM = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
OPCOES = {"A": "um", "B": "dois", "C": "três", "D": "quatro", "E": "cinco"}


def questao(identificador: str = "Q1", gabarito: str = "A") -> BenchmarkQuestion:
    """Questão de cinco alternativas, com o gabarito informado."""
    enunciado = "Pergunta\n\n" + "\n".join(f"{letra}) {texto}" for letra, texto in OPCOES.items())
    return BenchmarkQuestion(id=identificador, statement=enunciado, options=dict(OPCOES), expected_alternative=gabarito)


def configuracao() -> BenchmarkLLMConfig:
    """Configuração de modelo de teste."""
    return BenchmarkLLMConfig(
        model_name="vendor/modelo", provider=ModelProviderEnum.OPEN_ROUTER, max_tokens=4096, temperature=0.0
    )


def desfecho(
    mode: BenchmarkInferenceModeEnum = BenchmarkInferenceModeEnum.SIMPLE,
    correto: bool = True,
    erro: str | None = None,
    tokens: int = 10,
    session_id: str | None = "sess_1",
    duracao: float = 1.5,
) -> BenchmarkFlowOutcome:
    """Desfecho de fluxo com valores ajustáveis."""
    return BenchmarkFlowOutcome(
        mode=mode,
        session_id=session_id,
        selected_alternative="A" if erro is None else None,
        is_correct=correto,
        error=erro,
        duration_seconds=duracao,
        total_tokens=tokens,
    )


def bateria(
    *identificadores: str,
    status: BenchmarkSessionStatusEnum = BenchmarkSessionStatusEnum.RUNNING,
) -> BenchmarkSession:
    """Bateria em execução com as questões informadas, todas pendentes."""
    return BenchmarkSession(
        id="bench_1",
        llm_config=configuracao(),
        max_parallel=2,
        status=status,
        created_at=CRIADO_EM,
        updated_at=CRIADO_EM,
        questions=[
            BenchmarkQuestionRun(question_id=item, expected_alternative="A") for item in identificadores or ("Q1",)
        ],
    )
