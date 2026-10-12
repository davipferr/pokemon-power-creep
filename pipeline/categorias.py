"""Who is compared with whom.

Power creep is only meaningful between comparable Pokémon: a Gen 9 legendary
against a Gen 1 baby says nothing. Every species gets an evolution stage and
a *grupo*:

- Lendário / Mítico — PokeAPI's own flags;
- Ultra Fera / Paradoxo — "sub-legendaries" the API doesn't flag, from fixed lists;
- Pseudolendário — derived: last stage of a three-stage line with exactly 600 base stats;
- Comum, totalmente evoluído — the main comparison group;
- Comum, em evolução — everything that still evolves (including babies).
"""

from __future__ import annotations

import polars as pl

ULTRA_FERAS = {
    "nihilego", "buzzwole", "pheromosa", "xurkitree", "celesteela", "kartana",
    "guzzlord", "poipole", "naganadel", "stakataka", "blacephalon",
}  # fmt: skip

PARADOXOS = {
    # Ancient (Scarlet)
    "great-tusk", "scream-tail", "brute-bonnet", "flutter-mane", "slither-wing", "sandy-shocks",
    "roaring-moon", "walking-wake", "gouging-fire", "raging-bolt",
    # Future (Violet)
    "iron-treads", "iron-bundle", "iron-hands", "iron-jugulis", "iron-moth", "iron-thorns",
    "iron-valiant", "iron-leaves", "iron-boulder", "iron-crown",
}  # fmt: skip

GRUPOS = [
    "Comum, totalmente evoluído",
    "Comum, em evolução",
    "Pseudolendário",
    "Ultra Fera",
    "Paradoxo",
    "Lendário",
    "Mítico",
]
PRINCIPAL = GRUPOS[0]


def with_stages(species: pl.DataFrame) -> pl.DataFrame:
    """Add ``estagio`` (1 = base), ``final`` (nothing evolves from it),
    ``base_id`` (first stage of its line) and ``geracao_linha`` (that first
    stage's generation).

    Needs ``especie_id``, ``evolui_de`` (nullable species id) and
    ``geracao_especie``. A species with no pre-evolution and no evolution is
    stage 1 and final (e.g. Tauros).
    """
    ids = species["especie_id"].to_list()
    parent = dict(zip(ids, species["evolui_de"].to_list()))
    gen = dict(zip(ids, species["geracao_especie"].to_list()))

    def walk(sid: int) -> tuple[int, int]:
        """(stage, root id) of one species."""
        n, seen = 1, {sid}
        while (p := parent.get(sid)) is not None:
            if p in seen:  # defensive: a cycle would be a data error
                raise ValueError(f"evolution cycle at species {p}")
            seen.add(p)
            n, sid = n + 1, p
        return n, sid

    walked = [walk(s) for s in ids]
    has_child = set(species["evolui_de"].drop_nulls().to_list())
    return species.with_columns(
        pl.Series("estagio", [w[0] for w in walked], pl.Int32),
        (~pl.col("especie_id").is_in(list(has_child))).alias("final"),
        pl.Series("base_id", [w[1] for w in walked], pl.Int64),
        pl.Series("geracao_linha", [gen[w[1]] for w in walked], pl.Int32),
    )


def grupo_expr(total: str = "total") -> pl.Expr:
    """The comparison group of one species (needs slug, lendario, mitico, estagio,
    final and the default form's base stat ``total``)."""
    especie = pl.col("especie_slug")
    return (
        pl.when(pl.col("mitico"))
        .then(pl.lit("Mítico"))
        .when(pl.col("lendario"))
        .then(pl.lit("Lendário"))
        .when(especie.is_in(list(ULTRA_FERAS)))
        .then(pl.lit("Ultra Fera"))
        .when(especie.is_in(list(PARADOXOS)))
        .then(pl.lit("Paradoxo"))
        .when(pl.col("final") & (pl.col("estagio") == 3) & (pl.col(total) == 600))
        .then(pl.lit("Pseudolendário"))
        .when(pl.col("final") & ~pl.col("bebe"))
        .then(pl.lit(PRINCIPAL))
        .otherwise(pl.lit("Comum, em evolução"))
        .alias("grupo")
    )
