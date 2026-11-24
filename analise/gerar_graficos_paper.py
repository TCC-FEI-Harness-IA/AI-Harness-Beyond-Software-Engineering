"""Gera as figuras do paper e um documento independente, sem editar o relatório.

Dependência de visualização: matplotlib (versão usada registrada nos dados exportados).
Uso: python3 analise/gerar_graficos_paper.py
"""

from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from matplotlib.patches import Patch
import numpy as np

import reproduzir_analise as calc


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "graficos_paper"
FULL = "#355F85"
CLEAN = "#C47722"
INK = "#263441"
MUTED = "#62717F"
GRID = "#E5E9ED"
WRONG = "#8798A8"
FAIL = "#BB5945"
FIGURES = []
CHECKS = []

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.edgecolor": "#BBC4CC",
    "axes.linewidth": .65,
    "svg.fonttype": "none",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "hatch.linewidth": .55,
    "axes.unicode_minus": True,
})


def fmt(v, decimals=2, sign=False):
    return f"{v:+.{decimals}f}".replace(".", ",") if sign else f"{v:.{decimals}f}".replace(".", ",")


def title(fig, main, subtitle):
    fig.text(.035, .958, main, fontsize=13, weight="bold", va="top")
    fig.text(.035, .906, subtitle, fontsize=8.3, color=MUTED, va="top")


def foot(fig, lines):
    fig.text(.035, .037, "\n".join(lines), fontsize=7.2, color=MUTED, va="bottom", linespacing=1.55)


def clean_axes(ax):
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=.7)
    ax.tick_params(axis="both", length=0, pad=7)


def save(fig, stem, payload):
    """Exporta sem crop automático e recusa textos fora da tela."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    hidden_tick_labels = set()
    for ax in fig.axes:
        for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
            lower, upper = sorted(limits)
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if tick.get_loc() < lower or tick.get_loc() > upper:
                    hidden_tick_labels.update([tick.label1, tick.label2])
    for artist in fig.findobj():
        if isinstance(artist, matplotlib.text.Text) and artist not in hidden_tick_labels and artist.get_visible() and artist.get_text():
            bb = artist.get_window_extent(renderer)
            # Pequena tolerância para métricas de glifos na borda da tela.
            if bb.width and bb.height:
                assert bb.x0 >= bounds.x0-2 and bb.y0 >= bounds.y0-2, (stem, artist.get_text(), tuple(bb.bounds))
                assert bb.x1 <= bounds.x1+2 and bb.y1 <= bounds.y1+2, (stem, artist.get_text(), tuple(bb.bounds))
    for ext in ["png", "svg"]:
        fig.savefig(OUT / f"{stem}.{ext}", dpi=600, metadata={"Creator": "Análise dos resultados do Ralph Loop adaptado"} if ext=="svg" else None)
    CHECKS.append({"figure": stem, "text_within_canvas": True,
                   "width_inches": float(fig.get_figwidth()), "height_inches": float(fig.get_figheight()),
                   "png_dpi": 600})
    FIGURES.append({"id": stem, **payload})
    plt.close(fig)


def comparison(items, stem, main, subtitle, xlim, notes, height=5.0, separators=(), global_band=False):
    """Diferenças observadas, com duas séries explicitamente identificadas."""
    fig, ax = plt.subplots(figsize=(7.8, height))
    fig.subplots_adjust(left=.335, right=.825, bottom=.19, top=.76)
    title(fig, main, subtitle)
    n = len(items)
    ys = np.arange(n-1, -1, -1)
    if global_band:
        ax.axhspan(ys[0]-.45, ys[0]+.45, color="#F0F3F6", zorder=0)
    for y, (label, a, b) in zip(ys, items):
        for dy, s, color, marker in [(.145, a, FULL, "o"), (-.145, b, CLEAN, "^")]:
            value = s["delta_pp"]
            ax.scatter(value, y+dy, s=37, marker=marker, color=color, edgecolors="white", linewidth=.6, zorder=4)
            align = "left" if value >= 0 else "right"
            shift = 6 if value >= 0 else -6
            ax.annotate(fmt(value, sign=True) if abs(value)>1e-9 else "0,00", (value, y+dy),
                        xytext=(shift, 0), textcoords="offset points", va="center", ha=align,
                        color=color, fontsize=8.2)
        ax.text(1.045, y, f"{a['n']} / {b['n']}", transform=ax.get_yaxis_transform(), va="center", fontsize=8.2, color=MUTED)
    for after in separators:
        ax.axhline(n-after-.5, color=GRID, linewidth=.8)
    ax.set_yticks(ys, [i[0] for i in items])
    ax.set_ylim(-.55, n-.4)
    ax.set_xlim(xlim)
    ax.xaxis.set_major_locator(MultipleLocator(5 if xlim[1]-xlim[0]>20 else 2))
    ax.axvline(0, color="#606D79", linewidth=.9)
    ax.set_xlabel("Diferença de acurácia: Ralph − simples (p.p.)", labelpad=10)
    clean_axes(ax)
    ax.text(1.045, 1.09, "n total /\nsem falha", transform=ax.transAxes, color=MUTED, fontsize=7.4, va="bottom")
    handles = [Line2D([], [], marker="o", linestyle="none", color=FULL, label="Com falhas"),
               Line2D([], [], marker="^", linestyle="none", color=CLEAN, label="Sem falhas")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.325,.858), ncol=2,
               frameon=False, fontsize=8.4, columnspacing=1.7, handletextpad=.4)
    foot(fig, notes)
    save(fig, stem, {"kind": "observed_paired_accuracy_difference", "rows": [
        {"label": label, "full": a, "clean": b} for label,a,b in items]})


def failures(all_rows, logs):
    a = calc.summary(all_rows)
    cause_order = ["task_attempts", "parse_or_schema", "session_timeout", "format_final", "planning_attempts", "provider_credit"]
    cause_names = ["Cinco tentativas de tarefa", "JSON / contrato de saída", "Tempo de sessão",
                   "Resposta final inválida", "Cinco planos reprovados", "Crédito do provedor"]
    counts = [sum(l["kind"]==kind for l in logs) for kind in cause_order]
    assert counts == [16,8,3,2,1,1]
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.8, 6.15), gridspec_kw={"height_ratios":[1.08,2.2]})
    fig.subplots_adjust(left=.335, right=.90, top=.78, bottom=.19, hspace=.78)
    title(fig, "Falhas operacionais alteram o resultado de ponta a ponta", "Todos os 743 pares; os 106 resultados não corretos do Ralph têm logs disponíveis.")
    ax0.set_title("A   Resultados não corretos por fluxo", loc="left", pad=13, weight="bold")
    semantic = [len(all_rows)-a["simple_correct"]-a["simple_failure"], len(all_rows)-a["ralph_correct"]-a["ralph_failure"]]
    operational = [a["simple_failure"],a["ralph_failure"]]
    for y, valid, failed in zip([1,0],semantic,operational):
        ax0.barh(y, valid, height=.45, color=WRONG)
        ax0.barh(y, failed, left=valid, height=.45, color=FAIL, hatch="///", edgecolor="white", linewidth=.5)
        ax0.text(valid/2,y,str(valid),ha="center",va="center",fontsize=9,color="white",weight="bold")
        if failed>5:
            ax0.text(valid+failed/2,y,str(failed),ha="center",va="center",fontsize=9,color="white",weight="bold")
        else:
            ax0.annotate(str(failed), (valid+failed/2,y+.225), xytext=(0,11), textcoords="offset points",
                         ha="center",va="bottom",color=FAIL,fontsize=8.3,
                         arrowprops={"arrowstyle":"-", "color":FAIL, "linewidth":.65})
        ax0.text(valid+failed+2.4,y,str(valid+failed),va="center",weight="bold",fontsize=9)
    ax0.set_yticks([1,0],["Simples","Ralph"])
    ax0.set_xlim(0,120)
    ax0.set_ylim(-.6,1.8)
    ax0.xaxis.set_major_locator(MultipleLocator(30))
    clean_axes(ax0)
    fig.legend(handles=[Patch(facecolor=WRONG,label="Alternativa errada válida"),
                        Patch(facecolor=FAIL,hatch="///",edgecolor="white",label="Falha operacional")],
               loc="upper left",bbox_to_anchor=(.325,.883),frameon=False,ncol=2,fontsize=8.1,columnspacing=1.5)
    ax1.set_title("B   Causa terminal das 31 falhas do Ralph",loc="left",pad=15,weight="bold")
    ys = np.arange(5,-1,-1)
    ax1.barh(ys, counts, height=.56, color=FAIL)
    for y,c in zip(ys,counts):
        ax1.text(c+.3,y,f"{c}  ({fmt(c/31*100,1)}%)",va="center",fontsize=8.3)
    ax1.set_yticks(ys,cause_names)
    ax1.set_xlim(0,20)
    ax1.set_ylim(-.65,5.65)
    ax1.xaxis.set_major_locator(MultipleLocator(4))
    ax1.set_xlabel("Número de questões",labelpad=9)
    clean_axes(ax1)
    foot(fig,["O motivo terminal não identifica, sozinho, a causa de origem de cada falha.",
              "Os limites de tarefa, planejamento e tempo somam 20/31 falhas (64,5%)."])
    save(fig,"05_erros_e_causas_das_falhas",{"kind":"error_decomposition", "semantic_errors":{"simple":semantic[0],"ralph":semantic[1]},
        "operational_errors":{"simple":operational[0],"ralph":operational[1]},
        "causes":[{"code":kind,"label":label,"count":c} for kind,label,c in zip(cause_order,cause_names,counts)]})


def cost_figure(all_summary,clean_summary,clean_groups):
    fig, ax = plt.subplots(figsize=(7.8,5.5))
    fig.subplots_adjust(left=.13,right=.955,bottom=.215,top=.78)
    title(fig,"Mais computação não garante ganho de acurácia", "Pares sem falha; custo medido pela razão entre as somas de tokens.")
    items=[("GPQA Diamond",clean_groups["gpqa"],"o",(-10,9),"right"),
           ("Vestibulares",clean_groups["vestibular"],"s",(-9,-36),"right"),
           ("MMLU",clean_groups["mmlu"],"^",(9,-4),"left"),
           ("Global",clean_summary,"D",(11,10),"left")]
    for label,s,marker,offset,align in items:
        color=INK if label=="Global" else CLEAN
        lo,hi=s["paired_delta_ci_pp_approx"]
        ax.errorbar(s["token_ratio"],s["delta_pp"],yerr=[[s["delta_pp"]-lo],[hi-s["delta_pp"]]],
                    marker=marker,color=color,markersize=6,capsize=3,linewidth=1.1,
                    markeredgecolor="white",markeredgewidth=.7,zorder=3)
        ax.annotate(f"{label} · n={s['n']}\n{fmt(s['token_ratio'],1)}×; {fmt(s['delta_pp'],sign=True)} p.p.",
                    (s["token_ratio"],s["delta_pp"]),xytext=offset,textcoords="offset points",
                    va="bottom" if offset[1]>0 else "top",ha=align,fontsize=8.2,color=color)
    ax.axhline(0,color="#606D79",linewidth=.85,linestyle="--")
    ax.set_xlim(58,173)
    ax.set_ylim(-6.5,15)
    ax.set_xticks([60,80,100,120,140,160], ["60×","80×","100×","120×","140×","160×"])
    ax.set_xlabel("Tokens Ralph / tokens simples",labelpad=10)
    ax.set_ylabel("Diferença de acurácia (p.p.)",labelpad=10)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.grid(True,color=GRID,linewidth=.7)
    clean_axes(ax)
    foot(fig,["Barras verticais: IC95% aproximado da diferença pareada; não corrigido por multiplicidade.",
              "Global agrega os três conjuntos. Comparação sem controle com orçamento equivalente."])
    save(fig,"06_custo_e_ganho_de_acuracia",{"kind":"token_cost_and_accuracy", "population":"clean", "rows":[
        {"label":label,"summary":s} for label,s,*_ in items]})


def write_document():
    def links(stem):
        return f"[PNG 600 dpi](graficos_paper/{stem}.png) · [SVG vetorial](graficos_paper/{stem}.svg)"
    def embed(stem, alt):
        return f"![{alt}](graficos_paper/{stem}.png)\n\n{links(stem)}"
    chunks=["""# Figuras para os resultados e a conclusão do paper

Este documento reúne seis figuras baseadas nos mesmos CSVs e logs da análise detalhada. Ele é independente: o relatório original e os arquivos de entrada foram preservados. As figuras usam diferenças pareadas de acurácia, amostras identificadas e a mesma definição de falha da análise.

**Para uma conclusão curta:** priorize a Figura 1, que resume o ganho e sua dependência das falhas, e a Figura 5, que explica a perda operacional. A Figura 2 resume as frentes de conhecimento; a Figura 3 detalha as matérias e a Figura 4 trata de origem e nível. Use a Figura 6 quando discutir viabilidade e custo. As seis são opções de apresentação, não uma recomendação de colocar seis figuras na conclusão.

As figuras têm largura de 7,8 polegadas, adequada à largura de duas colunas após pequeno redimensionamento. Use o **SVG** para manter nitidez em qualquer escala e o **PNG a 600 dpi** quando o editor exigir imagem raster. Títulos e rótulos estão em português. A escolha de cores é acompanhada por formas de marcadores e, na Figura 5, por hachura, para facilitar a leitura em escala de cinza.

## Figura 1. Resultado global e por benchmark
""",
embed("01_resultado_global_e_benchmarks","Diferença de acurácia entre Ralph e simples no total e em cada benchmark, com e sem falhas."),
"""**Legenda sugerida para o paper.** Diferença de acurácia entre o Ralph Loop adaptado e a inferência simples no conjunto global e nos três benchmarks. Valores positivos favorecem o Ralph. O cenário completo contabiliza falhas como resultados não corretos; o cenário sem falhas exclui o par inteiro se algum fluxo apresentar erro de execução ou resposta inválida. A coluna à direita informa os tamanhos das duas amostras. O ganho global observado muda de −2,02 p.p. em 743 pares para +1,27 p.p. em 711 pares; os testes de McNemar exatos bicaudais não são conclusivos a 5% (p=0,1329 e p=0,3057, respectivamente).

**Mensagem que a figura sustenta:** o ganho condicional concentra-se no GPQA e nos vestibulares; o MMLU continua desfavorável sem falhas. Os dois cenários têm amostras diferentes, portanto a distância entre os marcadores não é uma estimativa causal isolada do efeito de corrigir as falhas.

## Figura 2. Comparação entre frentes do conhecimento
""",
embed("02_areas_do_conhecimento","Diferença de acurácia por área de conhecimento nos dois cenários de avaliação."),
"""**Legenda sugerida para o paper.** Diferenças observadas de acurácia por área, segundo o reagrupamento complementar da análise: exatas e tecnologia, biológicas e saúde, humanas e sociais e geral/interdisciplinar. As categorias são mutuamente exclusivas e cobrem os 743 pares disponíveis. Exatas e tecnologia apresenta o maior ganho sem falhas (+3,76 p.p.; +14 acertos líquidos), seguido de biológicas e saúde (+1,98 p.p.; +2); humanas e sociais apresenta perda (−3,07 p.p.; −7). Os dez pares de geral/interdisciplinar empatam em 100% nos dois fluxos.

**Mensagem que a figura sustenta:** a frente com maior melhoria comparativa é exatas; biológicas apresenta benefício menor e humanas mantém perda. Isso descreve melhoria sobre a simples, e não um ranking de acurácia final. A análise é exploratória: o p nominal de exatas sem falhas (0,0336) não resiste à correção de Holm entre as quatro áreas (p ajustado=0,1342). As regras de classificação permanecem as do relatório: psicologia em humanas, sexualidade/envelhecimento em biológicas e negócios em humanas; não são categorias oficiais novas dos benchmarks.

## Figura 3. Comparação por matéria
""",
embed("03_comparacao_por_materia","Comparação das dez matérias com pelo menos dezoito pares em cada cenário."),
"""**Legenda sugerida para o paper.** Diferença de acurácia nas dez matérias que possuem pelo menos 18 pares em ambos os cenários. São apresentadas todas as matérias elegíveis: três do GPQA e sete dos vestibulares. As 57 matérias do MMLU têm cinco pares cada na base completa e não entram neste gráfico; seu resultado agregado está na Figura 1. O critério de inclusão depende do tamanho amostral, não do sinal do resultado. Rótulos preservam o benchmark de origem para impedir a fusão silenciosa de matérias distintas.

**Mensagem que a figura sustenta:** Biologia do GPQA tem o maior ganho percentual sem falhas (+16,67 p.p. em 18 pares), e Química do GPQA tem o maior ganho líquido entre essas matérias (+5). Física dos vestibulares melhora nos dois cenários; Geografia perde nos dois. O grande ganho percentual de Biologia do GPQA equivale a três acertos líquidos em uma amostra pequena, não demonstração de superioridade em toda a Biologia. Os pontos representam estimativas observadas; não há barras de incerteza ou declaração de significância por matéria.

## Figura 4. Origem e nível das questões
""",
embed("04_origem_nivel_e_complexidade","Diferenças por prova de origem, GPQA Diamond e níveis nominais do MMLU."),
"""**Legenda sugerida para o paper.** Diferença de acurácia por origem das questões dos vestibulares, GPQA Diamond e nível nominal das matérias do MMLU. Todos os dez grupos disponíveis são exibidos. O ITA apresenta ganho de +4,76 p.p. com falhas e +10,26 p.p. sem falhas; o GPQA Diamond muda de −3,16 para +6,51 p.p. O ENEM permanece desfavorável. Os tamanhos amostrais são indicados, incluindo FUVEST (n=7), ensino fundamental MMLU (n=5) e os demais recortes pequenos.

**Mensagem que a figura sustenta:** problemas de algumas origens mais exigentes mostram ganhos promissores, mas também risco de falha. Origem e nível são indicadores aproximados; a disposição categórica não é uma escala uniforme de dificuldade. No MMLU, não há tendência monotônica com o nível. A melhora sem falhas em graduação, profissional e UNICAMP corresponde a apenas um acerto líquido em cada grupo.

## Figura 5. Erros e causas das falhas
""",
embed("05_erros_e_causas_das_falhas","Composição dos resultados não corretos e causas terminais das trinta e uma falhas do Ralph."),
"""**Legenda sugerida para o paper.** (A) Resultados não corretos nos 743 pares, separados entre alternativa válida divergente do gabarito e falha operacional. A inferência simples tem 89 alternativas erradas válidas e duas falhas (91 erros no total); o Ralph tem 75 alternativas erradas válidas e 31 falhas (106 no total). (B) Classificação terminal das 31 falhas Ralph: 16 esgotamentos de tentativas de tarefa, oito falhas de JSON/contrato, três estouros de tempo, duas respostas finais inválidas, um esgotamento de planejamento e um bloqueio de crédito do provedor. As porcentagens do painel B usam 31 como denominador.

**Mensagem que a figura sustenta:** as falhas operacionais revertem o benefício observado entre as saídas válidas. O bloqueio de crédito é apenas uma das 31 ocorrências; não há suporte para justificar todas as perdas como indisponibilidade externa. Motivo terminal não equivale a causa única: os limites podem decorrer de premissas erradas, critérios inadequados e ausência de revisão das dependências. A comparação de 89 e 75 erros válidos é descritiva: os fluxos não entregaram saídas válidas exatamente nas mesmas questões. Além das falhas, existem 26 regressões válidas do Ralph na comparação pareada.

## Figura 6. Ganho de acurácia e custo computacional
""",
embed("06_custo_e_ganho_de_acuracia","Relação entre multiplicador de tokens e diferença de acurácia, com intervalos aproximados da diferença pareada."),
"""**Legenda sugerida para o paper.** Relação entre a razão de tokens Ralph/simples e a diferença de acurácia nos pares sem falha. A razão é calculada entre as somas de tokens de cada fluxo no mesmo recorte. As barras verticais representam intervalos de 95% aproximados da média das diferenças pareadas (−1, 0, +1), sem correção por múltiplas comparações. O ponto global agrega os três benchmarks e não constitui uma quarta observação independente. Todos os intervalos exibidos incluem zero; o teste de referência do relatório é o McNemar exato.

**Mensagem que a figura sustenta:** o maior consumo não acompanha necessariamente o maior ganho: o MMLU usa 140,80 vezes os tokens e perde 2,13 p.p. No global, são 98,36 vezes os tokens para ganho observado de 1,27 p.p., cerca de 4,60 milhões de tokens adicionais por acerto líquido. Não houve comparação com outra estratégia de orçamento equivalente; a figura não demonstra efeito causal da quantidade de tokens. O eixo horizontal tem escala linear e representa um diagrama de dispersão, não barras iniciadas em zero.

## Fontes e reprodução

As quatro primeiras figuras usam os dois CSVs originais. A classificação das falhas da Figura 5 usa os três ZIPs, conciliados com os 106 resultados não corretos do Ralph. A Figura 6 usa somente o CSV sem falhas. Os gabaritos e as exclusões são os mesmos do relatório; dez questões declaradas sem pares disponíveis continuam fora da análise. Não foram simulados ganhos após correções nem criados resultados novos.

O arquivo [dados_figuras.json](graficos_paper/dados_figuras.json) registra as métricas exibidas, hashes SHA-256 das fontes, configuração de exportação e versão do Matplotlib. O script [gerar_graficos_paper.py](gerar_graficos_paper.py) pode reproduzir as figuras com Python 3 e Matplotlib:

```bash
python3 analise/gerar_graficos_paper.py
```

Definições, intervalos aproximados, classificação das áreas e limitações seguem o [relatório detalhado original](RELATORIO_DETALHADO_RESULTADOS_RALPH_LOOP.md), que permanece inalterado. As comparações por matéria, área e nível são exploratórias. Nas Figuras 1 a 4, diferenças com e sem falha são mostradas como estimativas pontuais para evitar atribuir precisão excessiva a recortes pequenos; a Figura 6 explicita a incerteza nos conjuntos maiores.
"""]
    (ROOT/"GRAFICOS_RESULTADOS_PAPER.md").write_text("\n\n".join(chunks),encoding="utf-8")


def main():
    protected = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir()
                 if p.is_file() and p.name not in {Path(__file__).name,"GRAFICOS_RESULTADOS_PAPER.md"}}
    OUT.mkdir(exist_ok=True)
    all_rows=calc.read_csv("analise-benchmark-questoes_considera-erros.csv")
    clean_rows=calc.read_csv("analise-benchmark-questoes_desconsidera-erros.csv")
    assert {r["question_id"] for r in clean_rows} == {r["question_id"] for r in all_rows if not r["simples_falha"] and not r["ralph_falha"]}
    a,b=calc.summary(all_rows),calc.summary(clean_rows)
    assert (a["n"],b["n"],a["net"],b["net"])==(743,711,-15,9)
    g={field:(calc.grouped(all_rows,field),calc.grouped(clean_rows,field))
       for field in ["benchmark","area_reagrupada","materia","nivel"]}
    items=[("Global",a,b)]+[(name,g["benchmark"][0][key],g["benchmark"][1][key])
        for key,name in [("gpqa","GPQA Diamond"),("mmlu","MMLU"),("vestibular","Vestibulares")]]
    comparison(items,"01_resultado_global_e_benchmarks","O resultado muda ao contabilizar as falhas",
        "Diferença pareada de acurácia; os dois cenários usam amostras distintas.",(-6,11),
        ["Global: com falhas, 87,75% → 85,73%; sem falhas, 88,19% → 89,45% (simples → Ralph).",
         "McNemar exato global: p=0,1329 e p=0,3057. Diferenças globais não conclusivas a 5%."],global_band=True)
    areas=["Exatas e tecnologia","Biológicas e saúde","Humanas e sociais","Geral/interdisciplinar"]
    comparison([(key,g["area_reagrupada"][0][key],g["area_reagrupada"][1][key]) for key in areas],
        "02_areas_do_conhecimento","O ganho observado é maior em exatas",
        "Reagrupamento complementar das áreas; todas as questões disponíveis estão representadas.",(-6,8),
        ["Valores positivos favorecem o Ralph; as comparações por área são exploratórias.",
         "Exatas sem falha: +14 acertos líquidos; biológicas: +2; humanas: −7. Geral: n=10, empate."])
    subject_names={"biology":"GPQA · Biologia","chemistry":"GPQA · Química","physics":"GPQA · Física",
        "FISICA":"Vest. · Física","MATEMATICA":"Vest. · Matemática","QUIMICA":"Vest. · Química",
        "BIOLOGIA":"Vest. · Biologia","GEOGRAFIA":"Vest. · Geografia","HISTORIA":"Vest. · História",
        "FILOSOFIA_SOCIOLOGIA":"Vest. · Filosofia/Sociologia"}
    eligible={k for k,s in g["materia"][0].items() if s["n"]>=18 and g["materia"][1][k]["n"]>=18}
    assert eligible==set(subject_names)
    comparison([(name,g["materia"][0][key],g["materia"][1][key]) for key,name in subject_names.items()],
        "03_comparacao_por_materia","Comparação por matéria e benchmark de origem",
        "Todas as dez matérias com pelo menos 18 pares em ambos os cenários.",(-12,24),
        ["MMLU não exibido por matéria: apenas cinco questões por disciplina na base completa.",
         "São diferenças observadas; Biologia do GPQA tem 18 pares sem falha e ganho líquido de três acertos."],
        height=7.0,separators=[3])
    levels=[("Vestibular · ENEM","Vest. · ENEM"),("Vestibular · UNICAMP","Vest. · UNICAMP"),
        ("Vestibular · FUVEST","Vest. · FUVEST"),("Vestibular · ITA","Vest. · ITA"),
        ("GPQA · Diamond","GPQA · Diamond"),("MMLU · Ensino fundamental","MMLU · Fundamental"),
        ("MMLU · Ensino médio","MMLU · Ensino médio"),("MMLU · Graduação","MMLU · Graduação"),
        ("MMLU · Profissional","MMLU · Profissional"),("MMLU · geral/especializado","MMLU · Geral/especializado")]
    comparison([(name,g["nivel"][0][key],g["nivel"][1][key]) for key,name in levels],
        "04_origem_nivel_e_complexidade","O benefício varia com a origem e o nível",
        "Todos os dez grupos disponíveis; observe os tamanhos amostrais à direita.",(-10,17),
        ["Origem e nível são aproximações de complexidade, não uma escala comum de dificuldade.",
         "Recortes pequenos são descritivos: UNICAMP, graduação e profissional ganham um acerto líquido."],
        height=7.0,separators=[5])
    logs=calc.load_logs(all_rows)
    failures(all_rows,logs)
    cost_figure(a,b,g["benchmark"][1])
    write_document()
    source_files=[p for p in protected if p.name in {"analise-benchmark-questoes_considera-erros.csv",
                 "analise-benchmark-questoes_desconsidera-erros.csv"} or p.suffix==".zip"]
    manifest={"matplotlib_version":matplotlib.__version__,"source_sha256":{p.name:protected[p] for p in source_files},
              "original_report_sha256":protected[ROOT/"RELATORIO_DETALHADO_RESULTADOS_RALPH_LOOP.md"],
              "figures":FIGURES,"export_checks":CHECKS}
    (OUT/"dados_figuras.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for path,digest in protected.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, f"Arquivo protegido alterado: {path}"
    assert len(FIGURES)==6
    print(f"Geradas {len(FIGURES)} figuras em PNG 600 dpi e SVG: {OUT}")
    print(f"Documento: {ROOT/'GRAFICOS_RESULTADOS_PAPER.md'}")
    print(f"Preservados os {len(protected)} arquivos preexistentes de dados e análise.")


if __name__=="__main__":
    main()
