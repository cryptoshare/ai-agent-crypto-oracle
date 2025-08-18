import os, json, datetime as dt
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from settings import settings
from providers import call_openai_web_search, fetch_cryptopanic_posts, call_openai_analyze_posts
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
    cp_items = []  # Convert CP posts to items format
    cp_scores = {}  # Scores from ChatGPT analysis
    
    if settings.CRYPTOPANIC_TOKEN:
        try:
            cp_posts = fetch_cryptopanic_posts(
                token=settings.CRYPTOPANIC_TOKEN,
                minutes=settings.CRYPTOPANIC_WINDOW_MIN,
                kind=settings.CRYPTOPANIC_KIND,
                flt=settings.CRYPTOPANIC_FILTER,
                public=settings.CRYPTOPANIC_PUBLIC
            )
            
            if cp_posts:
                # Send CryptoPanic posts to ChatGPT for analysis
                try:
                    cp_raw = call_openai_analyze_posts(
                        model=settings.OPENAI_MODEL,
                        api_key=settings.OPENAI_API_KEY,
                        posts=cp_posts,
                        window=win
                    )
                    
                    # Parse ChatGPT's analysis of CryptoPanic posts
                    try:
                        cleaned_cp_raw = cp_raw.strip()
                        if cleaned_cp_raw.startswith("```json"):
                            cleaned_cp_raw = cleaned_cp_raw[7:]
                        if cleaned_cp_raw.endswith("```"):
                            cleaned_cp_raw = cleaned_cp_raw[:-3]
                        cleaned_cp_raw = cleaned_cp_raw.strip()
                        
                        cp_payload = json.loads(cleaned_cp_raw)
                        cp_items = cp_payload.get("items", [])
                        cp_scores = cp_payload.get("scores", {})
                        
                        # Update source to CryptoPanic for all items
                        for item in cp_items:
                            item["source"] = "CryptoPanic"
                            item["url"] = item.get("url", "")  # Keep original URL if provided
                        
                    except Exception as e:
                        print(f"CryptoPanic ChatGPT parse error: {e}")
                        # Fallback to simple keyword analysis
                        cp_sub = cryptopanic_subscore(cp_posts)
                        cp_items = []
                        
                except Exception as e:
                    print(f"CryptoPanic ChatGPT analysis error: {e}")
                    # Fallback to simple keyword analysis
                    cp_sub = cryptopanic_subscore(cp_posts)
                    cp_items = []
            
            # If no ChatGPT analysis, use simple scoring
            if not cp_items:
                cp_sub = cryptopanic_subscore(cp_posts)
                
        except Exception as e:
            print(f"CryptoPanic error: {e}")
            cp_posts = []
            cp_sub = 0.0

    # (C) Combine items from both sources
    all_items = items + cp_items
    
    # (D) Combine into final scores:
    # Use ChatGPT's analysis of CryptoPanic if available, otherwise use simple scoring
    if cp_scores:
        # Blend ChatGPT's analysis of both sources
        news_final = max(-1.0, min(1.0, 0.6*cp_scores.get("news", 0.0) + 0.4*scores_ws.get("news", 0.0)))
        macro_final = max(-1.0, min(1.0, 0.6*cp_scores.get("macro", 0.0) + 0.4*scores_ws.get("macro", 0.0)))
        geop_final = max(-1.0, min(1.0, 0.6*cp_scores.get("geopolitics", 0.0) + 0.4*scores_ws.get("geopolitics", 0.0)))
        ctx_final = max(-1.0, min(1.0, 0.6*cp_scores.get("btc_eth_context", 0.0) + 0.4*scores_ws.get("btc_eth_context", 0.0)))
        
        scores = {
            "news": news_final,
            "macro": macro_final,
            "geopolitics": geop_final,
            "btc_eth_context": ctx_final,
            "news_cp": cp_scores.get("news", 0.0),  # expose for transparency
            "news_openai": scores_ws.get("news", 0.0)  # expose for transparency
        }
    else:
        # Fallback to simple scoring
        news_final = max(-1.0, min(1.0, 0.6*cp_sub + 0.4*scores_ws.get("news", 0.0)))
        scores = dict(scores_ws)  # copy
        scores["news"] = news_final
        scores["news_cp"] = cp_sub  # expose for transparency

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
        "items": all_items[:20],  # Show up to 20 items total (OpenAI + CryptoPanic)
        "notes": payload.get("notes", ""),
        "sources": {
            "openai_count": len(items),
            "cryptopanic_count": len(cp_posts),
            "total_items": len(all_items)
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
