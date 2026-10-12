"""Linear trends per generation with 95 % confidence intervals.

- ``principal``: fully evolved, non-legendary Pokémon (the fair comparison);
- ``todos``: every species, which mixes in composition changes;
- ``golpes``: power of new damaging moves (gimmick moves excluded).
"""

import polars as pl

from pipeline import categorias, creep, frames
from pipeline.io import emit_json

d = frames.pokemon().filter(pl.col("padrao"))
principal = d.filter(pl.col("grupo") == categorias.PRINCIPAL)
dano = frames.golpes().filter(~pl.col("gimmick"), pl.col("classe") != "Status", pl.col("poder_lanc").is_not_null())

emit_json(
    {
        "principal": creep.tendencias(principal),
        "todos": creep.tendencia(d["geracao"].to_list(), d["total"].to_list()),
        "golpes": {
            "poder_lanc": creep.tendencia(dano["geracao"].to_list(), dano["poder_lanc"].to_list()),
            "poder": creep.tendencia(dano["geracao"].to_list(), dano["poder"].to_list()),
        },
    }
)
