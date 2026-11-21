"""As fixtures de paridade do frontend são capturas reais do caso de uso, não reconstruções.

Cada `capture-*.json` precisa coincidir com uma nova execução do mesmo roteiro: frames do WebSocket e
sessão persistida da mesma execução. Se a emissão de eventos ou a persistência mudar, este teste falha
até as fixtures serem regravadas (instruções em `tests/doubles/frontend_parity_capture.py`).
"""
import json
from pathlib import Path

import pytest

from tests.doubles.frontend_parity_capture import CASES, FIXTURE_PREFIX, capture

_FIXTURES = Path(__file__).parents[3] / "frontend" / "src" / "test" / "fixtures"


def _sem_relogio_de_parede(documento: dict) -> dict:
    """`Session.finish` grava `updated_at` com o relógio real numa falha; o campo não participa da paridade."""
    return {**documento, "session": {**documento["session"], "updated_at": None}}


@pytest.mark.parametrize("name", list(CASES))
async def test_fixture_do_frontend_e_a_captura_atual_do_backend(name: str) -> None:
    gravada = json.loads((_FIXTURES / f"{FIXTURE_PREFIX}{name}.json").read_text(encoding="utf-8"))

    assert _sem_relogio_de_parede(gravada) == _sem_relogio_de_parede(await capture(name))


async def test_auditoria_de_c3_fica_armazenada_e_so_a_resposta_aceita_gera_os_eventos_de_c3() -> None:
    capturada = await capture("v2-plan-revision-c3-audit")

    c3 = [m for m in capturada["session"]["messages"] if m["phase"] == "C3"]
    assert [(m["source"], m["subtype"]) for m in c3] == [("system", None), ("llm_agent", "compile")]
    assert "resposta sem json" in c3[0]["content"]
    eventos_c3 = [(e["type"], e["content"]) for e in capturada["events"] if e["phase"] == "C3"]
    assert eventos_c3 == [("thinking", "D) Nenhuma das anteriores"), ("result", "D) Nenhuma das anteriores")]
