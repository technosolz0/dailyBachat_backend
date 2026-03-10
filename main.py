from fastapi import FastAPI
from app.api.v1.auth import auth_router
from app.api.v1.transactions import transaction_router

app = FastAPI(title="DailyBachat API")

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(transaction_router.router, prefix="/api/v1/transactions", tags=["transactions"])

@app.get("/")
async def root():
    return {"message": "Welcome to DailyBachat API"}
