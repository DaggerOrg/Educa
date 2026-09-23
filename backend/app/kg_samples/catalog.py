from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    board_id: str  # stable, so running the seeder twice never makes a duplicate
    file: str  # JSON next to this module: {title, nodes, relationships}


SAMPLES = [Sample(board_id="kgboard_sample_english", file="english_language.json")]
