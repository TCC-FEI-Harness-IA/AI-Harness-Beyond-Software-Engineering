# Análise Simples × Ralph Loop

## Execuções

- `bench_c0b581509c944a10adde91d57d80ef7f` — sem alias · GPQA Diamond · generativo · 0-shot · deepseek/deepseek-v4-flash-0731 · 198 questões
- `bench_9be03b85641c4b62bfa7cd81ebe62d03` — sem alias · MMLU · generativo · 0-shot · deepseek/deepseek-v4-flash-0731 · 285 questões
- `bench_b72b883cb604496c917119d00e55d3b3` — sem alias · Vestibulares · deepseek/deepseek-v4-flash-0731 · 270 questões

## Visão geral

- Pares analisados: **711**
- Acurácia simples: **88,2%** (IC 95% 85,6%–90,4%)
- Acurácia Ralph Loop: **89,5%** (IC 95% 87%–91,5%)
- Diferença: **+1,3 p.p.** — Ralph melhor (n.s.); McNemar exato p = 0,31
- Quando a simples erra, o Ralph acerta: **35 de 84** (41,7%)
- Quando a simples acerta, o Ralph erra: **26 de 627** (4,1%)
- Redução relativa do erro: 10,7%
- Ambos erram: 49 (41 com a mesma alternativa)
- Falhas técnicas: simples 0, Ralph 0
- Tokens: simples 424.991, Ralph 41.800.522 (98,4×); 4.597.281 tokens extras por acerto líquido

## Por execução

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPQA · 08/11/2026, 22:04 | 169 | 72,8% | 79,3% | +6,5 p.p. | 22 | 11 | +11 | 47,8% | 8,9% | 0,08 | 99,1× |
| MMLU · 08/11/2026, 21:20 | 282 | 90,1% | 87,9% | -2,1 p.p. | 8 | 14 | -6 | 28,6% | 5,5% | 0,29 | 140,8× |
| Vestibulares · 08/11/2026, 20:54 | 260 | 96,2% | 97,7% | +1,5 p.p. | 5 | 1 | +4 | 50% | 0,4% | 0,22 | 76,9× |

## Por benchmark

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPQA | 169 | 72,8% | 79,3% | +6,5 p.p. | 22 | 11 | +11 | 47,8% | 8,9% | 0,08 | 99,1× |
| MMLU | 282 | 90,1% | 87,9% | -2,1 p.p. | 8 | 14 | -6 | 28,6% | 5,5% | 0,29 | 140,8× |
| Vestibulares | 260 | 96,2% | 97,7% | +1,5 p.p. | 5 | 1 | +4 | 50% | 0,4% | 0,22 | 76,9× |

## Por matéria

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstract algebra | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 123,8× |
| anatomy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 158,2× |
| astronomy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 160,7× |
| Biologia | 28 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 84,9× |
| biology | 18 | 61,1% | 77,8% | +16,7 p.p. | 4 | 1 | +3 | 57,1% | 9,1% | 0,38 | 107× |
| business ethics | 5 | 80% | 80% | 0,0 p.p. | 1 | 1 | 0 | 100% | 25% | 1 | 191,3× |
| chemistry | 73 | 61,6% | 68,5% | +6,8 p.p. | 12 | 7 | +5 | 42,9% | 15,6% | 0,36 | 103,3× |
| clinical knowledge | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 140,9× |
| college biology | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 132,7× |
| college chemistry | 5 | 60% | 80% | +20,0 p.p. | 1 | 0 | +1 | 50% | 0% | 1 | 121,5× |
| college computer science | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 120,1× |
| college mathematics | 3 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 112,1× |
| college medicine | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 165,5× |
| college physics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 131,6× |
| computer security | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 150× |
| conceptual physics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 150,5× |
| econometrics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 127,3× |
| electrical engineering | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 168,6× |
| elementary mathematics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 161,4× |
| Filosofia e Sociologia | 30 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 82,4× |
| Física | 48 | 91,7% | 97,9% | +6,3 p.p. | 3 | 0 | +3 | 75% | 0% | 0,25 | 80× |
| formal logic | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 111,7× |
| Geografia | 29 | 100% | 96,6% | -3,4 p.p. | 0 | 1 | -1 | — | 3,4% | 1 | 85,8× |
| global facts | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 208,9× |
| high school biology | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 178,5× |
| high school chemistry | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 153,2× |
| high school computer science | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 140,9× |
| high school european history | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 80,8× |
| high school geography | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 153,7× |
| high school government and politics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 154,7× |
| high school macroeconomics | 4 | 100% | 75% | -25,0 p.p. | 0 | 1 | -1 | — | 25% | 1 | 113,8× |
| high school mathematics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 111,5× |
| high school microeconomics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 158,3× |
| high school physics | 5 | 80% | 60% | -20,0 p.p. | 0 | 1 | -1 | 0% | 25% | 1 | 121,1× |
| high school psychology | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 122,6× |
| high school statistics | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 139,6× |
| high school us history | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 89,6× |
| high school world history | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 85,9× |
| História | 30 | 93,3% | 93,3% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 76,8× |
| human aging | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 147,2× |
| human sexuality | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 181,7× |
| international law | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 153,5× |
| jurisprudence | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 152,3× |
| logical fallacies | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 156,2× |
| machine learning | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 133,6× |
| management | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 189,3× |
| marketing | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 146,1× |
| Matemática | 47 | 97,9% | 100% | +2,1 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 88,9× |
| medical genetics | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 130,2× |
| miscellaneous | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 243,3× |
| moral disputes | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 124,9× |
| moral scenarios | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 173,5× |
| nutrition | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 140,6× |
| philosophy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 139,2× |
| physics | 78 | 85,9% | 89,7% | +3,8 p.p. | 6 | 3 | +3 | 54,5% | 4,5% | 0,51 | 92× |
| prehistory | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 199,1× |
| professional accounting | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 95,2× |
| professional law | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 138,9× |
| professional medicine | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 141,9× |
| professional psychology | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 170,4× |
| public relations | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 149,4× |
| Química | 48 | 93,8% | 95,8% | +2,1 p.p. | 1 | 0 | +1 | 33,3% | 0% | 1 | 59,1× |
| security studies | 5 | 40% | 60% | +20,0 p.p. | 1 | 0 | +1 | 33,3% | 0% | 1 | 153,8× |
| sociology | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 150,4× |
| us foreign policy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 119,2× |
| virology | 5 | 20% | 20% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 207,6× |
| world religions | 5 | 60% | 60% | 0,0 p.p. | 1 | 1 | 0 | 50% | 33,3% | 1 | 174,3× |

## Por área do conhecimento

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exatas e biológicas (STEM) | 428 | 85,5% | 89,3% | +3,7 p.p. | 30 | 14 | +16 | 48,4% | 3,8% | 0,023 | 92,6× |
| Humanidades | 125 | 92% | 88% | -4,0 p.p. | 1 | 6 | -5 | 10% | 5,2% | 0,13 | 98,2× |
| Ciências sociais | 88 | 94,3% | 90,9% | -3,4 p.p. | 1 | 4 | -3 | 20% | 4,8% | 0,38 | 115,2× |
| Outras (saúde, negócios, geral) | 70 | 90% | 91,4% | +1,4 p.p. | 3 | 2 | +1 | 42,9% | 3,2% | 1 | 158,2× |

## Por nível / origem da questão

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Vestibular · ENEM | 198 | 98,5% | 98% | -0,5 p.p. | 0 | 1 | -1 | 0% | 0,5% | 1 | 84,4× |
| Vestibular · UNICAMP | 16 | 93,8% | 100% | +6,3 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 76,7× |
| Vestibular · FUVEST | 7 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 63,4× |
| Vestibular · ITA | 39 | 84,6% | 94,9% | +10,3 p.p. | 4 | 0 | +4 | 66,7% | 0% | 0,13 | 61,1× |
| MMLU · Ensino fundamental | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 161,4× |
| MMLU · Ensino médio | 69 | 95,7% | 89,9% | -5,8 p.p. | 2 | 6 | -4 | 66,7% | 9,1% | 0,29 | 121,8× |
| MMLU · Graduação | 28 | 92,9% | 96,4% | +3,6 p.p. | 1 | 0 | +1 | 50% | 0% | 1 | 128,8× |
| MMLU · Profissional | 20 | 85% | 90% | +5,0 p.p. | 1 | 0 | +1 | 33,3% | 0% | 1 | 132,5× |
| MMLU · geral/especializado | 160 | 87,5% | 85% | -2,5 p.p. | 4 | 8 | -4 | 20% | 5,7% | 0,39 | 155,4× |
| GPQA · Diamond | 169 | 72,8% | 79,3% | +6,5 p.p. | 22 | 11 | +11 | 47,8% | 8,9% | 0,08 | 99,1× |

## Por tokens da inferência simples (quartil)

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 · menor | 181 | 92,8% | 92,3% | -0,6 p.p. | 4 | 5 | -1 | 30,8% | 3% | 1 | 127,1× |
| Q2 | 177 | 91,5% | 92,1% | +0,6 p.p. | 8 | 7 | +1 | 53,3% | 4,3% | 1 | 112,5× |
| Q3 | 176 | 85,8% | 87,5% | +1,7 p.p. | 10 | 7 | +3 | 40% | 4,6% | 0,63 | 103,3× |
| Q4 · maior | 177 | 82,5% | 85,9% | +3,4 p.p. | 13 | 7 | +6 | 41,9% | 4,8% | 0,26 | 77,6× |

## Por tokens do Ralph Loop (quartil)

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 · menor | 179 | 91,1% | 93,9% | +2,8 p.p. | 8 | 3 | +5 | 50% | 1,8% | 0,23 | 74,1× |
| Q2 | 177 | 92,7% | 93,8% | +1,1 p.p. | 6 | 4 | +2 | 46,2% | 2,4% | 0,75 | 88,9× |
| Q3 | 178 | 89,9% | 89,3% | -0,6 p.p. | 6 | 7 | -1 | 33,3% | 4,4% | 1 | 100,1× |
| Q4 · maior | 177 | 79,1% | 80,8% | +1,7 p.p. | 15 | 12 | +3 | 40,5% | 8,6% | 0,7 | 118,1× |

## Questões divergentes

| Execução | Questão | Desfecho | Gabarito | Simples | Ralph |
|---|---|---|---|---|---|
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recZbxrocrxh9YENH | Ralph corrige | C | D | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recw4rROcnHKNZhtK | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_reczzzihL7btBH7RO | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recnawZPumSCLMVgp | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recZdZxsN0AxDx0pB | Ralph piora | B | B | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec9ubQihAh6g9bft | Ralph piora | D | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec527dNeEtWJrYNl | Ralph corrige | D | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recRhwQwHijW0gCLo | Ralph corrige | B | A | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_reczQ4I0VpENdMtIj | Ralph corrige | D | B | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recUBgVlkKzcRPDdK | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recrHBEJJoDTV05JR | Ralph piora | A | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recrNbtgTNoabJJi6 | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recMicVBcqy1xM1jq | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rechKl68Uc6H7vU0N | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recqFDvYKKRmbnoUb | Ralph piora | A | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recuyeuT5rQ6qDt8F | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recEmTBhx2hgw6tPQ | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rechtUKxC6G67H7Pr | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recINSFEYLCyyd08m | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recwW1A85nfyQpReG | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recvZlMbpPz0yLDle | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recA1i5ZAh0Uzclxp | Ralph piora | C | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recDDxpS9s8cwkqfq | Ralph piora | A | A | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recVE8cUNHpHZIAvL | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recyrk6XBVwugG5u8 | Ralph corrige | C | A | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec6sE2CRtD4drtHg | Ralph piora | B | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recBXlqrZUCR897It | Ralph corrige | D | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recyl3usDqb7ruXJx | Ralph piora | B | B | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recb2M22zaD3tL6Qc | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recNAiPUKOulQbKVP | Ralph corrige | A | D | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recooG6bivTUJpDBz | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_reckl6PkaEMWM50yZ | Ralph corrige | C | B | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rectXfsCM1dj4Kv2c | Ralph corrige | B | C | B |
| MMLU · 08/11/2026, 21:20 | MMLU_moral_scenarios_test_0622 | Ralph piora | C | C | D |
| MMLU · 08/11/2026, 21:20 | MMLU_college_chemistry_test_0021 | Ralph corrige | D | A | D |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_us_history_test_0000 | Ralph piora | D | D | C |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_macroeconomics_test_0213 | Ralph piora | D | D | C |
| MMLU · 08/11/2026, 21:20 | MMLU_computer_security_test_0092 | Ralph piora | B | B | A |
| MMLU · 08/11/2026, 21:20 | MMLU_medical_genetics_test_0089 | Ralph piora | C | C | D |
| MMLU · 08/11/2026, 21:20 | MMLU_public_relations_test_0081 | Ralph piora | D | D | B |
| MMLU · 08/11/2026, 21:20 | MMLU_world_religions_test_0058 | Ralph piora | D | D | B |
| MMLU · 08/11/2026, 21:20 | MMLU_business_ethics_test_0075 | Ralph piora | C | C | D |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_statistics_test_0130 | Ralph corrige | D | C | D |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_geography_test_0125 | Ralph piora | D | D | B |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_physics_test_0081 | Ralph piora | D | D | C |
| MMLU · 08/11/2026, 21:20 | MMLU_prehistory_test_0244 | Ralph piora | D | D | B |
| MMLU · 08/11/2026, 21:20 | MMLU_business_ethics_test_0040 | Ralph corrige | D | A | D |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_world_history_test_0137 | Ralph piora | A | A | B |
| MMLU · 08/11/2026, 21:20 | MMLU_jurisprudence_test_0091 | Ralph piora | C | C | B |
| MMLU · 08/11/2026, 21:20 | MMLU_clinical_knowledge_test_0220 | Ralph corrige | D | B | D |
| MMLU · 08/11/2026, 21:20 | MMLU_security_studies_test_0048 | Ralph corrige | D | A | D |
| MMLU · 08/11/2026, 21:20 | MMLU_world_religions_test_0018 | Ralph corrige | D | A | D |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_computer_science_test_0062 | Ralph corrige | B | C | B |
| MMLU · 08/11/2026, 21:20 | MMLU_professional_accounting_test_0061 | Ralph corrige | A | D | A |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_biology_test_0215 | Ralph piora | D | D | B |
| Vestibulares · 08/11/2026, 20:54 | FISICA_ITA_2024_F1_UNICA_Q004 | Ralph corrige | B | A | B |
| Vestibulares · 08/11/2026, 20:54 | FISICA_ITA_2024_F1_UNICA_Q007 | Ralph corrige | E | B | E |
| Vestibulares · 08/11/2026, 20:54 | FISICA_UNICAMP_2025_F1_QZ_Q011 | Ralph corrige | B | C | B |
| Vestibulares · 08/11/2026, 20:54 | GEOGRAFIA_ENEM_2022_AZUL_Q064 | Ralph piora | A | A | C |
| Vestibulares · 08/11/2026, 20:54 | MATEMATICA_ITA_2024_F1_UNICA_Q038 | Ralph corrige | E | C | E |
| Vestibulares · 08/11/2026, 20:54 | QUIMICA_ITA_2024_F1_UNICA_Q054 | Ralph corrige | A | E | A |
