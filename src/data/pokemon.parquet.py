"""Every Pokémon and alternate form: group, types and stats (today and at launch)."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.pokemon())
