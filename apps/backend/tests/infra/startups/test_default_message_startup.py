from pathlib import Path
from typing import Any

import pytest

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.interfaces.clock_interface import IClock
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.session_recorder_interface import ISessionRecorder
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup

_SAIDA_DE_APLICACAO = DefaultMessageOutputDTO(
    message="pergunta do usuario",
    response="resposta do modelo",
    session_id="sess_ab12",
    tokens_input=11,
    tokens_output=22,
    inference_time_ms=812,
)


class _SpyUseCase:
    """Dublê do caso de uso que captura o DTO recebido e devolve uma saída fixa."""

    def __init__(self, output: DefaultMessageOutputDTO) -> None:
        self.output = output
        self.recebidos: list[DefaultMessageInputDTO] = []

    async def execute(self, user_input: DefaultMessageInputDTO) -> DefaultMessageOutputDTO:
        """Captura a entrada e devolve a saída programada."""
        self.recebidos.append(user_input)
        return self.output


def _build_payload(temperature: float | None = 0.3) -> DefaultInputDTO:
    llm_model_config: dict[str, Any] = {
        "provider": "open_router",
        "provider_config": {"model_name": "vendor/modelo"},
        "max_tokens": 100,
    }
    if temperature is not None:
        llm_model_config["temperature"] = temperature

    return DefaultInputDTO.model_validate(
        {"message": {"user_input": "pergunta do usuario"}, "llm_model_config": llm_model_config}
    )


def _build_startup_com_spy() -> tuple[DefaultMessageStartup, _SpyUseCase]:
    startup = DefaultMessageStartup()
    spy = _SpyUseCase(output=_SAIDA_DE_APLICACAO)
    startup.default_message_use_case = spy  # type: ignore[assignment]
    return startup, spy


@pytest.fixture(autouse=True)
def ambiente_de_modelo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Garante configuração suficiente para o grafo do startup ser construído."""
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/modelo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "vendor/modelo")
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo() -> None:
    startup = DefaultMessageStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_injeta_a_porta_de_completions_no_caso_de_uso() -> None:
    startup = DefaultMessageStartup()

    assert isinstance(startup.default_message_use_case, DefaultMessageUseCase)
    assert isinstance(startup.default_message_use_case.llm_completions, ILLMCompletions)


def test_injeta_o_recorder_e_o_relogio_no_caso_de_uso() -> None:
    startup = DefaultMessageStartup()

    assert isinstance(startup.default_message_use_case.session_recorder, ISessionRecorder)
    assert isinstance(startup.default_message_use_case.clock, IClock)


async def test_traduz_o_dto_de_transporte_para_o_dto_de_aplicacao() -> None:
    startup, spy = _build_startup_com_spy()

    await startup.run(payload=_build_payload(temperature=0.3))

    recebido = spy.recebidos[0]
    assert recebido == DefaultMessageInputDTO(
        user_input="pergunta do usuario",
        model_name="vendor/modelo",
        max_tokens=100,
        temperature=0.3,
    )


async def test_temperatura_ausente_assume_o_default_do_contrato() -> None:
    startup, spy = _build_startup_com_spy()

    await startup.run(payload=_build_payload(temperature=None))

    assert spy.recebidos[0].temperature == 0.7


async def test_traduz_a_saida_de_aplicacao_para_o_dto_de_transporte() -> None:
    startup, _ = _build_startup_com_spy()

    resposta = await startup.run(payload=_build_payload())

    assert resposta.message == "pergunta do usuario"
    assert resposta.response == "resposta do modelo"
    assert resposta.session_id == "sess_ab12"
    assert resposta.tokens_input == 11
    assert resposta.tokens_output == 22
    assert resposta.inference_time_ms == 812
