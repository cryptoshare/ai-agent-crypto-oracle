from math import exp
from typing import List, Dict

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def weighted_mean(pairs):
    num = sum(v*w for v,w in pairs)
    den = sum(w for _,w in pairs) or 1e-9
    return num / den

def normalize_items(items: List[Dict]) -> Dict[str, float]:
    """items: list of {sentiment [-1..1], impact [0..1], source/topic optional}"""
    # Partition items by rough theme using simple keywords (MVP):
    news_pairs, macro_pairs, geo_pairs, ctx_pairs = [], [], [], []
    for it in items:
        s = clamp(float(it.get("sentiment", 0)), -1, 1)
        w = clamp(float(it.get("impact", 0.5)), 0, 1)
        title = (it.get("title") or "").lower()
        reason = (it.get("reason") or "").lower()
        txt = f"{title} {reason}"

        if any(k in txt for k in ["cpi","inflation","fed","pce","jobs","nfp","unemployment"]):
            macro_pairs.append((s, w))
        elif any(k in txt for k in ["war","sanction","geopolitic","conflict"]):
            geo_pairs.append((s, w))
        elif any(k in txt for k in ["btc","bitcoin","eth","ethereum","funding","open interest","driver"]):
            ctx_pairs.append((s, w))
        else:
            news_pairs.append((s, w))

    news = clamp(weighted_mean(news_pairs) if news_pairs else 0.0, -1, 1)
    macro = clamp(weighted_mean(macro_pairs) if macro_pairs else 0.0, -1, 1)
    geop = clamp(weighted_mean(geo_pairs) if geo_pairs else 0.0, -1, 1)
    ctx  = clamp(weighted_mean(ctx_pairs)  if ctx_pairs  else 0.0, -1, 1)
    return {"news": news, "macro": macro, "geopolitics": geop, "btc_eth_context": ctx}

def composite_score(scores: Dict[str,float]) -> float:
    c = 0.40*scores["news"] + 0.20*scores["macro"] + 0.10*scores["geopolitics"] + 0.30*scores["btc_eth_context"]
    return clamp(c, -1, 1)

def regime_from_composite(c: float) -> str:
    if c > 0.25: return "RISK_ON"
    if c < -0.25: return "RISK_OFF"
    return "NEUTRAL"

def default_guidance(regime: str):
    if regime == "RISK_ON":
        return dict(allow_new_trades=True, direction_bias="both", risk_budget_pct=0.40, daily_dd_cap_pct=2.0, max_leverage=4.0, do_not_trade_until=None)
    if regime == "RISK_OFF":
        return dict(allow_new_trades=False, direction_bias="short_only", risk_budget_pct=0.20, daily_dd_cap_pct=2.0, max_leverage=2.0, do_not_trade_until=None)
    return dict(allow_new_trades=True, direction_bias="both", risk_budget_pct=0.30, daily_dd_cap_pct=2.0, max_leverage=3.0, do_not_trade_until=None)


# CryptoPanic scoring functions
def cp_tag_weight(tags: list[str]) -> float:
    # Tune these gradually
    weights = {
        "hack": -0.8, "exploit": -0.7, "scam": -0.6, "delist": -0.6, "halt": -0.6, "lawsuit": -0.5,
        "regulation": -0.3, "ban": -0.4,
        "upgrade": 0.3, "partnership": 0.2, "etf": 0.4, "listing": 0.15
    }
    return sum(weights.get(t.lower(), 0.0) for t in tags or [])


def cp_vote_score(votes: dict) -> float:
    # CryptoPanic exposes vote counts (e.g., important/bullish/bearish)
    # Map to [-1..+1] using simple net / total:
    bullish = float(votes.get("positive", 0) + votes.get("bullish", 0))
    bearish = float(votes.get("negative", 0) + votes.get("bearish", 0))
    total = bullish + bearish
    if total <= 0: return 0.0
    net = bullish - bearish
    # clamp to [-1,1] softly
    return max(-1.0, min(1.0, net / total))


def cryptopanic_subscore(posts: list[dict]) -> float:
    pairs = []
    for p in posts:
        # Extract title and description for sentiment analysis
        title = p.get("title", "") or ""
        description = p.get("description", "") or ""
        text = f"{title} {description}".lower()
        
        # Simple keyword-based sentiment (since we don't have tags/votes in v2 API)
        base = 0.0
        positive_keywords = ["surge", "bullish", "rally", "breakout", "high", "gain", "up", "positive", "etf", "approval", "partnership"]
        negative_keywords = ["drop", "bearish", "crash", "fall", "low", "loss", "down", "negative", "hack", "exploit", "breach", "delay"]
        
        pos_count = sum(1 for word in positive_keywords if word in text)
        neg_count = sum(1 for word in negative_keywords if word in text)
        
        if pos_count > neg_count:
            base = min(0.8, (pos_count - neg_count) * 0.2)
        elif neg_count > pos_count:
            base = max(-0.8, (neg_count - pos_count) * -0.2)
        
        # freshness: newer posts get more weight (half-life ~ 6h for 24h delay)
        freshness_w = 1.0
        try:
            from datetime import datetime, timezone
            ts = p.get("published_at") or p.get("created_at")
            dtp = datetime.fromisoformat(ts.replace("Z","+00:00"))
            minutes = (datetime.now(timezone.utc) - dtp).total_seconds()/60.0
            freshness_w = pow(0.5, minutes/360.0)  # 6-hour half-life
        except Exception:
            pass

        sent = max(-1.0, min(1.0, base))
        w = freshness_w
        pairs.append((sent, max(0.05, w)))
    if not pairs:
        return 0.0
    return max(-1.0, min(1.0, weighted_mean(pairs)))
