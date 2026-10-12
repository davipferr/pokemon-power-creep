"""Build metadata and data-quality report: counts, groups, forms and exclusions."""

from datetime import datetime, timezone

import polars as pl

from pipeline import categorias, frames
from pipeline.io import emit_json


def counts(df: pl.DataFrame, col: str) -> list[dict]:
    return df.group_by(col).agg(pl.len().alias("n")).sort("n", descending=True).to_dicts()


pk = frames.pokemon()
d = pk.filter(pl.col("padrao"))
mv = frames.golpes()
tp = frames.tipos()

emit_json(
    {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "especies": d.height,
        "pokemon": pk.height,
        "geracoes": sorted(d["geracao"].unique().to_list()),
        "grupos": [{"grupo": g, "n": d.filter(pl.col("grupo") == g).height} for g in categorias.GRUPOS],
        "pseudolendarios": d.filter(pl.col("grupo") == "Pseudolendário")["nome"].to_list(),
        "formas": counts(pk, "forma_tipo"),
        "stats_alterados": d.filter(pl.col("stats_mudaram_em").is_not_null()).height,
        "tipos_alterados": d.filter((pl.col("tipo1") != pl.col("tipo1_lanc")) | (pl.col("tipo2").ne_missing(pl.col("tipo2_lanc")))).height,
        "evolucoes_tardias": d.filter(pl.col("evolucao_tardia")).height,
        "golpes": {
            "total": mv.height,
            "gimmick": mv.filter(pl.col("gimmick")).height,
            "status": mv.filter(pl.col("classe") == "Status").height,
            "poder_alterado": mv.filter(pl.col("poder").ne_missing(pl.col("poder_lanc"))).height,
        },
        "tabela_tipos": {
            "relacoes": tp.filter(pl.col("ate_geracao").is_null()).height,
            "mudancas": tp.filter(pl.col("ate_geracao").is_not_null()).height,
        },
        "sem_arte": pk.filter(pl.col("arte").is_null())["nome"].to_list(),
    }
)
