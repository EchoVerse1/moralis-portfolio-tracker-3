import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from moralis import evm_api
import requests

app = FastAPI(
    title="Moralis Portfolio Tracker API",
    version="1.0.0",
    description="API to fetch wallet token balances using Moralis and update Notion"
)

MORALIS_API = os.getenv("MORALIS_API")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not MORALIS_API:
    raise RuntimeError("Missing MORALIS_API environment variable")
if not NOTION_API_KEY:
    raise RuntimeError("Missing NOTION_API_KEY environment variable")
if not NOTION_DATABASE_ID:
    raise RuntimeError("Missing NOTION_DATABASE_ID environment variable")

WALLETS = [
    "0x47C7c4E3b59D2C03E98bf54C104e7481474842E5",
    "0x980F71B0D813d6cC81a248e39964c8D1a7BE01E5",
]

CHAINS = ["eth", "bsc", "polygon", "avalanche", "fantom", "arbitrum", "optimism"]

class HealthCheckResponse(BaseModel):
    message: str

class TokenBalance(BaseModel):
    chain: str
    wallet: str
    symbol: Optional[str]
    name: Optional[str]
    balance: float

class NotionUpdateResponse(BaseModel):
    updated_pages: int

@app.get("/", response_model=HealthCheckResponse, operation_id="getRoot", summary="Health check endpoint")
def root():
    return HealthCheckResponse(message="Moralis Portfolio Tracker (Python) is live 🚀")

def get_balances_for_wallet(chain: str, address: str) -> List[TokenBalance]:
    try:
        data = evm_api.token.get_wallet_token_balances(
            api_key=MORALIS_API,
            params={"address": address, "chain": chain}
        )
        out = []
        for t in data:
            decimals = int(t.get("decimals") or 0)
            raw = t.get("balance") or "0"
            try:
                balance = int(raw) / (10 ** decimals) if decimals > 0 else int(raw)
            except Exception:
                balance = 0
            out.append(TokenBalance(
                chain=chain,
                wallet=address,
                symbol=t.get("symbol"),
                name=t.get("name"),
                balance=balance
            ))
        return out
    except Exception as e:
        print(f"[Moralis ERROR] {chain} - {address}: {e}")
        return []

@app.get("/portfolio", response_model=List[TokenBalance], operation_id="getPortfolio", summary="Get token balances for tracked wallets")
def portfolio():
    results = []
    for wallet in WALLETS:
        for chain in CHAINS:
            results.extend(get_balances_for_wallet(chain, wallet))
    return [r for r in results if r.balance > 0]

@app.post("/update_notion", response_model=NotionUpdateResponse, operation_id="updateNotion", summary="Push balances to Notion")
def update_notion():
    balances = []
    for wallet in WALLETS:
        for chain in CHAINS:
            balances.extend(get_balances_for_wallet(chain, wallet))

    updated_count = 0
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    for balance in balances:
        data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Wallet": {"title": [{"text": {"content": balance.wallet}}]},
                "Chain": {"rich_text": [{"text": {"content": balance.chain}}]},
                "Symbol": {"rich_text": [{"text": {"content": balance.symbol or ""}}]},
                "Balance": {"number": balance.balance},
            }
        }
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
        if response.ok:
            updated_count += 1
        else:
            print(f"Failed to update Notion page: {response.text}")

    return NotionUpdateResponse(updated_pages=updated_count)
