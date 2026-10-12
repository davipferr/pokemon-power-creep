"""BST quartiles and median stats per generation × comparison group, today and
at launch. Default forms only; group "Todos" pools every species."""

import polars as pl

from pipeline import creep, frames
from pipeline.io import emit_parquet

d = frames.pokemon().filter(pl.col("padrao"))
emit_parquet(
    pl.concat([creep.resumo_geracoes(d), creep.resumo_geracoes(d.with_columns(pl.lit("Todos").alias("grupo")))])
)
