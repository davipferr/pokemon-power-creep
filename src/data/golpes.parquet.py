"""Main-series moves: generation, type, class, power and accuracy at launch and today."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.golpes())
