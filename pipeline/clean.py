"""Small, pure helpers for PokeAPI's quirks: ids in URLs, roman-numeral
generations, form names, and stats/move values "as of" a past generation."""

from __future__ import annotations

import re

# Generation metadata the API doesn't carry in a usable shape.
GERACOES = {
    1: {"regiao": "Kanto", "ano": 1996, "jogos": "Red / Green / Blue"},
    2: {"regiao": "Johto", "ano": 1999, "jogos": "Gold / Silver"},
    3: {"regiao": "Hoenn", "ano": 2002, "jogos": "Ruby / Sapphire"},
    4: {"regiao": "Sinnoh", "ano": 2006, "jogos": "Diamond / Pearl"},
    5: {"regiao": "Unova", "ano": 2010, "jogos": "Black / White"},
    6: {"regiao": "Kalos", "ano": 2013, "jogos": "X / Y"},
    7: {"regiao": "Alola", "ano": 2016, "jogos": "Sun / Moon"},
    8: {"regiao": "Galar", "ano": 2019, "jogos": "Sword / Shield"},
    9: {"regiao": "Paldea", "ano": 2022, "jogos": "Scarlet / Violet"},
}

# PokeAPI stat names -> our column names (Portuguese, short).
STATS = {
    "hp": "hp",
    "attack": "ataque",
    "defense": "defesa",
    "special-attack": "atq_esp",
    "special-defense": "def_esp",
    "speed": "velocidade",
}
STAT_COLS = list(STATS.values())

# The 18 battle types. PokeAPI has no Portuguese names; these are the ones used
# by the Brazilian TCG and anime.
TIPOS = {
    "normal": "Normal",
    "fire": "Fogo",
    "water": "Água",
    "grass": "Planta",
    "electric": "Elétrico",
    "ice": "Gelo",
    "fighting": "Lutador",
    "poison": "Venenoso",
    "ground": "Terrestre",
    "flying": "Voador",
    "psychic": "Psíquico",
    "bug": "Inseto",
    "rock": "Pedra",
    "ghost": "Fantasma",
    "dragon": "Dragão",
    "dark": "Sombrio",
    "steel": "Aço",
    "fairy": "Fada",
}

CLASSES_GOLPE = {"physical": "Físico", "special": "Especial", "status": "Status"}

_ROMAN = {"i": 1, "v": 5, "x": 10}


def id_from_url(url: str) -> int:
    """``https://pokeapi.co/api/v2/pokemon-species/12/`` -> 12."""
    m = re.search(r"/(\d+)/?$", url)
    if not m:
        raise ValueError(f"no id at the end of {url!r}")
    return int(m.group(1))


def roman_to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s.lower()):
        v = _ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def generation_number(name: str) -> int:
    """``generation-iv`` -> 4."""
    m = re.fullmatch(r"generation-([ivx]+)", name)
    if not m:
        raise ValueError(f"unexpected generation name {name!r}")
    return roman_to_int(m.group(1))


def english_name(names: list[dict], fallback: str = "") -> str:
    """Pick the English entry from a PokeAPI ``names`` list."""
    for n in names or []:
        if n["language"]["name"] == "en" and n["name"]:
            return n["name"]
    return fallback


def pretty_slug(slug: str) -> str:
    """Last-resort display name from a slug: ``iron-treads`` -> ``Iron Treads``."""
    return " ".join(w.capitalize() for w in slug.split("-"))


def display_name(slug: str, especie_slug: str, especie_nome: str, padrao: bool, forma_nome: str | None, **_) -> str:
    """Species name for default forms; the form's own English name ("Mega
    Charizard X", "Alolan Raichu") when PokeAPI has one; otherwise the species
    name plus the slug suffix: ``Basculin (Blue Striped)``."""
    if padrao:
        return especie_nome
    if forma_nome:
        return forma_nome
    suffix = slug.removeprefix(especie_slug).strip("-")
    return f"{especie_nome} ({pretty_slug(suffix)})" if suffix else especie_nome


REGIONAIS = ("alola", "galar", "hisui", "paldea")


def form_kind(slug: str, is_default: bool, is_mega: bool = False) -> str:
    """Classify one /pokemon entry by its slug.

    Megas and primal reversions are the classic "retro power-ups" of old
    Pokémon; Gigantamax forms have the same base stats as the default form;
    totems are bigger in-game bosses with the same stats.
    """
    if is_default:
        return "padrão"
    parts = slug.split("-")
    if "gmax" in parts:
        return "gigantamax"
    if is_mega or "mega" in parts:
        return "mega"
    if "primal" in parts:
        return "primal"
    if "totem" in parts:
        return "totem"
    if any(r in parts for r in REGIONAIS):
        return "regional"
    return "outra"


def stats_at(current: dict[str, int], past: list[tuple[int, dict[str, int]]], gen: int) -> dict[str, int]:
    """Base stats as they were in generation ``gen``.

    PokeAPI's ``past_stats`` lists blocks of (generation, stats): "up to and
    including this generation, these stats had these values". Only the stats
    that changed are listed. For each stat we take the earliest block whose
    generation is >= ``gen`` and that mentions the stat; otherwise today's value.

    Generation 1 had a single "special" stat instead of special attack/defense;
    it is ignored here, so callers should ask for gen >= 2 when they need six
    comparable stats.
    """
    out = dict(current)
    for stat in current:
        candidates = [(g, s[stat]) for g, s in past if g >= gen and stat in s]
        if candidates:
            out[stat] = min(candidates)[1]
    return out


def types_at(current: list[str], past: list[tuple[int, list[str]]], gen: int) -> list[str]:
    """Types as they were in generation ``gen`` (same "up to and including"
    semantics as ``stats_at``). Clefable was pure Normal until Gen 5, for example."""
    candidates = [(g, t) for g, t in past if g >= gen]
    return min(candidates, key=lambda c: c[0])[1] if candidates else current


def value_at(current: object, past: list[tuple[int, object]], order: int) -> object:
    """A move field (power, accuracy…) as it was in version-group ``order``.

    Each ``past_values`` entry carries the value the move had *before* that
    version group changed it (null = that field didn't change then). So the
    value at ``order`` is the one from the earliest change made after it.
    """
    later = [(o, v) for o, v in past if o > order and v is not None]
    return min(later, key=lambda t: t[0])[1] if later else current
