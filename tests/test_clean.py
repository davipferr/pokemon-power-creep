import pytest

from pipeline.clean import (
    display_name,
    english_name,
    form_kind,
    generation_number,
    id_from_url,
    stats_at,
    types_at,
    value_at,
)


def test_id_from_url():
    assert id_from_url("https://pokeapi.co/api/v2/pokemon-species/12/") == 12
    assert id_from_url("https://pokeapi.co/api/v2/move/10001") == 10001
    with pytest.raises(ValueError):
        id_from_url("https://pokeapi.co/api/v2/pokemon/")


@pytest.mark.parametrize(("name", "n"), [("generation-i", 1), ("generation-iv", 4), ("generation-v", 5), ("generation-vi", 6), ("generation-ix", 9)])
def test_generation_number(name, n):
    assert generation_number(name) == n


def test_english_name_and_fallback():
    names = [{"language": {"name": "ja"}, "name": "フシギダネ"}, {"language": {"name": "en"}, "name": "Bulbasaur"}]
    assert english_name(names) == "Bulbasaur"
    assert english_name([], "fallback") == "fallback"


@pytest.mark.parametrize(
    ("slug", "default", "mega", "kind"),
    [
        ("charizard", True, False, "padrão"),
        ("charizard-mega-x", False, True, "mega"),
        ("garchomp-mega-z", False, False, "mega"),  # slug alone is enough
        ("kyogre-primal", False, False, "primal"),
        ("charizard-gmax", False, False, "gigantamax"),
        ("toxtricity-low-key-gmax", False, False, "gigantamax"),
        ("raticate-totem-alola", False, False, "totem"),  # totem wins over region
        ("raichu-alola", False, False, "regional"),
        ("tauros-paldea-aqua-breed", False, False, "regional"),
        ("rotom-wash", False, False, "outra"),
        ("meganium", True, False, "padrão"),  # "mega" inside a word is not a Mega
    ],
)
def test_form_kind(slug, default, mega, kind):
    assert form_kind(slug, default, mega) == kind


def test_display_name():
    base = {"slug": "basculin-blue-striped", "especie_slug": "basculin", "especie_nome": "Basculin"}
    assert display_name(**base, padrao=False, forma_nome="") == "Basculin (Blue Striped)"
    assert display_name(**base, padrao=False, forma_nome="Blue-Striped Basculin") == "Blue-Striped Basculin"
    assert display_name(**base, padrao=True, forma_nome=None) == "Basculin"


BUTTERFREE = {"hp": 60, "ataque": 45, "defesa": 50, "atq_esp": 90, "def_esp": 80, "velocidade": 70}


def test_stats_at_butterfree_gen6_buff():
    # Real PokeAPI data: Sp. Atk was 80 up to and including Gen 5.
    past = [(5, {"atq_esp": 80})]
    assert stats_at(BUTTERFREE, past, 2)["atq_esp"] == 80
    assert stats_at(BUTTERFREE, past, 5)["atq_esp"] == 80
    assert stats_at(BUTTERFREE, past, 6)["atq_esp"] == 90
    assert stats_at(BUTTERFREE, past, 2)["hp"] == 60


def test_stats_at_takes_earliest_block_per_stat():
    current = {"ataque": 100, "defesa": 100}
    past = [(3, {"ataque": 80}), (6, {"ataque": 90, "defesa": 95})]
    assert stats_at(current, past, 2) == {"ataque": 80, "defesa": 95}
    assert stats_at(current, past, 4) == {"ataque": 90, "defesa": 95}
    assert stats_at(current, past, 7) == current


def test_types_at_fairy_retcon():
    # Clefable: Normal up to Gen 5, Fairy since Gen 6.
    assert types_at(["fairy"], [(5, ["normal"])], 1) == ["normal"]
    assert types_at(["fairy"], [(5, ["normal"])], 6) == ["fairy"]


def test_value_at_tackle_history():
    # Tackle: 35 power until B/W (order 14), 50 until Sun/Moon (order 17), 40 today.
    past = [(14, 35), (17, 50)]
    assert value_at(40, past, 1) == 35
    assert value_at(40, past, 14) == 50
    assert value_at(40, past, 16) == 50
    assert value_at(40, past, 17) == 40
    # A null in past_values means "this field didn't change then".
    assert value_at(95, [(14, None)], 1) == 95
