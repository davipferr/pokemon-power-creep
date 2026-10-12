"""Build-time data pipeline for the Pokémon power-creep site.

``pokeapi`` fetches and flattens PokeAPI resources; ``frames`` joins them into
clean Polars tables (memoised as Parquet); ``creep`` holds the measures. The
Observable Framework data loaders in ``src/data`` are thin scripts that call
into this package and write the result to stdout.
"""
