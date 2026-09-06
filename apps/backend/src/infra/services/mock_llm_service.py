import json
import logging
import re
from typing import Any

from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.llm_service_provider.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class MockLLMService(ILLMService):
    """Serviço Mock de LLM para testes locais e validação offline da lógica do Ralph Loop.

    Gera respostas consistentes com os templates do paper sem depender de chamadas externas de rede.
    """

    def __init__(self, logger: logging.Logger, settings: ISettings) -> None:
        self.logger = logger
        self.settings = settings

    @property
    def provider(self) -> ModelProviderEnum:
        return ModelProviderEnum.MOCK

    def verify_provider_settings(self) -> bool:
        return True

    def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        self.logger.info("MockLLMService gerando resposta simulada")

        last_message = request.messages[-1].content if request.messages else ""

        # Identifica a fase do prompt através de palavras-chave
        if "TEMPLATE_A1_CRITERIA" in last_message or "CRITÉRIOS DE ACEITE GERAIS" in last_message:
            output = json.dumps({
                "criteria": [
                    "A pergunta deve ser respondida em Português do Brasil.",
                    "Responda somente a alternativa correspondente, sem conter explicações adicionais no resultado final.",
                    "Garanta que o valor encontrado ao final corresponde a uma das alternativas fornecidas no enunciado.",
                ]
            }, ensure_ascii=False)

        elif "TEMPLATE_A2_DECOMPOSITION" in last_message or "DECOMPOSIÇÃO EM TAREFAS" in last_message:
            output = json.dumps({
                "tasks": [
                    {
                        "id": "T1",
                        "title": "Números primos",
                        "description": "Dadas as opções (2, 4, 6), identifique quais desses números são primos.",
                        "acceptance_criteria": [
                            "Deve retornar a lista de números primos encontrados nas alternativas.",
                            "Deve incluir uma breve explicação da regra de identificação de números primos.",
                            "A resposta não deve tentar resolver a questão final.",
                            "A resposta não deve avaliar nenhuma outra condição.",
                        ],
                    },
                    {
                        "id": "T2",
                        "title": "Números pares",
                        "description": "Dadas as opções (2, 4, 6), identifique quais desses números são pares.",
                        "acceptance_criteria": [
                            "Deve retornar a lista de números pares encontrados nas alternativas.",
                            "Deve incluir uma breve explicação da regra de identificação de números pares.",
                            "A resposta não deve tentar resolver a questão final.",
                            "A resposta não deve avaliar nenhuma outra condição.",
                        ],
                    },
                    {
                        "id": "T3",
                        "title": "Maiores que 2",
                        "description": "Dadas as opções (2, 4, 6), identifique quais desses números são estritamente maiores que 2.",
                        "acceptance_criteria": [
                            "Deve retornar a lista de números maiores que 2 encontrados nas alternativas.",
                            "Deve incluir uma breve justificativa matemática para a comparação estabelecida.",
                            "A resposta não deve tentar resolver a questão final.",
                            "A resposta não deve avaliar nenhuma outra condição.",
                        ],
                    },
                ]
            }, ensure_ascii=False)

        elif "TEMPLATE_B2_VERIFY" in last_message or "VERIFICAÇÃO DE CRITÉRIOS DA TAREFA" in last_message:
            # Simula aprovação de critérios
            output = json.dumps({
                "approved": True,
                "feedback": "Todos os critérios individuais foram satisfeitos.",
                "evaluations": [
                    {"criterion": "Critério atendido", "met": True, "reason": "Conforme esperado"}
                ]
            }, ensure_ascii=False)

        elif "TEMPLATE_B4_LEARN" in last_message or "EXTRAÇÃO DE APRENDIZADOS PONTUAIS" in last_message:
            # Simula extração de fatos objetivos
            output = json.dumps({
                "facts": [
                    "Dado factual extraído da análise da tarefa.",
                ]
            }, ensure_ascii=False)

        elif "TEMPLATE_C1_VERIFY_GLOBAL" in last_message or "VERIFICAÇÃO GLOBAL" in last_message:
            output = json.dumps({
                "approved": True,
                "unmet_criteria": [],
                "feedback": "Todos os critérios gerais foram satisfeitos com os dados acumulados.",
            }, ensure_ascii=False)

        elif "TEMPLATE_C2_ADDITIONAL_PLANNING" in last_message:
            output = json.dumps({"new_tasks": []}, ensure_ascii=False)

        elif "TEMPLATE_C3_FINAL_SYNTHESIS" in last_message or "RESPOSTA FINAL" in last_message:
            output = "D) Nenhuma das anteriores"

        elif "TEMPLATE_B1_EXECUTE" in last_message or "EXECUÇÃO DE TAREFA" in last_message:
            output = (
                "Análise detalhada da tarefa em execução: identificação direta das propriedades pedidas. "
                "Resultado consolidado para a tarefa."
            )

        else:
            output = "Resposta padrão simulada pelo MockLLMService."

        return LLMProviderResponse(
            output_text=output,
            input_tokens=120,
            output_tokens=85,
            finish_reason="stop",
            raw_response={"mock": True},
        )
