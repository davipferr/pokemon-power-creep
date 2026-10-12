---
toc: false
---

# Power creep Pokémon

<p class="lede">Os Pokémon novos são mais fortes que os antigos? 1.025 espécies, 9 gerações e 919 golpes da PokeAPI, comparando só o que é comparável: um Pokémon comum totalmente evoluído com outro, nunca um lendário com um bebê.</p>

```js
import {parquet} from "./components/parquet.js";
import {num, num1, pct, PRINCIPAL, rows, sinal} from "./components/format.js";
import {palette} from "./components/palette.js";
import {genStrip, miniColumns, slopeText} from "./components/charts.js";

const pokemon = rows(await parquet(FileAttachment("data/pokemon.parquet")));
const golpes = rows(await parquet(FileAttachment("data/golpes.parquet")));
const tend = await FileAttachment("data/tendencias.json").json();
const qualidade = FileAttachment("data/qualidade.json").json();
```

```js
const pal = palette(dark);
const especies = pokemon.filter((d) => d.padrao);
const principal = especies.filter((d) => d.grupo === PRINCIPAL);
const medGen = (g, rows = principal, y = "total") => d3.median(rows.filter((d) => d.geracao === g), (d) => d[y]);
const t = tend.principal.total;
const ganho9 = t.inclinacao * 8; // Gen 1 -> Gen 9 along the fitted line
const iqr = d3.median(d3.range(1, 10), (g) => {
  const v = principal.filter((d) => d.geracao === g).map((d) => d.total);
  return d3.quantile(v, 0.75) - d3.quantile(v, 0.25);
});
```

<div class="card hero">
  <h2 class="hero-title">Existe power creep, mas ele é pequeno: um Pokémon comum totalmente evoluído ganha em média ${num1(t.inclinacao)} pontos de atributos por geração — cerca de ${num(ganho9)} pontos da 1ª à 9ª geração, menos da metade da diferença típica entre dois Pokémon da mesma geração (${num(iqr)}).</h2>
  ${resize((width) => genStrip(principal, {width, pal, trend: t, height: Math.min(420, Math.max(300, width * 0.42))}))}
  <p class="muted small">Cada ponto é um Pokémon comum totalmente evoluído (sem lendários, míticos, pseudolendários, Ultra Feras e Paradoxos), com os atributos de hoje. Barra azul: metade central da geração; círculo: mediana; linha tracejada: tendência linear, ${slopeText(t)}. A geração explica só ${pct(t.r2)} da variação do total. <a href="./geracoes">Ver todos os grupos →</a></p>
</div>

```js
// Card data.
const tardias = principal.filter((d) => d.evolucao_tardia);
const nativas = principal.filter((d) => !d.evolucao_tardia);
const premio = d3.median(tardias, (d) => d.total) - d3.median(nativas, (d) => d.total);
const megas = pokemon.filter((d) => d.forma_tipo === "mega");
const megasGen = d3.rollups(megas, (v) => v.length, (d) => d.geracao).map(([geracao, n]) => ({geracao, n}));
const dano = golpes.filter((d) => !d.gimmick && d.classe !== "Status" && d.poder_lanc != null);
const forte = d3
  .rollups(dano, (v) => d3.mean(v, (d) => d.poder_lanc >= 100), (d) => d.geracao)
  .map(([geracao, p]) => ({geracao, p}))
  .sort((a, b) => a.geracao - b.geracao);
const buffs = especies.filter((d) => d.stats_mudaram_em != null && d.total > d.total_lanc);
const buffGen = d3.rollups(buffs, (v) => v.length, (d) => d.stats_mudaram_em).map(([geracao, n]) => ({geracao, n}));
const tardiaGen = d3.rollups(tardias, (v) => v.length, (d) => d.geracao).map(([geracao, n]) => ({geracao, n}));
const forteRecente = d3.mean(dano.filter((d) => d.geracao >= 8), (d) => d.poder_lanc >= 100);
```

<div class="grid grid-cols-4">
  <a class="card card-link" href="./evolucoes">
    <h2>Evoluções tardias</h2>
    <span class="big">${sinal(premio, num)} pontos</span>
    <p class="muted">${num(tardias.length)} evoluções novas de linhas antigas (Magmortar, Togekiss…) têm mediana acima das criadas junto com a linha</p>
    ${resize((width) => miniColumns(tardiaGen, {width, x: "geracao", y: "n", pal, highlight: (d) => d.geracao === 4, title: (d) => `Gen ${d.geracao}: ${d.n} evoluções tardias`}))}
    <p class="muted small">Quantas por geração; em azul, Gen 4, a recordista</p>
  </a>
  <a class="card card-link" href="./golpes">
    <h2>Golpes</h2>
    <span class="big">${pct(forte[0].p)} → ${pct(forteRecente)}</span>
    <p class="muted">dos golpes de dano novos têm poder 100 ou mais (Gen 1 → Gen 8–9, poder no lançamento)</p>
    ${resize((width) => miniColumns(forte, {width, x: "geracao", y: "p", pal, highlight: (d) => d.geracao >= 8, title: (d) => `Gen ${d.geracao}: ${pct(d.p)} com poder ≥ 100`}))}
    <p class="muted small">Os golpes inflacionaram mais que os atributos</p>
  </a>
  <a class="card card-link" href="./formas">
    <h2>Megaevoluções</h2>
    <span class="big">${num(megas.length)}</span>
    <p class="muted">formas Mega, cada uma com ~100 pontos a mais que a forma normal; ${num(megasGen.find((d) => d.geracao === 9)?.n ?? 0)} chegaram com Legends: Z-A (2025)</p>
    ${resize((width) => miniColumns(d3.range(1, 10).map((g) => ({geracao: g, n: megasGen.find((d) => d.geracao === g)?.n ?? 0})), {width, x: "geracao", y: "n", pal, highlight: (d) => d.geracao === 9, title: (d) => `Gen ${d.geracao}: ${d.n} megas`}))}
    <p class="muted small">Megas por geração em que foram lançadas</p>
  </a>
  <a class="card card-link" href="./formas#ajustes-retroativos">
    <h2>Ajustes retroativos</h2>
    <span class="big">${num(buffs.length)}</span>
    <p class="muted">Pokémon antigos ganharam atributos depois de lançados, quase todos nas gerações 6 e 7: o creep também corre para trás</p>
    ${resize((width) => miniColumns(d3.range(1, 10).map((g) => ({geracao: g, n: buffGen.find((d) => d.geracao === g)?.n ?? 0})), {width, x: "geracao", y: "n", pal, highlight: (d) => d.geracao >= 6 && d.geracao <= 7, title: (d) => `Gen ${d.geracao}: ${d.n} Pokémon reforçados`}))}
    <p class="muted small">Reforços por geração em que entraram em vigor</p>
  </a>
</div>

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Por que separar grupos?</h3>
    <p>A mediana de <em>todas</em> as espécies sobe de ${num(medGen(1, especies))} (Gen 1) para ${num(medGen(9, especies))} (Gen 9) — muito mais que a dos comuns totalmente evoluídos (${num(medGen(1))} → ${num(medGen(9))}). A diferença é composição: as gerações recentes têm mais lendários e Paradoxos e menos estágios intermediários. <a href="./geracoes#composicao">Veja a composição →</a></p>
  </div>
  <div class="card">
    <h3>Consulta SQL no navegador</h3>
    <p>Os mesmos arquivos Parquet que alimentam os gráficos podem ser consultados com SQL via <a href="./sql">DuckDB-WASM</a>, sem servidor. Procure seu Pokémon favorito no <a href="./pokemon">perfil</a>.</p>
  </div>
</div>

<p class="muted small">Dados gerados em ${new Date(qualidade.gerado_em).toLocaleString("pt-BR")}. <a href="./sobre">Metodologia e fontes</a>.</p>

<style>
.lede { font-size: 1.15rem; max-width: 52rem; color: var(--theme-foreground-muted); }
.card-link { text-decoration: none; color: inherit; transition: border-color 150ms, transform 150ms, box-shadow 150ms; }
.card-link:hover { border-color: var(--theme-foreground-focus); transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35); }
.card-link:focus-visible { outline: 2px solid var(--theme-foreground-focus); outline-offset: 2px; }
.card-link h2::after { content: "→"; display: inline-block; margin-left: 0.35em; color: var(--theme-foreground-focus); transition: transform 150ms; }
.card-link:hover h2::after { transform: translateX(3px); }
@media (prefers-reduced-motion: reduce) { .card-link, .card-link h2::after { transition: none; } .card-link:hover { transform: none; } }
.card-link svg { display: block; margin-top: 0.75rem; }
.card .big { font-size: 28px; }
.hero { padding: 1.5rem; }
.hero .hero-title { font: 600 clamp(19px, 2.4vw, 26px)/1.3 var(--serif); max-width: 52rem; margin-bottom: 1rem; color: var(--theme-foreground); }
</style>
