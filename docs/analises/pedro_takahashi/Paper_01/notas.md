# Análise do Paper

## Dados Gerais

| Campo  | Descrição |
|--------|-----------|
| **Título** | Tree of Thoughts: Deliberate Problem Solving with Large Language Models |
| **Autores** | YAO, S.; YU, D.; ZHAO, J.; SHAFRAN, I.; GRIFFITHS, T. L.; CAO, Y.; NARASIMHAN, K. |
| **Instituições** | Princeton University; Google DeepMind |
| **Fonte** | https://par.nsf.gov/servlets/purl/10542045 |

---

## Leitura da Introdução

- LMs estão sendo cada vez mais usados para resolução de problemas gerais, mas estão confinados a um processo de tomada de decisão linear (da esquerda para a direita, token por token) associado ao pensamento rápido do "Sistema 1".
- Para resolver tarefas complexas, o principal desafio é a falta de exploração, visão estratégica de futuro (*lookahead*) e a incapacidade de corrigir decisões iniciais ruins (retrocesso/*backtracking*).
- O artigo aponta que abordagens atuais (como o *Chain-of-Thought* — CoT) são limitadas principalmente por:
    - Não explorarem continuações diferentes dentro de um mesmo processo de raciocínio (não criam "ramos").
    - Não incorporarem nenhum tipo de planejamento global baseado em heurísticas.
- Para resolver isso, os autores introduzem o framework **"Tree of Thoughts" (ToT)**, que enquadra a resolução de problemas como uma busca em uma árvore combinatória clássica, onde cada nó é um "pensamento" (um passo intermediário coerente).
- O framework se baseia em quatro pilares para orquestrar o LLM:
    1. **Decomposição de pensamentos:** Quebrar o problema em passos intermediários avaliáveis.
    2. **Geração de pensamentos:** O modelo gera múltiplas opções (ramos) para o próximo passo (por amostragem ou proposta sequencial).
    3. **Avaliador de estados:** O próprio LLM atua como uma função heurística, avaliando independentemente cada caminho (ex.: certeza/talvez/impossível) ou votando no melhor.
    4. **Algoritmo de busca:** Uso de algoritmos clássicos da computação, como Busca em Largura (BFS) ou Busca em Profundidade (DFS), para navegar na árvore.

---

## Validação Experimental

Foram testados três problemas que exigem planejamento e que o GPT-4 não consegue resolver com métodos convencionais:

| Tarefa | Métrica | Resultado |
|--------|---------|-----------|
| **Game of 24** (Raciocínio Matemático) | Taxa de sucesso para chegar ao número 24 usando 4 números | ToT: **74%** vs. CoT: 4% |
| **Creative Writing** (Planejamento Criativo) | Coerência avaliada por humanos e GPT-4 *zero-shot* | ToT preferido em **41/100** casos (CoT preferido em 21) |
| **Mini Crosswords 5×5** (Busca e Léxico) | Taxa de sucesso por palavra | ToT: **60%** vs. CoT: 15,6% |

---

## Leitura da Conclusão

- O sistema associativo linear dos LLMs pode ser fortemente aprimorado ao ser embutido em um "Sistema 2" baseado na busca por uma árvore de caminhos.
- Existem limitações relevantes:
    - O método exige muito mais recursos computacionais e chamadas de API do que a amostragem padrão, sendo mais caro.
    - A busca deliberada (ToT) não é necessária para tarefas em que o modelo já atinge excelência facilmente (o ganho em tarefas mais fáceis, como GSM8K, é marginal e não compensa o custo).
    - O sucesso depende da qualidade da heurística do modelo; se o LLM falhar ao avaliar se um estado é impossível (falso negativo), ele pode podar o caminho certo — como visto no jogo de palavras-cruzadas.

---

## Conclusões Pessoais

- **Alinhamento com o TCC:** Este artigo é uma prova contundente para a tese. Ele mostra que o ganho de performance em tarefas complexas não veio de aumentar a base de conhecimento do GPT-4, mas sim de envolvê-lo em uma arquitetura de sistema (os algoritmos clássicos de Busca BFS e DFS).
- O ponto que mais chama a atenção é que **o ToT não é um sistema multi-agente autônomo**, mas sim uma **arquitetura híbrida de "sistema tradicional + LLM"**. É um código Python puro rodando um loop de grafos (árvores), usando o LLM apenas como uma "ferramenta" (*tool*) para gerar e avaliar nós.
- Isso valida exatamente o ponto da tese: não precisamos forçar a criação de enxames de agentes complexos para resolver problemas difíceis; criar um invólucro de código (*tooling*/sistema) bem estruturado que controle o fluxo de raciocínio do modelo via *prompts* dinâmicos é o suficiente para elevar exponencialmente a capacidade de IA de forma controlada e sem treinamento adicional.

---

## Referência (ABNT)


YAO, Shunyu et al. Tree of thoughts: Deliberate problem solving with large language models. In: 37th Conference on Neural Information Processing Systems (NeurIPS), 2023. Disponível em:[ arXiv preprint arXiv:2305.10601.](https://arxiv.org/pdf/2305.10601) Acesso em: 03 mar. 2026.
