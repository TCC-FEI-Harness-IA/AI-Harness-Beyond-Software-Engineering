from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_question_status_enum import BenchmarkQuestionStatusEnum


@dataclass
class BenchmarkQuestionRun:
    """Execução de uma questão dentro da bateria: inferência simples e depois Ralph.

    Attributes:
        question_id: Identificador da questão.
        expected_alternative: Letra do gabarito.
        status: Estado da questão na bateria.
        simple: Desfecho da inferência simples, quando já terminou.
        ralph: Desfecho do Ralph Loop, quando já terminou.
        current_mode: Fluxo em execução, ou o que estava em execução quando a bateria foi interrompida.
        current_tokens: Tokens já consumidos pelo fluxo em execução, ainda sem desfecho.
    """

    question_id: str
    expected_alternative: str
    status: BenchmarkQuestionStatusEnum = BenchmarkQuestionStatusEnum.PENDING
    simple: BenchmarkFlowOutcome | None = None
    ralph: BenchmarkFlowOutcome | None = None
    current_mode: BenchmarkInferenceModeEnum | None = None
    current_tokens: int = 0

    @property
    def outcomes(self) -> list[BenchmarkFlowOutcome]:
        """Desfechos já registrados, na ordem de execução.

        Returns:
            list[BenchmarkFlowOutcome]: Desfechos da inferência simples e do Ralph, quando existem.
        """
        return [outcome for outcome in (self.simple, self.ralph) if outcome is not None]

    @property
    def total_tokens(self) -> int:
        """Tokens da questão: desfechos registrados mais o consumo do fluxo em execução.

        Returns:
            int: Tokens consumidos pela questão até o momento.
        """
        return sum(outcome.total_tokens for outcome in self.outcomes) + self.current_tokens

    @property
    def session_ids(self) -> list[str]:
        """Sessões persistidas pelos fluxos da questão.

        Returns:
            list[str]: Identificadores das sessões, na ordem de execução.
        """
        return [outcome.session_id for outcome in self.outcomes if outcome.session_id is not None]

    def outcome(self, mode: BenchmarkInferenceModeEnum) -> BenchmarkFlowOutcome | None:
        """Devolve o desfecho de um fluxo.

        Args:
            mode: Fluxo consultado.

        Returns:
            BenchmarkFlowOutcome | None: Desfecho registrado, ou `None`.
        """
        return self.simple if mode is BenchmarkInferenceModeEnum.SIMPLE else self.ralph

    def start_flow(self, mode: BenchmarkInferenceModeEnum) -> None:
        """Marca o início de um fluxo da questão.

        Args:
            mode: Fluxo iniciado.

        Raises:
            ValueError: Quando a questão já terminou, outro fluxo está em execução ou o fluxo já tem desfecho.
        """
        if self.status not in (BenchmarkQuestionStatusEnum.PENDING, BenchmarkQuestionStatusEnum.RUNNING):
            raise ValueError(f"A questão '{self.question_id}' já foi encerrada com status '{self.status.value}'.")
        if self.current_mode is not None:
            raise ValueError(f"A questão '{self.question_id}' já executa o fluxo '{self.current_mode.value}'.")
        if self.outcome(mode) is not None:
            raise ValueError(f"O fluxo '{mode.value}' da questão '{self.question_id}' já terminou.")

        self.status = BenchmarkQuestionStatusEnum.RUNNING
        self.current_mode = mode
        self.current_tokens = 0

    def track_tokens(self, total_tokens: int) -> None:
        """Atualiza o consumo acumulado do fluxo em execução, sem nunca decrescer.

        Args:
            total_tokens: Consumo acumulado informado pelo fluxo.

        Raises:
            ValueError: Quando nenhum fluxo está em execução.
        """
        if self.current_mode is None:
            raise ValueError(f"A questão '{self.question_id}' não tem fluxo em execução.")
        self.current_tokens = max(self.current_tokens, total_tokens)

    def record_outcome(self, outcome: BenchmarkFlowOutcome) -> None:
        """Registra o desfecho do fluxo em execução.

        Args:
            outcome: Desfecho do fluxo.

        Raises:
            ValueError: Quando o desfecho não é do fluxo em execução.
        """
        if outcome.mode is not self.current_mode:
            raise ValueError(f"O fluxo '{outcome.mode.value}' não está em execução na questão '{self.question_id}'.")

        if outcome.mode is BenchmarkInferenceModeEnum.SIMPLE:
            self.simple = outcome
        else:
            self.ralph = outcome
        self.current_mode = None
        self.current_tokens = 0

    def finish(self) -> None:
        """Encerra a questão depois dos dois fluxos.

        Raises:
            ValueError: Quando há fluxo em execução ou falta o desfecho de algum fluxo.
        """
        if self.current_mode is not None or self.simple is None or self.ralph is None:
            raise ValueError(f"A questão '{self.question_id}' só termina depois dos dois fluxos.")
        self.status = BenchmarkQuestionStatusEnum.FINISHED

    def interrupt(self) -> None:
        """Marca como interrompida a questão que estava em execução.

        O fluxo e o consumo em andamento são preservados para diagnóstico e contabilidade.
        Questões pendentes ou encerradas não são alteradas.
        """
        if self.status is BenchmarkQuestionStatusEnum.RUNNING:
            self.status = BenchmarkQuestionStatusEnum.INTERRUPTED
