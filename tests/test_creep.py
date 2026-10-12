import polars as pl
import pytest

from pipeline.clean import STAT_COLS
from pipeline.creep import resumo_geracoes, tendencia, with_shape


def test_tendencia_recovers_exact_line():
    x = [1, 2, 3, 4, 5]
    t = tendencia(x, [10 + 3 * v for v in x])
    assert t["inclinacao"] == pytest.approx(3)
    assert t["intercepto"] == pytest.approx(10)
    assert t["r2"] == pytest.approx(1)
    assert t["ic95"][0] == pytest.approx(3) and t["ic95"][1] == pytest.approx(3)


def test_tendencia_ci_contains_zero_for_noise():
    x = [1, 1, 2, 2, 3, 3, 4, 4]
    y = [5, 1, 1, 5, 5, 1, 1, 5]
    t = tendencia(x, y)
    assert t["ic95"][0] < 0 < t["ic95"][1]


def test_tendencia_needs_variance():
    with pytest.raises(ValueError):
        tendencia([2, 2, 2], [1, 2, 3])


def stats(*values):
    return dict(zip(STAT_COLS, values))


def test_with_shape():
    df = pl.DataFrame([stats(100, 100, 100, 100, 100, 100), stats(50, 10, 230, 10, 230, 5)])
    out = with_shape(df)
    assert out["especializacao"][0] == 0
    assert out["especializacao"][1] > 1  # Shuckle-like
    assert out["maior_stat"].to_list() == ["hp", "defesa"]  # ties go to the first stat


def test_resumo_geracoes_both_measures():
    rows = []
    for g, totals in ((1, [300, 400, 500]), (2, [400, 500, 600])):
        for i, t in enumerate(totals):
            s = stats(*[t // 6] * 6)
            rows.append({"geracao": g, "grupo": "A", **s, **{f"{k}_lanc": v for k, v in s.items()}, "especializacao": 0.0})
    df = pl.DataFrame(rows).with_columns(pl.sum_horizontal(STAT_COLS).alias("total"), pl.sum_horizontal([f"{c}_lanc" for c in STAT_COLS]).alias("total_lanc"))
    r = resumo_geracoes(df)
    assert set(r["medida"]) == {"atual", "lancamento"}
    g2 = r.filter(pl.col("medida") == "atual", pl.col("geracao") == 2).row(0, named=True)
    assert g2["n"] == 3 and g2["mediana"] == 498  # 83 * 6
