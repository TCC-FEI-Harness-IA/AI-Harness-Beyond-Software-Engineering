import json
import re
from typing import Any

# ==============================================================================
# PROMPT TEMPLATES - RALPH WIGGUM LOOP ADAPTADO PARA PERGUNTAS GERAIS
# Alinhado com as especificações do artigo acadêmico (TCC.tex)
# ==============================================================================


TEMPLATE_A1_CRITERIA = """\
[SISTEMA - TEMPLATE_A1_CRITERIA]
Você é o módulo de Planejamento A.1 do Ralph Loop Harness.
Sua missão é analisar o enunciado da pergunta do usuário e definir os CRITÉRIOS DE ACEITE GERAIS que a resposta final deverá respeitar.

Diretrizes obrigatórias para os critérios:
1. Idioma: Identificar e fixar o idioma de resposta adequado (ex: Português do Brasil).
2. Formato de Saída: Se for múltipla escolha, especificar a regra de formato final (ex: responder somente a alternativa correspondente sem explicações adicionais).
3. Restrições e Consistência: Exigir que o valor encontrado corresponda a uma das opções fornecidas ou responda estritamente ao solicitado.

Pergunta do usuário:
---
{user_input}
---

Responda OBRIGATORIAMENTE em formato JSON com a seguinte estrutura:
```json
{{
  "criteria": [
    "A pergunta deve ser respondida em Português do Brasil.",
    "Responda somente a alternativa, sem conter explicações adicionais.",
    "Garanta que o valor encontrado ao final corresponde a uma das alternativas fornecidas."
  ]
}}
```
"""


TEMPLATE_A2_DECOMPOSITION = """\
[SISTEMA - TEMPLATE_A2_DECOMPOSITION]
Você é o módulo de Planejamento A.2 do Ralph Loop Harness.
Sua missão é decompor a pergunta do usuário em pequenas TAREFAS DE OBJETIVO ÚNICO, independentes e verificáveis.

Regras e princípios do Fresh Context (Ralph Loop):
1. Cada tarefa deve ter uma única responsabilidade atômica (ex: avaliar apenas uma propriedade ou condição por tarefa).
2. Cada tarefa deve ter sua própria lista de CRITÉRIOS DE ACEITE INDIVIDUAIS.
3. RESTRIÇÃO DE ESCOPO OBRIGATÓRIA: Em cada tarefa, deve constar como critério explícito:
   - "A resposta não deve tentar resolver a questão final."
   - "A resposta não deve avaliar nenhuma outra condição."
4. As tarefas devem gerar os insumos lógicos necessários para que, posteriormente, a síntese final responda à pergunta.

Pergunta do usuário:
---
{user_input}
---

Responda OBRIGATORIAMENTE em formato JSON com a seguinte estrutura:
```json
{{
  "tasks": [
    {{
      "id": "T1",
      "title": "Breve título descritivo",
      "description": "Enunciado claro e delimitado da tarefa",
      "acceptance_criteria": [
        "Critério específico sobre a saída esperada",
        "Critério de justificativa ou regra usada",
        "A resposta não deve tentar resolver a questão final.",
        "A resposta não deve avaliar nenhuma outra condição."
      ]
    }}
  ]
}}
```
"""


TEMPLATE_B1_EXECUTE = """\
[SISTEMA - TEMPLATE_B1_EXECUTE]
Você é o executor da tarefa no ciclo Ralph Loop.

{accumulated_learnings_section}

Sua tarefa atual:
Identificador: {task_id} - {task_title}
Enunciado da Tarefa:
{task_description}

Critérios de Aceite que você deve satisfazer:
{task_criteria}

ATENÇÃO ÀS RESTRIÇÕES:
- Foque UNICAMENTE no escopo demarcado para esta tarefa.
- NÃO resolva a questão final global da pergunta.
- NÃO cruze com condições de outras tarefas.
- Apresente sua análise e o resultado parcial específico desta tarefa.
"""


TEMPLATE_B2_VERIFY = """\
[SISTEMA - TEMPLATE_B2_VERIFY]
Você é o Validador de Controle de Qualidade da Tarefa (Fase B.2) no Ralph Loop.
Sua missão é avaliar se o Resultado Preliminar gerado satisfaz rigorosamente TODOS os critérios de aceite individuais da tarefa.

Enunciado da Tarefa:
{task_description}

Critérios de Aceite Individuais:
{task_criteria}

Resultado Preliminar a ser avaliado:
---
{preliminary_result}
---

Regras de validação:
- Se o modelo adiantou a resposta final da questão principal, REPROVE IMEDIATAMENTE.
- Se o modelo avaliou condições além do escopo delimitado, REPROVE IMEDIATAMENTE.
- Se algum critério obrigatório não foi cumprido, REPROVE.
- Se todos os critérios foram atendidos estritamente, APROVE.

Responda OBRIGATORIAMENTE em formato JSON:
```json
{{
  "approved": true,
  "feedback": "Justificativa resumida da decisão.",
  "evaluations": [
    {{
      "criterion": "Descrição do critério",
      "met": true,
      "reason": "Explicação objetiva de como foi atendido ou violado"
    }}
  ]
}}
```
"""


TEMPLATE_B4_LEARN = """\
[SISTEMA - TEMPLATE_B4_LEARN]
Você é o extrator de aprendizados pontuais (Fase B.4) do Ralph Loop.
Sua missão é sintetizar APRENDIZADOS FACTUAIS SECOS e objetivos descobertos ao longo da execução da tarefa.

Histórico de execução da tarefa:
---
{task_execution_history}
---

Diretrizes estritas:
1. Extraia apenas fatos concretos e restrições atômicas descobertas (ex: "Primos entre (2,4,6): [2]", "Um número par é divisível por 2 sem deixar resto").
2. NÃO crie narrativas de processo (evite frases como "Durante a execução nós analisamos...").
3. NÃO inclua definições óbvias sem utilidade operacional.
4. Mantenha os tópicos extremamente curtos e factuais.

Responda OBRIGATORIAMENTE em formato JSON:
```json
{{
  "facts": [
    "Fato conciso 1",
    "Fato conciso 2"
  ]
}}
```
"""


TEMPLATE_C1_VERIFY_GLOBAL = """\
[SISTEMA - TEMPLATE_C1_VERIFY_GLOBAL]
Você é o Validador Global da Síntese Final (Fase C.1) do Ralph Loop.
Sua missão é verificar se os Resultados Armazenados de todas as tarefas são suficientes para atender plenamente aos Critérios de Aceite Gerais estabelecidos no início.

Pergunta original:
{user_input}

Critérios de Aceite Gerais (A.1):
{general_criteria}

Resultados Armazenados das Tarefas Concluídas:
{stored_results}

Avalie: Os resultados acima contêm todas as informações necessárias para compor a resposta final satisfazendo cada um dos critérios gerais?
- Se sim, aprove.
- Se houver lacuna (por exemplo, faltou cruzar interseções ou avaliar alguma condição do enunciado), reprove e liste os critérios não atendidos.

Responda OBRIGATORIAMENTE em formato JSON:
```json
{{
  "approved": true,
  "unmet_criteria": [],
  "feedback": "Explicação resumida da conformidade ou das lacunas identificadas"
}}
```
"""


TEMPLATE_C2_ADDITIONAL_PLANNING = """\
[SISTEMA - TEMPLATE_C2_ADDITIONAL_PLANNING]
Você é o Planejador Adicional (Fase C.2) do Ralph Loop.
A validação global identificou lacunas que impedem a conclusão satisfatória da resposta final.
Sua missão é planejar NOVAS TAREFAS cirúrgicas para suprir exclusivamente o que está faltando, aproveitando o que já foi apurado.

Resultados já existentes:
{stored_results}

Critérios Gerais ainda não atendidos:
{unmet_criteria}

Feedbacks da reprovação:
{feedback}

Gere novas tarefas independentes para fechar essas lacunas.
Responda OBRIGATORIAMENTE em formato JSON:
```json
{{
  "new_tasks": [
    {{
      "id": "T_extra",
      "title": "Título da tarefa complementar",
      "description": "Enunciado específico da nova tarefa",
      "acceptance_criteria": [
        "Critério específico",
        "A resposta não deve construir a resposta final ao usuário."
      ]
    }}
  ]
}}
```
"""


TEMPLATE_C3_FINAL_SYNTHESIS = """\
[SISTEMA - TEMPLATE_C3_FINAL_SYNTHESIS]
Você é o Sintetizador Final (Fase C.3) do Ralph Loop.
Todos os critérios gerais foram satisfeitos pelas tarefas intermediárias homologadas.
Sua missão é compor a RESPOSTA FINAL ao usuário.

Pergunta original:
{user_input}

Critérios de Aceite Gerais (A.1):
{general_criteria}

Resultados Homologados das Tarefas:
{stored_results}

REGRAS RÍGIDAS DE COMPOSIÇÃO:
1. Baseie-se EXCLUSIVAMENTE nos resultados homologados acima. É proibido inventar ou presumir fatos não apurados.
2. Respeite estritamente o formato e idioma exigidos pelos critérios gerais (por exemplo: se for múltipla escolha e os critérios pedirem apenas a alternativa, retorne somente a alternativa como "D) Nenhuma das anteriores").
3. Não adicione saudações ou meta-comentários além do exigido pelos critérios.
"""


def extract_json_payload(text: str) -> dict[str, Any]:
    """Extrai e faz o parse de payload JSON de blocos markdown ou texto cru."""
    text_clean = text.strip()

    # Tenta bloco ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_clean, re.IGNORECASE)
    if match:
        raw_json = match.group(1).strip()
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Tenta achar o primeiro '{' e último '}'
    start = text_clean.find("{")
    end = text_clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text_clean[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {}
