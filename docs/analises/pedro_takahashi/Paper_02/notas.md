## Dados Gerais

- **Título:** Toolformer: Language Models Can Teach Themselves to Use Tools
- **Autores:** Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, Roberta Raileanu, Maria Lomeli, Eric Hambro, Luke Zettlemoyer, Nicola Cancedda, Thomas Scialom (Meta FAIR).
- **Fonte:** https://openreview.net/pdf?id=Yacmpz84TH

## Leitura da Introdução

- Os Modelos de Linguagem (LLMs) possuem limitações inerentes que não podem ser resolvidas apenas com o aumento de escala (parâmetros), como a incapacidade de acessar informações atualizadas, tendência a alucinar fatos, falta de habilidades matemáticas para cálculos precisos e desconhecimento da passagem do tempo.

- As abordagens anteriores para ensinar LLMs a usar ferramentas dependiam de grandes quantidades de anotação humana ou limitavam o uso a tarefas muito específicas.

- Para resolver isso, os autores introduzem o **Toolformer**, um modelo treinado para decidir sozinho *quais* APIs chamar, *quando* chamá-las, *quais argumentos* passar e *como* incorporar os resultados para prever palavras futuras.

- O aprendizado é autossupervisionado, usando a seguinte lógica:
    1. **Amostragem:** O modelo usa *prompts* (*in-context learning*) para gerar dezenas de possíveis chamadas de API em um grande volume de textos.
    2. **Execução:** O sistema executa essas chamadas de API.
    3. **Filtragem:** O modelo calcula se a resposta da API reduz a "perda" (dificuldade) para prever as próximas palavras do texto. Se a API ajudar, a chamada é mantida; caso contrário, é descartada.
    4. **Ajuste Fino (*Finetuning*):** O modelo é treinado no novo *dataset* enriquecido com essas chamadas úteis.
- Ferramentas integradas: Sistema de Perguntas e Respostas (Q&A), Calculadora, Busca na Wikipédia, Tradutor Automático e Calendário.

## Validação Experimental

- O modelo base utilizado foi o GPT-J (6,7 bilhões de parâmetros).

- Foram testados cenários *zero-shot* (sem passar exemplos manuais na hora do teste) em várias tarefas *downstream*.
- **Métricas e Tarefas:**
    - **Matemática (SVAMP, MAWPS, ASDiv):** Ao poder usar a calculadora (acionada em 97,9% das vezes), o Toolformer mais do que dobrou sua *performance* original e superou largamente modelos muito maiores, como o GPT-3 (175 bilhões de parâmetros) e o OPT (66 bilhões de parâmetros).

    - **Fatos e Conhecimento (LAMA):** O modelo decidiu acionar a API de Perguntas e Respostas em 98,1% dos casos, superando todos os *baselines* do mesmo tamanho e sendo competitivo com o GPT-3.

    - **Habilidade de Linguagem (*Language Modeling*):** O estudo provou que o treinamento com ferramentas não degradou a habilidade original do modelo de prever texto (a perplexidade se manteve estável).

## Leitura da Conclusão

- O Toolformer ensina a si mesmo a usar diversas ferramentas por meio de chamadas de API simples, melhorando consideravelmente o desempenho *zero-shot* em várias tarefas e superando modelos muito maiores.

- Limitações identificadas:
    - O modelo ainda não consegue "encadear" ferramentas (usar a saída de uma como entrada de outra), pois as chamadas são geradas de forma independente.

    - A busca não é interativa (se a busca da Wikipédia falhar, ele não tenta reformular a pesquisa ativamente).

    - Ainda é sensível à estruturação das palavras no *prompt* na hora de decidir se deve ou não chamar uma API.

## Conclusões Pessoais

- **Alinhamento com o TCC:** Este é, sem dúvida, um artigo que colabora com a nossa tese. Ele comprova numericamente que o caminho para a inteligência artificial não é apenas aumentar a base de conhecimento estática ("decorar" mais dados aumentando o modelo para 175B de parâmetros), mas sim dar a modelos menores (6,7B) a capacidade de usar ferramentas (*tooling*) para buscar a verdade fora de si mesmos.

- O artigo se mantém estritamente no escopo da restrição: não está criando um sistema de múltiplos agentes autônomos complexos ou robôs que navegam na internet sozinhos. É pura e simplesmente um LLM que aprendeu a gerar uma *string* estruturada de texto (ex.: `[Calculadora(5*5)]`) para acessar uma ferramenta simples quando percebe que a sua própria rede neural não consegue resolver a tarefa.

- A metodologia de filtragem (avaliar a redução da *loss* preditiva) é um argumento técnico excelente para mostrar *como* os LLMs reconhecem que ferramentas são úteis.

---

## Referência (ABNT)
SCHICK, Timo et al. Toolformer: Language Models Can Teach Themselves to Use Tools. In: 37th Conference on Neural Information Processing Systems (NeurIPS), 2023. Disponível em: <https://openreview.net/pdf?id=Yacmpz84TH>. Acesso em: 03 mar. 2026.