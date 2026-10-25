from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_llm_config import BenchmarkLLMConfig
from src.domain.entities.benchmark.benchmark_mode_summary import BenchmarkModeSummary
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum


@dataclass
class BenchmarkSession:
    """Bateria de benchmark: agrupa as questões executadas, as sessões geradas e os totais.

    Cada questão roda a inferência simples e depois o Ralph Loop, cada fluxo na sua própria
    `Session`, identificada pelo `run_id` dos metadados de benchmark. Os totais (acertos, erros,
    tokens, tempo) são derivados das questões, para que nunca divirjam delas.

    Attributes:
        id: Identificador único da bateria.
        llm_config: Modelo, provedor e parâmetros usados em todos os fluxos.
        max_parallel: Máximo de questões executadas em paralelo.
        status: Estado da bateria.
        created_at: Data e hora de criação em UTC.
        updated_at: Data e hora da última atualização em UTC.
        questions: Questões da bateria, na ordem do dataset.
        finished_at: Data e hora de encerramento em UTC, quando encerrada.
        wall_time_ms: Tempo de execução da bateria, em milissegundos.
        error: Diagnóstico de uma falha técnica da bateria, quando houve.
    """

    id: str
    llm_config: BenchmarkLLMConfig
    max_parallel: int
    status: BenchmarkSessionStatusEnum
    created_at: datetime
    updated_at: datetime
    questions: list[BenchmarkQuestionRun] = field(default_factory=list)
    finished_at: datetime | None = None
    wall_time_ms: int = 0
    error: str | None = None

    @property
    def question_count(self) -> int:
        """Quantidade de questões da bateria."""
        return len(self.questions)

    @property
    def pending_count(self) -> int:
        """Quantidade de questões que ainda não começaram."""
        return self.__count(BenchmarkQuestionStatusEnum.PENDING)

    @property
    def running_count(self) -> int:
        """Quantidade de questões em execução."""
        return self.__count(BenchmarkQuestionStatusEnum.RUNNING)

    @property
    def finished_count(self) -> int:
        """Quantidade de questões encerradas com os dois fluxos."""
        return self.__count(BenchmarkQuestionStatusEnum.FINISHED)

    @property
    def interrupted_count(self) -> int:
        """Quantidade de questões que estavam em execução quando a bateria foi interrompida."""
        return self.__count(BenchmarkQuestionStatusEnum.INTERRUPTED)

    @property
    def total_tokens(self) -> int:
        """Tokens consumidos por todas as sessões da bateria, inclusive fluxos em execução."""
        return sum(question.total_tokens for question in self.questions)

    @property
    def session_ids(self) -> list[str]:
        """Sessões persistidas pela bateria, na ordem das questões."""
        return [session_id for question in self.questions for session_id in question.session_ids]

    def summary(self, mode: BenchmarkInferenceModeEnum) -> BenchmarkModeSummary:
        """Totais de um fluxo na bateria.

        Args:
            mode: Fluxo resumido.

        Returns:
            BenchmarkModeSummary: Acertos, erros, falhas, tokens e duração do fluxo.
        """
        outcomes = [outcome for question in self.questions if (outcome := question.outcome(mode)) is not None]
        return BenchmarkModeSummary.from_outcomes(mode=mode, outcomes=outcomes)

    def question(self, question_id: str) -> BenchmarkQuestionRun:
        """Devolve a execução de uma questão da bateria.

        Args:
            question_id: Identificador da questão.

        Returns:
            BenchmarkQuestionRun: Execução da questão.

        Raises:
            ValueError: Quando a questão não pertence à bateria.
        """
        for question in self.questions:
            if question.question_id == question_id:
                return question
        raise ValueError(f"A questão '{question_id}' não pertence à bateria '{self.id}'.")

    def start_flow(self, question_id: str, mode: BenchmarkInferenceModeEnum, at: datetime) -> None:
        """Marca o início de um fluxo de uma questão.

        Args:
            question_id: Questão executada.
            mode: Fluxo iniciado.
            at: Instante do início.

        Raises:
            ValueError: Quando a bateria já foi encerrada ou o fluxo não pode começar.
        """
        self.__ensure_running()
        self.question(question_id).start_flow(mode=mode)
        self.updated_at = at

    def track_tokens(self, question_id: str, total_tokens: int) -> None:
        """Atualiza o consumo do fluxo em execução de uma questão.

        Args:
            question_id: Questão executada.
            total_tokens: Consumo acumulado informado pelo fluxo.
        """
        self.question(question_id).track_tokens(total_tokens=total_tokens)

    def record_outcome(self, question_id: str, outcome: BenchmarkFlowOutcome, at: datetime) -> None:
        """Registra o desfecho de um fluxo de uma questão.

        Args:
            question_id: Questão executada.
            outcome: Desfecho do fluxo.
            at: Instante do registro.
        """
        self.__ensure_running()
        self.question(question_id).record_outcome(outcome=outcome)
        self.updated_at = at

    def finish_question(self, question_id: str, at: datetime) -> None:
        """Encerra uma questão depois dos dois fluxos.

        Args:
            question_id: Questão encerrada.
            at: Instante do encerramento.
        """
        self.__ensure_running()
        self.question(question_id).finish()
        self.updated_at = at

    def update_wall_time(self, wall_time_ms: int) -> None:
        """Atualiza o tempo de execução enquanto a bateria está em andamento.

        Args:
            wall_time_ms: Tempo decorrido desde o início, em milissegundos.
        """
        if self.status is BenchmarkSessionStatusEnum.RUNNING:
            self.wall_time_ms = wall_time_ms

    def finish(
        self,
        status: BenchmarkSessionStatusEnum,
        at: datetime,
        wall_time_ms: int,
        error: str | None = None,
    ) -> None:
        """Encerra a bateria.

        Questões em execução numa bateria que não concluiu passam a `interrupted`.

        Args:
            status: Estado final.
            at: Instante do encerramento.
            wall_time_ms: Tempo total de execução, em milissegundos.
            error: Diagnóstico da falha técnica, quando houve.

        Raises:
            ValueError: Quando a bateria já foi encerrada, o status final é `running` ou uma
                bateria concluída deixou questões sem terminar.
        """
        self.__ensure_running()
        if status is BenchmarkSessionStatusEnum.RUNNING:
            raise ValueError("Uma bateria não pode ser encerrada com status 'running'.")
        if status is BenchmarkSessionStatusEnum.COMPLETED and self.finished_count != self.question_count:
            raise ValueError(f"A bateria '{self.id}' só conclui depois de todas as questões.")

        for question in self.questions:
            question.interrupt()
        self.status = status
        self.error = error
        self.wall_time_ms = wall_time_ms
        self.finished_at = at
        self.updated_at = at

    def __ensure_running(self) -> None:
        """Recusa alterações numa bateria encerrada.

        Raises:
            ValueError: Quando a bateria já foi encerrada.
        """
        if self.status is not BenchmarkSessionStatusEnum.RUNNING:
            raise ValueError(f"A bateria '{self.id}' já foi encerrada com status '{self.status.value}'.")

    def __count(self, status: BenchmarkQuestionStatusEnum) -> int:
        """Conta as questões em um estado."""
        return sum(question.status is status for question in self.questions)
