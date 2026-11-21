from typing import Any

from pydantic import BaseModel


class BenchmarkFrameDTO(BaseModel):
    """Frame emitido pelo WebSocket de benchmark.

    `type` é `progress` enquanto a bateria executa e `result` no frame final, já encerrado.
    `benchmark_session` é o documento completo da bateria, o mesmo de `GET /v1/benchmark/sessions/{id}`.
    """

    type: str
    benchmark_session: dict[str, Any]
