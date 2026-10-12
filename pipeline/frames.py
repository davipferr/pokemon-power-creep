"""Cleaned, shared frames, memoised as Parquet in the cache directory.

The raw responses are already cached by ``http``; this layer caches the joined
and derived tables so several loaders can share them without re-parsing ~3,700
JSON files each.

File names carry a hash of the ``pipeline`` source, so editing any cleaning
code invalidates every memoised frame — including ones restored from the CI
cache, which may be younger than ``max_age`` but built by older code.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import polars as pl

from . import categorias, creep, pokeapi
from .clean import STAT_COLS, display_name, form_kind, stats_at, types_at, value_at
from .http import CACHE_DIR, log
from .schema import require_columns

FRAMES = CACHE_DIR / "frames"


def _code_version() -> str:
    """Short hash of every module in this package (line endings normalised, so a
    Windows checkout and CI agree)."""
    h = hashlib.sha256()
    for src in sorted(Path(__file__).parent.glob("*.py")):
        h.update(src.name.encode())
        h.update(src.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


CODE_VERSION = _code_version()


def memo(name: str, build: Callable[[], pl.DataFrame], max_age: timedelta = timedelta(days=1)) -> pl.DataFrame:
    path = FRAMES / f"{name}-{CODE_VERSION}.parquet"
    if path.exists() and time.time() - path.stat().st_mtime < max_age.total_seconds():
        return pl.read_parquet(path)
    t0 = time.time()
    df = build()
    FRAMES.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.part")
    df.write_parquet(tmp)
    tmp.replace(path)
    # Drop copies built by other code versions.
    for old in FRAMES.glob(f"{name}-*.parquet"):
        if old != path:
            old.unlink(missing_ok=True)
    log(f"frame {name}: {df.height:,} rows in {time.time() - t0:.1f}s")
    return df


def version_groups() -> pl.DataFrame:
    return memo("version_groups", pokeapi.version_groups)


def especies() -> pl.DataFrame:
    def build() -> pl.DataFrame:
        df = require_columns(pokeapi.species(), ["especie_id", "evolui_de", "geracao_especie"], "PokeAPI species", min_rows=1000)
        return categorias.with_stages(df)

    return memo("especies", build)


def _launch_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Stats and types as they were when each Pokémon/form was introduced.

    Gen 1 had a single "special" stat, so Gen 1 Pokémon are measured with their
    Gen 2 stats (the first six-stat generation).
    """
    rows = []
    for r in df.select("pokemon_id", "geracao", *STAT_COLS, "tipo1", "tipo2", "past_stats", "past_types").iter_rows(named=True):
        ref = max(r["geracao"], 2)
        past: dict[int, dict[str, int]] = {}
        for p in r["past_stats"] or []:
            past.setdefault(p["geracao"], {})[p["stat"]] = p["valor"]
        current = {c: r[c] for c in STAT_COLS}
        blocks = sorted(past.items())
        launch = stats_at(current, blocks, ref)
        # past_stats also records EV-yield changes with identical base stats;
        # only blocks whose base stats differ from the next generation's count.
        changed_until = [g for g, _ in blocks if g >= ref and stats_at(current, blocks, g) != stats_at(current, blocks, g + 1)]
        types = types_at(
            [t for t in (r["tipo1"], r["tipo2"]) if t],
            [(p["geracao"], p["tipos"]) for p in r["past_types"] or []],
            r["geracao"],
        )
        rows.append(
            {
                "pokemon_id": r["pokemon_id"],
                **{f"{c}_lanc": launch[c] for c in STAT_COLS},
                # Stats changed in the generation after the last "past" block.
                "stats_mudaram_em": max(changed_until) + 1 if changed_until else None,
                "tipo1_lanc": types[0],
                "tipo2_lanc": types[1] if len(types) > 1 else None,
            }
        )
    return df.join(pl.DataFrame(rows, schema_overrides={"stats_mudaram_em": pl.Int32}), on="pokemon_id", how="left")


def pokemon() -> pl.DataFrame:
    """One row per /pokemon (default forms and alternate forms), with species
    attributes, comparison group, current and launch stats."""

    def build() -> pl.DataFrame:
        sp = especies()
        vg = version_groups()
        pk = require_columns(pokeapi.pokemon(), ["pokemon_id", "especie_id", "padrao", *STAT_COLS], "PokeAPI pokemon", min_rows=1000)

        alt_urls = pk.filter(~pl.col("padrao"), pl.col("forma_url").is_not_null())["forma_url"].to_list()
        fm = pokeapi.forms(alt_urls).join(vg.select(pl.col("vg").alias("forma_vg"), pl.col("geracao").alias("geracao_forma")), on="forma_vg", how="left")

        df = (
            pk.join(sp, on="especie_id", how="left")
            .join(fm, on="pokemon_id", how="left")
            .with_columns(
                pl.coalesce(pl.when(~pl.col("padrao")).then("geracao_forma"), "geracao_especie").cast(pl.Int32).alias("geracao"),
                pl.sum_horizontal(STAT_COLS).alias("total"),
                pl.col("mega").fill_null(False),
            )
        )
        df = _launch_columns(df).with_columns(pl.sum_horizontal([f"{c}_lanc" for c in STAT_COLS]).alias("total_lanc"))

        cols = df.select("slug", "especie_slug", "especie_nome", "padrao", "forma_nome", "mega").to_dicts()
        df = df.with_columns(
            pl.Series("nome", [display_name(**r) for r in cols], pl.String),
            pl.Series("forma_tipo", [form_kind(r["slug"], r["padrao"], r["mega"]) for r in cols], pl.String),
        )

        # Comparison group is a species property, decided by its default form.
        grupos = df.filter(pl.col("padrao")).select("especie_id", "especie_slug", "lendario", "mitico", "bebe", "estagio", "final", "total")
        grupos = grupos.with_columns(categorias.grupo_expr()).select("especie_id", "grupo")
        df = df.join(grupos, on="especie_id", how="left")
        df = creep.with_shape(df)

        # Late evolutions: a species added generations after its line started
        # (Magmortar, Gen 4, evolves from Gen 1's Magmar). ``total_pre`` is the
        # pre-evolution's total, to measure how much the new stage adds.
        default_total = df.filter(pl.col("padrao")).select(pl.col("especie_id").alias("evolui_de"), pl.col("total").alias("total_pre"))
        df = df.join(default_total, on="evolui_de", how="left").with_columns(
            (pl.col("geracao_especie") > pl.col("geracao_linha")).alias("evolucao_tardia")
        )

        return df.select(
            "pokemon_id", "slug", "nome", "especie_id", "especie_slug", "especie_nome", "padrao", "forma_tipo",
            "geracao", "geracao_especie", "grupo", "estagio", "final", "lendario", "mitico", "bebe",
            "evolui_de", "base_id", "geracao_linha", "evolucao_tardia", "total_pre",
            "tipo1", "tipo2", "tipo1_lanc", "tipo2_lanc",
            *STAT_COLS, "total", *[f"{c}_lanc" for c in STAT_COLS], "total_lanc", "stats_mudaram_em",
            "especializacao", "maior_stat", "arte",
        ).sort("geracao", "especie_id", "pokemon_id")  # fmt: skip

    return memo("pokemon", build)


def tipos() -> pl.DataFrame:
    return memo("tipos", pokeapi.type_chart)


def golpes() -> pl.DataFrame:
    """Every main-series move with its power/accuracy at launch and today."""

    def build() -> pl.DataFrame:
        vg = version_groups()
        order = dict(zip(vg["vg"], vg["vg_ordem"]))
        first_of_gen = vg.group_by("geracao").agg(pl.col("vg_ordem").min())
        first = dict(zip(first_of_gen["geracao"], first_of_gen["vg_ordem"]))
        mv = require_columns(pokeapi.moves(), ["golpe_id", "geracao", "poder", "classe"], "PokeAPI moves", min_rows=800)

        rows = []
        for r in mv.select("golpe_id", "geracao", "poder", "precisao", "past_values").iter_rows(named=True):
            past = r["past_values"] or []
            launch = first[r["geracao"]]
            rows.append(
                {
                    "golpe_id": r["golpe_id"],
                    "poder_lanc": value_at(r["poder"], [(order[p["vg"]], p["poder"]) for p in past], launch),
                    "precisao_lanc": value_at(r["precisao"], [(order[p["vg"]], p["precisao"]) for p in past], launch),
                    "mudancas": len(past),
                }
            )
        extra = pl.DataFrame(rows, schema={"golpe_id": pl.Int64, "poder_lanc": pl.Int64, "precisao_lanc": pl.Int64, "mudancas": pl.Int64})
        return mv.join(extra, on="golpe_id").drop("past_values").sort("geracao", "golpe_id")

    return memo("golpes", build)

