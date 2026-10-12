---
title: Perfil do Pokémon
toc: false
---

# Perfil do Pokémon

```js
import {parquet} from "./components/parquet.js";
import {gen, genLonga, num, pct, rows, sinal, STATS} from "./components/format.js";
import {palette} from "./components/palette.js";
import {badges} from "./components/tipos.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const pal = palette(dark);
const especies = pokemon.filter((d) => d.padrao);
const ordenados = [...pokemon].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
```

```js
const escolhido = view(
  Inputs.search(ordenados, {placeholder: "Buscar Pokémon ou forma (ex.: Garchomp, Mega Lucario)…", format: (n) => `${num(n)} resultados`, width: 420})
);
```

```js
const p = view(
  Inputs.select(escolhido.length ? escolhido : ordenados, {
    label: "Pokémon",
    format: (d) => d.nome,
    value: (escolhido.length ? escolhido : ordenados).find((d) => d.slug === "garchomp") ?? (escolhido.length ? escolhido : ordenados)[0]
  })
);
```

```js
// Peers: same comparison group and generation (default forms).
const pares = especies.filter((d) => d.grupo === p.grupo && d.geracao === p.geracao_especie);
const grupoTodo = especies.filter((d) => d.grupo === p.grupo);
const percentil = d3.mean(grupoTodo, (d) => d.total < p.total) + d3.mean(grupoTodo, (d) => d.total === p.total) / 2;
const barras = STATS.map((s) => ({stat: s.nome, valor: p[s.key], lanc: p[`${s.key}_lanc`], mediana: d3.median(pares, (d) => d[s.key])}));
const linha = especies.filter((d) => d.base_id === p.base_id).sort((a, b) => a.estagio - b.estagio || a.especie_id - b.especie_id);
const formas = pokemon.filter((d) => d.especie_id === p.especie_id && d.pokemon_id !== p.pokemon_id);
const pesoForma = {padrão: "Forma padrão", mega: "Mega", primal: "Primal", regional: "Forma regional", gigantamax: "Gigantamax", totem: "Totem", outra: "Forma alternativa"};
```

<div class="grid grid-cols-3">
  <div class="card perfil">
    ${p.arte ? html`<img src=${p.arte} alt=${`Arte oficial de ${p.nome}`} width="220" height="220" loading="lazy">` : ""}
    <h2 class="nome">${p.nome}</h2>
    <p>${badges(p)}</p>
    <p class="muted">${pesoForma[p.forma_tipo]} · lançado na ${genLonga(p.geracao)}<br>${p.grupo}${p.evolucao_tardia ? html` · <a href="./evolucoes">evolução tardia</a> de uma linha da ${gen(p.geracao_linha)}` : ""}</p>
  </div>
  <div class="card">
    <h2>Total de atributos</h2>
    <span class="big">${num(p.total)}</span>
    <p class="muted">${sinal(p.total - d3.median(pares, (d) => d.total), num)} em relação à mediana dos ${num(pares.length)} Pokémon do grupo "${p.grupo}" da ${gen(p.geracao_especie)}</p>
    <p class="muted">Maior que ${pct(percentil)} do grupo, somando todas as gerações</p>
    ${p.stats_mudaram_em != null ? html`<p><strong>Atributos alterados na ${genLonga(p.stats_mudaram_em)}</strong>: total ${num(p.total_lanc)} → ${num(p.total)}.</p>` : ""}
    ${p.tipo1 !== p.tipo1_lanc || p.tipo2 !== p.tipo2_lanc ? html`<p><strong>Tipos no lançamento:</strong> ${badges({tipo1: p.tipo1_lanc, tipo2: p.tipo2_lanc})}</p>` : ""}
  </div>
  <div class="card">
    <h2>Atributos × pares</h2>
    ${resize((width) => Plot.plot({
      width,
      height: 230,
      marginLeft: 76,
      marginRight: 36,
      x: {domain: [0, Math.max(160, d3.max(barras, (d) => Math.max(d.valor, d.mediana)) + 10)], axis: null},
      y: {domain: STATS.map((s) => s.nome), label: null, tickSize: 0},
      marks: [
        Plot.barX(barras, {y: "stat", x: "valor", fill: pal.accent, rx2: 4, insetTop: 4, insetBottom: 4, tip: {format: {fill: false}}, channels: {"Mediana dos pares": "mediana"}}),
        Plot.tickX(barras, {y: "stat", x: "mediana", stroke: "currentColor", strokeWidth: 2}),
        Plot.text(barras, {y: "stat", x: "valor", text: (d) => num(d.valor), dx: 5, textAnchor: "start", fill: "currentColor", fontSize: 11})
      ]
    }))}
    <p class="muted small">Barra: atributo do Pokémon; traço: mediana do mesmo grupo e geração.</p>
  </div>
</div>

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Linha evolutiva</h2>
    ${Inputs.table(linha.map((d) => ({...d, tipos: d})), {columns: ["nome", "tipos", "estagio", "geracao", "total"], header: {nome: "Pokémon", tipos: "Tipos", estagio: "Estágio", geracao: "Lançado", total: "Total"}, format: {tipos: badges, geracao: gen}, sort: null, select: false, layout: "auto"})}
  </div>
  <div class="card">
    <h2>Outras formas da espécie</h2>
    ${formas.length ? Inputs.table(formas.map((d) => ({...d, tipos: d, tipo: pesoForma[d.forma_tipo]})), {columns: ["nome", "tipo", "tipos", "geracao", "total"], header: {nome: "Forma", tipo: "Tipo de forma", tipos: "Tipos", geracao: "Lançada", total: "Total"}, format: {tipos: badges, geracao: gen}, sort: null, select: false, layout: "auto"}) : html`<p class="muted">Nenhuma.</p>`}
  </div>
</div>

<p class="muted small">Arte oficial servida pelo repositório de sprites da PokeAPI no GitHub (a única coisa que o navegador busca fora deste site).</p>

<style>
.perfil { text-align: center; }
.perfil img { max-width: 100%; height: auto; }
.perfil .nome { font: 700 26px/1.2 var(--serif); margin: 0.25rem 0; }
</style>
