#!/usr/bin/env python3
"""
Decomposição do carrego real da NTN-B em prêmio ex-ante e erro de expectativa
=============================================================================
Extensão do paper "Repensando o ativo sem risco: uma visão brasileira"
(Marinho, Ribeiro e Wichmann, jun/2026) — passo 1 da nota "Carrego, não proteção".

O que o script faz
------------------
1. Reconstrói, a partir da Tabela 7 do paper (transcrita abaixo), a taxa real
   travada na NTN-B de ~5 anos em cada data de entrada.
2. Baixa do Banco Central (API SGS) o IPCA e o CDI mensais e recalcula, para
   cada janela de 5 anos, a Selic real média REALIZADA. Valida contra a Tabela 7.
3. Baixa do Banco Central (API Olinda / Focus) as expectativas de Selic e IPCA
   por ano-calendário vigentes em cada data de entrada e constrói a Selic real
   média ESPERADA para os 5 anos seguintes.
4. Decompõe:   carrego realizado = (yield real − Selic real esperada)   [prêmio ex-ante]
                                 + (Selic real esperada − Selic real realizada) [erro de expectativa]
5. Salva CSV + gráfico PNG e imprime o resumo.

Como rodar (Mac)
----------------
    python3 -m venv .venv && source .venv/bin/activate
    pip install pandas requests matplotlib
    python3 decompoe_carrego.py

Saídas: decomposicao_carrego.csv, decomposicao_carrego.png, validacao_tabela7.csv

Hipóteses declaradas
--------------------
- A expectativa Focus de Selic é para o FIM de cada ano; usamos como proxy da
  média do ano. O Focus cobre até 4 anos à frente; o 5º ano repete o 4º.
- Expectativa real de cada ano = (1+Selic_esp)/(1+IPCA_esp) − 1; média geométrica
  dos 5 anos.
- Usamos a mediana do Focus na primeira data disponível a partir do 1º dia útil
  do mês de entrada (jan ou jul).
- Taxa real da NTN-B extraída da Tabela 7: aporte = 500.000 × IPCA_acum(jan/10→entrada) / (1+r)^5.
  O IPCA acumulado até a entrada vem do próprio SGS (por isso todas as 23 janelas entram).
"""
import io, sys, json, math
from datetime import date, timedelta
import pandas as pd
import requests

# --------------------------------------------------------------------------
# Tabela 7 do paper (transcrição): início, resgate, aporte, faculdade corrigida, CDI
# --------------------------------------------------------------------------
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
BASE = 500_000.0
H = 5  # anos

# --------------------------------------------------------------------------
# 1. SGS: IPCA (433) e CDI mensal (4391)
# --------------------------------------------------------------------------
import os
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cache")
os.makedirs(CACHE, exist_ok=True)

def sgs(codigo, nome, ini="01/12/2009", fim="31/01/2026"):
    """Série mensal do SGS. Usa data/cache/sgs_<codigo>_<nome>.csv se existir; senão baixa e salva."""
    fcache = os.path.join(CACHE, f"sgs_{codigo}_{nome}.csv")
    if os.path.exists(fcache):
        df = pd.read_csv(fcache)
        df["ym"] = pd.PeriodIndex(df["ym"], freq="M")
        return df.set_index("ym")["valor"].astype(float)
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    r = requests.get(url, params={"formato":"json","dataInicial":ini,"dataFinal":fim}, timeout=60)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
    df["ym"] = df["data"].dt.to_period("M")
    df[["ym","valor"]].to_csv(fcache, index=False)
    return df.set_index("ym")["valor"]

print("Carregando IPCA e CDI (cache local ou SGS)...")
ipca = sgs(433, "ipca")  # variação % mensal
cdi  = sgs(4391, "cdi")  # CDI acumulado no mês, %

def fator(serie, ym_ini, ym_fim):
    """Produto de (1+x/100) de ym_ini (inclusive) a ym_fim (exclusive) — meses do período."""
    s = serie[(serie.index >= pd.Period(ym_ini, "M")) & (serie.index < pd.Period(ym_fim, "M"))]
    return float((1 + s/100).prod()), len(s)

# --------------------------------------------------------------------------
# 2. Reconstrução e validação contra a Tabela 7
# --------------------------------------------------------------------------
rows = []
for ini, fim, aporte, facul, cdi_fin in TAB7:
    # IPCA acumulado de jan/2010 até a entrada e até o resgate
    # (a Tabela 7 corrige R$500 mil de jan/2010; usamos IPCA de dez/2009 em diante)
    I_ini, _ = fator(ipca, "2009-12", ini)      # dez/09 → mês anterior à entrada
    I_fim, _ = fator(ipca, "2009-12", fim)
    I_win = I_fim / I_ini
    C_win, n = fator(cdi, ini, fim)              # CDI acumulado na janela
    r_ntnb = (BASE * I_ini / aporte) ** (1/H) - 1          # taxa real travada
    cdi_real = (C_win / I_win) ** (1/H) - 1                # Selic real média realizada
    rows.append(dict(inicio=ini, resgate=fim, aporte=aporte,
                     faculdade_paper=facul, faculdade_recalc=BASE*I_fim,
                     cdi_paper=cdi_fin, cdi_recalc=aporte*C_win,
                     yield_real_ntnb=r_ntnb*100, selic_real_realizada=cdi_real*100,
                     carrego_realizado=(r_ntnb-cdi_real)*100, meses=n))
val = pd.DataFrame(rows)
val["erro_faculdade_%"] = (val.faculdade_recalc/val.faculdade_paper-1)*100
val["erro_cdi_%"]       = (val.cdi_recalc/val.cdi_paper-1)*100
val.to_csv("validacao_tabela7.csv", index=False)
print("\nValidação contra a Tabela 7 (erro % na faculdade corrigida e no portfólio CDI):")
print(val[["inicio","erro_faculdade_%","erro_cdi_%"]].round(2).to_string(index=False))
print("Se os erros forem < 1%, a reconstrução bate com o paper (diferenças = dia exato de entrada).")

# --------------------------------------------------------------------------
# 3. Focus (Olinda): expectativas anuais de Selic e IPCA vigentes na entrada
# --------------------------------------------------------------------------
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"

FOCUS_CACHE = os.path.join(CACHE, "focus_anuais_entradas.csv")

def focus_anual(indicador, data_ini, data_fim):
    """Expectativas anuais do Focus. Usa data/cache/focus_anuais_entradas.csv se existir
    (medianas de Selic e IPCA nos 15 primeiros dias de cada mês de entrada da Tabela 7);
    senão baixa da API Olinda, por janela de entrada, e salva o cache."""
    if os.path.exists(FOCUS_CACHE):
        df = pd.read_csv(FOCUS_CACHE)
    else:
        parts = []
        for ini, *_ in TAB7:
            flt = (f"(Indicador eq 'Selic' or Indicador eq 'IPCA') and "
                   f"Data ge '{ini}-01' and Data le '{ini}-15'")
            params = {"$filter": flt, "$format": "json", "$top": "5000",
                      "$select": "Indicador,Data,DataReferencia,Mediana,baseCalculo"}
            r = requests.get(OLINDA, params=params, timeout=120); r.raise_for_status()
            parts.append(pd.DataFrame(r.json()["value"]))
        df = pd.concat(parts, ignore_index=True)
        df.to_csv(FOCUS_CACHE, index=False)
    df = df[df["Indicador"] == indicador].copy()
    if df.empty: return df
    df["Data"] = pd.to_datetime(df["Data"])
    df["DataReferencia"] = df["DataReferencia"].astype(int)
    df["Mediana"] = pd.to_numeric(df["Mediana"], errors="coerce")
    if "baseCalculo" in df and df["baseCalculo"].notna().any():
        df = df[df["baseCalculo"] == 0]
    return df

def expectativa_vigente(df, data_entrada, ano_ref):
    """Mediana na primeira data de pesquisa >= data_entrada (até 10 dias depois)."""
    d0 = pd.Timestamp(data_entrada)
    sub = df[(df.DataReferencia == ano_ref) & (df.Data >= d0) & (df.Data <= d0 + timedelta(days=10))]
    if sub.empty:
        sub = df[(df.DataReferencia == ano_ref) & (df.Data <= d0)].sort_values("Data").tail(1)
    return float(sub.sort_values("Data").iloc[0]["Mediana"]) if not sub.empty else math.nan

print("\nCarregando expectativas Focus (cache local ou Olinda)...")
sel = focus_anual("Selic", "2009-12-01", "2021-02-01")
inf = focus_anual("IPCA",  "2009-12-01", "2021-02-01")

dec = []
for r in rows:
    ano0 = int(r["inicio"][:4]); d_ent = f"{r['inicio']}-01"
    reais, usados = [], []
    for k in range(H):
        ano = ano0 + k
        s = expectativa_vigente(sel, d_ent, ano); p = expectativa_vigente(inf, d_ent, ano)
        if math.isnan(s) or math.isnan(p):
            # 5º ano (ou faltante): repete o último disponível
            if reais: reais.append(reais[-1]); usados.append(f"{ano}*")
            continue
        reais.append((1+s/100)/(1+p/100)-1); usados.append(str(ano))
    if not reais:
        continue
    selic_real_esp = (math.prod(1+x for x in reais))**(1/len(reais)) - 1
    premio_ex_ante = r["yield_real_ntnb"] - selic_real_esp*100
    erro_exp = selic_real_esp*100 - r["selic_real_realizada"]
    dec.append(dict(inicio=r["inicio"], yield_real_ntnb=r["yield_real_ntnb"],
                    selic_real_esperada=selic_real_esp*100, selic_real_realizada=r["selic_real_realizada"],
                    carrego_realizado=r["carrego_realizado"], premio_ex_ante=premio_ex_ante,
                    erro_expectativa=erro_exp, anos_focus=" ".join(usados)))
out = pd.DataFrame(dec)
out.to_csv("decomposicao_carrego.csv", index=False)

pd.set_option("display.width", 200)
print("\n=== Decomposição do carrego (pontos percentuais ao ano) ===")
print(out[["inicio","yield_real_ntnb","selic_real_esperada","selic_real_realizada",
           "carrego_realizado","premio_ex_ante","erro_expectativa"]].round(2).to_string(index=False))
print(f"""
Médias ({len(out)} janelas):
  carrego realizado  = {out.carrego_realizado.mean():+.2f} pp/ano
  prêmio ex-ante     = {out.premio_ex_ante.mean():+.2f} pp/ano   (positivo em {(out.premio_ex_ante>0).sum()} janelas)
  erro de expectativa= {out.erro_expectativa.mean():+.2f} pp/ano   (positivo em {(out.erro_expectativa>0).sum()} janelas)

Leitura: prêmio ex-ante > 0 = o mercado já cobrava para carregar duration (hipótese das
expectativas falha com prêmio positivo). erro > 0 = a Selic real veio ABAIXO do esperado
(o Focus superestimou o juro real futuro). A soma dos dois é o carrego realizado.
""")

# --------------------------------------------------------------------------
# 4. Gráfico
# --------------------------------------------------------------------------
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 5.5))
    x = range(len(out)); w = 0.4
    ax.bar([i-w/2 for i in x], out.premio_ex_ante, w, color="#D99A3B", label="prêmio a termo ex-ante (yield real − Selic real esperada)")
    ax.bar([i+w/2 for i in x], out.erro_expectativa, w, color="#6B1E2C", label="erro de expectativa (Selic esperada − realizada)")
    ax.plot(list(x), out.carrego_realizado, "o-", color="#123329", lw=2, label="carrego realizado (soma)")
    ax.axhline(0, color="#231F1A", lw=1)
    ax.set_xticks(list(x)); ax.set_xticklabels([i.replace("-","/") for i in out.inicio], rotation=45, ha="right")
    ax.set_ylabel("p.p. ao ano"); ax.set_title("Decomposição do carrego real da NTN-B de 5 anos, por janela de entrada")
    ax.legend(frameon=False, fontsize=9); ax.spines[["top","right"]].set_visible(False)
    plt.tight_layout(); plt.savefig("decomposicao_carrego.png", dpi=160)
    print("Gráfico salvo em decomposicao_carrego.png")
except Exception as e:
    print("matplotlib indisponível; gráfico não gerado:", e)

# --------------------------------------------------------------------------
# 5. (Opcional) Passo 2 — prefixado de 5 anos na Tabela 7
#    Precisa do histórico de taxas do Tesouro Direto (LTN/NTN-F). O arquivo é grande
#    (~100 MB). Descomente para rodar.
# --------------------------------------------------------------------------
PASSO2 = False
if PASSO2:
    URL_TD = ("https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto/"
              "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
    print("\nBaixando histórico do Tesouro Direto (pode demorar)...")
    td = pd.read_csv(URL_TD, sep=";", decimal=",", encoding="latin1")
    td["Data Base"] = pd.to_datetime(td["Data Base"], dayfirst=True)
    td["Data Vencimento"] = pd.to_datetime(td["Data Vencimento"], dayfirst=True)
    pre = td[td["Tipo Titulo"].str.contains("Prefixado|LTN|NTN-F", regex=True)]
    res = []
    for r in rows:
        d_ent = pd.Timestamp(r["inicio"] + "-01"); d_alvo = pd.Timestamp(r["resgate"] + "-01")
        cand = pre[(pre["Data Base"] >= d_ent) & (pre["Data Base"] <= d_ent + timedelta(days=10))].copy()
        if cand.empty: continue
        cand["dist"] = (cand["Data Vencimento"] - d_alvo).abs()
        best = cand.sort_values(["dist","Data Base"]).iloc[0]
        tx_nom = best["Taxa Compra Manha"]/100
        I_ini,_ = fator(ipca, "2009-12", r["inicio"]); I_fim,_ = fator(ipca, "2009-12", r["resgate"]); I_win = I_fim/I_ini
        # prefixado: aporte igual ao da NTN-B; valor final nominal travado
        final_pre = r["aporte"] * (1+tx_nom)**H
        res.append(dict(inicio=r["inicio"], titulo=best["Tipo Titulo"], venc=best["Data Vencimento"].date(),
                        taxa_nominal=tx_nom*100, final_prefixado=final_pre, faculdade=BASE*I_fim,
                        gap_prefixado_pct=(final_pre/(BASE*I_fim)-1)*100,
                        inflacao_implicita=((1+tx_nom)/(1+r["yield_real_ntnb"]/100)-1)*100,
                        inflacao_realizada=(I_win**(1/H)-1)*100))
    p2 = pd.DataFrame(res); p2.to_csv("tabela7_prefixado.csv", index=False)
    print(p2.round(2).to_string(index=False))
    print("\nGap do prefixado vs faculdade: positivo = a inflação realizada ficou ABAIXO da implícita (proteção não pagou).")
