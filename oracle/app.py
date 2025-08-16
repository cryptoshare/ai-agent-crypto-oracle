import os, json, datetime as dt
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from settings import settings
from providers import call_openai_web_search, fetch_cryptopanic_posts
from scoring import normalize_items, composite_score, regime_from_composite, default_guidance, cryptopanic_subscore

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/oracle/run")
def run_oracle(window: str = Query(default=None, description="e.g., 2h, 1h")):
    win = window or settings.DEFAULT_WINDOW

    # (A) web_search pass
    raw = call_openai_web_search(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        queries=settings.queries,
        domains=settings.domains,
        window=win
    )

    try:
        # Clean up the response - remove code fences if present
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]  # Remove ```json
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]  # Remove ```
        cleaned_raw = cleaned_raw.strip()
        
        payload = json.loads(cleaned_raw)
    except Exception as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {raw[:500]}...")
        return JSONResponse(failsafe_snapshot(reason="parse_error"))

    items = payload.get("items", [])
    scores_ws = payload.get("scores") or normalize_items(items)

    # (B) CryptoPanic pass
    cp_posts = []
    cp_sub = 0.0
    if settings.CRYPTOPANIC_TOKEN:
        try:
            cp_posts = fetch_cryptopanic_posts(
                token=settings.CRYPTOPANIC_TOKEN,
                minutes=settings.CRYPTOPANIC_WINDOW_MIN,
                kind=settings.CRYPTOPANIC_KIND,
                flt=settings.CRYPTOPANIC_FILTER,
                public=settings.CRYPTOPANIC_PUBLIC
            )
            cp_sub = cryptopanic_subscore(cp_posts)
        except Exception as e:
            print(f"CryptoPanic error: {e}")
            cp_posts = []
            cp_sub = 0.0

    # (C) Combine into final scores:
    # Treat CP as a strong contributor to the 'news' channel
    news_final = max(-1.0, min(1.0, 0.6*cp_sub + 0.4*scores_ws.get("news", 0.0)))
    scores = dict(scores_ws)  # copy
    scores["news"] = news_final
    scores["news_cp"] = cp_sub  # expose for transparency (optional)

    composite = composite_score(scores)
    regime = regime_from_composite(composite)
    guidance = default_guidance(regime)

    snapshot = {
        "at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "window": win,
        "scores": scores,
        "composite": composite,
        "regime": regime,
        "guidance": guidance,
        "items": items[:12],
        "notes": payload.get("notes", ""),
        "sources": {
            "cryptopanic_count": len(cp_posts)
        }
    }
    return JSONResponse(snapshot)

def failsafe_snapshot(reason: str):
    return {
        "at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "window": settings.DEFAULT_WINDOW,
        "scores": {"news":0, "macro":0, "geopolitics":0, "btc_eth_context":0},
        "composite": 0.0,
        "regime": "NEUTRAL",
        "guidance": default_guidance("NEUTRAL"),
        "items": [],
        "notes": f"Failsafe due to {reason}"
    }
