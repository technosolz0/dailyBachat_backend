from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
import app.models

# Explicitly import the router modules
from app.api.v1.auth import auth_router
from app.api.v1.transactions import transaction_router
from app.api.v1.categories import category_router
from app.api.v1.loans import loan_router
from app.api.v1 import business_router, invoice_router, product_router, feedback_router, notification_router
from app.core.firebase_config import initialize_firebase

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize Firebase
initialize_firebase()

app = FastAPI(title="DailyBachat API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - Updated prefix to /auth to match Flutter logs
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(transaction_router.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(category_router.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(loan_router.router, prefix="/api/v1/loans", tags=["loans"])
app.include_router(business_router.router, prefix="/api/v1/business", tags=["business"])
app.include_router(invoice_router.router, prefix="/api/v1/business", tags=["billing"])
app.include_router(product_router.router, prefix="/api/v1/business/inventory", tags=["inventory"])
app.include_router(feedback_router.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(notification_router.router, prefix="/api/v1/notifications", tags=["notifications"])

@app.get("/")
async def root():
    return {"message": "Welcome to DailyBachat API"}
