# Título, Metadados e Resumo

## Título

Um *Harness* de IA para Resolução de Perguntas em Linguagem Natural: Adaptando o *Ralph Wiggum Loop* Além do Desenvolvimento de Software

## Autores e Filiação

- **Autores:** Hugo Emílio Nomura, Pedro Henrique Correia de Oliveira, Pedro Henrique Satoru Lima Takahashi, Vitor Monteiro Vianna
- **Filiação:** Ciência da Computação — Centro Universitário FEI, *campus* São Paulo
- **E-mails:** `unifhnomura@fei.edu.br`, `unifpoliveira@fei.edu.br`, `unifptakahashi@fei.edu.br`, `unievvianna@fei.edu.br`
- **Orientador:** Charles Henrique Porto Ferreira — Departamento de Ciência da Computação, Centro Universitário FEI (`cferreira@fei.edu.br`)

---

## Resumo

Os *Large Language Models* (LLMs), embora sejam em essência geradores probabilísticos de *tokens*, alcançam ganhos expressivos de desempenho quando o processo de inferência é estruturado por *harnesses* que incorporam planejamento, decomposição de tarefas e ciclos iterativos de verificação. Entretanto, arquiteturas que preservam o histórico completo de execução em uma única janela de contexto introduzem degradação progressiva da qualidade das respostas conforme o volume textual acumulado cresce, fenômeno denominado *context rot*, que compromete a confiabilidade dos resultados em execuções longas. 

Este trabalho propõe, implementa e avalia empiricamente uma adaptação do *Ralph Wiggum Loop*, paradigma de orquestração originalmente concebido para engenharia de software baseado que traz soluções para mitigar problemas de *context rot*, baseado em decomposição atômica, validação iterativa e reinicialização de contexto (*Fresh Context*), para um fluxo generalista de resolução de perguntas em linguagem natural. A arquitetura resultante estrutura-se em três macrofases: (A) Planejamento em quatro etapas, incluindo definição de critérios gerais (`A.1`), decomposição em tarefas candidatas com dependências explícitas (`A.2`), validação semântica do plano por rubrica fixa de sete regras (`A.3`) e extração prévia de dados literais do enunciado (`A.4`); (B) Execução em Loop com isolamento rigoroso de janela por invocação de fase, critério fixo de validade técnica obrigatória, livro de estados de resultados com suporte a revisões auditáveis, memória transversal de aprendizados com procedência rastreável e escalonamento dinâmico de temperatura em retentativas; e (C) Criação da Resposta Final, combinando verificação global de suficiência e consistência (`C.1`), planejamento adicional com possibilidade de revisão de resultados prévios (`C.2`) e síntese fiel sobre *snapshot* imutável (`C.3`), sob contrato JSON estrito e guardrails de orçamento com política *fail-closed*. A avaliação experimental comparou de forma pareada a inferência direta (*baseline* 0-shot) e o *harness* proposto utilizando o modelo `deepseek/deepseek-v4-flash-0731` (com *reasoning* nativo desabilitado e temperatura base `0,0`) em 743 questões válidas pareadas distribuídas em três *benchmarks*: Vestibulares brasileiros (`vestibular-v1`, 268/270 questões), MMLU generativo 0-shot (285 questões em 57 disciplinas) e GPQA Diamond generativo 0-shot (190/198 questões). Na métrica ponta-a-ponta, o *harness* apresentou desempenho inferior ao *baseline* no agregado ($85{,}73\%$ contra $87{,}75\%$; $\Delta = -2{,}02\text{ p.p.}$, $p = 0{,}133$), influenciado por 31 falhas operacionais *fail-closed* que explicam $49{,}0\%$ ($25/51$) das regressões totais, ao custo mediano de $79{,}2\times$ a $140{,}7\times$ mais *tokens*. Contudo, entre as 711 execuções válidas concluídas, o *harness* superou o *baseline* no agregado ($89{,}45\%$ contra $88{,}19\%$; $\Delta = +1{,}27\text{ p.p.}$, $p = 0{,}306$), atingindo ganhos expressivos e estatisticamente significativos no regime de alta complexidade analítica (GPQA Diamond, ITA e UNICAMP: $83{,}48\%$ contra $76{,}34\%$; $\Delta = +7{,}14\text{ p.p.}$, $p = 0{,}0139$) e em disciplinas STEM ($89{,}3\%$ contra $85{,}5\%$; $\Delta = +3{,}7\text{ p.p.}$, $p = 0{,}023$), enquanto registrou perdas em questões factuais, de humanidades e em regimes próximos ao teto de desempenho (ENEM e MMLU Humanidades). A análise de causa raiz identifica seis mecanismos de falha — destacando *deadlocks* em `B.2` sem *backtracking* para erros *upstream*, fragilidade de serialização JSON e superdecomposição em itens simples — e fundamenta seis hipóteses técnicas para evolução da arquitetura.

## Palavras-chave

*Large Language Models* (LLMs). *Ralph Wiggum Loop*. Sistemas Compostos de IA. Orquestração de Inferência. Decaimento de Contexto (*context rot*). Avaliação em *Benchmarks*.
