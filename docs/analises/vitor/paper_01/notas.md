# Analise do paper 01

## Dados Gerais:

- Nome: Reasoning-Aware Prompt Orchestration: A Foundation Model for Multi-Agent Language Model Coordination
- Autor: Hassen Dhrif - Amazon
- Fonte: https://arxiv.org/abs/2510.00326





## Leitura da introdução:

- Cita LLMs conseguem resolver tarefas de maneira autônoma, mas não tarefas complexas
    - Para resolver tarefas com complexidade e problemas do mundo real é necessário a criação de sistemas de agentes especializados, onde cada agente deve reforçar diferentes aspectos de um LLM
- O principal desafio nesse sistema é a coordenação entre agentes.
    - Cita tambem que o "prompt engineering" para essa coordenação é um pouco diferente do tradicional para funcionar
    - Prompt engineering tradicional é focado em agente único, e essa arquitetura é diferente

- Lidar com aplicações de multi agentes possui algumas dificuldades "context loss during agent transitions, conflicting logical frameworks, and poor scalability under load"
    - Para resolver isso "introducing a formal framework for dynamic prompt orchestration in multi-agent systems"
    - Basicamente, as abordagens atuais são limitas principalmente por usar:
        - Templates estaticos de prompts
        - Mecanismos de coordenação entre agentes simples (como round-robin)
    - O problema principal com isso é que mata o dinamismo necessario para um raciocinio multi agente


- Para resolver tudo isso é a ideia é criar um framework para orquestração dinâmica de prompts com os seguintes pilares:
    - Captura de estados para evolução do raciocínio
    - Mecanismo de Consenso distribuído entre agentes para manter consistência lógica
    - Roteamento de agentes adaptativo e baseano em suas capacidades


- Estudo entra em mais alguns pontos de formalização técnica, dando estados aos agentes


- *validação experimental*:
    - Latência
    - Consistência
    - Taxa de sucesso em tarefas


## leitura da conclusão

- Existem limites para a coordenação de agentes via prompt
- Há comportamentos emergentes não previstos por modelos teóricos simplificados (mean-field)
- Existem limitações:
    - Ocorreu melhora nos resultados, porém somente em casos de média/alta complexidade, principalmente usando entre 5-10 agentes
    - Após esse ponto existe degradação acentuada do desempenho
        - NOTA: verificar a data do artigo, e qual será o módulo usado. Será problema de janela de contexto?
	- Essa limitação aparece independentemente do mecanismo de coordenação utilizado.



## Conclusões pessoais:

- Aparentemente esse paper pode agregar muito, porém tem um ponto que me chama mais a atenção:
    - A orquestração pelo o que entendi foi feita somente com agentes
    - Não precisamos nos forçar a isso, podemos usar uma arquitetura híbrida de "sistema" + prompts
