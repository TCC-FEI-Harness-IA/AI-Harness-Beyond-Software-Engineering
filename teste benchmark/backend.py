"""Integra os composition roots existentes, com uma instância por fluxo e questão."""

import json
import os
import sys
from contextlib import aclosing
from pathlib import Path

from benchmark import MODEL, Reply


def configure_backend(project: Path, output: Path, env_file: Path) -> None:
    """Carrega credenciais e prepara configurações apenas para este processo."""
    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        raise ValueError("Configure OPENROUTER_API_KEY no ambiente ou no arquivo --env-file.")
    backend = project / "apps" / "backend"
    sys.path.insert(0, str(backend))
    templates = Path(os.environ.get("RALPH_PROMPT_TEMPLATES_PATH", "src/infra/templates"))
    if not templates.is_absolute():
        templates = backend / templates
    if not templates.is_dir():
        raise ValueError(f"Diretório de templates não encontrado: {templates}")
    os.environ.update({
        "LLM_PROVIDER": "open_router",
        "LLM_MODEL": MODEL,
        "GENAI_AVAILABLE_MODELS": json.dumps([MODEL]),
        "GENAI_AVAILABLE_PROVIDERS": json.dumps(["open_router"]),
        "RALPH_PROMPT_TEMPLATES_PATH": str(templates.resolve()),
        "RALPH_SESSION_STORAGE_BACKEND": "json_file",
        "RALPH_SESSIONS_STORAGE_PATH": str((output / "sessions").resolve()),
    })


class BackendFlows:
    """Executa os mesmos fluxos expostos pela API sem precisar iniciar o servidor."""

    def __init__(self, output: Path, max_tokens: int, temperature: float) -> None:
        self.output = output
        self.max_tokens = max_tokens
        self.temperature = temperature

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

    async def simple(self, question_id: str, prompt: str) -> Reply:
        """Faz uma inferência direta usando uma sessão exclusiva."""
        from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
        from src.infra.startups.default_message_startup import DefaultMessageStartup

        startup = DefaultMessageStartup()
        result = await startup.run(DefaultInputDTO.model_validate(self.__payload(prompt)))
        return Reply(response=result.response, session_id=result.session_id)

    async def ralph(self, question_id: str, prompt: str) -> Reply:
        """Consome o Ralph completo e avalia somente seu evento terminal result."""
        from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
        from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

        startup = RalphThinkingStartup()
        response = ""
        session_id = None
        error = None
        payload = ReasoningInputDTO.model_validate(self.__payload(prompt))
        events_path = self.output / f"{question_id}_ralph_eventos.jsonl"
        try:
            with events_path.open("w", encoding="utf-8") as file:
                async with aclosing(startup.run(payload)) as events:
                    async for event in events:
                        file.write(event.model_dump_json() + "\n")
                        file.flush()
                        session_id = event.session_id
                        if event.type == "result":
                            response = event.content
                        elif event.type == "error":
                            error = event.content
        except Exception as exception:
            error = error or f"{type(exception).__name__}: {exception}"
        if not response and error is None:
            error = "O RALPH terminou sem emitir uma resposta final."
        return Reply(response=response, session_id=session_id, error=error)
