# Notas gerais para uso do TCC


## ReAct - Synergizing Reasoning and Acting
- Estudo em: https://arxiv.org/abs/2210.03629
- Modelos tradicionais de deep thinking usam o modelo ReAct (Synergizing Reasoning and Acting) (?).
    - Aqui, os agentes operam mantendo um histórico contínuo e crescente de pensamentos, ações, observações e resultados dentro de uma única janela de contexto
    - No entanto, evidências empíricas e estudos de longo prazo demonstraram que, à medida que a complexidade da tarefa aumenta, esse histórico se expande exponencialmente, resultando no fenômeno que a comunidade de engenharia identifica como "esgotamento de contexto", "podridão de contexto" (context rot) ou "compactação". 2


- O desenvolvimento de agentes autônomos tem sido historicamente dominado por arquiteturas onde o modelo de linguagem atua como um repositório central de estado. Em frameworks tradicionais baseados no padrão ReAct (Synergizing Reasoning and Acting), os agentes operam mantendo um histórico contínuo e crescente de pensamentos, ações, observações e resultados dentro de uma única janela de contexto. 1
https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. (2023). ReAct:
Synergizing reasoning and acting in language models. In International Conference on Learning
Representations (ICLR).


- No entanto, evidências empíricas e estudos de longo prazo demonstraram que, à medida que a complexidade da tarefa aumenta, esse histórico se expande exponencialmente, resultando no fenômeno que a comunidade de engenharia identifica como "esgotamento de contexto", "podridão de contexto" (context rot) ou "compactação". 2
https://arxiv.org/abs/2210.03629

- Quando o contexto é compactado ou sobrecarregado, o LLM perde a capacidade de rastrear as instruções fundamentais, resultando em alucinações severas e na degradação irreversível da qualidade da saída. 3
https://openreview.net/pdf?id=vAElhFcKW6


## Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
https://arxiv.org/pdf/2201.11903


## Tree of Thoughts: Deliberate Problem Solving with Large Language Models
https://arxiv.org/abs/2305.10601
