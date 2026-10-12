---
title: Megas, formas e ajustes
---

# Megas, formas e ajustes

O creep não vem só de Pokémon novos. Pokémon antigos também ficaram mais fortes: com formas Mega e Primal, com versões regionais e com reforços diretos nos atributos.

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, pct, rows, sinal, STATS, statNome} from "./components/format.js";
import {palette} from "./components/palette.js";
import {hbars} from "./components/charts.js";
import {badges} from "./components/tipos.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const pal = palette(dark);
const padrao = new Map(pokemon.filter((d) => d.padrao).map((d) => [d.especie_id, d]));
const comBase = (d) => ({...d, base: padrao.get(d.especie_id), ganho: d.total - padrao.get(d.especie_id).total, geracao_base: padrao.get(d.especie_id).geracao});
```

## Megaevoluções

```js
const megas = pokemon.filter((d) => d.forma_tipo === "mega" || d.forma_tipo === "primal").map(comBase);
const ondas = new Map([[6, "X/Y e ORAS (2013–14)"], [9, "Legends: Z-A (2025)"]]);
const porBase = d3
  .rollups(megas, (v) => v.length, (d) => d.geracao_base, (d) => ondas.get(d.geracao) ?? genLonga(d.geracao))
  .flatMap(([geracao_base, os]) => os.map(([onda, n]) => ({geracao_base, onda, n})));
const ondaDomain = [...new Set(megas.map((d) => ondas.get(d.geracao) ?? genLonga(d.geracao)))];
const fora100 = megas.filter((d) => d.ganho !== 100);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>${num(megas.length)} formas Mega e Primal, por geração do Pokémon original</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 280,
      x: {domain: d3.range(1, 10), tickFormat: (g) => `Gen ${g}`, label: null, tickSize: 0},
      y: {grid: true, label: "Formas"},
      color: {domain: ondaDomain, range: [pal.accent, pal.categorical[1], pal.categorical[2]].slice(0, ondaDomain.length), legend: true},
      marks: [
        Plot.barY(porBase, Plot.stackY({x: "geracao_base", y: "n", fill: "onda", inset: 0.5, ry2: 3, tip: {format: {x: genLonga}}})),
        Plot.ruleY([0], {strokeOpacity: 0.4})
      ]
    }))}
    <p class="muted small">A primeira leva privilegiou Pokémon de Kanto e Hoenn; a de 2025 foi para gerações que nunca tinham ganho megas, como Kalos e Paldea.</p>
  </div>
  <div class="card">
    <h2>Quanto uma Mega acrescenta</h2>
    <p>${pct(1 - fora100.length / megas.length)} das formas Mega e Primal somam exatamente <strong>100 pontos</strong> ao total da forma normal. As exceções:</p>
    ${Inputs.table(fora100.map((d) => ({nome: d.nome, base: d.base.total, total: d.total, ganho: d.ganho})), {header: {nome: "Forma", base: "Normal", total: "Mega", ganho: "Ganho"}, format: {ganho: (x) => sinal(x, num)}, sort: "ganho", reverse: true, select: false, rows: 8, layout: "auto"})}
  </div>
</div>

```js
const buscaMega = view(Inputs.search(megas, {placeholder: "Buscar mega…", format: (n) => `${num(n)} formas`}));
```

```js
Inputs.table(buscaMega.map((d) => ({...d, tipos: d, total_base: d.base.total})), {
  columns: ["nome", "tipos", "geracao", "geracao_base", "total_base", "total", ...STATS.map((s) => s.key)],
  header: {nome: "Forma", tipos: "Tipos", geracao: "Lançada", geracao_base: "Original", total_base: "Total normal", total: "Total", ...statNome},
  format: {tipos: badges, geracao: gen, geracao_base: gen},
  rows: 12,
  layout: "auto"
})
```

## Formas regionais

Versões de Pokémon antigos adaptadas a outra região (Alola, Galar, Hisui, Paldea), com tipos e atributos próprios.

```js
const regionais = pokemon.filter((d) => d.forma_tipo === "regional").map(comBase);
const regGanho = d3.median(regionais, (d) => d.ganho);
```

<div class="card">
  <h2>${num(regionais.length)} formas regionais: a mediana muda ${sinal(regGanho, num)} pontos em relação à forma original</h2>
  ${resize((width) => hbars(regionais.filter((d) => d.ganho !== 0), {width, y: "nome", x: "ganho", fill: (d) => (d.ganho > 0 ? pal.accent : pal.diverging.neg), format: (x) => sinal(x, num), maxMargin: 220}))}
  <p class="muted small">Só as ${num(regionais.filter((d) => d.ganho !== 0).length)} formas cujo total difere da original; as outras ${num(regionais.filter((d) => d.ganho === 0).length)} redistribuem os mesmos pontos. Em vermelho, formas mais fracas que a original.</p>
</div>

<h2 id="ajustes-retroativos">Ajustes retroativos</h2>

A PokeAPI guarda os atributos que cada Pokémon teve em gerações passadas. A geração 6 (X/Y) reforçou Pokémon como Pikachu, Butterfree e Alakazam; a 7 (Sun/Moon) fez outra rodada para Pokémon pouco usados. As poucas reduções são recentes e atingiram Pokémon dominantes em competições.

```js
const ajustes = pokemon
  .filter((d) => d.stats_mudaram_em != null)
  .map((d) => ({
    ...d,
    tipos: d,
    diff: d.total - d.total_lanc,
    mudou: STATS.filter((s) => d[s.key] !== d[`${s.key}_lanc`]).map((s) => `${s.nome} ${sinal(d[s.key] - d[`${s.key}_lanc`], num)}`).join(", ")
  }))
  .sort((a, b) => a.stats_mudaram_em - b.stats_mudaram_em || b.diff - a.diff);
const resumoAjustes = d3
  .rollups(ajustes, (v) => ({n: v.length, pontos: d3.sum(v, (d) => d.diff)}), (d) => d.stats_mudaram_em)
  .map(([geracao, s]) => ({geracao, ...s}));
```

<div class="grid grid-cols-4">
  ${resumoAjustes.map((d) => html`<div class="card"><h2>Na ${genLonga(d.geracao)}</h2><span class="big">${num(d.n)}</span><p class="muted">${d.n === 1 ? "Pokémon alterado" : "Pokémon alterados"}, ${sinal(d.pontos, num)} pontos no total</p></div>`)}
</div>

```js
Inputs.table(ajustes, {
  columns: ["nome", "tipos", "geracao", "stats_mudaram_em", "total_lanc", "total", "mudou"],
  header: {nome: "Pokémon", tipos: "Tipos", geracao: "Lançado", stats_mudaram_em: "Alterado", total_lanc: "Antes", total: "Hoje", mudou: "O que mudou"},
  format: {tipos: badges, geracao: gen, stats_mudaram_em: gen},
  rows: 20,
  layout: "auto"
})
```

<p class="muted small">Comparação com os atributos da geração de lançamento (da Gen 2 para Pokémon da Gen 1). Mudanças só nos pontos de esforço (EVs) que um Pokémon rende não contam.</p>
