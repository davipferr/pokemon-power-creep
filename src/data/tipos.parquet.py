"""Type chart (attacker × defender multipliers), today and before each past change."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.tipos())
