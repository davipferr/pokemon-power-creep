import {html} from "npm:htl";

// The 18 types in the games' canonical order, with Portuguese names and the
// canonical type colours (used only on labelled badges, never as chart series).
export const TIPOS = [
  {key: "normal", nome: "Normal", cor: "#9a9a78"},
  {key: "fire", nome: "Fogo", cor: "#d9652b"},
  {key: "water", nome: "Água", cor: "#4f7fe0"},
  {key: "grass", nome: "Planta", cor: "#5e9e3a"},
  {key: "electric", nome: "Elétrico", cor: "#c9a400"},
  {key: "ice", nome: "Gelo", cor: "#5fb3b3"},
  {key: "fighting", nome: "Lutador", cor: "#b0342c"},
  {key: "poison", nome: "Venenoso", cor: "#94429a"},
  {key: "ground", nome: "Terrestre", cor: "#b8953e"},
  {key: "flying", nome: "Voador", cor: "#8a76d6"},
  {key: "psychic", nome: "Psíquico", cor: "#e04a7a"},
  {key: "bug", nome: "Inseto", cor: "#8a9a1c"},
  {key: "rock", nome: "Pedra", cor: "#a38c35"},
  {key: "ghost", nome: "Fantasma", cor: "#6a5591"},
  {key: "dragon", nome: "Dragão", cor: "#6a3cf0"},
  {key: "dark", nome: "Sombrio", cor: "#6b5547"},
  {key: "steel", nome: "Aço", cor: "#8f8fab"},
  {key: "fairy", nome: "Fada", cor: "#d0789a"}
];
export const tipoNome = Object.fromEntries(TIPOS.map((t) => [t.key, t.nome]));
export const tipoCor = Object.fromEntries(TIPOS.map((t) => [t.key, t.cor]));

export const badge = (t) => (t ? html`<span class="tipo" style=${{background: tipoCor[t]}}>${tipoNome[t]}</span>` : "");
export const badges = (d) => html`${badge(d.tipo1)}${badge(d.tipo2)}`;
