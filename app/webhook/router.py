from fastapi import APIRouter, Request, HTTPException
from app.worker.tasks import review_pr
import hmac
import hashlib
import os
router = APIRouter()

@router.post("/webhook/github")
async def github_webhook(request : Request):
    raw = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    if(not verify_signature(raw , signature)):
        raise HTTPException(status_code=401 , detail="Invalid signature")
    payload = await request.json()
    print("Received GitHub webhook:", payload)
    if payload.get("action") not in ["opened", "synchronize"]:
        return {"received": True}

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pull_number = payload["pull_request"]["number"]
    head_sha = payload["pull_request"]["head"]["sha"]
    print(f"Enqueuing review task for PR #{pull_number} in {owner}/{repo}")
    review_pr.delay(owner, repo, pull_number, head_sha)

    return {"received": True}

def verify_signature(raw : bytes , signature: str) -> bool : 
    if not signature:
        return false
    secret = os.getenv("GITHUB_WEBHOOK_SECRET").encode()
    expected = "sha256=" + hmac.new(secret, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)