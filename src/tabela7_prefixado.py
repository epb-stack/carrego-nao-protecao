"""
Passo 2 — o prefixado de 5 anos como terceiro portfólio da Tabela 7.

A Tabela 7 do paper (Marinho, Ribeiro e Wichmann, 2026) compara, em 23 janelas de 5 anos,
uma NTN-B casada ao passivo (a "faculdade" corrigida pelo IPCA) com um portfólio em CDI.
Falta o único comparador que testa PROTEÇÃO contra inflação: o prefixado de mesmo prazo.

  NTN-B − CDI        mede prazo (carrego)            → passo 1 (decompoe_carrego.py)
  Prefixado − NTN-B  mede indexador (proteção)       → este script

Para cada janela:
  - entrada e aporte iguais aos da NTN-B (Tabela 7);
  - título: Tesouro Prefixado (LTN) ou Prefixado com Juros Semestrais (NTN-F) com vencimento
    mais próximo do resgate, cotado nos 15 primeiros dias do mês de entrada (Taxa Compra Manhã,
    a taxa que o investidor recebe ao comprar);
  - valor final nominal = aporte × (1 + taxa)^5 (bruto, como a Tabela 7; cupons da NTN-F
    reinvestidos à própria taxa);
  - alvo = R$ 500 mil de jan/2010 corrigidos pelo IPCA até o resgate (a faculdade).

Inflação implícita na entrada = (1 + taxa prefixada) / (1 + yield real da NTN-B) − 1.
Proteção realizada = inflação realizada − inflação implícita: positiva quando a NTN-B venceu
o prefixado (a inflação surpreendeu para cima), negativa quando o prefixado venceu.

Dados: data/cache/tesouro_direto_prefixados_entradas.csv (recorte do histórico do Tesouro
Direto, Tesouro Transparente, só prefixados nos 15 primeiros dias de cada entrada) e
data/cache/sgs_433_ipca.csv. Saída: outputs/tabela7_prefixado.csv e .png.
"""
import os, math
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "data", "cache")
OUT = os.path.join(HERE, "..", "outputs")
os.makedirs(OUT, exist_ok=True)

BASE = 500_000.0
H = 5
TAB7 = [
 ("2010-01","2015-01", 361216.06,  675973.26,  574335.01),
 ("2010-07","2015-07", 370476.53,  713291.97,  598309.47),
 ("2011-01","2016-01", 396074.86,  748344.94,  649787.07),
 ("2011-07","2016-07", 397573.27,  775607.17,  659618.70),
 ("2012-01","2017-01", 433654.85,  788410.99,  726745.02),
 ("2012-07","2017-07", 469363.00,  796637.43,  794490.41),
 ("2013-01","2018-01", 521308.92,  810920.50,  885868.60),
 ("2013-07","2018-07", 482797.31,  832364.10,  818339.17),
 ("2014-01","2019-01", 471251.31,  841545.04,  788530.86),
 ("2014-07","2019-07", 492986.39,  859184.34,  809944.00),
 ("2015-01","2020-01", 499446.77,  876819.83,  798989.96),
 ("2015-07","2020-07", 517452.26,  878992.42,  795090.79),
 ("2016-01","2021-01", 526632.92,  916794.58,  764358.91),
 ("2016-07","2021-07", 568453.55,  958054.68,  783049.92),
 ("2017-01","2022-01", 588860.51, 1011952.68,  783114.45),
 ("2017-07","2022-07", 604657.16, 1054523.45,  802591.25),
 ("2018-01","2023-01", 639644.33, 1070386.07,  870080.68),
 ("2018-07","2023-07", 631631.93, 1096624.71,  886887.22),
 ("2019-01","2024-01", 677786.54, 1118624.49,  979247.35),
 ("2019-07","2024-07", 734963.64, 1145953.58, 1083877.25),
 ("2020-01","2025-01", 775588.26, 1169632.36, 1172646.72),
 ("2020-07","2025-07", 789268.13, 1205832.20, 1248267.02),
 ("2021-01","2026-01", 827692.83, 1221579.84, 1392554.14),
]

# ---- IPCA (cache do passo 1) ----
ipca = pd.read_csv(os.path.join(CACHE, "sgs_433_ipca.csv"))
ipca["ym"] = pd.PeriodIndex(ipca["ym"], freq="M")
ipca = ipca.set_index("ym")["valor"].astype(float)

def fator(serie, ym_ini, ym_fim):
    s = serie[(serie.index >= pd.Period(ym_ini, "M")) & (serie.index < pd.Period(ym_fim, "M"))]
    return float((1 + s/100).prod())

# ---- Tesouro Direto: prefixados nos 15 primeiros dias de cada entrada ----
td = pd.read_csv(os.path.join(CACHE, "tesouro_direto_prefixados_entradas.csv"), sep=";", decimal=",")
td["Data Base"] = pd.to_datetime(td["Data Base"], dayfirst=True)
td["Data Vencimento"] = pd.to_datetime(td["Data Vencimento"], dayfirst=True)
td = td[td["Taxa Compra Manha"] > 0]   # linhas sem oferta de compra têm taxa 0

rows = []
for ini, fim, aporte, facul_paper, cdi_paper in TAB7:
    d_ent = pd.Timestamp(ini + "-01"); d_alvo = pd.Timestamp(fim + "-01")
    cand = td[(td["Data Base"] >= d_ent) & (td["Data Base"] <= d_ent + pd.Timedelta(days=15))].copy()
    cand["dist"] = (cand["Data Vencimento"] - d_alvo).abs()
    # vencimento mais próximo do resgate; entre iguais, a cotação mais antiga
    best = cand.sort_values(["dist", "Data Base"]).iloc[0]
    tx = best["Taxa Compra Manha"] / 100
    I_ini = fator(ipca, "2009-12", ini); I_fim = fator(ipca, "2009-12", fim); I_win = I_fim / I_ini
    r_ntnb = (BASE * I_ini / aporte) ** (1/H) - 1
    alvo = BASE * I_fim
    final_pre = aporte * (1 + tx) ** H
    infl_impl = (1 + tx) / (1 + r_ntnb) - 1
    infl_real = I_win ** (1/H) - 1
    rows.append(dict(
        inicio=ini, resgate=fim, titulo=best["Tipo Titulo"], vencimento=best["Data Vencimento"].date(),
        cotacao=best["Data Base"].date(), desvio_venc_meses=round(best["dist"].days/30.4, 1),
        taxa_prefixada=tx*100, yield_real_ntnb=r_ntnb*100,
        inflacao_implicita=infl_impl*100, inflacao_realizada=infl_real*100,
        protecao_realizada=(infl_real-infl_impl)*100,
        aporte=aporte, alvo=alvo, final_prefixado=final_pre, final_cdi=cdi_paper,
        gap_prefixado_pct=(final_pre/alvo-1)*100, gap_cdi_pct=(cdi_paper/alvo-1)*100,
        retorno_real_prefixado=((1+tx)**H/I_win)**(1/H)*100-100,
    ))
p2 = pd.DataFrame(rows)
p2.to_csv(os.path.join(OUT, "tabela7_prefixado.csv"), index=False)

pd.set_option("display.width", 220)
print("=== Tabela 7 com o prefixado de 5 anos (bruto, como no paper) ===")
print(p2[["inicio","titulo","vencimento","desvio_venc_meses","taxa_prefixada","yield_real_ntnb",
          "inflacao_implicita","inflacao_realizada","protecao_realizada","gap_prefixado_pct","gap_cdi_pct"]]
      .round(2).to_string(index=False))
n = len(p2)
print(f"""
Médias ({n} janelas):
  inflação implícita na entrada   = {p2.inflacao_implicita.mean():.2f}% a.a.
  inflação realizada              = {p2.inflacao_realizada.mean():.2f}% a.a.
  proteção realizada (real − impl)= {p2.protecao_realizada.mean():+.2f} pp/ano  (positiva em {(p2.protecao_realizada>0).sum()} de {n})
  gap do prefixado vs alvo        = {p2.gap_prefixado_pct.mean():+.1f}%  (acima do alvo em {(p2.gap_prefixado_pct>0).sum()} de {n}; pior {p2.gap_prefixado_pct.min():+.1f}%, melhor {p2.gap_prefixado_pct.max():+.1f}%)
  gap do CDI vs alvo              = {p2.gap_cdi_pct.mean():+.1f}%  (acima do alvo em {(p2.gap_cdi_pct>0).sum()} de {n})
  gap da NTN-B vs alvo            = 0 por construção

Leitura: proteção realizada > 0 = a inflação veio ACIMA da implícita e a NTN-B venceu o prefixado;
< 0 = o prefixado venceu. Média perto de zero = o seguro contra inflação foi precificado justo.
""")

# ---- gráfico ----
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 5.5))
    x = range(n); w = 0.4
    ax.bar([i-w/2 for i in x], p2.inflacao_implicita, w, color="#D99A3B", label="inflação implícita na entrada (prefixado vs NTN-B)")
    ax.bar([i+w/2 for i in x], p2.inflacao_realizada, w, color="#6B1E2C", label="inflação realizada nos 5 anos (IPCA)")
    ax.plot(list(x), p2.protecao_realizada, "o-", color="#123329", lw=2, label="proteção realizada = realizada − implícita")
    ax.axhline(0, color="#231F1A", lw=1)
    ax.set_xticks(list(x)); ax.set_xticklabels([i.replace("-","/") for i in p2.inicio], rotation=45, ha="right")
    ax.set_ylabel("% ao ano"); ax.set_title("Prefixado vs NTN-B de 5 anos: inflação implícita, realizada e proteção, por janela de entrada")
    ax.legend(frameon=False, fontsize=9); ax.spines[["top","right"]].set_visible(False)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "tabela7_prefixado.png"), dpi=160)
    print("Gráfico salvo em outputs/tabela7_prefixado.png")
except Exception as e:
    print("matplotlib indisponível; gráfico não gerado:", e)
