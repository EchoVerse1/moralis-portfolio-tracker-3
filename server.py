import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
MORALIS_BASE = "https://deep-index.moralis.io/api/v2.2"


@app.get("/")
@app.head("/")   # ✅ handle HEAD so Render health checks pass
def home():
    return {"status": "running", "wallet": WALLET_ADDRESS}


@app.get("/ping")
def ping():
    return "pong"


@app.get("/moralis/raw")
def moralis_raw(chain: str = "bsc", wallet: str | None = None):
    """Return raw Moralis balances (exact API output)."""
    w = wallet or WALLET_ADDRESS
    if not w:
        return JSONResponse({"error": "Missing wallet"}, status_code=400)
    if not MORALIS_API_KEY:
        return JSONResponse({"error": "Missing MORALIS_API_KEY"}, status_code=500)

    url = f"{MORALIS_BASE}/wallets/{w}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    r = requests.get(url, headers=headers, params={"chain": chain}, timeout=20)
    return JSONResponse(content=r.json(), status_code=r.status_code)


@app.get("/moralis")
def moralis_parsed(chain: str = "bsc", wallet: str | None = None):
    """Return simplified, human-readable balances."""
    w = wallet or WALLET_ADDRESS
    if not w:
        return JSONResponse({"error": "Missing wallet"}, status_code=400)
    if not MORALIS_API_KEY:
        return JSONResponse({"error": "Missing MORALIS_API_KEY"}, status_code=500)

    url = f"{MORALIS_BASE}/wallets/{w}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    r = requests.get(url, headers=headers, params={"chain": chain}, timeout=20)
    if r.status_code != 200:
        return JSONResponse({"error": r.text}, status_code=r.status_code)

    data = r.json()
    items = data.get("result", data if isinstance(data, list) else [])

    parsed = []
    for t in items:
        try:
            raw = float(t.get("balance", 0))
            decimals = int(t.get("decimals", 0) or 0)
            balance = raw / (10 ** decimals) if decimals else raw
        except Exception:
            balance = t.get("balance")
        parsed.append({
            "name": t.get("name"),
            "symbol": t.get("symbol"),
            "balance": balance,
            "balance_raw": t.get("balance"),
            "decimals": t.get("decimals"),
            "token_address": t.get("token_address"),
        })

    return {"wallet": w, "chain": chain, "count": len(parsed), "tokens": parsed}
