from fastapi import FastAPI
from app.core.database import engine, Base
import app.models # Import models to register them with Base
from app.api.v1.auth import auth_router
from app.api.v1.transactions import transaction_router
from app.api.v1.categories import category_router
from app.api.v1.loans import loan_router
from app.api.v1 import business_router, invoice_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DailyBachat API")

app.include_router(auth_router.router, prefix="/api/v1/user", tags=["user"])
app.include_router(transaction_router.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(category_router.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(loan_router.router, prefix="/api/v1/loans", tags=["loans"])
app.include_router(business_router.router, prefix="/api/v1/business", tags=["business"])
app.include_router(invoice_router.router, prefix="/api/v1/business", tags=["billing"])

@app.get("/")
async def root():
    return {"message": "Welcome to DailyBachat API"}
