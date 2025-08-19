import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Load env vars (set these in Render)
# NOTION_API_KEY = os.getenv("NOTION_API_KEY")
# NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

# NOTION_HEADERS = {
#     "Authorization": f"Bearer {NOTION_API_KEY}",
#     "Content-Type": "application/json",
#     "Notion-Version": "2022-06-28"
# }

MORALIS_BASE = "https://deep-index.moralis.io/api/v2.2"

app = FastAPI()


def fetch_wallet_tokens(wallet: str, chain: str = "bsc"):
    """Fetch tokens from Moralis (explicit chain avoids fake/demo tokens)"""
    url = f"{MORALIS_BASE}/wallets/{wallet}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    resp = requests.get(url, headers=headers, params={"chain": chain}, timeout=20)

    if resp.status_code != 200:
        print("Moralis error:", resp.text)
        return []

    data = resp.json()
    return data.get("result", data if isinstance(data, list) else [])


# def push_to_notion(token):
#     """Send token data into Notion DB"""
#     name = token.get("name", "Unknown")
#     symbol = token.get("symbol", "")
#     balance_raw = float(token.get("balance", 0))
#     decimals = int(token.get("decimals", 0)) if token.get("decimals") else 0
# 
#     try:
#         balance = balance_raw / (10 ** decimals) if decimals > 0 else balance_raw
#     except Exception:
#         balance = balance_raw
# 
#     chain_display = token.get("token_address", "")[:6]  # crude fallback
# 
#     payload = {
#         "parent": {"database_id": NOTION_DATABASE_ID},
#         "properties": {
#             "Name": {"title": [{"text": {"content": name}}]},  # Title property
#             "Symbol": {"rich_text": [{"text": {"content": symbol}}]},
#             "Balance": {"number": balance},
#             "Chain": {"rich_text": [{"text": {"content": chain_display}}]}
#         }
#     }
# 
#     notion_url = "https://api.notion.com/v1/pages"
#     r = requests.post(notion_url, headers=NOTION_HEADERS, json=payload)
#     if r.status_code != 200:
#         print("Notion error:", r.text)
#     return r.json()


@app.get("/")
def home():
    return {"status": "running", "wallet": WALLET_ADDRESS}


@app.get("/moralis")
def moralis_only(chain: str = "bsc", wallet: str | None = None):
    """Return simplified balances (no Notion writes)."""
    w = wallet or WALLET_ADDRESS
    if not w:
        return JSONResponse({"error": "Missing wallet"}, status_code=400)

    tokens = fetch_wallet_tokens(w, chain=chain)
    parsed = []
    for t in tokens:
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
            "token_address": t.get("token_address"),
            "decimals": t.get("decimals"),
        })
    return {"wallet": w, "chain": chain, "count": len(parsed), "tokens": parsed}


@app.get("/moralis/raw")
def moralis_raw(chain: str = "bsc", wallet: str | None = None):
    """Return exact Moralis API JSON."""
    w = wallet or WALLET_ADDRESS
    if not w:
        return JSONResponse({"error": "Missing wallet"}, status_code=400)

    url = f"{MORALIS_BASE}/wallets/{w}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    r = requests.get(url, headers=headers, params={"chain": chain}, timeout=20)
    return JSONResponse(content=r.json(), status_code=r.status_code)
