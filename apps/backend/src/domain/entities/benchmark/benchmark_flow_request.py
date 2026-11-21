from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_llm_config import BenchmarkLLMConfig
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum


@dataclass(frozen=True)
class BenchmarkFlowRequest:
    """Pedido de execução de um fluxo para uma questão da bateria.

    Attributes:
        question: Questão avaliada; o gabarito não entra no prompt.
        mode: Fluxo a executar.
        prompt: Enunciado seguido da instrução de resposta, enviado ao fluxo.
        llm_config: Configuração do modelo da bateria.
        benchmark_session_id: Bateria à qual a sessão do fluxo pertence.
    """

    question: BenchmarkQuestion
    mode: BenchmarkInferenceModeEnum
    prompt: str
    llm_config: BenchmarkLLMConfig
    benchmark_session_id: str
