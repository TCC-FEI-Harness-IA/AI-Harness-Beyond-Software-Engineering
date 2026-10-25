"""Executa os fluxos da API e persiste no mesmo repositório configurado no backend."""

import json
import os
import sys
from contextlib import aclosing
from dataclasses import replace
from pathlib import Path

from benchmark import MODEL, Outcome, Question, Reply


def configure_backend(backend: Path, env_file: Path) -> None:
    """Carrega credenciais sem substituir o armazenamento configurado pela API."""
    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        raise ValueError("Configure OPENROUTER_API_KEY no ambiente ou no arquivo --env-file.")
    if not (backend / "src").is_dir():
        raise ValueError(f"Código do backend não encontrado: {backend}")
    sys.path.insert(0, str(backend))
    templates = Path(os.environ.get("RALPH_PROMPT_TEMPLATES_PATH", "src/infra/templates"))
    if not templates.is_absolute():
        templates = backend / templates
    if not templates.is_dir():
        raise ValueError(f"Diretório de templates não encontrado: {templates}")
    storage = Path(os.environ.get("RALPH_SESSIONS_STORAGE_PATH", "./data/sessions"))
    if not storage.is_absolute():
        storage = backend / storage
    os.environ.update({
        "LLM_PROVIDER": "open_router",
        "LLM_MODEL": MODEL,
        "GENAI_AVAILABLE_MODELS": json.dumps([MODEL]),
        "GENAI_AVAILABLE_PROVIDERS": json.dumps(["open_router"]),
        "RALPH_PROMPT_TEMPLATES_PATH": str(templates.resolve()),
        "RALPH_SESSIONS_STORAGE_PATH": str(storage.resolve()),
    })


class BackendFlows:
    """Cria sessões normais, identificadas como benchmark desde a primeira gravação."""

    def __init__(self, output: Path, max_tokens: int, temperature: float, questions: list[Question]) -> None:
        self.output = output
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.questions = {question.id: question for question in questions}
        self.recorders = {}

    def __payload(self, prompt: str) -> dict:
        return {
            "message": {"user_input": prompt},
            "llm_model_config": {
                "provider": "open_router",
                "provider_config": {"model_name": MODEL},
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }

    def __details(self, question_id: str, mode: str):
        from src.domain.entities.session.benchmark_details import BenchmarkDetails
        from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum

        question = self.questions[question_id]
        return BenchmarkDetails(
            is_banchmark=True,
            question_name=question_id,
            corret_answer=f"{question.expected}) {question.options[question.expected]}",
            inference_mode=BenchmarkInferenceModeEnum(mode),
            run_id=self.output.name,
            expected_alternative=question.expected,
        )

    async def simple(self, question_id: str, prompt: str) -> Reply:
        """Executa a mesma inferência simples da API, com sessão exclusiva."""
        from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
        from src.infra.startups.default_message_startup import DefaultMessageStartup

        startup = DefaultMessageStartup(benchmark_details=self.__details(question_id, "simple"))
        recorder = startup.default_message_use_case.session_recorder
        self.recorders[(question_id, "simple")] = recorder
        try:
            result = await startup.run(DefaultInputDTO.model_validate(self.__payload(prompt)))
            return Reply(response=result.response, session_id=result.session_id)
        except Exception as error:
            return Reply(session_id=self.__session_id(recorder), error=f"{type(error).__name__}: {error}")

    async def ralph(self, question_id: str, prompt: str) -> Reply:
        """Consome o Ralph completo e usa apenas o evento terminal result como resposta."""
        from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
        from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

        startup = RalphThinkingStartup(benchmark_details=self.__details(question_id, "ralph"))
        self.recorders[(question_id, "ralph")] = startup.session_recorder
        response = ""
        error = None
        payload = ReasoningInputDTO.model_validate(self.__payload(prompt))
        events_path = self.output / f"{question_id}_ralph_eventos.jsonl"
        try:
            with events_path.open("w", encoding="utf-8") as file:
                async with aclosing(startup.run(payload)) as events:
                    async for event in events:
                        file.write(event.model_dump_json() + "\n")
                        file.flush()
                        if event.type == "result":
                            response = event.content
                        elif event.type == "error":
                            error = event.content
        except Exception as exception:
            error = error or f"{type(exception).__name__}: {exception}"
        if not response and error is None:
            error = "O RALPH terminou sem emitir uma resposta final."
        return Reply(response=response, session_id=self.__session_id(startup.session_recorder), error=error)

    async def record_outcome(self, question_id: str, mode: str, outcome: Outcome) -> None:
        """Atualiza os metadados pelo mesmo recorder/repositório que gravou o chat."""
        recorder = self.recorders.get((question_id, mode))
        if recorder is None or self.__session_id(recorder) is None:
            return
        details = replace(
            recorder.session.benchmark_details,
            providade_answer=outcome.response or None,
            selected_alternative=outcome.selected,
            is_correct=outcome.correct,
            duration_seconds=outcome.seconds,
            error=outcome.error,
        )
        await recorder.update_benchmark_details(details)

    @staticmethod
    def __session_id(recorder) -> str | None:
        try:
            return recorder.session.id
        except ValueError:
            return None
