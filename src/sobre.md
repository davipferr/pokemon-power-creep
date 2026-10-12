---
title: Sobre os dados
---

# Sobre os dados

```js
import {num} from "./components/format.js";
const q = await FileAttachment("data/qualidade.json").json();
const manifesto = await FileAttachment("data/manifest.json").json();
```

Este é um site estático. Os dados são baixados e limpos **em tempo de build** por _data loaders_ em Python (Polars) do Observable Framework; o navegador recebe apenas arquivos Parquet/JSON prontos. Última geração: **${new Date(q.gerado_em).toLocaleString("pt-BR")}**.

## Fonte

A [PokeAPI](https://pokeapi.co) é uma API REST aberta, sem chave, mantida por voluntários. Ela serve um documento JSON por recurso, então o build lista cada tipo de recurso e baixa todos (em paralelo, com cache em disco de 30 dias):

| Recurso | Endpoint | O que usamos |
| --- | --- | --- |
| Espécies | `/pokemon-species` | Geração, lendário/mítico/bebê, de quem evolui |
| Pokémon e formas | `/pokemon` | Atributos e tipos atuais, `past_stats` e `past_types` (valores em gerações passadas), arte oficial |
| Formas | `/pokemon-form` | Em que jogo cada forma alternativa estreou; se é Mega |
| Grupos de versão | `/version-group` | Jogo → geração, e a ordem cronológica dos jogos |
| Tipos | `/type` | Tabela de efetividade atual e `past_damage_relations` |
| Golpes | `/move` | Geração, tipo, classe, poder, precisão e `past_values` |

São ${num(q.especies)} espécies, ${num(q.pokemon)} Pokémon contando as formas alternativas e ${num(q.golpes.total)} golpes.

## Quem é comparado com quem

Comparar um lendário da Gen 9 com um bebê da Gen 1 não diz nada sobre creep. Cada espécie recebe um **estágio evolutivo** (calculado seguindo `evolves_from_species` até a base da linha) e um **grupo**:

```js
Inputs.table(q.grupos, {header: {grupo: "Grupo", n: "Espécies"}, format: {n: num}, sort: null, select: false, layout: "auto"})
```

- **Lendário** e **Mítico**: as marcações da própria PokeAPI.
- **Ultra Fera** e **Paradoxo**: "quase lendários" que a API não marca; vêm de listas fixas em `pipeline/categorias.py`.
- **Pseudolendário**: derivado, não listado — último estágio de uma linha de três estágios com exatamente 600 pontos. A regra encontra exatamente os ${q.pseudolendarios.length} conhecidos: ${q.pseudolendarios.join(", ")}.
- **Comum, totalmente evoluído**: não evolui mais e não está em nenhum grupo acima. É o grupo principal das comparações. Inclui Pokémon de estágio único, como Tauros.
- **Comum, em evolução**: todo o resto (inclui bebês).

## Limpeza e armadilhas da API

- **Gerações em algarismos romanos.** A API usa `generation-iv`; o pipeline converte para 4.
- **Atributos de lançamento.** `past_stats` diz "até a geração X (inclusive), estes atributos tinham estes valores", listando só os que mudaram. O valor numa geração G é o do primeiro bloco com geração ≥ G que menciona o atributo; senão, o atual. O mesmo vale para `past_types`.
- **O "Especial" da Gen 1.** Na Gen 1 não havia Ataque e Defesa Especial separados, só "Especial". Para Pokémon da Gen 1, "no lançamento" usa os atributos da Gen 2, a primeira com seis atributos.
- **Mudanças só de EV.** `past_stats` também registra mudanças nos pontos de esforço que um Pokémon rende, com os mesmos atributos-base. Essas não contam como ajuste (${num(q.stats_alterados)} espécies tiveram atributos realmente alterados).
- **Formas.** Cada forma alternativa é um `/pokemon` próprio. A geração de uma forma é a do jogo em que estreou (`/pokemon-form` → `version_group` → geração), então as megas de Legends: Z-A (2025) contam como Gen 9. Gigantamax e Totem têm os mesmos atributos da forma normal. As análises por geração usam só a forma padrão de cada espécie.
- **Golpes de "truque".** Z-Moves (Gen 7, 1 PP) e Max Moves (Gen 8) são criados no meio da batalha e não se aprendem; ficam fora das análises de golpes (${num(q.golpes.gimmick)} golpes). Os golpes "sombrios" de Pokémon Colosseum (ids acima de 10.000) também ficam fora.
- **Poder no lançamento.** Cada item de `past_values` guarda o valor que o golpe tinha *antes* daquele jogo mudá-lo. O valor num jogo é o da primeira mudança feita depois dele; o jogo de referência é o primeiro da geração de estreia.
- **Nomes.** A PokeAPI não tem nomes em português, então os nomes de Pokémon e golpes estão em inglês (que no Brasil são, em geral, os mesmos). Os tipos foram traduzidos à mão.

## Medidas

- **Total de atributos (BST)**: soma dos seis atributos-base.
- **Tendência**: reta de mínimos quadrados do total contra o número da geração, com intervalo de confiança de 95 % para a inclinação (distribuição t). O R² diz quanto da variação do total a geração explica.
- **Especialização**: desvio-padrão dos seis atributos dividido pela média (coeficiente de variação).
- **Evolução tardia**: espécie lançada numa geração posterior à do primeiro estágio da sua linha (${num(q.evolucoes_tardias)} espécies).

## Limitações

- O total de atributos ignora habilidades, golpes que cada Pokémon aprende, tipos e mecânicas (Megas, Z-Moves, Dynamax, Terastal), que mudaram o jogo competitivo mais que os atributos.
- Grupos com poucas espécies (Míticos, Ultra Feras, pseudolendários) não comportam tendências confiáveis.
- A PokeAPI é mantida por voluntários: dados de jogos muito recentes podem chegar com atraso ou ser corrigidos depois.

${q.sem_arte.length ? html`<p class="muted small">${num(q.sem_arte.length)} formas não têm arte oficial na PokeAPI: ${q.sem_arte.join(", ")}.</p>` : ""}

## Versão dos dados

Cada build publica um manifesto com a versão do código, a data de download de cada índice da PokeAPI e a contagem de linhas de cada tabela. Ele também é publicado em `/manifest.json`, num endereço fixo, para comparar cada atualização com a anterior (${html`<a href=${FileAttachment("data/manifest.json").href}>ver o arquivo</a>`}).

<p class="muted">Código do pipeline: <code>${manifesto.codigo_pipeline}</code>${manifesto.commit ? html` · commit <a href=${`https://github.com/davipferr/pokemon-power-creep/commit/${manifesto.commit}`}><code>${manifesto.commit.slice(0, 7)}</code></a>` : ""}</p>

<p class="muted small">Pokémon e todos os nomes relacionados são marcas registradas da Nintendo, Game Freak e The Pokémon Company. Este é um projeto de fã, sem fins comerciais.</p>
