import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {gen, genLonga, num, num1} from "./format.js";

/** Cut a label to `n` characters with an ellipsis (the tooltip keeps the full text). */
export function truncate(text, n) {
  const s = String(text ?? "");
  return s.length > n ? `${s.slice(0, Math.max(1, n - 1)).trimEnd()}…` : s;
}

/** Left margin for bar labels: up to `max`, and at most ~45 % of a narrow chart. */
export function labelMargin(width, max = 200) {
  return Math.round(Math.max(72, Math.min(max, width * 0.45)));
}

/** Deterministic jitter in [-1, 1] from an integer id (no reshuffling on re-render). */
export const jitter = (id) => (((Math.sin(id * 12.9898) * 43758.5453) % 1) + 1) % 1 * 2 - 1;

/**
 * Horizontal bars, sorted, with the value printed at the end of each bar instead
 * of an x axis. Labels on the left are truncated to fit the (responsive) margin.
 */
export function hbars(data, {width, y, x = "valor", fill, format = num, limit, maxMargin = 200, channels, tipFormat} = {}) {
  const yOf = typeof y === "function" ? y : (d) => d[y];
  const rows = [...data].filter((d) => d[x] != null).sort((a, b) => b[x] - a[x]).slice(0, limit ?? Infinity);
  const marginLeft = labelMargin(width, maxMargin);
  const chars = Math.floor((marginLeft - 8) / 5.6); // ~5.6 px per character at Plot's 10px
  return Plot.plot({
    width,
    height: rows.length * 26 + 12,
    marginLeft,
    marginRight: 56,
    marginTop: 4,
    marginBottom: 4,
    x: {axis: null},
    y: {label: null, tickSize: 0, tickFormat: (d) => truncate(d, chars), domain: rows.map(yOf)},
    marks: [
      Plot.barX(rows, {y: yOf, x, fill, channels, rx2: 4, insetTop: 2, insetBottom: 2, tip: {format: {x: tipFormat ?? format, fill: false}}}),
      Plot.text(rows, {y: yOf, x, text: (d) => format(d[x]), dx: 5, textAnchor: "start", fill: "currentColor", fontSize: 11}),
      Plot.ruleX([0], {strokeOpacity: 0.4})
    ]
  });
}

/**
 * One dot per Pokémon (jittered within its generation), the interquartile range
 * as a thick rule and the median as a tick; optionally the fitted trend line.
 *
 * @param data   rows with geracao, pokemon_id, nome and the `y` field
 * @param opts   {width, y, pal, height, trend: {intercepto, inclinacao}, label,
 *                highlight(d) -> bool (accent dots; others muted), domain}
 */
export function genStrip(data, {width, y = "total", pal, height = 380, trend, label = "Total de atributos (BST)", highlight, domain} = {}) {
  const stats = d3
    .rollups(data, (v) => ({q1: d3.quantile(v, 0.25, (d) => d[y]), med: d3.median(v, (d) => d[y]), q3: d3.quantile(v, 0.75, (d) => d[y]), n: v.length}), (d) => d.geracao)
    .map(([geracao, s]) => ({geracao, ...s}))
    .sort((a, b) => a.geracao - b.geracao);
  const gens = d3.range(1, 10);
  const dotFill = highlight ? (d) => (highlight(d) ? pal.accent : pal.muted) : pal.muted;
  return Plot.plot({
    width,
    height,
    marginLeft: 44,
    marginBottom: 34,
    // Explicitly linear: generations are positions here (dots are jittered
    // around them), and an ordinal mark would silently turn this into a band
    // scale with no ticks.
    x: {type: "linear", domain: [0.5, 9.5], ticks: gens, tickFormat: width < 560 ? (g) => g : gen, label: null, tickSize: 0},
    y: {grid: true, label, domain, nice: true},
    marks: [
      Plot.dot(data, {
        x: (d) => d.geracao + jitter(d.pokemon_id) * 0.3,
        y,
        r: 2.6,
        fill: dotFill,
        fillOpacity: 0.75,
        channels: {Pokémon: "nome", Geração: (d) => genLonga(d.geracao)},
        tip: {format: {x: false, fill: false, y: num}}
      }),
      Plot.ruleX(stats, {x: "geracao", y1: "q1", y2: "q3", stroke: pal.accent, strokeWidth: 6, strokeLinecap: "round", strokeOpacity: 0.55}),
      // Median as a short horizontal bar (ruleY with numeric x1/x2; tickY would need an ordinal x).
      Plot.ruleY(stats, {y: "med", x1: (d) => d.geracao - 0.22, x2: (d) => d.geracao + 0.22, stroke: "currentColor", strokeWidth: 2.5}),
      Plot.dot(stats, {x: "geracao", y: "med", r: 4.5, fill: "var(--theme-background)", stroke: "currentColor", strokeWidth: 2, title: (d) => `${genLonga(d.geracao)}\nmediana ${num(d.med)} · metade entre ${num(d.q1)} e ${num(d.q3)}\n${num(d.n)} Pokémon`}),
      trend ? Plot.line([1, 9], {x: (g) => g, y: (g) => trend.intercepto + trend.inclinacao * g, stroke: pal.categorical[1], strokeWidth: 2, strokeDasharray: "5 4"}) : null
    ]
  });
}

/**
 * Compact chart for a stat tile: no axes, a hover tooltip, the de-emphasis hue
 * with the `highlight(d)` items in the accent.
 */
export function miniColumns(data, {width, x, y, highlight = () => false, pal, title, height = 64}) {
  return Plot.plot({
    width,
    height,
    margin: 0,
    marginTop: 4,
    x: {axis: null, type: "band", padding: 0.2},
    y: {axis: null},
    marks: [
      Plot.barY(data, {x, y, fill: (d) => (highlight(d) ? pal.accent : pal.muted), ry2: 2, tip: false}),
      Plot.tip(data, Plot.pointerX({x, y, title}))
    ]
  });
}

/** "+2,9 pontos por geração (IC 95 %: +1,2 a +4,6)" */
export function slopeText(t, unidade = "pontos") {
  const s = (x) => `${x >= 0 ? "+" : "−"}${num1(Math.abs(x))}`;
  return `${s(t.inclinacao)} ${unidade} por geração (IC 95 %: ${s(t.ic95[0])} a ${s(t.ic95[1])})`;
}
