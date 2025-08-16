import os, requests, time
from datetime import datetime, timedelta
from urllib.parse import urlencode

def call_openai_web_search(model: str, api_key: str, queries, domains, window="2h"):
    SYSTEM = (
        "You are a crypto news sentinel for a trading system. "
        "Use web_search to find items from the last {window} about crypto market drivers, BTC/ETH movers, "
        "exchange incidents, regulation, ETF/macro prints. Return STRICT JSON with keys: "
        "`items` (<=12 of title,url,source,time,sentiment,impact,reason), "
        "`scores` (news,macro,geopolitics,btc_eth_context in [-1..+1]), and `notes`."
    ).format(window=window)

    user_text = (
        "Time window: last {window}. "
        "Domains (strict allow-list): {domains}. "
        "Queries: {queries}. "
        "Return JSON only, no prose."
    ).format(window=window, domains=", ".join(domains), queries=", ".join(queries))

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_text}
        ]
    }

    # Add retry logic for rate limiting
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload, timeout=120
            )
            r.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Rate limited, wait and retry
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                time.sleep(wait_time)
                continue
            else:
                # Print error details for debugging
                print(f"API Error {e.response.status_code}: {e.response.text}")
                raise
    data = r.json()
    
    # Extract the response content from the chat completions API
    if "choices" in data and len(data["choices"]) > 0:
        text = data["choices"][0]["message"]["content"]
    else:
        text = ""

    return text


def fetch_cryptopanic_posts(token: str, minutes: int = 120,
                            kind: str = "news", flt: str = "hot",
                            public: bool = True, page: int = 1, per_page: int = 50):
    base = "https://cryptopanic.com/api/developer/v2/posts/"
    since_iso = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat(timespec="seconds") + "Z"
    params = {
        "auth_token": token,
        "kind": kind,                 # news | media
        "filter": flt,                # hot | rising | bullish | bearish | important
        "public": "true" if public else "false",
        "page": page,
        "per_page": per_page
        # You can also add: currencies, regions, etc.
    }
    url = f"{base}?{urlencode(params)}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"CryptoPanic API request failed: {e}")
        return []
    except Exception as e:
        print(f"CryptoPanic API error: {e}")
        return []
    # Filter by time window ourselves to be safe:
    items = []
    for p in data.get("results", []):
        ts = p.get("published_at") or p.get("created_at")
        if not ts:
            continue
        if ts >= since_iso:
            items.append(p)
    return items
