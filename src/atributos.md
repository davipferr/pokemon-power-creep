---
title: Formato dos atributos
---

# Formato dos atributos

O total pode ficar parado enquanto a *distribuição* muda: mais Velocidade e menos Defesa, ou designs mais extremos (muito forte numa coisa, fraco no resto). Aqui, só os Pokémon comuns totalmente evoluídos.

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, num1, pct, PRINCIPAL, rows, sinal, STATS, statNome} from "./components/format.js";
import {palette} from "./components/palette.js";
import {genStrip, slopeText} from "./components/charts.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const resumo = rows(await parquet(FileAttachment("data/geracoes.parquet")));
const tend = await FileAttachment("data/tendencias.json").json();
const pal = palette(dark);
const principal = pokemon.filter((d) => d.padrao && d.grupo === PRINCIPAL);
```

## Cada atributo, geração a geração

```js
const porStat = STATS.flatMap(({key, nome}) =>
  resumo
    .filter((d) => d.grupo === PRINCIPAL && d.medida === "atual")
    .map((d) => ({stat: nome, geracao: d.geracao, med: d[`med_${key}`]}))
);
const inclinacoes = STATS.map(({key, nome}) => ({stat: nome, ...tend.principal[key]}));
const significativo = (t) => t.ic95[0] > 0 || t.ic95[1] < 0;
```

<div class="card">
  ${resize((width) => Plot.plot({
    width,
    height: width < 640 ? 560 : 300,
    marginTop: 24,
    fx: width < 640 ? undefined : {domain: STATS.map((s) => s.nome), label: null},
    fy: width < 640 ? {domain: STATS.map((s) => s.nome), label: null} : undefined,
    x: {ticks: [1, 5, 9], tickFormat: (g) => `G${g}`, label: null, domain: [1, 9]},
    y: {grid: true, label: "Mediana", domain: [50, 100], ticks: 3},
    marks: [
      Plot.frame({strokeOpacity: 0.15}),
      Plot.line(porStat, {x: "geracao", y: "med", ...(width < 640 ? {fy: "stat"} : {fx: "stat"}), stroke: pal.accent, strokeWidth: 2}),
      Plot.dot(porStat, {x: "geracao", y: "med", ...(width < 640 ? {fy: "stat"} : {fx: "stat"}), fill: pal.accent, r: 3, tip: {format: {x: genLonga, fx: false, fy: false}}})
    ]
  }))}
  <p class="muted small">Mediana de cada atributo entre os comuns totalmente evoluídos de cada geração.</p>
</div>

```js
Inputs.table(inclinacoes, {
  columns: ["stat", "inclinacao", "ic95", "r2"],
  header: {stat: "Atributo", inclinacao: "Por geração", ic95: "IC 95 %", r2: "R²"},
  format: {
    inclinacao: (x) => sinal(x),
    ic95: ([a, b]) => `${sinal(a)} a ${sinal(b)}`,
    r2: (x) => pct(x)
  },
  sort: null,
  select: false,
  layout: "auto"
})
```

<p class="muted small">Tendência linear de cada atributo. Só ${inclinacoes.filter(significativo).map((d) => d.stat).join(" e ") || "nenhum"} ${inclinacoes.filter(significativo).length === 1 ? "tem" : "têm"} intervalo de confiança inteiramente acima de zero: o pouco de creep que existe veio pelo ataque, não pela velocidade ou pela bulk.</p>

## Especialização

Para cada Pokémon, o *coeficiente de variação* dos seis atributos (desvio-padrão ÷ média). Um Pokémon com 100 em tudo tem 0; Shuckle (Defesa e Def. Esp. 230, Ataque e Atq. Esp. 10) tem o maior valor.

<div class="card">
  ${resize((width) => genStrip(principal, {width, pal, y: "especializacao", label: "Especialização (coef. de variação)", domain: [0, 1.2], height: 320, trend: tend.principal.especializacao}))}
  <p class="muted small">Linha tracejada: ${slopeText(tend.principal.especializacao, "")} — na prática, zero. Os designs não ficaram mais extremos.</p>
</div>

```js
const extremos = [...principal].sort((a, b) => b.especializacao - a.especializacao);
const linha = (d) => ({nome: d.nome, geracao: d.geracao, total: d.total, especializacao: d.especializacao, ...Object.fromEntries(STATS.map((s) => [s.key, d[s.key]]))});
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Mais especializados</h2>
    ${Inputs.table(extremos.slice(0, 8).map(linha), {columns: ["nome", "geracao", ...STATS.map((s) => s.key)], header: {nome: "Pokémon", geracao: "Gen", ...statNome}, format: {geracao: (g) => g}, sort: null, select: false, layout: "auto"})}
  </div>
  <div class="card">
    <h2>Mais equilibrados</h2>
    ${Inputs.table(extremos.slice(-8).reverse().map(linha), {columns: ["nome", "geracao", ...STATS.map((s) => s.key)], header: {nome: "Pokémon", geracao: "Gen", ...statNome}, format: {geracao: (g) => g}, sort: null, select: false, layout: "auto"})}
  </div>
</div>

## O atributo mais alto

```js
const maior = d3
  .rollups(principal, (v) => v.length, (d) => d.geracao, (d) => d.maior_stat)
  .flatMap(([geracao, ss]) => {
    const n = d3.sum(ss, ([, k]) => k);
    return ss.map(([stat, k]) => ({geracao, stat: statNome[stat], k, p: k / n}));
  });
const statOrdem = STATS.map((s) => s.nome);
const fisico = d3
  .rollups(principal, (v) => d3.mean(v, (d) => d.ataque > d.atq_esp), (d) => d.geracao)
  .map(([geracao, p]) => ({geracao, p}))
  .sort((a, b) => a.geracao - b.geracao);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Qual atributo é o maior de cada Pokémon</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 290,
      marginLeft: 44,
      x: {axis: "top", tickFormat: "%", label: null, grid: true},
      y: {domain: d3.range(1, 10), tickFormat: gen, label: null, tickSize: 0},
      color: {domain: statOrdem, range: pal.categorical.slice(0, 6), legend: true},
      marks: [Plot.barX(maior, Plot.stackX({y: "geracao", x: "p", fill: "stat", order: statOrdem, inset: 0.5, tip: {format: {x: pct, y: genLonga}}, channels: {Pokémon: "k"}}))]
    }))}
    <p class="muted small">Empates contam para o primeiro atributo na ordem HP, Ataque, Defesa, Atq. Esp., Def. Esp., Velocidade.</p>
  </div>
  <div class="card">
    <h2>Mais físicos que especiais</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 290,
      x: {ticks: d3.range(1, 10), tickFormat: (g) => `Gen ${g}`, label: null},
      y: {grid: true, domain: [0, 1], tickFormat: "%", label: "Ataque > Atq. Esp."},
      marks: [
        Plot.ruleY([0.5], {strokeOpacity: 0.4, strokeDasharray: "3 3"}),
        Plot.line(fisico, {x: "geracao", y: "p", stroke: pal.accent, strokeWidth: 2}),
        Plot.dot(fisico, {x: "geracao", y: "p", fill: pal.accent, r: 4, stroke: "var(--theme-background-alt)", strokeWidth: 2, tip: {format: {x: genLonga, y: pct}}})
      ]
    }))}
    <p class="muted small">Parcela dos comuns totalmente evoluídos com Ataque maior que Ataque Especial.</p>
  </div>
</div>
