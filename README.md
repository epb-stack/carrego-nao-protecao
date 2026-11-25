# Carrego, mais que proteção

Replicação e extensão de **Marinho, Ribeiro e Wichmann (2026), "Repensando o ativo sem risco: uma visão brasileira"** — Insper / XP.

**Tese do repositório:** a NTN-B casada ao passivo é o ativo sem risco *por construção* (argumento de Merton, Tabela 7). Mas o que a evidência de 2010–2026 mostra é um **prêmio a termo real positivo**, não um prêmio de inflação: o prefixado, sem proteção, rendeu o mesmo que o IPCA+ (Tabela 3). O excesso da NTN-B sobre o CDI é **carrego** (duration), não **proteção** (indexador).

Nota visual para os autores: [`docs/index.html`](docs/index.html).

## Resultados (só com os números publicados no paper)

| Achado | Número | Fonte |
|---|---|---|
| Prefixado (IDKA5) vs IPCA+ longo (IMAB5+), retorno real médio | 5,71% vs 5,47% (1a) · 5,06 vs 5,02 (5a) · 5,71 vs 5,55 (10a) | Tabela 3 |
| Anos em que o prefixado vence o IPCA+ longo | 9 de 16 | Tabela 1 |
| Carrego real realizado (yield real travada − Selic real média dos 5 anos seguintes) | **+2,5 pp/ano**, positivo em 11 de 14 janelas | derivado da Tabela 7 |
| Tabela 7 líquida de IR (15%) e custódia B3 | NTN-B 23/23 abaixo da meta, gap −7,4% (−5,7 a −8,6); CDI 21/23, dispersão 15,7% vs 2,3% | derivado da Tabela 7 |
| Aporte extra que restaura a imunização líquida | +8,0% | derivado da Tabela 7 |

Leitura: o imposto troca "imunização perfeita" por "imunização com prêmio conhecido"; o argumento de *retorno* da Seção 7 não se sustenta; o argumento de *variância do passivo* da Tabela 7 fica — e vira o único.

## Passo 2 concluído — o prefixado de 5 anos na Tabela 7 (25/11/2026)

Mesmo aporte da NTN-B; título prefixado (LTN/NTN-F) com vencimento mais próximo do resgate, cotado nos 15 primeiros dias da entrada (Tesouro Direto, taxa de compra); valor final bruto, como na Tabela 7.

| Portfólio | Gap médio vs faculdade | Acima do alvo | Dispersão |
|---|---|---|---|
| NTN-B casada | 0 (por construção) | — | 0 |
| Prefixado 5 anos | **−3,7%** | 4 de 23 | 7,7% |
| CDI | −9,8% | 3 de 23 | 9,8% |

Inflação implícita na entrada 5,07% a.a.; realizada 5,92%. **Proteção realizada +0,85 pp/ano, positiva em 19 de 23** (robusta ao descasamento de vencimento: títulos com desvio ≤ 6 meses, +0,89). Retorno real médio: NTN-B 5,27% · prefixado 4,44% · CDI 3,01%.

**Correção da tese (25/11/2026).** A frase de abertura era "carrego, não proteção", apoiada na Tabela 3 (índices de duration constante: prefixado ≈ IPCA+). Carregados até o vencimento, nas janelas que terminam entre 2015 e 2026, a proteção não foi zero: pagou 0,85 pp/ano — contra 2,26 de carrego (2,6×). Os dois resultados medem coisas diferentes e são ambos verdadeiros. A frase passa a ser **carrego, mais que proteção**. O nome do repositório fica como registro de onde a pesquisa começou. Resultados em `outputs/tabela7_prefixado.csv` e `.png`.

## Passo 1 concluído — decomposição do carrego com dados do BCB (25/11/2026)

Reconstrução da Tabela 7 com IPCA (SGS 433) e CDI (SGS 4391): erro máximo de 0,06% no portfólio CDI e de 1,8% na faculdade corrigida (dia exato de entrada). Com as medianas do Focus (Olinda, expectativas anuais de Selic e IPCA nos 15 primeiros dias de cada entrada), o carrego de cada janela se divide em duas partes:

| Componente | Média (23 janelas) | Positivo em |
|---|---|---|
| Carrego realizado (yield real NTN-B − Selic real realizada) | **+2,26 pp/ano** | 20 de 23 |
| Prêmio ex-ante (yield real − Selic real esperada pelo Focus) | **+1,03 pp/ano** | **23 de 23** |
| Erro de expectativa (Selic real esperada − realizada) | +1,23 pp/ano | 17 de 23 |

Leitura: em nenhuma janela a NTN-B foi comprada com yield real abaixo da Selic real esperada — o mercado sempre cobrou para carregar prazo. O excesso sobre o CDI é prêmio de prazo sistemático, não sorte nem proteção. O erro de expectativa domina nas entradas de 2016–18 e inverte em 2020–21: a decomposição é dependente de regime, e por isso serve de monitor. Resultados em `outputs/decomposicao_carrego.csv`, `outputs/validacao_tabela7.csv` e `outputs/decomposicao_carrego.png`.

## Estrutura

```
data/      tabelas do paper transcritas (Tabela 1, 3 e 7); data/cache/ séries do BCB usadas no passo 1
src/       scripts
outputs/   resultados em CSV
docs/      nota visual (HTML, tema claro/escuro)
```

## Reproduzir

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 src/carrego_realizado.py     # carrego por janela (só Tabela 7)
python3 src/tabela7_custos.py        # Tabela 7 com IR e custódia
python3 src/decompoe_carrego.py      # passo 1: decomposição com o Focus (usa data/cache/; baixa do BCB se faltar)
python3 src/tabela7_prefixado.py     # passo 2: prefixado de 5 anos na Tabela 7 (usa data/cache/)
```

`decompoe_carrego.py` lê IPCA, CDI e Focus de `data/cache/` (incluído no repositório, para rodar sem rede) ou os baixa das APIs SGS e Olinda do BCB e cria o cache; valida a reconstrução contra a Tabela 7 e decompõe o carrego em **prêmio a termo ex-ante** (yield real − Selic real esperada) e **erro de expectativa** (Selic esperada − realizada). `tabela7_prefixado.py` usa o recorte do histórico do Tesouro Direto em `data/cache/` (só prefixados nos 15 primeiros dias de cada entrada; o arquivo completo tem 14 MB e está em tesourotransparente.gov.br).

## Hipóteses declaradas

- IR de 15% sobre o ganho nominal nos dois ativos; custódia B3 só na NTN-B (0,30% até 2018, 0,25% até 2021, 0,20% depois), aproximada como arrasto composto. CDI sem custo — hipótese generosa com o CDI.
- Taxa real da NTN-B extraída da Tabela 7: `aporte = 500.000 × IPCA_acum(jan/10 → entrada) / (1 + r)^5`.
- Focus: expectativa de Selic de fim de ano como proxy da média; 5º ano repete o 4º; mediana da primeira pesquisa após a entrada.
- IMAB5+ tem duration maior que o IDKA5 (fixa em 5 anos): a comparação não é limpa, e o viés joga contra a NTN-B.

## Próximos passos

1. ~~Decomposição do carrego com o Focus (passo 1)~~ — feito, ver acima.
2. ~~Prefixado de 5 anos como terceiro portfólio da Tabela 7 (passo 2)~~ — feito, ver acima. Fica em aberto a versão líquida de IR sobre a correção monetária.
3. Default da previdência: glide path padrão com RendA+ como âncora; custo de ancorar no CDI em probabilidade de shortfall da renda-alvo (pré-projeto de dissertação, Insper MPE 2027).

## Autora

Érika Bosco · [IA for Finance](https://iaforfinance.com.br) · epbosco@gmail.com

Fonte: Marinho, E.; Ribeiro, R.; Wichmann, A. *Repensando o ativo sem risco: uma visão brasileira*, jun/2026. Todos os cálculos partem das tabelas publicadas; nenhum dado proprietário.
