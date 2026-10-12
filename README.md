# Power creep Pokémon

A static data site asking **are newer Pokémon stronger than older ones?**, built from the **PokeAPI** with a Python pipeline (**Polars**) and **Observable Framework** (Observable Plot for charts, DuckDB-WASM for in-browser SQL). The site is in Portuguese.

Every API call happens **at build time** in Framework data loaders. The browser only downloads pre-cleaned Parquet/JSON files (plus official artwork, hotlinked from PokeAPI's sprite repository on the profile page).

| Page | What it shows |
|---|---|
| Início | The headline: base stat total (BST) of fully evolved, non-legendary Pokémon by generation, with a fitted trend and 95 % CI; cards for late evolutions, moves, megas, retroactive buffs |
| Atributos por geração | Any comparison group, today's or launch stats; median table per group; composition of each generation; how the Gen 6–7 buffs changed the trend |
| Evoluções tardias | New evolutions of older lines (Crobat, Magmortar, Kingambit…) vs. Pokémon created with their line |
| Formato dos atributos | Each stat's trend, specialisation (coefficient of variation), highest stat, physical vs. special |
| Megas, formas e ajustes | Mega/Primal forms (2013–14 and the 2025 Legends Z-A wave), regional forms, every retroactive stat change |
| Tipos | Type frequency per generation (at launch), dual-type share, Fairy retcons, the type chart and its past changes |
| Golpes | Power of new damaging moves per generation, status-move share, moves buffed or nerfed after launch |
| Perfil do Pokémon | One Pokémon or form: stats vs. same group and generation, percentile, evolution line, other forms |
| Consulta SQL | Free-form SQL over all Parquet files with DuckDB-WASM |
| Sobre os dados | Source, comparison groups, cleaning, measures, limitations |

## Findings (October 2026 data)

- **Creep exists but is small.** Fully evolved, non-legendary Pokémon gain **+2.9 BST per generation (95 % CI +1.2 to +4.6)**, about 23 points from Gen 1 to Gen 9. Generation explains only ~3 % of the variance; the typical spread *within* a generation is about 50 points.
- **The headline number depends on who you compare.** The median of *all* species rises from 405 (Gen 1) to 489 (Gen 9), mostly from composition: recent generations have more legendaries and Paradox Pokémon and fewer middle stages.
- **Late evolutions are a constant premium, not the trend.** New evolutions of older lines sit about 40 points above the rest, but they appear in almost every generation; without them the slope is still +2.8.
- **Old Pokémon were buffed.** Generations 6 and 7 raised the stats of 54 older Pokémon (+780 points in total). With launch stats, the slope is +3.4, so today's data understates the creep at the time of each release.
- **Moves crept more than stats.** The share of new damaging moves with power ≥ 100 went from 16 % (Gen 1) to about 33 % (Gen 8–9).
- **Designs didn't become more extreme.** The specialisation index has no trend.

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js ≥ 18. No API key needed.

```bash
uv sync          # Python env (polars, duckdb, httpx, pyarrow, pytest)
npm install      # Observable Framework
npm run dev      # http://127.0.0.1:3000
npm run build    # static site in dist/
```

The first build makes ~3,700 requests to PokeAPI (one JSON document per species, Pokémon, form, move, type and version group) and takes about **1–2 minutes** with 6 parallel workers. Responses are cached in `data_cache/` for 30 days (the resource indexes for 7, so new Pokémon show up), so later builds make no requests.

Knobs (environment variables):

| Variable | Default | Effect |
|---|---|---|
| `POKEAPI_WORKERS` | `6` | Parallel requests. PokeAPI has no published rate limit, but its fair-use policy asks for caching and moderation |
| `PPC_CACHE_DIR` | `data_cache` | Where raw responses and memoised frames live |

## Data source

[PokeAPI](https://pokeapi.co) v2, no key. Each frame is "list every resource, then fetch them all":

| Endpoint | Used for |
|---|---|
| `/pokemon-species` | Generation, legendary/mythical/baby flags, `evolves_from_species` |
| `/pokemon` | Base stats, types, `past_stats`, `past_types`, official artwork |
| `/pokemon-form` | The version group in which each alternate form debuted; `is_mega` |
| `/version-group` | Game → generation, and chronological order of games |
| `/type` | Type chart and `past_damage_relations` |
| `/move` | Generation, type, class, power, accuracy, `past_values` |

## How it's organised

```
pipeline/            Python package: one module per concern
  http.py            cached GET (sharded on disk), retries, bounded thread pool
  clean.py           ids from URLs, roman generations, form kinds, values "as of" a past generation
  pokeapi.py         PokeAPI client: pure parse_* functions + fetchers
  categorias.py      evolution stages, line roots, comparison groups (legendary, pseudo-legendary…)
  creep.py           the measures: OLS trend with 95 % CI, specialisation, per-generation summaries
  frames.py          joined frames memoised as Parquet, shared across loaders
  manifest.py        build manifest + comparison with the live site (CI job summary)
  schema.py          fail fast when an API response changes shape
  io.py              stdout writers; casts int64 -> int32 so JS doesn't get BigInt
src/data/*.py        Framework data loaders (thin; run via `uv run`, see observablehq.config.js)
src/components/      formatting (pt-BR), palette, charts, type badges
src/*.md             pages
tests/               offline tests on trimmed real API responses and synthetic data
```

## Messy-data problems handled

- **Who to compare.** A Gen 9 legendary vs. a Gen 1 baby says nothing about creep. Every species gets an evolution stage (walking `evolves_from_species` to the root) and a group. Legendary/mythical come from the API; Ultra Beasts and Paradox Pokémon from fixed lists; **pseudo-legendaries are derived** (last stage of a three-stage line with exactly 600 BST), and the rule finds exactly the 10 known ones.
- **Stats at launch.** `past_stats` means "up to and including generation X, these stats had these values" and lists only the stats that changed. The value at generation G is the earliest block ≥ G mentioning the stat, else today's. Same for `past_types` (Clefable was Normal until Gen 5).
- **Gen 1's "Special".** Gen 1 had one Special stat instead of Sp. Atk/Sp. Def, so Gen 1 Pokémon are measured with Gen 2 stats.
- **EV-only changes.** `past_stats` also records effort-value changes with identical base stats (Blissey, Duskull…); those don't count as buffs.
- **Forms.** Each alternate form is its own `/pokemon`. Its generation is the one of the game it debuted in (`/pokemon-form` → `version_group` → generation), so the 2025 Legends Z-A megas are Gen 9. Form kind comes from the slug (`-mega`, `-primal`, `-gmax`, `-totem`, regional suffixes); "meganium" is not a Mega because slugs are split on hyphens.
- **Move history.** Each `past_values` entry holds the value *before* that version group changed it (null = unchanged then). The value at a game is the one from the earliest later change.
- **Gimmick moves.** Z-Moves (Gen 7, 1 PP) and Max/G-Max Moves (Gen 8) are excluded from move statistics; Colosseum's shadow moves (ids > 10,000) too.
- **No Portuguese names.** PokeAPI has no pt-BR names; Pokémon and moves keep their English names, types are translated by hand.

## Refreshing data

Framework caches each loader's output in `src/.observablehq/cache` and only reruns a loader when its own file changes. After changing code in `pipeline/`, run `npm run clean` (it clears the loader cache and the memoised frames in `data_cache/frames`, but keeps raw responses). Delete `data_cache/` to re-download everything. The GitHub Actions workflow rebuilds monthly and on every push, restoring `data_cache/` from the Actions cache.

## Tests

```bash
uv run pytest
```

Pokémon and all related names are trademarks of Nintendo, Game Freak and The Pokémon Company. This is a non-commercial fan project.
