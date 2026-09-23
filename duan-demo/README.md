# DUAN — DNA Matching Engine (Demo)

A standalone engineering demo of a "DNA + astrology → gemstone" matching
pipeline, built for an interview walkthrough. **Not related to the Educa
codebase** — kept in this separate top-level folder on purpose.

## What's real vs. simulated

- **Real:** the sun-sign astrology calculation (month/day → zodiac sign,
  element, ruling planet — `backend/astrology.py`), the API, the matching
  algorithm's scoring logic, and the frontend pipeline.
- **Simulated:** there is no real DNA input or sequencing anywhere. A
  "synthetic genetic profile" (fake marker IDs + trait scores) is derived
  deterministically from name + birth date (`backend/pipeline.py`) — same
  inputs always produce the same output, which is what makes the demo
  repeatable. The trait categories (Vitality Resonance, Calm & Balance,
  etc.) and their gemstone associations are hand-picked for internal
  consistency, not derived from any clinical or scientific source. The API
  response includes a `disclaimer` field saying exactly this, and it's
  shown in the UI — worth keeping that framing in the interview rather
  than presenting it as real pharmacogenomics.

## Architecture

```
Browser (HTML/CSS + TypeScript, compiled to app.js)  --fetch-->  FastAPI (/api/match)
                                                                       |
                                                     astrology.py (sun sign)
                                                     pipeline.py (synthetic markers, trait
                                                                  scores, gemstone matching)
                                                     gemstones.py (curated catalog)
```

One process, one port: FastAPI serves both the JSON API (`/api/*`) and the
static frontend (mounted from `../frontend`), so there's nothing to wire
up across two dev servers. The frontend logic is written in TypeScript
(`frontend/src/app.ts`, typed against the API's response shape) and
compiled to the plain `frontend/app.js` that `index.html` loads — no
bundler/framework, just `tsc`.

## Run it

**First time / after editing `app.ts`:**

```bash
cd duan-demo/frontend
npm install
npm run build   # compiles src/app.ts -> app.js
```

**Backend:**

```bash
cd duan-demo/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000   # use a different port if 8000 is taken
```

Open http://localhost:8000 (or whichever port you chose) — fill in a name
+ birth date and run the pipeline. Birth time/city are accepted but not
yet used in the calculation (a real ascendant/rising-sign calculation
needs ephemeris data); they're there to show where the pipeline would
extend. The compiled `app.js` is committed alongside `app.ts`, so the app
runs even if you skip the `npm run build` step — only re-run it if you
change `app.ts`.

## Extending this for a real pitch

If this needs to go from demo to something closer to production:

- Swap `pipeline.py`'s synthetic marker generation for a real intake flow
  (e.g. accepting a genotyping file/API from a lab partner) — the rest of
  the pipeline (trait scoring → matching → API shape) doesn't need to
  change, only where the input comes from.
- Add persistence (a real DB) — right now nothing is stored, each request
  is stateless.
- Add auth if this is ever tied to real personal/genetic data — that's
  sensitive data with real regulatory implications (e.g. GINA in the US),
  worth raising explicitly if the interview goes toward real DNA input.
