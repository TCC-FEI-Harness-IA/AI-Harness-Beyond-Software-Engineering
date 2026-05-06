# Sistemas Compostos de IA: Otimização de Respostas em Benchmarks Objetivos Através de uma Arquitetura Híbrida de Inferência e Validação com Multi-Agentes, Ferramentas e Orquestração Cognitiva




## Resumo


Os *Large Language Models* (*LLMs*)[1] têm, há algum tempo, deixado de ser apenas modelos voltados à geração de texto, consolidando-se como softwares e ferramentas completas. Essa evolução amplia significativamente seu escopo de aplicação, viabilizando funcionalidades como “pensamento prolongado”, acesso à internet e até mesmo suporte ao desenvolvimento de software por meio de interfaces especializadas, frequentemente referidas como *harnesses*, como CLIs — a exemplo de *Cloud Code*[2] (Anthropic), *Codex*[3] (OpenAI) e *OpenCLI*[4] (Open Source) — e *Integrated Development Environment* (IDEs), como *Cursor* e *Windsurf*. Em comum, essas soluções utilizam técnicas já consolidadas na literatura, muitas delas conhecidas há anos, como o princípio de “dividir para conquistar”, além de releituras dessas abordagens, com o objetivo de aproximar os resultados gerados do que é esperado, seja na construção de artefatos mais complexos ou na produção de respostas textuais mais precisas e alinhadas ao usuário. Nesse contexto, este estudo propõe a construção e análise desse conjunto de mecanismos e ferramentas que operam “ao redor” dos modelos de LLM, buscando verificar, na prática, se essas estratégias realmente melhoram a qualidade das respostas geradas. Para isso, serão utilizados como benchmark conjuntos de questões de múltipla escolha que abrangem diferentes áreas do conhecimento, como história, matemática, lógica, filosofia e relações públicas, desde níveis básicos de escolaridade até tópicos avançados em nível de doutorado (PhD).

## Introdução

- Aqui quero colocar:
    - 2 problemas:
        - Aquele sentimento de Nos modelos antigos do GPT parecia que ele dava a resposta errada, ai eu falava "Tem certeza?", e ai ele me respondia corretamente.
            - Hoje em dia o pensamento força isso automaticamente

        - Como são implementados os fluxos de pensamento hoje em dia:
            - Citar estudos que ja resolvem esse problema:
                - Estudos de quebra de tarefa e "THINKING": ReAct, buscar outros
                - Estudos de uso do ingles em prompts: (tem 3, ja esta ok)
            - Citar o "esgotamento de contexto", "podridão de contexto" (context rot) ou "compactação":
                - Como resolvemos isso: Ralph Wiggum Loop
                - Qual o historico do Ralph Wiggum Loop:
                    - Deve vir antes, junto com o os estudos que ja resolvem o problema?
                        - Decomposed Prompting (Khot et al., 2022)
                        - Plan-and-Solve Prompting (Wang et al., 2023)




## Glossario de termos

### Termos citados

[1] LLM - *Large Language Model*: modelo de inteligência artificial treinado em grandes volumes de texto para compreensão e geração de linguagem natural.
Link: https://en.wikipedia.org/wiki/Large_language_model

Ralph Wiggum Loop -

### Ferramentas citadas

[2] Cloud Code - CLI para desenvolvimento assistido por IA, com integração a modelos da Anthropic.
Link: https://www.anthropic.com/

[3] Codex - modelo e ferramenta da OpenAI voltados à geração e compreensão de código.
Link: https://openai.com/

[4] OpenCLI - interface de linha de comando open source para integração com modelos de linguagem.
Link: https://opencli.ai/
