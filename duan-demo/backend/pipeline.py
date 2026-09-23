"""The 'DNA matching' pipeline itself.

Everything genetic here is SIMULATED: there is no real DNA input, no
sequencing, and no validated link between genetic markers and gemstones
or the trait categories below. This deterministically derives a fake
genetic profile and trait scores from name + birth date (same inputs
always produce the same output, which is what makes the demo repeatable),
purely to exercise a realistic-looking pipeline: intake -> variant
analysis -> matching -> results.
"""

import hashlib
import random

from gemstones import GEMSTONES

TRAITS = {
    "vitality_index": "Vitality Resonance",
    "calm_index": "Calm & Balance",
    "focus_index": "Mental Clarity",
    "circulation_index": "Circulatory Harmony",
    "resilience_index": "Cellular Resilience",
}

MARKER_IDS = [
    "rs4363657", "rs1801133", "rs662799", "rs5882132", "rs4880",
    "rs1042522", "rs6265", "rs2233678", "rs1799983", "rs731236",
]
GENOTYPES = ["AA", "AG", "GG", "CC", "CT", "TT"]


def seed_from(name: str, birth_date: str) -> int:
    digest = hashlib.sha256(f"{name.strip().lower()}|{birth_date}".encode()).hexdigest()
    return int(digest[:16], 16)


def _stable_subseed(seed: int, label: str) -> int:
    """Derive a sub-seed that doesn't depend on Python's randomized hash()."""
    label_digest = int(hashlib.sha256(label.encode()).hexdigest()[:8], 16)
    return seed ^ label_digest


def generate_synthetic_markers(seed: int, count: int = 8) -> list[dict]:
    rng = random.Random(seed)
    chosen = rng.sample(MARKER_IDS, k=min(count, len(MARKER_IDS)))
    return [{"marker": marker_id, "genotype": rng.choice(GENOTYPES)} for marker_id in chosen]


def generate_trait_scores(seed: int) -> dict[str, int]:
    scores = {}
    for trait_key in TRAITS:
        rng = random.Random(_stable_subseed(seed, trait_key))
        scores[trait_key] = rng.randint(35, 96)
    return scores


def _build_reasoning(gem_name: str, top_trait_labels: list[str], gem_element: str, person_element: str) -> str:
    trait_phrase = " and ".join(top_trait_labels) if top_trait_labels else "overall profile balance"
    if gem_element == person_element:
        return (
            f"{gem_name} scores highly on {trait_phrase} from your synthetic marker profile, "
            f"and its {gem_element} elemental affinity matches your {person_element} sun sign."
        )
    return f"{gem_name} scores highly on {trait_phrase} from your synthetic marker profile."


def match_gemstones(trait_scores: dict[str, int], element: str, top_n: int = 3) -> list[dict]:
    scored = []
    for gem in GEMSTONES:
        weights = gem["trait_weights"]
        weight_total = sum(weights.values()) or 1
        base_score = sum(trait_scores[t] * w for t, w in weights.items()) / weight_total
        element_bonus = 12 if gem["element"] == element else 0
        total_score = min(round(base_score + element_bonus), 99)

        top_traits = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:2]
        top_trait_labels = [TRAITS[t] for t, w in top_traits if w > 0]

        scored.append({
            "id": gem["id"],
            "name": gem["name"],
            "color": gem["color"],
            "element": gem["element"],
            "description": gem["description"],
            "score": total_score,
            "reasoning": _build_reasoning(gem["name"], top_trait_labels, gem["element"], element),
        })

    scored.sort(key=lambda r: r["score"], reverse=True)
    top_matches = scored[:top_n]
    for rank, match in enumerate(top_matches, start=1):
        match["rank"] = rank
    return top_matches
