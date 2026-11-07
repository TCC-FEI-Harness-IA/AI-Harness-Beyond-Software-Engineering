import logging

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.settings_interface import ISettings
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.providers.mmlu_benchmark_question_provider import MMLUBenchmarkQuestionProvider
from src.infra.providers.gpqa_benchmark_question_provider import GPQABenchmarkQuestionProvider


class BenchmarkQuestionProviderFactory:
    """Resolve o dataset sem alterar a configuração global dos vestibulares."""

    def __init__(self, settings: ISettings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def create(self, dataset: BenchmarkDatasetEnum, few_shot: int = 0) -> IBenchmarkQuestionProvider:
        if dataset is BenchmarkDatasetEnum.MMLU:
            return MMLUBenchmarkQuestionProvider(few_shot=few_shot)
        if dataset is BenchmarkDatasetEnum.GPQA:
            return GPQABenchmarkQuestionProvider(few_shot=few_shot)
        return FileBenchmarkQuestionProvider(settings=self.settings, logger=self.logger)
