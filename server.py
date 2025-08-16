import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Load env vars (set these in Render)
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

MORALIS_BASE = "https://deep-index.moralis.io/api/v2.2"

app = FastAPI()


def fetch_wallet_tokens(wallet: str):
    """Fetch tokens from Moralis multichain balances"""
    url = f"{MORALIS_BASE}/{wallet}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        print("Moralis error:", resp.text)
        return []

    return resp.json()


def push_to_notion(token):
    """Send token data into Notion DB"""
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "")
    balance_raw = float(token.get("balance", 0))
    decimals = int(token.get("decimals", 0)) if token.get("decimals") else 0

    try:
        balance = balance_raw / (10 ** decimals) if decimals > 0 else balance_raw
    except Exception:
        balance = balance_raw

    chain_display = token.get("token_address", "")[:6]  # crude fallback

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {  # Title property
                "title": [{"text": {"content": name}}]
            },
            "Symbol": {
                "rich_text": [{"text": {"content": symbol}}]
            },
            "Balance": {
                "number": balance
            },
            "Chain": {
                "rich_text": [{"text": {"content": chain_display}}]
            }
        }
    }

    notion_url = "https://api.notion.com/v1/pages"
    r = requests.post(notion_url, headers=NOTION_HEADERS, json=payload)
    if r.status_code != 200:
        print("Notion error:", r.text)
    return r.json()


@app.get("/")
def home():
    return {"status": "running", "wallet": WALLET_ADDRESS}


@app.get("/sync")
def sync_wallet():
    """Fetch tokens from wallet via Moralis & push to Notion"""
    tokens = fetch_wallet_tokens(WALLET_ADDRESS)
    if not tokens:
        return JSONResponse(content={"error": "No tokens fetched"}, status_code=400)

    results = []
    for token in tokens:
        res = push_to_notion(token)
        results.append(res)

    return {"synced": len(results), "details": results}
