import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

SUPPORTED_CHAINS = ["eth", "bsc", "base"]  # Always fetch from these chains

if not NOTION_API_KEY:
    raise RuntimeError("Missing NOTION_API_KEY environment variable")
if not MORALIS_API_KEY:
    raise RuntimeError("Missing MORALIS_API_KEY environment variable")
if not WALLET_ADDRESS:
    raise RuntimeError("Missing WALLET_ADDRESS environment variable")
if not NOTION_DATABASE_ID:
    raise RuntimeError("Missing NOTION_DATABASE_ID environment variable")

app = FastAPI()

def get_wallet_tokens():
    all_tokens = []
    for chain in SUPPORTED_CHAINS:
        url = f"https://deep-index.moralis.io/api/v2.2/{WALLET_ADDRESS}/erc20"
        headers = {"X-API-Key": MORALIS_API_KEY}
        params = {"chain": chain}
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        tokens = r.json()
        for token in tokens:
            token["chain"] = chain  # annotate with chain
        all_tokens.extend(tokens)
    return all_tokens

def update_notion(tokens):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    responses = []
    for token in tokens:
        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": token.get("name", "Unknown")}}]},
                "Symbol": {"rich_text": [{"text": {"content": token.get("symbol", "")}}]},
                "Balance": {
                    "number": float(token.get("balance", 0)) / (10 ** int(token.get("decimals", 0)))
                },
                "Chain": {"rich_text": [{"text": {"content": token.get("chain", "")}}]}
            }
        }
        res = requests.post(url, headers=headers, json=payload)
        responses.append(res.json())
    return responses

@app.post("/update_notion")
def update_notion_endpoint():
    try:
        tokens = get_wallet_tokens()
        notion_responses = update_notion(tokens)
        return JSONResponse(content={
            "status": "success",
            "tokens_sent": len(tokens),
            "notion_responses": notion_responses
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/")
def root():
    return {"message": "Moralis Portfolio Tracker API running"}
