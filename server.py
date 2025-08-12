import os
from fastapi import FastAPI, HTTPException
from moralis import evm_api

app = FastAPI()

MORALIS_API = os.getenv("MORALIS_API")
if not MORALIS_API:
    raise RuntimeError("Missing MORALIS_API environment variable")

# Wallets to track
WALLETS = [
    "0x47C7c4E3b59D2C03E98bf54C104e7481474842E5",
    "0x980F71B0D813d6cC81a248e39964c8D1a7BE01E5",
]

# Moralis chain IDs
CHAINS = ["eth", "bsc", "polygon", "avalanche", "fantom", "arbitrum", "optimism"]

def get_balances_for_wallet(chain: str, address: str):
    try:
        data = evm_api.token.get_wallet_token_balances(
            api_key=MORALIS_API,
            params={"address": address, "chain": chain}
        )
        out = []
        for t in data:
            decimals = int(t.get("decimals") or 0) or 0
            raw = t.get("balance") or "0"
            try:
                balance = int(raw) / (10 ** decimals) if decimals > 0 else int(raw)
            except Exception:
                balance = 0
            out.append({
                "chain": chain,
                "wallet": address,
                "symbol": t.get("symbol"),
                "name": t.get("name"),
                "balance": balance
            })
        return out
    except Exception as e:
        print(f"[Moralis ERROR] {chain} - {address}: {e}")
        return []

@app.get("/")
def root():
    return {"message": "Moralis Portfolio Tracker (Python) is live 🚀"}

@app.get("/portfolio")
def portfolio():
    if not MORALIS_API:
        raise HTTPException(status_code=500, detail="MORALIS_API env var is missing on server")
    results = []
    for wallet in WALLETS:
        for chain in CHAINS:
            results.extend(get_balances_for_wallet(chain, wallet))
    return [r for r in results if r["balance"] and r["balance"] > 0]
