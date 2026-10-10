import os
from pathlib import Path
from typing import Literal, Optional

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import serp  # noqa: F401  (loads .env)
from .journey import investigate
from .models import CheckRequest, CheckResponse, JourneyInput, JourneyResponse
from .pipeline import check
from .samples import JOURNEY_SAMPLES, SAMPLES

app = FastAPI(title="OfferProof")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

Mode = Literal["live", "cached"]


def default_mode() -> str:
    return "live" if os.getenv("MODE", "cached") == "live" else "cached"


@app.post("/api/check", response_model=CheckResponse)
async def check_offer(req: CheckRequest, mode: Optional[Mode] = None):
    return await check(req, mode or default_mode())


@app.post("/api/investigate", response_model=JourneyResponse)
async def investigate_journey(req: JourneyInput, mode: Optional[Mode] = None):
    return await investigate(req, mode or default_mode())  # 422 comes from JourneyInput if no stage has content


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/samples")
def samples():
    return {**{k: {**v, "kind": "quick"} for k, v in SAMPLES.items()}, **JOURNEY_SAMPLES}


@app.get("/api/quota")
def quota(mode: Optional[Mode] = None):
    if (mode or default_mode()) == "cached":
        return {"total_searches_left": None}
    try:
        r = requests.get("https://serpapi.com/account.json", params={"api_key": os.getenv("SERPAPI_API_KEY", "")}, timeout=5)
        return {"total_searches_left": r.json().get("total_searches_left")}
    except Exception:
        return {"total_searches_left": None}


# Serve the built frontend from the same origin (run `npm run build` in frontend/ first).
# Mounted last so every /api route above wins.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
