"""PokeAPI client (https://pokeapi.co/api/v2, no key).

The REST API serves one document per resource, so each frame is "list every
resource, then fetch them all" (in parallel, cached on disk). The ``parse_*``
functions turn one JSON document into one flat row; they are pure, so the
tests exercise them on trimmed real responses.
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from .clean import (
    CLASSES_GOLPE,
    STATS,
    TIPOS,
    english_name,
    form_kind,
    generation_number,
    id_from_url,
    pretty_slug,
)
from .http import fetch_json, fetch_many

BASE = "https://pokeapi.co/api/v2"
# Resource ids above this are game-specific extras (Colosseum's shadow moves,
# the "unknown"/"shadow" types), not part of the main series.
MAX_MAIN_ID = 10_000


def index_url(resource: str) -> str:
    return f"{BASE}/{resource}?offset=0&limit=100000"


def index(resource: str) -> list[str]:
    """URLs of every resource of a kind. Re-listed weekly so new entries show up."""
    data = fetch_json(index_url(resource), max_age=timedelta(days=7))
    return [r["url"] for r in data["results"]]


# ---------------------------------------------------------------- parsing


def parse_version_group(d: dict) -> dict:
    return {"vg": d["name"], "vg_ordem": d["order"], "geracao": generation_number(d["generation"]["name"])}


def parse_species(d: dict) -> dict:
    prev = d.get("evolves_from_species")
    return {
        "especie_id": d["id"],
        "especie_slug": d["name"],
        "especie_nome": english_name(d["names"], pretty_slug(d["name"])),
        "geracao_especie": generation_number(d["generation"]["name"]),
        "lendario": d["is_legendary"],
        "mitico": d["is_mythical"],
        "bebe": d["is_baby"],
        "evolui_de": id_from_url(prev["url"]) if prev else None,
    }


def _stat_dict(stats: list[dict]) -> dict[str, int]:
    return {STATS[s["stat"]["name"]]: s["base_stat"] for s in stats if s["stat"]["name"] in STATS}


def _types(types: list[dict]) -> list[str]:
    return [t["type"]["name"] for t in sorted(types, key=lambda t: t["slot"])]


def parse_pokemon(d: dict) -> dict:
    """One /pokemon document (a species' default form or an alternate form).

    ``past_stats`` and ``past_types`` are kept as lists of structs; they are
    resolved against the generation of introduction later (see frames).
    """
    stats = _stat_dict(d["stats"])
    types = _types(d["types"])
    art = (d.get("sprites") or {}).get("other", {}).get("official-artwork", {}).get("front_default")
    return {
        "pokemon_id": d["id"],
        "slug": d["name"],
        "especie_id": id_from_url(d["species"]["url"]),
        "padrao": d["is_default"],
        **stats,
        "tipo1": types[0],
        "tipo2": types[1] if len(types) > 1 else None,
        "past_stats": [
            {"geracao": generation_number(p["generation"]["name"]), "stat": STATS[s["stat"]["name"]], "valor": s["base_stat"]}
            for p in d.get("past_stats") or []
            for s in p["stats"]
            if s["stat"]["name"] in STATS
        ],
        "past_types": [
            {"geracao": generation_number(p["generation"]["name"]), "tipos": _types(p["types"])} for p in d.get("past_types") or []
        ],
        "forma_url": d["forms"][0]["url"] if d.get("forms") else None,
        "arte": art,
    }


def parse_form(d: dict) -> dict:
    """One /pokemon-form document: when an alternate form was introduced and its name."""
    return {
        "pokemon_id": id_from_url(d["pokemon"]["url"]),
        "forma_vg": d["version_group"]["name"],
        "mega": d["is_mega"],
        "so_em_batalha": d["is_battle_only"],
        "forma_nome": english_name(d.get("names") or []),
    }


def parse_type(d: dict) -> list[dict]:
    """Rows (attacker, defender, multiplier) for one attacking type, today and
    in each past chart this type had (``past_damage_relations``)."""

    def rows(rel: dict, ate: int | None) -> list[dict]:
        out = []
        for key, mult in (("no_damage_to", 0.0), ("half_damage_to", 0.5), ("double_damage_to", 2.0)):
            out += [{"atacante": d["name"], "defensor": t["name"], "mult": mult, "ate_geracao": ate} for t in rel[key]]
        return out

    out = rows(d["damage_relations"], None)
    for past in d.get("past_damage_relations") or []:
        out += rows(past["damage_relations"], generation_number(past["generation"]["name"]))
    return out


def _is_gimmick_move(slug: str, gen: int, pp: int | None) -> bool:
    """Z-Moves (Gen 7, 1 PP) and Max/G-Max Moves (Gen 8) are battle gimmicks
    with no learnset; they would inflate any "power of new moves" chart."""
    return slug.startswith(("max-", "g-max-")) or (gen == 7 and pp == 1)


def parse_move(d: dict) -> dict:
    gen = generation_number(d["generation"]["name"])
    return {
        "golpe_id": d["id"],
        "golpe_slug": d["name"],
        "golpe_nome": english_name(d["names"], pretty_slug(d["name"])),
        "geracao": gen,
        "tipo": d["type"]["name"],
        "classe": CLASSES_GOLPE.get((d.get("damage_class") or {}).get("name"), None),
        "poder": d["power"],
        "precisao": d["accuracy"],
        "pp": d["pp"],
        "prioridade": d["priority"],
        "gimmick": _is_gimmick_move(d["name"], gen, d["pp"]),
        "past_values": [
            {"vg": p["version_group"]["name"], "poder": p["power"], "precisao": p["accuracy"], "pp": p["pp"]}
            for p in d.get("past_values") or []
        ],
    }


# ---------------------------------------------------------------- fetching


def version_groups() -> pl.DataFrame:
    return pl.DataFrame([parse_version_group(d) for d in fetch_many(index("version-group"), label="version groups")])


def species() -> pl.DataFrame:
    return pl.DataFrame([parse_species(d) for d in fetch_many(index("pokemon-species"), label="species")])


def pokemon() -> pl.DataFrame:
    rows = [parse_pokemon(d) for d in fetch_many(index("pokemon"), label="pokemon")]
    return pl.DataFrame(rows, infer_schema_length=None)


def forms(urls: list[str]) -> pl.DataFrame:
    return pl.DataFrame([parse_form(d) for d in fetch_many(urls, label="forms")])


def type_chart() -> pl.DataFrame:
    urls = [u for u in index("type") if id_from_url(u) < MAX_MAIN_ID]
    docs = [d for d in fetch_many(urls, label="types") if d["name"] in TIPOS]
    return pl.DataFrame([r for d in docs for r in parse_type(d)], schema_overrides={"ate_geracao": pl.Int32})


def moves() -> pl.DataFrame:
    urls = [u for u in index("move") if id_from_url(u) < MAX_MAIN_ID]
    return pl.DataFrame([parse_move(d) for d in fetch_many(urls, label="moves")], infer_schema_length=None)
