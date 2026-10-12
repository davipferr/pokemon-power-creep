"""The parse_* functions on trimmed real PokeAPI responses."""

from pipeline.pokeapi import parse_move, parse_pokemon, parse_species, parse_type

API = "https://pokeapi.co/api/v2"


def stat(name, value, effort=0):
    return {"base_stat": value, "effort": effort, "stat": {"name": name, "url": f"{API}/stat/1/"}}


def test_parse_pokemon_butterfree():
    doc = {
        "id": 12,
        "name": "butterfree",
        "is_default": True,
        "species": {"name": "butterfree", "url": f"{API}/pokemon-species/12/"},
        "stats": [stat("hp", 60), stat("attack", 45), stat("defense", 50), stat("special-attack", 90, 2), stat("special-defense", 80, 1), stat("speed", 70)],
        "past_stats": [
            {"generation": {"name": "generation-i"}, "stats": [stat("special", 80)]},
            {"generation": {"name": "generation-v"}, "stats": [stat("special-attack", 80, 2)]},
        ],
        "types": [{"slot": 2, "type": {"name": "flying"}}, {"slot": 1, "type": {"name": "bug"}}],
        "past_types": [],
        "forms": [{"name": "butterfree", "url": f"{API}/pokemon-form/12/"}],
        "sprites": {"other": {"official-artwork": {"front_default": "https://example.org/12.png"}}},
    }
    r = parse_pokemon(doc)
    assert r["especie_id"] == 12 and r["padrao"]
    assert (r["hp"], r["atq_esp"], r["velocidade"]) == (60, 90, 70)
    assert (r["tipo1"], r["tipo2"]) == ("bug", "flying")  # ordered by slot
    # Gen 1's single "special" stat is dropped; only six-stat names survive.
    assert r["past_stats"] == [{"geracao": 5, "stat": "atq_esp", "valor": 80}]
    assert r["arte"] == "https://example.org/12.png"


def test_parse_species():
    doc = {
        "id": 12,
        "name": "butterfree",
        "names": [{"language": {"name": "en"}, "name": "Butterfree"}],
        "generation": {"name": "generation-i"},
        "is_legendary": False,
        "is_mythical": False,
        "is_baby": False,
        "evolves_from_species": {"name": "metapod", "url": f"{API}/pokemon-species/11/"},
    }
    assert parse_species(doc) == {
        "especie_id": 12,
        "especie_slug": "butterfree",
        "especie_nome": "Butterfree",
        "geracao_especie": 1,
        "lendario": False,
        "mitico": False,
        "bebe": False,
        "evolui_de": 11,
    }


def test_parse_move_flags_gimmicks():
    base = {
        "id": 33,
        "name": "tackle",
        "names": [],
        "generation": {"name": "generation-i"},
        "type": {"name": "normal"},
        "damage_class": {"name": "physical"},
        "power": 40,
        "accuracy": 100,
        "pp": 35,
        "priority": 0,
        "past_values": [{"version_group": {"name": "black-white"}, "power": 35, "accuracy": 95, "pp": None}],
    }
    r = parse_move(base)
    assert r["golpe_nome"] == "Tackle" and r["classe"] == "Físico" and not r["gimmick"]
    assert r["past_values"] == [{"vg": "black-white", "poder": 35, "precisao": 95, "pp": None}]
    z = parse_move(base | {"name": "breakneck-blitz--physical", "generation": {"name": "generation-vii"}, "pp": 1})
    assert z["gimmick"]
    assert parse_move(base | {"name": "max-flare", "generation": {"name": "generation-viii"}, "pp": 10})["gimmick"]


def test_parse_type_current_and_past():
    rel = lambda **kw: {"no_damage_to": [], "half_damage_to": [], "double_damage_to": []} | kw  # noqa: E731
    doc = {
        "name": "ghost",
        "damage_relations": rel(no_damage_to=[{"name": "normal"}], half_damage_to=[{"name": "dark"}], double_damage_to=[{"name": "ghost"}]),
        "past_damage_relations": [
            {"generation": {"name": "generation-v"}, "damage_relations": rel(half_damage_to=[{"name": "dark"}, {"name": "steel"}])},
        ],
    }
    rows = parse_type(doc)
    now = {(r["defensor"], r["mult"]) for r in rows if r["ate_geracao"] is None}
    assert now == {("normal", 0.0), ("dark", 0.5), ("ghost", 2.0)}
    assert {"atacante": "ghost", "defensor": "steel", "mult": 0.5, "ate_geracao": 5} in rows
