import polars as pl

from pipeline.categorias import grupo_expr, with_stages


def species(rows):
    return pl.DataFrame(rows, orient="row", schema={"especie_id": pl.Int64, "evolui_de": pl.Int64, "geracao_especie": pl.Int32})


def test_stages_roots_and_late_evolutions():
    # Magby (Gen 2 baby) -> Magmar (Gen 1) -> Magmortar (Gen 4); Tauros alone.
    df = with_stages(species([(240, None, 2), (126, 240, 1), (467, 126, 4), (128, None, 1)])).sort("especie_id")
    by_id = {r["especie_id"]: r for r in df.iter_rows(named=True)}
    assert by_id[467]["estagio"] == 3 and by_id[467]["final"]
    assert not by_id[126]["final"]
    assert by_id[467]["base_id"] == 240
    assert by_id[467]["geracao_linha"] == 2
    assert by_id[128]["estagio"] == 1 and by_id[128]["final"]


def grupo(**kw):
    row = {"especie_slug": "x", "lendario": False, "mitico": False, "bebe": False, "estagio": 1, "final": True, "total": 500} | kw
    return pl.DataFrame([row]).select(grupo_expr())["grupo"][0]


def test_groups():
    assert grupo() == "Comum, totalmente evoluído"
    assert grupo(final=False) == "Comum, em evolução"
    assert grupo(final=False, bebe=True) == "Comum, em evolução"
    assert grupo(estagio=3, total=600) == "Pseudolendário"
    # 600 alone is not enough: Slaking-like (670) and two-stage 600s aren't pseudos.
    assert grupo(estagio=3, total=670) == "Comum, totalmente evoluído"
    assert grupo(estagio=2, total=600) == "Comum, totalmente evoluído"
    assert grupo(lendario=True, total=680) == "Lendário"
    assert grupo(mitico=True, lendario=True) == "Mítico"
    assert grupo(especie_slug="kartana") == "Ultra Fera"
    assert grupo(especie_slug="iron-valiant") == "Paradoxo"
