import logging

from src.domain.entities.benchmark.benchmark_definition import BenchmarkDefinition
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.gpqa_subset_enum import GPQASubsetEnum
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

    def create(
        self, dataset: BenchmarkDatasetEnum, few_shot: int = 0,
        gpqa_subset: GPQASubsetEnum = GPQASubsetEnum.DIAMOND,
    ) -> IBenchmarkQuestionProvider:
        if dataset is BenchmarkDatasetEnum.MMLU:
            return MMLUBenchmarkQuestionProvider(few_shot=few_shot)
        if dataset is BenchmarkDatasetEnum.GPQA:
            return GPQABenchmarkQuestionProvider(few_shot=few_shot, subset=gpqa_subset)
        return FileBenchmarkQuestionProvider(settings=self.settings, logger=self.logger)

    def for_definition(self, definition: BenchmarkDefinition) -> IBenchmarkQuestionProvider:
        """Restaura a origem persistida para reexecução e exportação."""
        subset = (
            GPQASubsetEnum(definition.split)
            if definition.dataset is BenchmarkDatasetEnum.GPQA else GPQASubsetEnum.DIAMOND
        )
        return self.create(dataset=definition.dataset, few_shot=definition.few_shot, gpqa_subset=subset)
