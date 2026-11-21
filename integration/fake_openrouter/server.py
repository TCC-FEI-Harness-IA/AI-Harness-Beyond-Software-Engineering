"""OpenRouter falsa para o teste de integração: nenhum crédito é consumido e nenhuma chave real é usada.

- GET  /api/v1/key               -> 200 só para a chave aceita; 401 para qualquer outra.
- POST /api/v1/chat/completions  -> completion fixa, depois de FAKE_DELAY_SECONDS; registra o header Authorization.
- GET  /__calls                  -> chaves vistas nas completions (introspecção do teste).
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ACCEPTED = os.environ.get("FAKE_ACCEPTED_KEYS", "").split(",")
DELAY = float(os.environ.get("FAKE_DELAY_SECONDS", "0"))
CALLS: list[str] = []


class Handler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: object) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _key(self) -> str:
        return self.headers.get("Authorization", "").removeprefix("Bearer ")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/v1/key":
            self._reply(200 if self._key() in ACCEPTED else 401, {"data": {"label": "fake"}})
        elif self.path == "/__calls":
            self._reply(200, {"keys": CALLS})
        else:
            self._reply(404, {})

    def do_POST(self) -> None:  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path != "/api/v1/chat/completions":
            self._reply(404, {})
            return
        CALLS.append(self._key())
        time.sleep(DELAY)
        self._reply(200, {
            "id": f"gen-{len(CALLS)}",
            "choices": [{"message": {"content": "RESPOSTA_FINAL: A"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        })

    def log_message(self, *_: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
