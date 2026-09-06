import asyncio
import unittest

from src.application.prompts.prompt_templates import (
    TEMPLATE_A1_CRITERIA,
    TEMPLATE_A2_DECOMPOSITION,
    TEMPLATE_B1_EXECUTE,
    TEMPLATE_B2_VERIFY,
    TEMPLATE_B4_LEARN,
    TEMPLATE_C1_VERIFY_GLOBAL,
    TEMPLATE_C3_FINAL_SYNTHESIS,
    extract_json_payload,
)
from src.application.usecases.ralph_loop_usecase import RalphLoopUseCase
from src.domain.classes.llm.models.genai_model import GenaiModel
from src.domain.classes.ralph_loop.ralph_loop_entities import (
    ContextWindowInfo,
    RalphLoopStepEvent,
    RalphTask,
)
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.adapters.llm_complitions_adapter import LLMComplitionsAdapter
from src.infra.config.settings import Settings
from src.infra.services.mock_llm_service import MockLLMService


class TestRalphLoopComponents(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings()
        self.logger = self.settings.logger(__file__)

    def test_json_payload_extraction(self) -> None:
        # Test markdown code block
        text_with_block = """
        Aqui está a resposta:
        ```json
        {
          "criteria": ["Critério 1", "Critério 2"]
        }
        ```
        """
        payload = extract_json_payload(text_with_block)
        self.assertIn("criteria", payload)
        self.assertEqual(len(payload["criteria"]), 2)

        # Test direct json without markdown
        raw_json = '{"approved": true, "feedback": "Ok"}'
        payload2 = extract_json_payload(raw_json)
        self.assertTrue(payload2.get("approved"))

    def test_model_provider_enum(self) -> None:
        self.assertEqual(ModelProviderEnum.AZURE_FOUNDRY.value, "azure_foundry")
        self.assertEqual(ModelProviderEnum.OPEN_ROUTER.value, "open_router")
        self.assertEqual(ModelProviderEnum.MOCK.value, "mock")

    def test_genai_model_validation(self) -> None:
        model = GenaiModel(settings=self.settings)
        model.new(
            model_name="meta-llama-3.1-8b-instruct",
            model_provider=ModelProviderEnum.AZURE_FOUNDRY,
        )
        self.assertEqual(model.model_name, "meta-llama-3.1-8b-instruct")
        self.assertEqual(model.model_provider, ModelProviderEnum.AZURE_FOUNDRY)

    def test_prompt_template_formatting(self) -> None:
        formatted_a1 = TEMPLATE_A1_CRITERIA.format(user_input="Qual número é primo?")
        self.assertIn("Qual número é primo?", formatted_a1)
        self.assertIn("TEMPLATE_A1_CRITERIA", formatted_a1)

        formatted_b1 = TEMPLATE_B1_EXECUTE.format(
            accumulated_learnings_section="Nenhum",
            task_id="T1",
            task_title="Primos",
            task_description="Achar primos",
            task_criteria="- Critério 1",
        )
        self.assertIn("T1 - Primos", formatted_b1)

    def test_ralph_loop_execution_with_mock(self) -> None:
        mock_service = MockLLMService(logger=self.logger, settings=self.settings)
        adapter = LLMComplitionsAdapter(
            llm_service=mock_service,
            logger=self.logger,
            settings=self.settings,
        )

        usecase = RalphLoopUseCase(llm_completions=adapter, logger=self.logger)

        question = "Qual dos seguintes números é simultaneamente primo, par e maior que 2? A) 2 B) 4 C) 6 D) Nenhuma das anteriores"

        summary = asyncio.run(
            usecase.execute_sync(
                user_input=question,
                provider="mock",
                model_name="mock-llama-3.1-8b",
            )
        )

        self.assertEqual(summary.question, question)
        self.assertTrue(len(summary.general_criteria) > 0)
        self.assertTrue(summary.tasks_count >= 1)
        self.assertEqual(summary.final_answer, "D) Nenhuma das anteriores")
        self.assertTrue(len(summary.events) >= 6)

        # Check that events have context windows
        event_types = [e.subtype for e in summary.events]
        self.assertIn("setup", event_types)
        self.assertIn("tasks", event_types)
        self.assertIn("execute", event_types)
        self.assertIn("store", event_types)
        self.assertIn("compile", event_types)


if __name__ == "__main__":
    unittest.main()
