---
title: Evoluções tardias
---

# Evoluções tardias

Algumas gerações deram evoluções novas a Pokémon antigos: Crobat (Gen 2) para Golbat, Magmortar e Electivire (Gen 4) para Magmar e Electabuzz, Kingambit (Gen 9) para Bisharp. Elas são o caso mais claro de "atualização" de um Pokémon antigo — e tendem a ser bem mais fortes do que os Pokémon criados junto com a própria linha.

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, num1, PRINCIPAL, rows, sinal} from "./components/format.js";
import {palette} from "./components/palette.js";
import {slopeText} from "./components/charts.js";
import {badges} from "./components/tipos.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const tend = await FileAttachment("data/tendencias.json").json();
const pal = palette(dark);
const especies = pokemon.filter((d) => d.padrao);
const porId = new Map(especies.map((d) => [d.especie_id, d]));
const principal = especies.filter((d) => d.grupo === PRINCIPAL);
const tardias = principal.filter((d) => d.evolucao_tardia);
```

```js
const comparacao = d3
  .rollups(principal, (v) => ({med: d3.median(v, (d) => d.total), n: v.length}), (d) => d.geracao, (d) => (d.evolucao_tardia ? "Evolução tardia" : "Criada com a linha"))
  .flatMap(([geracao, gs]) => gs.map(([serie, s]) => ({geracao, serie, ...s})));
const premio = d3.median(tardias, (d) => d.total) - d3.median(principal.filter((d) => !d.evolucao_tardia), (d) => d.total);
```

<div class="card">
  <h2>Mediana do total de atributos, comuns totalmente evoluídos</h2>
  ${resize((width) => Plot.plot({
    width,
    height: 280,
    x: {ticks: d3.range(1, 10), domain: [0.5, 9.5], tickFormat: width < 560 ? (g) => g : gen, label: null},
    y: {grid: true, label: "Mediana do total", nice: true},
    color: {domain: ["Criada com a linha", "Evolução tardia"], range: [pal.muted, pal.accent], legend: true},
    marks: [
      Plot.ruleX(d3.groups(comparacao, (d) => d.geracao).filter(([, v]) => v.length === 2), {x: ([g]) => g, y1: ([, v]) => d3.min(v, (d) => d.med), y2: ([, v]) => d3.max(v, (d) => d.med), stroke: "currentColor", strokeOpacity: 0.3}),
      Plot.dot(comparacao, {x: "geracao", y: "med", fill: "serie", r: (d) => Math.max(4, Math.sqrt(d.n) * 1.6), stroke: "var(--theme-background-alt)", strokeWidth: 2, tip: {format: {x: genLonga, fill: true, r: false}}, channels: {Espécies: "n"}})
    ]
  }))}
  <p class="muted small">O tamanho do círculo indica quantas espécies há em cada grupo. Nas gerações sem círculo azul não houve evolução tardia de Pokémon comum.</p>
</div>

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Prêmio da evolução tardia</h2>
    <span class="big">${sinal(premio, num)} pontos</span>
    <p class="muted">diferença entre as medianas das ${num(tardias.length)} evoluções tardias e dos demais comuns totalmente evoluídos</p>
  </div>
  <div class="card">
    <h2>Elas explicam o creep?</h2>
    <p>Não. Com elas, ${slopeText(tend.principal.total)}; sem elas, ${slopeText(tend.principal.total_nativos)}. Evoluções tardias aparecem em quase todas as gerações (a 2ª já tinha Crobat, Espeon e Kingdra), então somam um prêmio constante, não uma tendência.</p>
  </div>
</div>

## Todas as evoluções tardias

```js
const busca = view(Inputs.search(tardias, {placeholder: "Buscar Pokémon…", format: (n) => `${num(n)} Pokémon`}));
```

```js
Inputs.table(
  busca.map((d) => ({...d, tipos: d, pre: porId.get(d.evolui_de)?.nome, ganho: d.total_pre == null ? null : d.total - d.total_pre})),
  {
    columns: ["nome", "tipos", "geracao", "geracao_linha", "pre", "total_pre", "total", "ganho"],
    header: {nome: "Pokémon", tipos: "Tipos", geracao: "Lançado", geracao_linha: "Linha desde", pre: "Evolui de", total_pre: "Total antes", total: "Total", ganho: "Ganho"},
    format: {tipos: badges, geracao: gen, geracao_linha: gen, ganho: (x) => sinal(x, num)},
    sort: "ganho",
    reverse: true,
    rows: 20,
    layout: "auto"
  }
)
```

<p class="muted small">"Total antes" é o total de atributos do estágio anterior hoje. Scizor tem ganho zero: é uma evolução lateral de Scyther, com o mesmo total distribuído de outro jeito.</p>
