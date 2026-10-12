---
title: Tipos
---

# Tipos

O creep também pode vir de tipos: um tipo novo (Sombrio e Aço na Gen 2, Fada na Gen 6), combinações duplas mais comuns ou uma tabela de efetividade que muda.

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, pct, rows} from "./components/format.js";
import {palette} from "./components/palette.js";
import {badge, TIPOS, tipoNome} from "./components/tipos.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const tabela = rows(await parquet(FileAttachment("data/tipos.parquet")));
const pal = palette(dark);
const especies = pokemon.filter((d) => d.padrao);
```

## Que tipos cada geração trouxe

```js
// Types at launch, so Clefairy counts as Normal in Gen 1 (Fairy didn't exist yet).
const usos = especies.flatMap((d) => [d.tipo1_lanc, d.tipo2_lanc].filter(Boolean).map((t) => ({geracao: d.geracao, tipo: t})));
const porGen = d3.rollup(especies, (v) => v.length, (d) => d.geracao);
const freq = d3
  .rollups(usos, (v) => v.length, (d) => d.geracao, (d) => d.tipo)
  .flatMap(([geracao, ts]) => ts.map(([tipo, n]) => ({geracao, tipo, n, p: n / porGen.get(geracao)})));
```

<div class="card">
  ${resize((width) => Plot.plot({
    width,
    height: 520,
    marginLeft: 76,
    x: {domain: d3.range(1, 10), tickFormat: (g) => (width < 560 ? g : `Gen ${g}`), label: null, axis: "top", tickSize: 0},
    y: {domain: TIPOS.map((t) => t.key), tickFormat: (t) => tipoNome[t], label: null, tickSize: 0},
    color: {type: "linear", domain: [0, 0.3], range: [pal.blues(2)[0], pal.blues(2)[1]], clamp: true, legend: true, label: "Parcela das espécies da geração", tickFormat: "%"},
    marks: [
      Plot.cell(freq, {x: "geracao", y: "tipo", fill: "p", inset: 1, rx: 3, tip: {format: {x: genLonga, y: (t) => tipoNome[t], fill: pct}}, channels: {Espécies: "n"}}),
      Plot.text(freq, {x: "geracao", y: "tipo", text: (d) => (width < 560 ? "" : pct(d.p)), fill: (d) => (d.p > 0.17 ? "var(--theme-background)" : "currentColor"), fontSize: 10})
    ]
  }))}
  <p class="muted small">Parcela das espécies novas de cada geração que têm o tipo (como primeiro ou segundo tipo, no lançamento). Uma espécie com dois tipos conta duas vezes.</p>
</div>

```js
const duplos = d3
  .rollups(especies, (v) => ({lanc: d3.mean(v, (d) => d.tipo2_lanc != null), hoje: d3.mean(v, (d) => d.tipo2 != null)}), (d) => d.geracao)
  .map(([geracao, s]) => ({geracao, ...s}))
  .sort((a, b) => a.geracao - b.geracao);
const fada = especies.filter((d) => d.tipo1 !== d.tipo1_lanc || d.tipo2 !== d.tipo2_lanc);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Pokémon com dois tipos</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 260,
      x: {ticks: d3.range(1, 10), tickFormat: (g) => `Gen ${g}`, label: null},
      y: {grid: true, domain: [0, 1], tickFormat: "%", label: "Parcela com dois tipos"},
      marks: [
        Plot.line(duplos, {x: "geracao", y: "lanc", stroke: pal.accent, strokeWidth: 2}),
        Plot.dot(duplos, {x: "geracao", y: "lanc", fill: pal.accent, r: 4, stroke: "var(--theme-background-alt)", strokeWidth: 2, tip: {format: {x: genLonga, y: pct}}})
      ]
    }))}
    <p class="muted small">Dois tipos dão mais cobertura ofensiva e mais combinações de resistência — um creep que o total de atributos não mede.</p>
  </div>
  <div class="card">
    <h2>${num(fada.length)} Pokémon mudaram de tipo depois de lançados</h2>
    <p>Quase todos ganharam o tipo Fada na geração 6:</p>
    <p>${fada.map((d) => html`<span class="troca"><strong>${d.nome}</strong> ${badge(d.tipo1_lanc)}${badge(d.tipo2_lanc)} → ${badge(d.tipo1)}${badge(d.tipo2)}</span>`)}</p>
  </div>
</div>

## Tabela de efetividade

```js
const atual = tabela.filter((d) => d.ate_geracao == null);
const mult = new Map(atual.map((d) => [`${d.atacante}|${d.defensor}`, d.mult]));
const celulas = TIPOS.flatMap((a) => TIPOS.map((d) => ({atacante: a.key, defensor: d.key, mult: mult.get(`${a.key}|${d.key}`) ?? 1})));
const rotulo = new Map([[0, "0"], [0.5, "½"], [1, ""], [2, "2"]]);
const cor = new Map([[0, pal.diverging.neg], [0.5, `color-mix(in srgb, ${pal.diverging.neg} 45%, ${pal.diverging.mid})`], [1, pal.diverging.mid], [2, pal.diverging.pos]]);
```

<div class="card">
  ${resize((width) => Plot.plot({
    width,
    height: Math.min(width, 640) + 40,
    marginLeft: 76,
    marginTop: 76,
    x: {domain: TIPOS.map((t) => t.key), tickFormat: (t) => tipoNome[t], axis: "top", tickRotate: -45, label: "Tipo que defende →", tickSize: 0},
    y: {domain: TIPOS.map((t) => t.key), tickFormat: (t) => tipoNome[t], label: "Tipo do golpe ↓", tickSize: 0},
    marks: [
      Plot.cell(celulas, {x: "defensor", y: "atacante", fill: (d) => cor.get(d.mult), inset: 1, rx: 2, title: (d) => `${tipoNome[d.atacante]} contra ${tipoNome[d.defensor]}: ×${rotulo.get(d.mult) || "1"}`}),
      Plot.text(celulas, {x: "defensor", y: "atacante", text: (d) => rotulo.get(d.mult), fill: (d) => (d.mult === 1 ? "currentColor" : "#fff"), fontSize: 11, fontWeight: 600})
    ]
  }))}
  <div class="legend-row"><span><i style=${{background: pal.diverging.pos}}></i>×2 super efetivo</span><span><i style=${{background: cor.get(0.5)}}></i>×½ pouco efetivo</span><span><i style=${{background: pal.diverging.neg}}></i>×0 sem efeito</span></div>
</div>

```js
const passadas = d3.groups(tabela.filter((d) => d.ate_geracao != null), (d) => d.atacante, (d) => d.ate_geracao);
// A past chart lists every relation of that attacker at the time (absent = ×1);
// compare it with today's, ignoring Fairy, which didn't exist before Gen 6.
const diferencas = passadas.flatMap(([atacante, porGen]) =>
  porGen.flatMap(([ate, rel]) => {
    const antes = new Map(rel.map((d) => [d.defensor, d.mult]));
    return TIPOS.filter((t) => t.key !== "fairy")
      .map((t) => ({atacante, defensor: t.key, ate, antes: antes.get(t.key) ?? 1, hoje: mult.get(`${atacante}|${t.key}`) ?? 1}))
      .filter((d) => d.antes !== d.hoje);
  })
);
const fmt = (m) => `×${rotulo.get(m) || "1"}`;
```

Mudanças na tabela registradas pela PokeAPI, fora a chegada do tipo Fada:

${diferencas.map((d) => html`<p>${badge(d.atacante)} contra ${badge(d.defensor)}: ${fmt(d.antes)} até a ${genLonga(d.ate)}, ${fmt(d.hoje)} desde a ${gen(d.ate + 1)}.</p>`)}

<style>
.troca { display: inline-block; margin: 0 0.9rem 0.4rem 0; }
</style>
