"""The power-creep measures.

- ``total`` (base stat total, BST) per generation and comparison group — today's
  stats and the stats each Pokémon had at launch, since Gen 6 and 7 buffed many
  old Pokémon retroactively;
- a linear trend of BST on generation with a 95 % confidence interval, so "is
  there creep?" gets a number and an uncertainty instead of eyeballing medians;
- *especialização*: the coefficient of variation of the six stats. A Pokémon
  with 100 in everything scores 0; a glass cannon scores high. Creep can show
  up as more min-maxed designs even when the total stays flat.
"""

from __future__ import annotations

import math

import polars as pl

from .clean import STAT_COLS

# Two-sided 97.5 % quantile of Student's t for small samples (df = n - 2);
# beyond 30 the normal value is close enough.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
         12: 2.179, 15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042}  # fmt: skip


def _t975(df: int) -> float:
    if df > 30:
        return 1.96
    return _T975[max(k for k in _T975 if k <= df)]


def with_shape(df: pl.DataFrame) -> pl.DataFrame:
    """Add ``especializacao`` (std / mean of the six stats) and ``maior_stat``."""
    stats = pl.concat_list(STAT_COLS)
    return df.with_columns(
        (stats.list.std(ddof=0) / stats.list.mean()).round(4).alias("especializacao"),
        pl.concat_list([pl.when(pl.col(c) == pl.max_horizontal(STAT_COLS)).then(pl.lit(c)) for c in STAT_COLS])
        .list.drop_nulls()
        .list.first()
        .alias("maior_stat"),
    )


def tendencia(x: list[float], y: list[float]) -> dict:
    """Ordinary least squares y = a + b·x, with a 95 % CI for the slope b."""
    pts = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pts)
    if n < 3:
        raise ValueError("need at least 3 points for a trend")
    mx = sum(a for a, _ in pts) / n
    my = sum(b for _, b in pts) / n
    sxx = sum((a - mx) ** 2 for a, _ in pts)
    if sxx == 0:
        raise ValueError("x has no variance")
    sxy = sum((a - mx) * (b - my) for a, b in pts)
    slope = sxy / sxx
    intercept = my - slope * mx
    sse = sum((b - intercept - slope * a) ** 2 for a, b in pts)
    sst = sum((b - my) ** 2 for _, b in pts)
    se = math.sqrt(sse / (n - 2) / sxx)
    t = _t975(n - 2)
    return {
        "n": n,
        "inclinacao": slope,
        "intercepto": intercept,
        "ic95": [slope - t * se, slope + t * se],
        "r2": 1 - sse / sst if sst else 0.0,
    }


def resumo_geracoes(df: pl.DataFrame) -> pl.DataFrame:
    """Per generation × group × measure (``atual`` / ``lancamento``): count and
    quartiles of BST, plus the median of every stat and of especialização."""
    out = []
    for medida, sufixo in (("atual", ""), ("lancamento", "_lanc")):
        cols = [f"{c}{sufixo}" for c in STAT_COLS]
        total = f"total{sufixo}"
        agg = (
            df.group_by("geracao", "grupo")
            .agg(
                pl.len().alias("n"),
                pl.col(total).quantile(0.25, "linear").alias("q1"),
                pl.col(total).median().alias("mediana"),
                pl.col(total).quantile(0.75, "linear").alias("q3"),
                pl.col(total).mean().alias("media"),
                *[pl.col(c).median().alias(f"med_{s}") for c, s in zip(cols, STAT_COLS)],
                pl.col("especializacao").median().alias("med_especializacao"),
            )
            .with_columns(pl.lit(medida).alias("medida"))
        )
        out.append(agg)
    return pl.concat(out).sort("medida", "grupo", "geracao")


def tendencias(df: pl.DataFrame) -> dict:
    """BST and per-stat slopes per generation for one comparison group."""
    g = df["geracao"].to_list()
    nativos = df.filter(~pl.col("evolucao_tardia"))
    out = {
        "total": tendencia(g, df["total"].to_list()),
        # Without late evolutions of older lines (Magmortar, Togekiss…).
        "total_nativos": tendencia(nativos["geracao"].to_list(), nativos["total"].to_list()),
        "total_lanc": tendencia(g, df["total_lanc"].to_list()),
        "especializacao": tendencia(g, df["especializacao"].to_list()),
    }
    out |= {c: tendencia(g, df[c].to_list()) for c in STAT_COLS}
    return out
