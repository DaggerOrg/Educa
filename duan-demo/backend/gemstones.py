"""Curated gemstone catalog used by the matching engine.

`trait_weights` are hand-picked (not derived from any real biological or
mineralogical data) purely to give the demo's matching output some
internal consistency and variety.
"""

GEMSTONES = [
    {
        "id": "ruby",
        "name": "Ruby",
        "color": "#9B111E",
        "element": "Fire",
        "description": "A deep-red corundum long associated with vitality, passion, and courage.",
        "trait_weights": {"vitality_index": 0.9, "circulation_index": 0.6, "focus_index": 0.1, "calm_index": 0.0, "resilience_index": 0.3},
    },
    {
        "id": "sapphire",
        "name": "Sapphire",
        "color": "#0F52BA",
        "element": "Air",
        "description": "A cool-toned corundum prized for clarity of thought and wisdom.",
        "trait_weights": {"focus_index": 0.9, "calm_index": 0.5, "vitality_index": 0.1, "circulation_index": 0.0, "resilience_index": 0.3},
    },
    {
        "id": "emerald",
        "name": "Emerald",
        "color": "#50C878",
        "element": "Earth",
        "description": "A vivid green beryl linked to renewal, balance, and steady growth.",
        "trait_weights": {"calm_index": 0.8, "resilience_index": 0.6, "focus_index": 0.2, "vitality_index": 0.1, "circulation_index": 0.1},
    },
    {
        "id": "diamond",
        "name": "Diamond",
        "color": "#B9F2FF",
        "element": "Air",
        "description": "The hardest natural mineral, symbolizing clarity, resilience, and permanence.",
        "trait_weights": {"resilience_index": 0.9, "focus_index": 0.6, "calm_index": 0.2, "vitality_index": 0.1, "circulation_index": 0.0},
    },
    {
        "id": "amethyst",
        "name": "Amethyst",
        "color": "#9966CC",
        "element": "Water",
        "description": "A violet quartz traditionally tied to calm, clarity, and emotional balance.",
        "trait_weights": {"calm_index": 0.9, "focus_index": 0.4, "resilience_index": 0.2, "vitality_index": 0.0, "circulation_index": 0.0},
    },
    {
        "id": "citrine",
        "name": "Citrine",
        "color": "#E4D00A",
        "element": "Fire",
        "description": "A golden quartz associated with energy, optimism, and mental drive.",
        "trait_weights": {"vitality_index": 0.7, "focus_index": 0.5, "circulation_index": 0.2, "calm_index": 0.1, "resilience_index": 0.1},
    },
    {
        "id": "aquamarine",
        "name": "Aquamarine",
        "color": "#7FFFD4",
        "element": "Water",
        "description": "A pale blue-green beryl linked to calm circulation and emotional flow.",
        "trait_weights": {"calm_index": 0.7, "circulation_index": 0.6, "focus_index": 0.2, "vitality_index": 0.1, "resilience_index": 0.0},
    },
    {
        "id": "black_onyx",
        "name": "Black Onyx",
        "color": "#353839",
        "element": "Earth",
        "description": "A grounding black chalcedony associated with resilience and steady focus.",
        "trait_weights": {"resilience_index": 0.8, "focus_index": 0.5, "calm_index": 0.3, "vitality_index": 0.0, "circulation_index": 0.0},
    },
    {
        "id": "garnet",
        "name": "Garnet",
        "color": "#733635",
        "element": "Fire",
        "description": "A deep red mineral historically linked to vitality and physical stamina.",
        "trait_weights": {"vitality_index": 0.8, "resilience_index": 0.5, "circulation_index": 0.4, "focus_index": 0.0, "calm_index": 0.0},
    },
    {
        "id": "pearl",
        "name": "Pearl",
        "color": "#F0EAD6",
        "element": "Water",
        "description": "An organic gem formed in still water, associated with calm and gentle balance.",
        "trait_weights": {"calm_index": 0.8, "circulation_index": 0.3, "resilience_index": 0.2, "focus_index": 0.1, "vitality_index": 0.0},
    },
]
