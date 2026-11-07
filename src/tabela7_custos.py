"""Tabela 7 líquida de IR (15% sobre o ganho nominal) e custódia B3 (0,30%/0,25%/0,20%).
Usa apenas os números publicados na Tabela 7 (data/tabela7_paper.csv)."""
import numpy as np, pandas as pd
df = pd.read_csv("data/tabela7_paper.csv"); IR = 0.15
def fee(y): return 0.0030 if y<=2018 else (0.0025 if y<=2021 else 0.0020)
df["ano0"] = 2000 + df.inicio.str[-2:].astype(int)
df["fator_custodia"] = df.ano0.apply(lambda y: np.prod([1-fee(k) for k in range(y, y+5)]))
df["ntnb_liq"] = df.aporte + (df.faculdade_corrigida*df.fator_custodia - df.aporte)*(1-IR)
df["cdi_liq"]  = df.aporte + (df.portfolio_cdi - df.aporte)*(1-IR)
df["gap_cdi_bruto_%"] = (df.portfolio_cdi/df.faculdade_corrigida-1)*100
df["gap_cdi_liq_%"]   = (df.cdi_liq/df.faculdade_corrigida-1)*100
df["gap_ntnb_liq_%"]  = (df.ntnb_liq/df.faculdade_corrigida-1)*100
F = df.faculdade_corrigida/df.aporte*df.fator_custodia
df["aporte_extra_%"] = (df.faculdade_corrigida/((1-IR)*F+IR)/df.aporte-1)*100
df.to_csv("outputs/tabela7_custos.csv", index=False)
print(df[["inicio","gap_cdi_bruto_%","gap_cdi_liq_%","gap_ntnb_liq_%","aporte_extra_%"]].round(1).to_string(index=False))
print(f"\nNTN-B líquida abaixo da meta: {(df['gap_ntnb_liq_%']<0).sum()}/23 | gap médio {df['gap_ntnb_liq_%'].mean():.1f}% "
      f"(min {df['gap_ntnb_liq_%'].min():.1f}, max {df['gap_ntnb_liq_%'].max():.1f}) | desvio/aporte {((df.ntnb_liq-df.faculdade_corrigida)/df.aporte).std()*100:.1f}%")
print(f"CDI líquido abaixo da meta: {(df['gap_cdi_liq_%']<0).sum()}/23 | desvio/aporte {((df.cdi_liq-df.faculdade_corrigida)/df.aporte).std()*100:.1f}%")
print(f"Aporte extra para imunizar líquido: média {df['aporte_extra_%'].mean():.1f}%")
