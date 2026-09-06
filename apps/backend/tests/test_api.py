import json
import unittest

from fastapi.testclient import TestClient
from src.main import app


class TestApiEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_check(self) -> None:
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_default_message_endpoint_with_mock(self) -> None:
        payload = {
            "message": {
                "user_input": "Teste de pergunta simples"
            },
            "llm_model_config": {
                "provider": "mock",
                "provider_config": {
                    "model_name": "mock-llama-3.1-8b"
                },
                "max_tokens": 256,
                "temperature": 0.5
            }
        }
        response = self.client.post("/v1/message/default", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("response", data)
        self.assertEqual(data["message"], "Teste de pergunta simples")

    def test_reasoning_sync_endpoint_with_mock(self) -> None:
        payload = {
            "message": {
                "user_input": "Qual dos seguintes números é simultaneamente primo, par e maior que 2?"
            },
            "llm_model_config": {
                "provider": "mock",
                "provider_config": {
                    "model_name": "mock-llama-3.1-8b"
                },
                "max_tokens": 512,
                "temperature": 0.7
            }
        }
        response = self.client.post("/v1/message/reasoning/sync", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("final_answer", data)
        self.assertEqual(data["final_answer"], "D) Nenhuma das anteriores")
        self.assertIn("approved_results", data)
        self.assertIn("events", data)
        self.assertTrue(len(data["events"]) >= 5)

    def test_reasoning_stream_endpoint_with_mock(self) -> None:
        payload = {
            "message": {
                "user_input": "Qual dos seguintes números é simultaneamente primo, par e maior que 2?"
            },
            "llm_model_config": {
                "provider": "mock",
                "provider_config": {
                    "model_name": "mock-llama-3.1-8b"
                },
                "max_tokens": 512,
                "temperature": 0.7
            }
        }
        response = self.client.post("/v1/message/reasoning", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])

        lines = response.text.split("\n\n")
        parsed_events = []
        for line in lines:
            if line.startswith("data: "):
                chunk_str = line[6:].strip()
                if chunk_str:
                    parsed_events.append(json.loads(chunk_str))

        self.assertTrue(len(parsed_events) >= 5)
        last_event = parsed_events[-1]
        self.assertEqual(last_event.get("type"), "result")
        self.assertEqual(last_event.get("content"), "D) Nenhuma das anteriores")


if __name__ == "__main__":
    unittest.main()
