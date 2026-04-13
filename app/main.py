from fastapi import FastAPI
from app.webhook.router import router as webhook_router
from app.dashboard.router import router as dashboard_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.include_router(webhook_router)
app.include_router(dashboard_router)

@app.get("/health")
def health():
    return {"status": "ok"}