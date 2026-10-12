import * as d3 from "npm:d3";

// Brazilian number conventions: "." for thousands, "," for decimals.
export const locale = d3.formatLocale({decimal: ",", thousands: ".", grouping: [3], currency: ["", ""]});

const int = locale.format(",.0f");
const dec1 = locale.format(",.1~f"); // "1,5" but "20", not "20,0"
const pct0 = locale.format(".0%");
const pct1 = locale.format(".1%");

export const num = (x) => (x == null || Number.isNaN(x) ? "–" : int(x));
export const num1 = (x) => (x == null || Number.isNaN(x) ? "–" : dec1(x));
export const pct = (x) => (x == null || Number.isNaN(x) ? "–" : pct0(x));
export const pctd = (x) => (x == null || Number.isNaN(x) ? "–" : pct1(x));
/** Signed points: "+2,9" / "−1,2" (true minus sign). */
export const sinal = (x, f = num1) => (x == null || Number.isNaN(x) ? "–" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${f(Math.abs(x))}`);

/** Arrow table -> array of plain objects (Plot/D3 want plain objects). */
export function rows(table) {
  return Array.from(table, (r) => r.toJSON());
}

/** Result count for Inputs.search (its default label is English). */
export const resultados = (n) => (n === 0 ? "nenhum resultado" : `${int(n)} resultado${n === 1 ? "" : "s"}`);

export const GERACOES = {
  1: {regiao: "Kanto", ano: 1996},
  2: {regiao: "Johto", ano: 1999},
  3: {regiao: "Hoenn", ano: 2002},
  4: {regiao: "Sinnoh", ano: 2006},
  5: {regiao: "Unova", ano: 2010},
  6: {regiao: "Kalos", ano: 2013},
  7: {regiao: "Alola", ano: 2016},
  8: {regiao: "Galar", ano: 2019},
  9: {regiao: "Paldea", ano: 2022}
};
/** "Gen 4" axis label; the long form adds the region: "Gen 4 · Sinnoh". */
export const gen = (g) => `Gen ${g}`;
export const genLonga = (g) => `Gen ${g} · ${GERACOES[g]?.regiao ?? ""}`;

export const STATS = [
  {key: "hp", nome: "HP"},
  {key: "ataque", nome: "Ataque"},
  {key: "defesa", nome: "Defesa"},
  {key: "atq_esp", nome: "Atq. Esp."},
  {key: "def_esp", nome: "Def. Esp."},
  {key: "velocidade", nome: "Velocidade"}
];
export const statNome = Object.fromEntries(STATS.map((s) => [s.key, s.nome]));

export const PRINCIPAL = "Comum, totalmente evoluído";
export const GRUPOS = ["Comum, totalmente evoluído", "Comum, em evolução", "Pseudolendário", "Ultra Fera", "Paradoxo", "Lendário", "Mítico"];
