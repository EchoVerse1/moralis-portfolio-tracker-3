import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

SUPPORTED_CHAINS = ["eth", "bsc", "base"]  # Always fetch from these chains

# Safety checks
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
        try:
            url = f"https://deep-index.moralis.io/api/v2.2/{WALLET_ADDRESS}/erc20"
            headers = {"X-API-Key": MORALIS_API_KEY}
            params = {"chain": chain}

            print(f"🔎 Fetching {chain} tokens for {WALLET_ADDRESS}...")
            r = requests.get(url, headers=headers, params=params)
            r.raise_for_status()

            tokens = r.json()
            print(f"✅ Got {len(tokens)} tokens from {chain}")

            for token in tokens:
                token["chain"] = chain  # annotate with chain
            all_tokens.extend(tokens)

        except Exception as e:
            print(f"⚠️ Error fetching from {chain}: {e}")

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
        try:
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
            if res.status_code != 200:
                print(f"⚠️ Notion API error: {res.status_code} {res.text}")
            responses.append(res.json())
        except Exception as e:
            print(f"⚠️ Failed to update Notion for token {token.get('symbol', '?')}: {e}")

    return responses

@app.post("/update_notion")
def update_notion_endpoint():
    try:
        print("🚀 Starting Notion update...")
        tokens = get_wallet_tokens()
        print(f"🔎 Total tokens fetched: {len(tokens)}")

        if not tokens:
            print("⚠️ No tokens found for this wallet!")
            return JSONResponse(content={"status": "success", "tokens_sent": 0, "message": "No tokens found"})

        notion_responses = update_notion(tokens)
        print("✅ Finished sending data to Notion")

        return JSONResponse(content={
            "status": "success",
            "tokens_sent": len(tokens),
            "notion_responses": notion_responses
        })
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/")
def root():
    return {"message": "Moralis Portfolio Tracker API running"}
