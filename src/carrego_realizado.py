"""Carrego real realizado por janela, extraído só da Tabela 7:
yield real travada na NTN-B (da coluna aporte) menos Selic real média realizada (da coluna CDI).
Janelas com IPCA-até-a-entrada disponível na própria tabela (jan/10 e a partir de jan/15)."""
import numpy as np, pandas as pd
df = pd.read_csv("data/tabela7_paper.csv"); BASE=500000; H=5
I_end = df.faculdade_corrigida/BASE
I_start = pd.Series([1.0]+[np.nan]*22)
for i in range(10,23): I_start[i] = I_end[i-10]
ok = I_start.notna(); Iw = I_end/I_start
r0 = (BASE*I_start/df.aporte)**(1/H)-1
cdi_real = ((df.portfolio_cdi/df.aporte)/Iw)**(1/H)-1
out = pd.DataFrame({"inicio":df.inicio,"yield_real_ntnb_%":r0*100,"selic_real_realizada_%":cdi_real*100,"carrego_%":(r0-cdi_real)*100})[ok]
out.to_csv("outputs/carrego_realizado.csv", index=False)
print(out.round(2).to_string(index=False))
print(f"\nmédia {out['carrego_%'].mean():.2f} pp/ano | positivo em {(out['carrego_%']>0).sum()} de {len(out)}")
