---
title: Consulta SQL
---

# Consulta SQL no navegador

Os arquivos Parquet que alimentam o site são carregados num **DuckDB rodando no seu navegador** (DuckDB-WASM). Nada é enviado a servidor algum — faça as suas próprias comparações.

```js
import {parquet} from "./components/parquet.js";
// Tables are decoded to Arrow first (parquet-wasm, the same reader the other pages
// use) and copied into DuckDB, instead of letting DuckDB-WASM read the Parquet files
// itself. That avoids two problems: its HTTP range requests break on GitHub Pages,
// which gzips .parquet responses, and its bundled DuckDB 1.1 can't parse the footer
// of files written by Polars 2.
const db = DuckDBClient.of({
  pokemon: parquet(FileAttachment("data/pokemon.parquet")),
  geracoes: parquet(FileAttachment("data/geracoes.parquet")),
  golpes: parquet(FileAttachment("data/golpes.parquet")),
  tipos: parquet(FileAttachment("data/tipos.parquet"))
});
```

```js
const exemplos = new Map([
  ["Os mais fortes de cada geração (sem lendários)", `SELECT geracao, nome, total, grupo
FROM pokemon
WHERE padrao AND grupo NOT IN ('Lendário', 'Mítico')
QUALIFY row_number() OVER (PARTITION BY geracao ORDER BY total DESC) = 1
ORDER BY geracao`],
  ["Mediana do total por geração e grupo", `SELECT geracao, grupo, count(*) AS n, median(total) AS mediana
FROM pokemon
WHERE padrao
GROUP BY ALL
ORDER BY grupo, geracao`],
  ["Iniciais: o último estágio de cada geração", `-- Starters are the first three species of each regional Pokédex; by national id:
SELECT geracao, nome, total, velocidade
FROM pokemon
WHERE padrao AND final AND estagio = 3
  AND base_id IN (1, 4, 7, 152, 155, 158, 252, 255, 258, 387, 390, 393,
                  495, 498, 501, 650, 653, 656, 722, 725, 728, 810, 813, 816, 906, 909, 912)
ORDER BY geracao, base_id`],
  ["Golpes mais fortes que estrearam em cada geração", `SELECT geracao, golpe_nome, tipo, classe, poder_lanc
FROM golpes
WHERE NOT gimmick AND poder_lanc IS NOT NULL
QUALIFY rank() OVER (PARTITION BY geracao ORDER BY poder_lanc DESC) = 1
ORDER BY geracao`],
  ["Quanto cada Mega acrescenta, atributo por atributo", `SELECT m.nome,
       m.ataque - b.ataque         AS ataque,
       m.atq_esp - b.atq_esp       AS atq_esp,
       m.defesa - b.defesa         AS defesa,
       m.velocidade - b.velocidade AS velocidade,
       m.total - b.total           AS total
FROM pokemon m
JOIN pokemon b ON b.especie_id = m.especie_id AND b.padrao
WHERE m.forma_tipo = 'mega'
ORDER BY velocidade DESC`]
]);
const exemplo = view(Inputs.select(exemplos, {label: "Exemplo"}));
```

```js
const consulta = view(Inputs.textarea({value: exemplo, rows: 10, submit: "Executar", spellcheck: false, monospace: true, width: "100%"}));
```

```js
// DuckDB returns BIGINT/HUGEINT (e.g. count(*)) as JavaScript BigInt; convert to
// Number so formatting and charts work.
const resultado = await db.query(consulta).then(
  (r) => ({rows: Array.from(r, (row) => Object.fromEntries(Object.entries(row).map(([k, v]) => [k, typeof v === "bigint" ? Number(v) : v])))}),
  (error) => ({error})
);
```

${resultado.error ? html`<div class="caution"><strong>Erro:</strong> <code>${resultado.error.message}</code></div>` : html`<p class="muted">${resultado.rows.length.toLocaleString("pt-BR")} linhas</p>`}

```js
resultado.error ? null : Inputs.table(resultado.rows, {rows: 20, locale: "pt-BR"})
```

## Tabelas disponíveis

```js
const esquema = await Promise.all(
  ["pokemon", "geracoes", "golpes", "tipos"].map(async (t) => ({
    tabela: t,
    linhas: Number(Array.from(await db.query(`SELECT count(*) AS n FROM ${t}`))[0].n),
    colunas: Array.from(await db.query(`DESCRIBE ${t}`), (c) => `${c.column_name} (${c.column_type.toLowerCase()})`).join(", ")
  }))
);
```

```js
Inputs.table(esquema, {format: {linhas: (n) => n.toLocaleString("pt-BR")}, width: {tabela: 110, linhas: 80}, layout: "auto"})
```

<div class="tip"><code>pokemon</code> tem uma linha por forma; use <code>WHERE padrao</code> para ficar com uma linha por espécie. Colunas terminadas em <code>_lanc</code> são os valores no lançamento. Tipos estão em inglês (<code>fire</code>, <code>water</code>…), como na PokeAPI. <code>tipos.ate_geracao</code> nulo é a tabela de hoje.</div>
