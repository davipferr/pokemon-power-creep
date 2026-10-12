---
title: Golpes
---

# Golpes

Atributos são metade da força de um Pokémon; a outra metade são os golpes. Aqui estão os ${num(golpes.length)} golpes da série principal, sem os golpes de "truque" de batalha (Z-Moves da Gen 7 e Max Moves da Gen 8), que não se aprendem normalmente.

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, num1, pct, rows, sinal} from "./components/format.js";
import {palette} from "./components/palette.js";
import {genStrip, slopeText} from "./components/charts.js";
import {badge} from "./components/tipos.js";

const todos = rows(await parquet(FileAttachment("data/golpes.parquet")));
const tend = await FileAttachment("data/tendencias.json").json();
const pal = palette(dark);
const golpes = todos.filter((d) => !d.gimmick);
// genStrip expects pokemon_id/nome; a move's id and name play the same role.
const dano = golpes.filter((d) => d.classe !== "Status" && d.poder_lanc != null).map((d) => ({...d, pokemon_id: d.golpe_id, nome: d.golpe_nome}));
```

## Poder dos golpes novos

<div class="card">
  <h2>Poder no lançamento de cada golpe de dano, pela geração em que estreou</h2>
  ${resize((width) => genStrip(dano, {width, pal, y: "poder_lanc", label: "Poder", height: 380, trend: tend.golpes.poder_lanc}))}
  <p class="muted small">Linha tracejada: ${slopeText(tend.golpes.poder_lanc)} (R² = ${pct(tend.golpes.poder_lanc.r2)}). Golpes de poder variável (Low Kick, Gyro Ball…) não têm poder fixo e ficam de fora. Explosion (250) e Self-Destruct (200) não aparecem com esses valores porque foram lançados com 170 e 130.</p>
</div>

```js
const porGen = d3
  .rollups(
    golpes,
    (v) => {
      const d = v.filter((x) => x.classe !== "Status" && x.poder_lanc != null);
      return {n: v.length, status: d3.mean(v, (x) => x.classe === "Status"), forte: d3.mean(d, (x) => x.poder_lanc >= 100), med: d3.median(d, (x) => x.poder_lanc)};
    },
    (d) => d.geracao
  )
  .map(([geracao, s]) => ({geracao, ...s}))
  .sort((a, b) => a.geracao - b.geracao);
const linha = (y, label, fmt = pct) => (width) =>
  Plot.plot({
    width,
    height: 240,
    x: {ticks: d3.range(1, 10), tickFormat: (g) => `Gen ${g}`, label: null},
    y: {grid: true, domain: [0, 0.6], tickFormat: "%", label},
    marks: [
      Plot.line(porGen, {x: "geracao", y, stroke: pal.accent, strokeWidth: 2}),
      Plot.dot(porGen, {x: "geracao", y, fill: pal.accent, r: 4, stroke: "var(--theme-background-alt)", strokeWidth: 2, tip: {format: {x: genLonga, y: fmt}}, channels: {Golpes: "n"}})
    ]
  });
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Golpes de dano com poder 100 ou mais</h2>
    ${resize(linha("forte", "Parcela dos golpes de dano"))}
  </div>
  <div class="card">
    <h2>Golpes de status (sem dano)</h2>
    ${resize(linha("status", "Parcela dos golpes novos"))}
    <p class="muted small">Depois da Gen 6, cada geração trouxe proporcionalmente menos golpes de status e mais golpes de dano.</p>
  </div>
</div>

## Golpes alterados depois de lançados

```js
const alterados = golpes
  .filter((d) => d.poder != null && d.poder_lanc != null && d.poder !== d.poder_lanc)
  .map((d) => ({...d, diff: d.poder - d.poder_lanc}));
const subiram = alterados.filter((d) => d.diff > 0);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Mais fortes</h2>
    <span class="big">${num(subiram.length)}</span>
    <p class="muted">golpes ganharam poder depois de lançados (mediana ${sinal(d3.median(subiram, (d) => d.diff), num)})</p>
  </div>
  <div class="card">
    <h2>Mais fracos</h2>
    <span class="big">${num(alterados.length - subiram.length)}</span>
    <p class="muted">perderam poder — vários deles os fortes da Gen 1, como Hydro Pump e Blizzard (120 → 110)</p>
  </div>
</div>

```js
const buscaGolpe = view(Inputs.search(alterados, {placeholder: "Buscar golpe…", format: (n) => `${num(n)} golpes`}));
```

```js
Inputs.table(buscaGolpe, {
  columns: ["golpe_nome", "tipo", "classe", "geracao", "poder_lanc", "poder", "diff", "precisao_lanc", "precisao"],
  header: {golpe_nome: "Golpe", tipo: "Tipo", classe: "Classe", geracao: "Estreia", poder_lanc: "Poder antes", poder: "Poder hoje", diff: "Diferença", precisao_lanc: "Precisão antes", precisao: "Precisão hoje"},
  format: {tipo: badge, geracao: gen, diff: (x) => sinal(x, num)},
  sort: "diff",
  reverse: true,
  rows: 20,
  layout: "auto"
})
```

<p class="muted small">A classe (físico/especial) é a de hoje. Até a Gen 3, a classe dependia só do tipo do golpe; a separação por golpe veio na Gen 4.</p>
