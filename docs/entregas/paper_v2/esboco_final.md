# Sistemas Compostos de IA: Otimização de Respostas em Benchmarks Objetivos Através de uma Arquitetura Híbrida de Inferência e Validação com Multi-Agentes, Ferramentas e Orquestração Cognitiva




## Resumo

Os *Large Language Models* (*LLMs*)[1] têm, há algum tempo, deixado de ser apenas modelos voltados à geração de texto, consolidando-se como softwares e ferramentas completas. Essa evolução amplia significativamente seu escopo de aplicação, viabilizando funcionalidades como “pensamento prolongado”, acesso à internet e até mesmo suporte ao desenvolvimento de software por meio de interfaces especializadas, frequentemente referidas como *harnesses*, como CLIs — a exemplo de *Cloud Code*[2] (Anthropic), *Codex*[3] (OpenAI) e *OpenCLI*[4] (Open Source) — e *Integrated Development Environment* (IDEs), como *Cursor* e *Windsurf*. Em comum, essas soluções utilizam técnicas já consolidadas na literatura, muitas delas conhecidas há anos, como o princípio de “dividir para conquistar”, além de releituras dessas abordagens, com o objetivo de aproximar os resultados gerados do que é esperado, seja na construção de artefatos mais complexos ou na produção de respostas textuais mais precisas e alinhadas ao usuário. Nesse contexto, este estudo propõe a construção e análise desse conjunto de mecanismos e ferramentas que operam “ao redor” dos modelos de LLM, buscando verificar, na prática, se essas estratégias realmente melhoram a qualidade das respostas geradas. Para isso, serão utilizados como benchmark conjuntos de questões de múltipla escolha que abrangem diferentes áreas do conhecimento, como história, matemática, lógica, filosofia e relações públicas, desde níveis básicos de escolaridade até tópicos avançados em nível de doutorado (PhD).

## Palavras-chave
- Esperar ate o fim do desenvolvimento do glossario, e deposi colocar aqui

## Introdução

Os modelos de linguagem de grande porte (*Large Language Models* — *LLMs*)[1] deixaram de ser meramente geradores de texto e hoje funcionam como plataformas compostas por camadas de processamento, coordenação e ferramentas auxiliares. Essa transição viabiliza capacidades como raciocínio em múltiplas etapas, orquestração de subagentes e uso de ferramentas externas, porém também revela limitações estruturais: nem sempre a melhoria observada no comportamento final advém apenas do modelo base, mas das arquiteturas que organizam e abstraem o processo de inferência.

Este trabalho parte de dois problemas centrais observados na prática e documentados na literatura: (1) a aparente discordância entre respostas iniciais e respostas revisadas por um mesmo modelo — uma sensação comum em interações com modelos mais antigos (por exemplo, no período de popularização do GPT-3.5) de que perguntas de confirmação como “Tem certeza?”, “revise sua resposta” ou mesmo o simples apontamento de erro (“você errou”) induziam o modelo a corrigir-se —, e (2) a forma como fluxos de pensamento (prompting encadeado, agentes e pipelines) são atualmente implementados, incluindo suas fragilidades frente ao crescimento do contexto.

O primeiro problema decorre do fato de que, em tarefas não-triviais, a resposta “de primeira” tende a ser apenas uma primeira tentativa, sujeita a erros e omissões, que pode ser significativamente aprimorada quando a inferência é estruturada em fases explícitas e curtas, com feedback intermediário (muitas vezes com quebra ou reinicialização parcial do contexto entre etapas). Trabalhos como *Chain-of-Thought*[5] e *Tree of Thoughts*[9] mostram ganhos ao induzir o modelo a produzir e avaliar passos intermediários; *ReAct*[6] evidencia a utilidade de alternar raciocínio e ações/observações; e linhas mais diretamente iterativas, como *Reflexion*[7] (reflexão após julgamento externo) e abordagens de *Self-Debugging*[8] (correção guiada por testes), demonstram que ciclos de tentativa–avaliação–revisão podem elevar a taxa de acerto ao transformar “repetir a pergunta” em um mecanismo sistemático de melhoria. Em paralelo, métodos de decomposição e planejamento — como *Least-to-Most Prompting*[10], *Decomposed Prompting*[11] e *Plan-and-Solve Prompting*[12] — reforçam empiricamente que quebrar objetivos complexos em subtarefas, separar planejamento de execução e limitar o escopo contextual de cada passo reduz erros de lógica e omissões de etapas, especialmente quando combinado com verificação automática. Assim, a melhoria não se explica apenas por “mais tokens” ou por uma chamada mais longa, mas pelo desenho de um pipeline que controla o que entra no contexto, quando o modelo planeja, e como a resposta é validada e reescrita.

O segundo problema refere-se às práticas correntes de “thinking” em LLMs e às limitações impostas por janelas de contexto longas. Em arquiteturas populares de agentes, como *ReAct*[6] (*Synergizing Reasoning and Acting*) já mencionado, o modelo tende a operar acumulando em uma única janela um histórico crescente de raciocínios, ações e observações — um desenho que facilita o encadeamento narrativo do processo, mas que também amplia o risco de degradação conforme o volume de contexto aumenta. Esse tipo de limitação é consistente com evidências empíricas sobre o uso de contextos longos: em “*Lost in the Middle*”[13] (Liu et al.), por exemplo, observa-se degradação de desempenho em cenários nos quais o modelo precisa recuperar e utilizar informações relevantes em sequências extensas, especialmente quando esses trechos ficam “perdidos” no meio do contexto. Na prática, a comunidade de engenharia costuma descrever esse acúmulo progressivo e suas consequências como “esgotamento de contexto”, “compactação” e “context rot”: à medida que o histórico cresce, parte do conteúdo relevante perde saliência, compete por atenção com ruído e pode ser “diluída” por resumos implícitos, levando a omissões, inconsistências e aumento de alucinações.

Frente a essas propostas, adotamos como referência prática a implementação do *Ralph Wiggum Loop* popularizada por Geoffrey Huntley no contexto de desenvolvimento de software, na qual um agente é conduzido por um ciclo rígido de execução e verificação para produzir artefatos corretos (p. ex., código) sob restrições operacionais claras. O objetivo deste trabalho é adaptar essa arquitetura — originalmente aplicada a tarefas de engenharia de software — para investigar se os mesmos princípios melhoram a resolução de questões objetivas em benchmarks de múltipla escolha. Em termos gerais, o *Ralph Wiggum Loop* pode ser entendido como um pipeline em que (i) ocorre uma quebra inicial do objetivo em subtarefas e fases, e (ii) cada fase é executada de maneira isolada e “stateless”, isto é, sem carregar diretamente o histórico completo da fase anterior: em vez de continuidade conversacional, o sistema preserva apenas artefatos controlados (como instruções, respostas intermediárias ou resultados de validação) e reinicializa o contexto a cada iteração (“*Fresh Context*”). Embora o nome e o formato operacional sejam recentes, a lógica do loop se apoia em linhas acadêmicas já discutidas — decomposição (*Least-to-Most*[10]; *Decomposed Prompting*[11]), separação entre planejamento e execução (*Plan-and-Solve*[12]) e ciclos de reflexão/autodepuração guiados por avaliação externa (*Reflexion*[7]; *Self-Debugging*[8]) — oferecendo um arcabouço pragmático para aplicar esses achados em orquestrações reproduzíveis.

Neste trabalho, adotamos a hipótese de que a qualidade objetiva de saídas em tarefas de múltipla escolha depende tanto do LLM quanto do “*Harness*” que governa seu uso — isto é, do ferramental e do conjunto de políticas de decomposição, verificação e orquestração aplicadas entre prompt inicial e resposta final. Para testar essa hipótese, buscamos medir o quanto esse *Harness* melhora resultados frente a chamadas simples, comparando cinco modelos (MODELO_1, MODELO_2, MODELO_3, MODELO_4 e MODELO_5) escolhidos para cobrir uma progressão de complexidade — de modelos mais simples, com menos parâmetros, até incluir ao menos um modelo considerado “moderno”. Para cada um desses modelos, comparamos duas configurações: (i) uma inferência “linear”, por meio de uma única requisição direta ao modelo, e (ii) a mesma inferência mediada pelo nosso *Harness* (um pipeline estruturado inspirado no *Ralph Wiggum Loop*, com validações intermediárias e possibilidade de uso de ferramentas externas quando necessário). A comparação de desempenho é realizada por meio de benchmarks construídos sobre as bases GPQA e MMLU, que fornecem questões de múltipla escolha com alternativas e gabaritos; nesses conjuntos, a métrica primária adotada é a acurácia obtida pela correspondência entre a alternativa selecionada pelo sistema e o gabarito.



## Glossario de termos

### Termos citados

[1] LLM - *Large Language Model*: modelo de inteligência artificial treinado em grandes volumes de texto para compreensão e geração de linguagem natural.
Link: https://en.wikipedia.org/wiki/Large_language_model

Ralph Wiggum Loop - *Todo*: adicionar explicação e os links para o blog do Huntey

“Harness” - *Todo*: adicionar explicação. Tb tem um estudo que fala sobnre isso em "https://arxiv.org/abs/2603.16744" (Nonstandard Errors in AI Agents)

### Ferramentas citadas

[2] Cloud Code - CLI para desenvolvimento assistido por IA, com integração a modelos da Anthropic.
Link: https://www.anthropic.com/

[3] Codex - modelo e ferramenta da OpenAI voltados à geração e compreensão de código.
Link: https://openai.com/

[4] OpenCLI - interface de linha de comando open source para integração com modelos de linguagem.
Link: https://opencli.ai/

## Referências (seleção de insumos utilizados)

[5] Chain-of-Thought prompting (ver notas em `docs/analises/vitor`).

[6] ReAct: Synergizing Reasoning and Acting (ver `docs/analises/vitor/notas_adicionais.md`).

[7] Reflexion: Language Agents with Verbal Reinforcement Learning (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[8] Teaching Large Language Models to Self-Debug (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[9] Tree of Thoughts (ver `docs/analises/vitor/notas_adicionais.md`).

[10] Least-to-Most Prompting (Zhou et al.) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[11] Decomposed Prompting — Khot et al. (2022) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[12] Plan-and-Solve Prompting — Wang et al. (2023) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[13] Lost in the Middle: How Language Models Use Long Contexts (Liu et al.) (ver `docs/analises/vitor/dados_para_o_texto/ralph_loop.md`).

[14] Beyond English: The Impact of Prompt Translation Strategies across Languages and Tasks in Multilingual LLMs (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[15] Language Models are Multilingual Chain-of-Thought Reasoners (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[16] Cross-lingual Prompting: Improving Zero-shot Chain-of-Thought Reasoning across Languages (ver `docs/analises/vitor/dados_para_o_texto/ingles_em_promps.md`).

[17] Notas e análises adicionais sobre orquestração de agentes e prompt orchestration (ver `docs/analises/vitor/paper_01/notas.md` e `docs/analises/vitor/papers/links.md`).
