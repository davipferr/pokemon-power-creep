---
title: Atributos por geração
---

# Atributos por geração

O *total de atributos* (BST, de *base stat total*) soma HP, Ataque, Defesa, Ataque Especial, Defesa Especial e Velocidade. É a medida mais usada de "força bruta" de um Pokémon, mesmo sem contar habilidades, golpes e tipos.

```js
import {parquet} from "./components/parquet.js";
import {genLonga, GRUPOS, num, num1, pct, PRINCIPAL, rows} from "./components/format.js";
import {palette} from "./components/palette.js";
import {genStrip, slopeText} from "./components/charts.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const resumo = rows(await parquet(FileAttachment("data/geracoes.parquet")));
const tend = await FileAttachment("data/tendencias.json").json();
const pal = palette(dark);
const especies = pokemon.filter((d) => d.padrao);
```

## Um grupo de cada vez

```js
const grupo = view(Inputs.radio(["Todos", ...GRUPOS], {label: "Grupo", value: PRINCIPAL}));
const medida = view(Inputs.radio(new Map([["Hoje", "total"], ["No lançamento", "total_lanc"]]), {label: "Atributos", value: "total"}));
```

```js
const sel = grupo === "Todos" ? especies : especies.filter((d) => d.grupo === grupo);
const extent = d3.extent(especies, (d) => d.total);
```

<div class="card">
  <h2>${grupo} — ${num(sel.length)} espécies</h2>
  ${resize((width) => genStrip(sel, {width, pal, y: medida, domain: [0, extent[1]], trend: grupo === PRINCIPAL ? (medida === "total" ? tend.principal.total : tend.principal.total_lanc) : grupo === "Todos" && medida === "total" ? tend.todos : null}))}
  <p class="muted small">Cada ponto é uma espécie (forma padrão); passe o mouse para ver o nome. Barra azul: metade central; círculo: mediana. ${grupo === PRINCIPAL ? `Linha tracejada: ${slopeText(medida === "total" ? tend.principal.total : tend.principal.total_lanc)}.` : grupo === "Todos" && medida === "total" ? `Linha tracejada: ${slopeText(tend.todos)}.` : ""} "No lançamento" usa os atributos que cada Pokémon tinha na geração em que foi lançado (os da Gen 2 para a Gen 1, que não separava Ataque e Defesa Especial).</p>
</div>

## Mediana por grupo

```js
const pivot = d3.range(1, 10).map((g) => ({
  geracao: genLonga(g),
  ...Object.fromEntries(["Todos", ...GRUPOS].map((gr) => [gr, resumo.find((d) => d.medida === "atual" && d.grupo === gr && d.geracao === g)]))
}));
const cell = (d) => (d ? html`<span title=${`${num(d.n)} espécies · metade entre ${num(d.q1)} e ${num(d.q3)}`}>${num(d.mediana)} <span class="muted small">(${num(d.n)})</span></span>` : html`<span class="muted">–</span>`);
```

```js
Inputs.table(pivot, {
  columns: ["geracao", "Todos", ...GRUPOS],
  header: {geracao: "Geração"},
  format: Object.fromEntries(["Todos", ...GRUPOS].map((g) => [g, cell])),
  sort: null,
  select: false,
  rows: 10,
  layout: "auto"
})
```

<p class="muted small">Mediana do total de atributos (entre parênteses, o número de espécies). Lendários e Míticos variam muito porque cada geração tem poucos — e alguns, como Cosmog e Kubfu, ainda evoluem.</p>

<h2 id="composicao">Composição</h2>

Quanto de cada geração é lendário, comum ou estágio intermediário. As gerações recentes trazem proporcionalmente mais lendários, Ultra Feras e Paradoxos, e menos Pokémon que ainda evoluem — isso sozinho já empurra a mediana geral para cima, sem que nenhum Pokémon comparável tenha ficado mais forte.

```js
const ordem = GRUPOS;
const cores = new Map(ordem.map((g, i) => [g, pal.categorical[i]]));
const comp = d3
  .rollups(especies, (v) => v.length, (d) => d.geracao, (d) => d.grupo)
  .flatMap(([geracao, gs]) => {
    const n = d3.sum(gs, ([, k]) => k);
    return gs.map(([grupo, k]) => ({geracao, grupo, k, p: k / n}));
  });
```

<div class="card">
  ${resize((width) => Plot.plot({
    width,
    height: 300,
    marginLeft: width < 560 ? 54 : 100,
    x: {axis: "top", tickFormat: "%", label: null, grid: true},
    y: {domain: d3.range(1, 10), tickFormat: width < 560 ? (g) => `Gen ${g}` : genLonga, label: null, tickSize: 0},
    color: {domain: ordem, range: ordem.map((g) => cores.get(g)), legend: true},
    marks: [
      Plot.barX(comp, Plot.stackX({y: "geracao", x: "p", fill: "grupo", order: ordem, inset: 0.5, tip: {format: {x: pct, y: genLonga}}, channels: {Espécies: "k"}}))
    ]
  }))}
</div>

## Hoje × no lançamento

```js
const linhas = ["atual", "lancamento"].flatMap((m) =>
  resumo.filter((d) => d.grupo === PRINCIPAL && d.medida === m).map((d) => ({...d, serie: m === "atual" ? "Hoje" : "No lançamento"}))
);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Média do total, comuns totalmente evoluídos</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 260,
      x: {ticks: d3.range(1, 10), tickFormat: (g) => `Gen ${g}`, label: null},
      y: {grid: true, label: "Média do total", nice: true},
      color: {domain: ["Hoje", "No lançamento"], range: [pal.accent, pal.categorical[1]], legend: true},
      marks: [
        Plot.line(linhas, {x: "geracao", y: "media", stroke: "serie", strokeWidth: 2}),
        Plot.dot(linhas, {x: "geracao", y: "media", fill: "serie", r: 4, stroke: "var(--theme-background-alt)", strokeWidth: 2}),
        Plot.tip(linhas, Plot.pointer({x: "geracao", y: "media", title: (d) => `${genLonga(d.geracao)} · ${d.serie}\nmédia ${num1(d.media)}`}))
      ]
    }))}
  </div>
  <div class="card">
    <h2>O que os reforços fizeram com a tendência</h2>
    <p>Com os atributos de hoje: <strong>${slopeText(tend.principal.total)}</strong>.</p>
    <p>Com os atributos de lançamento: <strong>${slopeText(tend.principal.total_lanc)}</strong>.</p>
    <p>As gerações 6 e 7 reforçaram dezenas de Pokémon das gerações 1 a 5 (Pikachu, Butterfree, Alakazam…). Isso aproxima os antigos dos novos e deixa o creep medido hoje um pouco menor do que ele foi na época de cada lançamento. <a href="./formas#ajustes-retroativos">Ver a lista →</a></p>
    <p class="muted small">Tendência linear por mínimos quadrados sobre ${num(tend.principal.total.n)} espécies; R² = ${num1(tend.principal.total.r2 * 100)} %.</p>
  </div>
</div>
