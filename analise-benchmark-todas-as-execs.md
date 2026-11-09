# Análise Simples × Ralph Loop

## Execuções

- `bench_c0b581509c944a10adde91d57d80ef7f` — sem alias · GPQA Diamond · generativo · 0-shot · deepseek/deepseek-v4-flash-0731 · 198 questões
- `bench_9be03b85641c4b62bfa7cd81ebe62d03` — sem alias · MMLU · generativo · 0-shot · deepseek/deepseek-v4-flash-0731 · 285 questões
- `bench_b72b883cb604496c917119d00e55d3b3` — sem alias · Vestibulares · deepseek/deepseek-v4-flash-0731 · 270 questões

## Visão geral

- Pares analisados: **743**
- Acurácia simples: **87,8%** (IC 95% 85,2%–89,9%)
- Acurácia Ralph Loop: **85,7%** (IC 95% 83%–88,1%)
- Diferença: **-2,0 p.p.** — Ralph pior (n.s.); McNemar exato p = 0,13
- Quando a simples erra, o Ralph acerta: **36 de 91** (39,6%)
- Quando a simples acerta, o Ralph erra: **51 de 652** (7,8%)
- Redução relativa do erro: -16,5%
- Ambos erram: 55 (42 com a mesma alternativa)
- Falhas técnicas: simples 2, Ralph 31
- Tokens: simples 651.365, Ralph 45.653.918 (70,1×)

## Por execução

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPQA · 08/11/2026, 22:04 | 190 | 73,7% | 70,5% | -3,2 p.p. | 22 | 28 | -6 | 44% | 20% | 0,48 | 48,5× |
| MMLU · 08/11/2026, 21:20 | 285 | 89,8% | 87% | -2,8 p.p. | 8 | 16 | -8 | 27,6% | 6,3% | 0,15 | 137,1× |
| Vestibulares · 08/11/2026, 20:54 | 268 | 95,5% | 95,1% | -0,4 p.p. | 6 | 7 | -1 | 50% | 2,7% | 1 | 77,1× |

## Por benchmark

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPQA | 190 | 73,7% | 70,5% | -3,2 p.p. | 22 | 28 | -6 | 44% | 20% | 0,48 | 48,5× |
| MMLU | 285 | 89,8% | 87% | -2,8 p.p. | 8 | 16 | -8 | 27,6% | 6,3% | 0,15 | 137,1× |
| Vestibulares | 268 | 95,5% | 95,1% | -0,4 p.p. | 6 | 7 | -1 | 50% | 2,7% | 1 | 77,1× |

## Por matéria

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstract algebra | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 123,8× |
| anatomy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 158,2× |
| astronomy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 160,7× |
| Biologia | 30 | 100% | 93,3% | -6,7 p.p. | 0 | 2 | -2 | — | 6,7% | 0,5 | 83,1× |
| biology | 19 | 57,9% | 73,7% | +15,8 p.p. | 4 | 1 | +3 | 50% | 9,1% | 0,38 | 8,6× |
| business ethics | 5 | 80% | 80% | 0,0 p.p. | 1 | 1 | 0 | 100% | 25% | 1 | 191,3× |
| chemistry | 85 | 63,5% | 58,8% | -4,7 p.p. | 12 | 16 | -4 | 38,7% | 29,6% | 0,57 | 111,7× |
| clinical knowledge | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 140,9× |
| college biology | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 132,7× |
| college chemistry | 5 | 60% | 80% | +20,0 p.p. | 1 | 0 | +1 | 50% | 0% | 1 | 121,5× |
| college computer science | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 120,1× |
| college mathematics | 5 | 100% | 60% | -40,0 p.p. | 0 | 2 | -2 | — | 40% | 0,5 | 43,8× |
| college medicine | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 165,5× |
| college physics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 131,6× |
| computer security | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 150× |
| conceptual physics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 150,5× |
| econometrics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 127,3× |
| electrical engineering | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 168,6× |
| elementary mathematics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 161,4× |
| Filosofia e Sociologia | 30 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 82,4× |
| Física | 49 | 89,8% | 98% | +8,2 p.p. | 4 | 0 | +4 | 80% | 0% | 0,13 | 79,1× |
| formal logic | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 111,7× |
| Geografia | 30 | 100% | 93,3% | -6,7 p.p. | 0 | 2 | -2 | — | 6,7% | 0,5 | 88,1× |
| global facts | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 208,9× |
| high school biology | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 178,5× |
| high school chemistry | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 153,2× |
| high school computer science | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 140,9× |
| high school european history | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 80,8× |
| high school geography | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 153,7× |
| high school government and politics | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 154,7× |
| high school macroeconomics | 5 | 80% | 60% | -20,0 p.p. | 0 | 1 | -1 | 0% | 25% | 1 | 133,2× |
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
| Matemática | 49 | 98% | 95,9% | -2,0 p.p. | 1 | 2 | -1 | 100% | 4,2% | 1 | 89,9× |
| medical genetics | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 130,2× |
| miscellaneous | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 243,3× |
| moral disputes | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 124,9× |
| moral scenarios | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 173,5× |
| nutrition | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 140,6× |
| philosophy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 139,2× |
| physics | 86 | 87,2% | 81,4% | -5,8 p.p. | 6 | 11 | -5 | 54,5% | 14,7% | 0,33 | 91,2× |
| prehistory | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 199,1× |
| professional accounting | 5 | 80% | 100% | +20,0 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 95,2× |
| professional law | 5 | 60% | 60% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 138,9× |
| professional medicine | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 141,9× |
| professional psychology | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 170,4× |
| public relations | 5 | 100% | 80% | -20,0 p.p. | 0 | 1 | -1 | — | 20% | 1 | 149,4× |
| Química | 50 | 92% | 92% | 0,0 p.p. | 1 | 1 | 0 | 25% | 2,2% | 1 | 59,9× |
| security studies | 5 | 40% | 60% | +20,0 p.p. | 1 | 0 | +1 | 33,3% | 0% | 1 | 153,8× |
| sociology | 5 | 80% | 80% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 150,4× |
| us foreign policy | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 119,2× |
| virology | 5 | 20% | 20% | 0,0 p.p. | 0 | 0 | 0 | 0% | 0% | 1 | 207,6× |
| world religions | 5 | 60% | 60% | 0,0 p.p. | 1 | 1 | 0 | 50% | 33,3% | 1 | 174,3× |

## Por área do conhecimento

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Exatas e biológicas (STEM) | 458 | 85,2% | 83,6% | -1,5 p.p. | 31 | 38 | -7 | 45,6% | 9,7% | 0,47 | 60,4× |
| Humanidades | 125 | 92% | 88% | -4,0 p.p. | 1 | 6 | -5 | 10% | 5,2% | 0,13 | 98,2× |
| Ciências sociais | 90 | 93,3% | 88,9% | -4,4 p.p. | 1 | 5 | -4 | 16,7% | 6% | 0,22 | 116,6× |
| Outras (saúde, negócios, geral) | 70 | 90% | 91,4% | +1,4 p.p. | 3 | 2 | +1 | 42,9% | 3,2% | 1 | 158,2× |

## Por nível / origem da questão

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Vestibular · ENEM | 203 | 98% | 96,1% | -2,0 p.p. | 1 | 5 | -4 | 25% | 2,5% | 0,22 | 84,3× |
| Vestibular · UNICAMP | 16 | 93,8% | 100% | +6,3 p.p. | 1 | 0 | +1 | 100% | 0% | 1 | 76,7× |
| Vestibular · FUVEST | 7 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 63,4× |
| Vestibular · ITA | 42 | 83,3% | 88,1% | +4,8 p.p. | 4 | 2 | +2 | 57,1% | 5,7% | 0,69 | 62,8× |
| MMLU · Ensino fundamental | 5 | 100% | 100% | 0,0 p.p. | 0 | 0 | 0 | — | 0% | 1 | 161,4× |
| MMLU · Ensino médio | 70 | 94,3% | 88,6% | -5,7 p.p. | 2 | 6 | -4 | 50% | 9,1% | 0,29 | 122,9× |
| MMLU · Graduação | 30 | 93,3% | 90% | -3,3 p.p. | 1 | 2 | -1 | 50% | 7,1% | 1 | 103,3× |
| MMLU · Profissional | 20 | 85% | 90% | +5,0 p.p. | 1 | 0 | +1 | 33,3% | 0% | 1 | 132,5× |
| MMLU · geral/especializado | 160 | 87,5% | 85% | -2,5 p.p. | 4 | 8 | -4 | 20% | 5,7% | 0,39 | 155,4× |
| GPQA · Diamond | 190 | 73,7% | 70,5% | -3,2 p.p. | 22 | 28 | -6 | 44% | 20% | 0,48 | 48,5× |

## Por tokens da inferência simples (quartil)

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 · menor | 188 | 92% | 91% | -1,1 p.p. | 5 | 7 | -2 | 33,3% | 4% | 0,77 | 126,7× |
| Q2 | 184 | 92,4% | 89,1% | -3,3 p.p. | 7 | 13 | -6 | 50% | 7,6% | 0,26 | 113,5× |
| Q3 | 186 | 85,5% | 84,4% | -1,1 p.p. | 10 | 12 | -2 | 37% | 7,5% | 0,83 | 106× |
| Q4 · maior | 185 | 81,1% | 78,4% | -2,7 p.p. | 14 | 19 | -5 | 40% | 12,7% | 0,49 | 39,4× |

## Por tokens do Ralph Loop (quartil)

| Grupo | n | Acurácia simples | Acurácia Ralph | Δ | Ralph corrige | Ralph piora | Líquido | Recuperação | Regressão | p (McNemar) | Tokens Ralph/simples |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 · menor | 187 | 90,9% | 89,8% | -1,1 p.p. | 8 | 10 | -2 | 47,1% | 5,9% | 0,81 | 71,4× |
| Q2 | 185 | 93% | 94,1% | +1,1 p.p. | 6 | 4 | +2 | 46,2% | 2,3% | 0,75 | 89,2× |
| Q3 | 187 | 87,7% | 87,2% | -0,5 p.p. | 10 | 11 | -1 | 43,5% | 6,7% | 1 | 102× |
| Q4 · maior | 184 | 79,3% | 71,7% | -7,6 p.p. | 12 | 26 | -14 | 31,6% | 17,8% | 0,034 | 53,5× |

## Questões divergentes

| Execução | Questão | Desfecho | Gabarito | Simples | Ralph |
|---|---|---|---|---|---|
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recZbxrocrxh9YENH | Ralph corrige | C | D | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recgM7o1tcc7tP778 | Ralph piora | D | D | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recIj8lR4tuDgrHou | Ralph piora | D | D | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recPSTGXK3P39yNYT | Ralph piora | D | D | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recw4rROcnHKNZhtK | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_reczzzihL7btBH7RO | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recnawZPumSCLMVgp | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recZdZxsN0AxDx0pB | Ralph piora | B | B | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec9ubQihAh6g9bft | Ralph piora | D | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec527dNeEtWJrYNl | Ralph corrige | D | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recRhwQwHijW0gCLo | Ralph corrige | B | A | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_reczQ4I0VpENdMtIj | Ralph corrige | D | B | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recZ13cwgDQf9jRd9 | Ralph piora | B | B | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recUBgVlkKzcRPDdK | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recJZ3QEfRKjYw9a7 | Ralph piora | A | A | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recrHBEJJoDTV05JR | Ralph piora | A | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recrNbtgTNoabJJi6 | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recMicVBcqy1xM1jq | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rechKl68Uc6H7vU0N | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recINGR1z01Fh1Z3A | Ralph piora | D | D | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recPzW1WqRnPs57D6 | Ralph piora | B | B | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recqFDvYKKRmbnoUb | Ralph piora | A | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recuyeuT5rQ6qDt8F | Ralph corrige | D | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recqGD3fxPCI59vPQ | Ralph piora | C | C | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recLAgwx9vbgB5EHk | Ralph piora | A | A | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recEmTBhx2hgw6tPQ | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rechtUKxC6G67H7Pr | Ralph piora | C | C | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recdya6FuYraBU5Rh | Ralph piora | A | A | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec2fsnzUuvNtUYK8 | Ralph piora | A | A | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recINSFEYLCyyd08m | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recwW1A85nfyQpReG | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recvZlMbpPz0yLDle | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recA1i5ZAh0Uzclxp | Ralph piora | C | C | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recDDxpS9s8cwkqfq | Ralph piora | A | A | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recVE8cUNHpHZIAvL | Ralph corrige | B | D | B |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recyrk6XBVwugG5u8 | Ralph corrige | C | A | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recO3hvCWRGiG0odN | Ralph piora | C | C | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recYCMJWH7IpcdqwE | Ralph piora | C | C | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec9W28HgpEUeUN8k | Ralph piora | C | C | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recBGxVySx1pkrO1i | Ralph piora | B | B | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_rec6sE2CRtD4drtHg | Ralph piora | B | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recBXlqrZUCR897It | Ralph corrige | D | A | D |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recyl3usDqb7ruXJx | Ralph piora | B | B | C |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recXsYa3i2UhGF5fe | Ralph piora | A | A | — |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recb2M22zaD3tL6Qc | Ralph corrige | A | B | A |
| GPQA · 08/11/2026, 22:04 | GPQA_diamond_recGee5m84dg5FZkc | Ralph piora | C | C | — |
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
| MMLU · 08/11/2026, 21:20 | MMLU_college_mathematics_test_0098 | Ralph piora | D | D | — |
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
| MMLU · 08/11/2026, 21:20 | MMLU_college_mathematics_test_0093 | Ralph piora | B | B | — |
| MMLU · 08/11/2026, 21:20 | MMLU_professional_accounting_test_0061 | Ralph corrige | A | D | A |
| MMLU · 08/11/2026, 21:20 | MMLU_high_school_biology_test_0215 | Ralph piora | D | D | B |
| Vestibulares · 08/11/2026, 20:54 | BIOLOGIA_ENEM_2022_AZUL_Q133 | Ralph piora | D | D | — |
| Vestibulares · 08/11/2026, 20:54 | BIOLOGIA_ENEM_2024_AZUL_Q105 | Ralph piora | D | D | — |
| Vestibulares · 08/11/2026, 20:54 | FISICA_ENEM_2020_AZUL_Q114 | Ralph corrige | C | — | C |
| Vestibulares · 08/11/2026, 20:54 | FISICA_ITA_2024_F1_UNICA_Q004 | Ralph corrige | B | A | B |
| Vestibulares · 08/11/2026, 20:54 | FISICA_ITA_2024_F1_UNICA_Q007 | Ralph corrige | E | B | E |
| Vestibulares · 08/11/2026, 20:54 | FISICA_UNICAMP_2025_F1_QZ_Q011 | Ralph corrige | B | C | B |
| Vestibulares · 08/11/2026, 20:54 | GEOGRAFIA_ENEM_2022_AZUL_Q064 | Ralph piora | A | A | C |
| Vestibulares · 08/11/2026, 20:54 | GEOGRAFIA_ENEM_2024_AZUL_Q071 | Ralph piora | D | D | — |
| Vestibulares · 08/11/2026, 20:54 | MATEMATICA_ENEM_2023_AZUL_Q138 | Ralph piora | C | C | — |
| Vestibulares · 08/11/2026, 20:54 | MATEMATICA_ITA_2024_F1_UNICA_Q038 | Ralph corrige | E | C | E |
| Vestibulares · 08/11/2026, 20:54 | MATEMATICA_ITA_2024_F1_UNICA_Q043 | Ralph piora | E | E | — |
| Vestibulares · 08/11/2026, 20:54 | QUIMICA_ITA_2024_F1_UNICA_Q054 | Ralph corrige | A | E | A |
| Vestibulares · 08/11/2026, 20:54 | QUIMICA_ITA_2025_F1_UNICA_Q035 | Ralph piora | E | E | — |
