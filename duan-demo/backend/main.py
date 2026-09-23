"""DUAN DNA-matching demo API.

Serves the JSON pipeline under /api/* and the static frontend from
../frontend at /. See pipeline.py for what's real vs. simulated.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from astrology import get_sun_sign
from gemstones import GEMSTONES
from pipeline import TRAITS, generate_synthetic_markers, generate_trait_scores, match_gemstones, seed_from

app = FastAPI(title="DUAN DNA Matching Demo")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

DISCLAIMER = (
    "Demo pipeline only: genetic markers are synthetically generated from your "
    "name and birth date (not real DNA), and the trait/gemstone associations "
    "are illustrative, not clinically or scientifically validated."
)


class MatchRequest(BaseModel):
    name: str
    birth_date: date
    birth_time: Optional[str] = None
    birth_city: Optional[str] = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/gemstones")
def list_gemstones():
    return {"gemstones": GEMSTONES}


@app.post("/api/match")
def match(payload: MatchRequest):
    birth_date_str = payload.birth_date.isoformat()
    seed = seed_from(payload.name, birth_date_str)

    markers = generate_synthetic_markers(seed)
    trait_scores = generate_trait_scores(seed)
    sign = get_sun_sign(payload.birth_date.month, payload.birth_date.day)
    matches = match_gemstones(trait_scores, sign["element"])

    return {
        "profile": {
            "seed": f"{seed:016x}",
            "synthetic_markers": markers,
        },
        "trait_scores": {TRAITS[key]: value for key, value in trait_scores.items()},
        "astrology": sign,
        "matches": matches,
        "disclaimer": DISCLAIMER,
    }


# Mounted last so it only catches requests the /api/* routes above didn't handle.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
