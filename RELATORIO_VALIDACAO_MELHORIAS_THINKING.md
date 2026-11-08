# Relatório de validação — melhorias do thinking (etapas 01 a 07)

Este relatório consolida a validação da etapa 07, que integrou as cinco frentes do thinking:
**estrutura e recuperação** (recuperação integral, isolamento de contexto, livro de resultados e
revisão auditável), **aprendizados**, **planejamento**, **validação** e **síntese fiel**. As regras e
a procedência de cada etapa estão em [`NOVAS_REGRAS_RALPH_LOOP.md`](NOVAS_REGRAS_RALPH_LOOP.md)
(seções “Melhorias do thinking — 01” a “— 07”); os relatórios parciais anteriores
(`VALIDACAO_MELHORIAS_THINKING_01_02_03.md`, `VALIDACAO_MELHORIAS_THINKING_04.md`) continuam como
registro histórico.

> **Leitura obrigatória antes dos números.** Toda evidência abaixo é **programática** ou de **contrato
> de prompt**. As saídas do modelo nos testes são roteirizadas — inclusive as corretas —, então nenhum
> cenário mede acurácia. Nenhuma inferência paga e nenhum benchmark foram executados nesta etapa.

## 1. Resultado em uma tabela

| Verificação (pasta `apps/backend`, `.venv`, Python 3.12.10) | Resultado real |
|---|---|
| Linha de base antes da etapa 07: `flake8 src tests` | Saída vazia, código 0. |
| Linha de base antes da etapa 07: suíte completa | Verde, cobertura 100,00% (5.591 statements, 1.002 branches). |
| Testes novos antes das correções (46 então existentes) | **8 falhas, 38 aprovações** (detalhes na seção 4). |
| Testes novos depois das correções | **48 passaram** em 0,30 s (18 de integração + 30 de contrato). |
| Suítes de aplicação, providers, adapters, domínio e mapeadores (`-o addopts=''`) | **1.892 passaram** em 4,80 s. |
| `flake8 src tests` final | Saída vazia, código 0. |
| `pytest --cov=src --cov-report=term-missing --cov-fail-under=100` final | **2.438 passaram** em 80,76 s; cobertura **100,00%** — 5.598 statements e 1.004 branches, nenhum ausente. |
| `git diff --check` | Sem erros. |
| Transcrição literal da Metodologia em `RALPH_LOOP_ADAPTADO.md` | Idêntica ao `HEAD` (comparação por `diff` da seção). |
| `NOVAS_REGRAS_RALPH_LOOP.md` | O conteúdo do `HEAD` é prefixo byte a byte do arquivo atual (`cmp`); a seção 07 foi anexada. |

Comandos executados:

```bash
cd apps/backend
pytest -o addopts='' -q tests/application/usecases/test_ralph_five_fronts_integration.py \
  tests/infra/providers/test_integration_prompt_contracts.py
pytest -o addopts='' -q tests/application tests/infra/providers tests/infra/adapters tests/domain tests/infra/mappers
flake8 src tests
pytest --cov=src --cov-report=term-missing --cov-fail-under=100
cd ../.. && git diff --check
```

Nenhum limiar de cobertura foi reduzido, nenhum arquivo foi excluído da medição e nenhum teste
anterior foi removido ou afrouxado.

## 2. Matriz de regressões integradas

Arquivo de testes: [`apps/backend/tests/application/usecases/test_ralph_five_fronts_integration.py`](apps/backend/tests/application/usecases/test_ralph_five_fronts_integration.py).
Fixture versionada: [`apps/backend/tests/fixtures/integration_regressions_v1.json`](apps/backend/tests/fixtures/integration_regressions_v1.json).
Componentes reais: caso de uso, nove fases, `FilePromptTemplateProvider`, `StructuredResponseParserAdapter`,
`TaskQueue`, `ResultsLedger`, `LearningsMemory`, `SessionRecorderAdapter`, repositório em memória e, quando
indicado, `CostGuardAdapter`. Falsa: só a porta do modelo (`ScriptedLLMCompletions`).

| Caso | Defeito original | Teste | O que é verificado (estado persistido, sequência e `prompt_input`) | Antes da correção |
|---|---|---|---|---|
| Recuperação de Marte | Plano de 3 tarefas com `title` ausente; corte em 1.000 caracteres | `test_marte_recuperacao_preserva_o_plano_integral_e_executa_as_tres_tarefas` | Saída recusada integral na 2ª chamada (T3 depois do caractere 1.000) + orientação de cobertura; vínculo de recuperação; temperatura 1 só na correção; 3 tarefas executadas com `depends_on` no livro; notas de A.3 em todas as fases B/C; nenhum oráculo injetado no planejamento | Passou (guarda da 01) |
| Cobertura de Marte | Razão de distâncias aceita como período | `test_cobertura_de_marte_encaminha_a_c2_completa_a_analise_e_reverifica_antes_de_c3` | A.2 recuperada com só a razão é aceita; C.1 → C.2 (motivo, Prompt Original, vigentes) → B → nova C.1 → C.3; 14 chamadas | Passou (guarda 01/03/04) |
| Colisões | T3 contraditória aprovada e misturada na síntese | `test_colisoes_revisao_aprovada_atualiza_resultados_e_memoria_vigentes_com_historico_auditado` | Livro (T3 `superseded` por T4), memória (só o fato exclusivo de T3 sai; fato com fonte independente e notas de A.3 ficam), mensagem antiga preservada, `result_revisions`, B.3, nova C.1 e C.3 só com vigentes; mapeador, sessão antiga e ZIP de exportação | Passou (guarda 05/06) |
| Tacho | Plano prescreveu a origem da energia | `test_tacho_planejamento_separa_origem_e_efeito_sem_transformar_hipotese_em_obrigacao` | Instrução origem × efeito renderizada em A.2; oráculo ausente dos prompts de planejamento; dependente recebe a conclusão pela memória, não a resolução; B.2 com regra contra antecipação do plano | Passou (guarda 02/03) |
| Microscópio | Referência trocada; linear → angular | `test_microscopio_preserva_referencias_e_grandeza_linear_com_retentativa_em_janela_nova` | Retentativa em janela nova, temperatura 1, histórico explícito; B.4 vê a tentativa rejeitada; memória, C.1 e C.3 só com o resultado linear; “da objetiva”/“da ocular” intactos | Passou (guarda 01/02/04) |
| Geografia | Reprovação literalista e assimétrica | `test_geografia_retentativa_explicita_o_vinculo_sem_trocar_a_conclusao_sustentada` | Instrução de manter a conclusão não refutada e explicitar o vínculo; mesmo padrão de conteúdo implícito em B.2 | Passou (guarda 04) |
| Probabilidade | Dupla condição justificada por opção próxima | `test_probabilidade_revisao_percorre_as_fases_e_nao_acontece_na_sintese` | Revisão por C.2 → B → C.1; C.3 uma vez, só com T3, sem `21/64` em nenhuma área | Passou (guarda 04/05/06) |
| Contagem FUVEST | Definição enfraquecida; 47 “igual” a 44 | `test_contagem_preserva_definicao_e_igualdade_falsa_vira_investigacao` | Condições idênticas em B.1/B.2/B.4/C.1/C.2/C.3; igualdade falsa como diagnóstico de C.2; C.1 distingue igualdade falsa de melhor ajuste | Passou (guarda 02/04/05) |
| Química | Mapeamento letra–teste perdido | `test_quimica_tabela_e_alternativas_chegam_a_c1_e_c3_para_pareamento_literal` | Tabela e alternativas literais em C.1 e C.3; conferência de fidelidade em C.3 | Passou (guarda 02/06) |
| Aproximação legítima | Risco de rigidez excessiva | `test_aproximacao_legitima_e_aceita_sem_c2_e_apresentada_como_melhor_ajuste` | Sem C.2; política de diferença numérica em C.1; melhor ajuste chega a C.3 | Passou (guarda 04/06) |
| Pergunta aberta | Dependência de alternativas/marcadores | `test_pergunta_aberta_preserva_siglas_nomes_unidades_e_condicoes_sem_alternativas` | Sigla, nomes semelhantes, unidade e condição em todas as fases; nenhum dado de benchmark | Passou (guarda 02/06) |
| Revisão confirmatória | Recência tratada como prova; registro omitia a confirmação | `test_revisao_confirmatoria_nao_substitui_por_recencia_e_e_registrada_para_c1`; `test_confirmacao_vencida_por_nova_evidencia_sai_do_registro_de_confirmados` | Alvo vigente com seus aprendizados; nada retirado; registro de C.1 com “confirmed by `T4`”; nova evidência pode substituí-lo depois | **Falhou** (registro dizia que nada fora revisado); o segundo teste foi escrito depois da correção |

Fluxos transversais:

| Fluxo | Teste | Antes da correção |
|---|---|---|
| Normal sem revisão | Marte, química, aproximação, pergunta aberta, tacho, microscópio, geografia | Passaram |
| Revisão aprovada | Colisões, probabilidade, contagem | Passaram |
| Revisão rejeitada até esgotar | `test_revisao_rejeitada_ate_esgotar_as_tentativas_nao_muda_estado_e_contabiliza_tudo` | Passou |
| Recuperação de contrato inválida em C.2 | `test_recuperacao_de_c2_com_referencia_invalida_corrige_a_referencia_sem_abandonar_a_investigacao` | **Falhou** (mensagem sem orientação para `review`/`depends_on`) |
| Orçamento real esgotado | `test_orcamento_real_esgotado_depois_da_revisao_aplicada_encerra_sem_sintese_e_com_auditoria` | Escrito depois; passou na primeira execução |
| Cancelamento (2 variantes) | `test_cancelamento_propaga_sem_sintese_e_sem_chamada_fora_da_contabilizacao` | Passou |

Em todos os cenários concluídos, `_c3_recebe_exatamente_a_ultima_c1` confere C.3 como última chamada,
janela de uma mensagem, resultados/critérios/memória iguais aos da última C.1 e `prompt_input`
persistido igual à conversa enviada; `_contabilizacao_integral` confere que toda chamada virou
invocação concluída e entrou nos totais.

Contratos de prompt: [`apps/backend/tests/infra/providers/test_integration_prompt_contracts.py`](apps/backend/tests/infra/providers/test_integration_prompt_contracts.py)
(30 testes). Antes das correções falharam 6: numeração do formato de C.2, `depends_on` no formato de A.2,
descrição de vigentes em C.2, confirmados no registro de C.1 e de C.2, e a regra de confirmação em C.1.
Um sétimo falhava só porque o arquivo de integração ainda não existia. Os demais — ausência de comandos
contraditórios nos nove templates e nas mensagens internas, coexistência retrabalho × revisão em C.2,
tratamento único de aproximação em B.2/C.1/C.3, síntese sem revisão, oráculos ausentes dos templates e
núcleo sem fixture, `question.options` ou `expected_answer` — passaram desde o início.

## 3. Decisões finais de contrato

| Contrato | Decisão |
|---|---|
| Registro de revisões (C.1/C.2) | Três grupos: substituídos (histórico), **confirmados por revisora vigente** (vigentes, com motivo aprovado) e aguardando revalidação. Sem revisões, `No stored result has been revised or suspended.` |
| C.1 | Recência não prova nada; resultado confirmado por revisão aprovada continua vigente; o mesmo conflito só volta com novo motivo concreto. Aproximação fundamentada aprovada; igualdade falsa reprovada. |
| C.2 | Recebe só vigentes (assim descritos); pode revisar com `review` quando há motivo concreto; não revisa de novo o confirmado sem novo motivo; exemplo de saída com `T{{next_task_number}}`. |
| A.2 | `depends_on` opcional documentado no formato de saída; sem `review`. |
| Recuperação de A.2/C.2 | Saída recusada integral na mesma janela; cobertura até a determinação final; com defeito de `review`/`depends_on`, corrigir a referência sem abandonar a investigação ou a dependência usada. |
| C.3 | Inalterado na etapa 07: recebe exatamente o que a última C.1 aprovou, sem registro de revisões; pareamento literal e apresentação, sem reconciliação. |
| Schemas, parser, limites | Inalterados. Nenhuma fase, chamada ou pós-validador novo. |
| Frontend | Inalterado; nenhuma mudança de contrato exigiu ajuste. |

Arquivos de produção alterados nesta etapa: `apps/backend/src/application/usecases/ralph_thinking_usecase.py`
(registro de confirmações), `apps/backend/src/application/phases/base_thinking_phase.py` (mensagem de
recuperação), `a2_task_decomposition.md`, `b1_task_resolution.md` (só quebra de linha),
`c1_global_verification.md` e `c2_additional_planning.md`.

## 4. TDD e correções de teste

1. Testes de integração e de contrato escritos antes de qualquer mudança de produção.
2. Primeira execução: além das falhas esperadas, dois erros dos próprios testes — comparação do texto
   descritivo da área **Key Learnings** (que difere entre C.1 e C.3) em vez da memória renderizada, e a
   suposição de `benchmark_details is None` (é um objeto com `is_banchmark=False`). Ambos corrigidos no teste.
3. Estado vermelho válido: **8 falhas, 38 aprovações**.
4. Correções mínimas nos componentes responsáveis; os 46 passaram.
5. Um teste anterior protegia a frase “its statement and the conclusion” de C.2; a redação foi ajustada
   para preservá-la, sem mudar o teste.
6. Dois testes acrescentados depois, verdes na primeira execução: confirmação vencida por nova
   evidência (cobre o ramo em que o alvo confirmado deixa de ser vigente) e orçamento real esgotado.

## 5. Estado das cinco frentes e evidência

| Frente | Estado integrado | Evidência programática | Contrato de prompt |
|---|---|---|---|
| Estrutura e recuperação | Saídas recusadas integrais; janela nova por fase; correção na própria janela; retentativa de B.1 com histórico explícito; livro de resultados vigentes; revisão só por referência aprovada; confirmações visíveis; auditoria e exportação | Marte, colisões, microscópio, recuperação de C.2, cancelamento, orçamento, revisão rejeitada | Mensagens de correção coerentes com revisão |
| Aprendizados | Notas de A.3 com associações em todas as fases B/C; B.4 com histórico; memória vigente com proveniência; fatos de A.3 e de fonte independente nunca retirados por revisão | Todos os cenários; colisões, probabilidade, confirmatória | A.3/B.4 (etapa 02) sem conflito com a revisão |
| Planejamento | Sem resposta antecipada; cobertura até a determinação final; `depends_on` declarado e transportado; C.2 com diagnóstico de C.1 | Tacho, cobertura de Marte, contagem | Formatos de saída de A.2/C.2 alinhados ao parser |
| Validação | Política única de evidência; contradição e igualdade falsa encaminhadas; aproximação fundamentada aceita; confirmação não confundida com conflito pendente | Aproximação, geografia, probabilidade, contagem, confirmatória | B.1/B.2/C.1 coerentes; nenhum “escolheu, aprovou” |
| Síntese fiel | C.3 sobre a cópia da última aprovação; sem registro de revisões, sem resultados substituídos | Auxiliar aplicado a todos os cenários concluídos | C.3 sem reconciliação; aproximação ≠ igualdade |

**Caráter generalista.** O núcleo (fases, caso de uso, fila, memória, livro) não lê `question.options`,
`expected_answer`, fixtures ou IDs de questões (teste de contrato). As perguntas dos testes são
sintéticas e incluem uma pergunta aberta sem alternativas. Os oráculos ficam na fixture e não aparecem
nos templates nem nos prompts montados pelo harness antes das saídas do modelo.

**Aproximações fundamentadas preservadas.** Os cenários de aproximação legítima e de Marte aceitam melhor
ajuste sem C.2 e sem igualdade; os textos de B.2/C.1/C.3 mantêm “a numerical difference alone is not a
defect” e “do not re-validate it with stricter standards than the approval applied”. Nenhum cenário de
aproximação foi removido.

## 6. Limitações

- Toda resposta do modelo nos testes é roteirizada; os testes provam fiação, estado e contratos.
- O parser valida estrutura e referências; não decide se uma investigação, uma aproximação ou uma
  confirmação está semanticamente correta.
- A substituição é por resultado inteiro; dependências não declaradas não são detectadas; fatos
  reformulados por outras tarefas não são retirados por semelhança.
- Cancelamento: no caso de uso, `CancelledError` ou o fechamento do gerador por desconexão do WebSocket
  propagam sem encerrar a sessão como `failed`. No benchmark, o `BenchmarkFlowRunnerAdapter` a encerra; na
  rota WebSocket ela permanece `running`. Comportamento anterior às etapas 01–07, não alterado; as
  chamadas continuam contabilizadas (a chamada em curso fica como invocação `started`).
- A exportação `benchmark-session-bench_736136f41a3d4f09bee4e50eaca509c5-ralph-loop-errors/` e o
  `RELATORIO_BENCHMARK_VESTIBULARES_736136f4.md` não são lidos pelos testes; os casos foram convertidos em
  perguntas sintéticas da fixture, com os valores de referência fornecidos no enunciado da etapa.

## 7. Avaliação semântica não executada

Nada abaixo foi medido. Não se atribui acurácia aos fakes nem se afirma “corrigiu N de N questões”.
Uma avaliação real exige autorização de custo e deve registrar versão da fixture, commit dos templates,
modelo, temperatura, saída bruta, sessão exportada e evidência textual para cada `review_check`.

1. Recuperação de Marte e cobertura: se o modelo corrige o `title` mantendo T3 e se C.1 reprova a razão
   sem período e aprova 17,76 → 18 sem C.2.
2. Colisões: se C.1 aponta a contradição sem escolher o lado e se a revisora substitui só com erro
   concreto identificado.
3. Tacho: se o planejamento deixa a origem da energia em aberto e se B.1 identifica resfriamento e
   condensação do vapor como origem e a evaporação como destino.
4. Microscópio: se o modelo mantém aumento linear e referenciais (130 mm, 60 mm, −420 mm, 25 × 7 = 175)
   sem supor imagem no infinito.
5. Geografia: se B.2 aplica o mesmo padrão de conteúdo implícito e se a retentativa mantém D.
6. Probabilidade: se B.2/C.1 reconhecem a dupla condição (42/64 × 1/2) em vez de aceitar a opção próxima.
7. Contagem: se a moda e a ordenação são preservadas (8 listas) e se C.1 deixa de escrever 47 = 44.
8. Química: se C.3 escreve a letra que rotula o teste aprovado.
9. Aproximação legítima e pergunta aberta: se não há rigidez excessiva nem perda de unidade/condição.
10. Revisão confirmatória: se C.1 deixa de reabrir um conflito já confirmado e se o modelo evita viés para
    `superseded` ou `confirmed`.
11. Custo: efeito do registro maior e das instruções acrescentadas nos tokens, na latência e na taxa de
    recusas de contrato.
