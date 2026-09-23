"""Ready-made knowledge-graph boards, kept apart from `kg_boards.py` (which
only knows how to store/serve boards) and from the agent that proposes new
ones.

    catalog.py   which samples exist (pure data, safe to import anywhere)
    seed.py      creates the ones that are missing (needs the DB + Liveblocks)
    *.json       the graph for each sample

Run `python -m app.kg_samples` to create any missing sample boards.
"""
