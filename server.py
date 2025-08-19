# server.py
import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")  # default wallet from env
MORALIS_BASE = "https://deep-index.moralis.io/api/v2.2"


@app.get("/")
@app.head("/")
def root():
    """Health check endpoint for Render."""
    return {"status": "running", "wallet": WALLET_ADDRESS}


@app.get("/ping")
def ping():
    return "pong"


@app.get("/tokens")
def get_tokens(chain: str = "eth"):
    """Get tokens for default env wallet."""
    if not WALLET_ADDRESS:
        return JSONResponse({"error": "Missing WALLET_ADDRESS"}, status_code=500)
    return fetch_tokens(WALLET_ADDRESS, chain)


@app.get("/tokens/{wallet}")
def get_tokens_for_wallet(wallet: str, chain: str = "eth"):
    """Get tokens for any given wallet."""
    return fetch_tokens(wallet, chain)


def fetch_tokens(wallet: str, chain: str):
    """Helper to fetch ERC20 balances from Moralis."""
    if not MORALIS_API_KEY:
        return JSONResponse({"error": "Missing MORALIS_API_KEY"}, status_code=500)

    url = f"{MORALIS_BASE}/wallets/{wallet}/erc20"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}

    try:
        r = requests.get(url, headers=headers, params={"chain": chain}, timeout=20)
        return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
