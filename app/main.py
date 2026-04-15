from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.core.database import engine, Base
import app.models

# Explicitly import the router modules
from app.api.v1.auth import auth_router
from app.api.v1.transactions import transaction_router
from app.api.v1.categories import category_router
from app.api.v1.loans import loan_router
from app.api.v1 import (
    business_router, invoice_router, product_router, 
    feedback_router, notification_router, admin_router,
    payment_router
)
from app.api.v1.whatsapp_router import router as whatsapp_router
from app.core.firebase_config import initialize_firebase
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.notification_service import process_reminders
from app.core.database import SessionLocal

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize Firebase
initialize_firebase()

# Initialize Scheduler
scheduler = BackgroundScheduler()

def scheduled_reminders():
    db = SessionLocal()
    try:
        process_reminders(db)
    finally:
        db.close()

# Run once every hour for timely reminder delivery (2-day, 1-day, due-date windows)
scheduler.add_job(scheduled_reminders, 'interval', hours=1)
scheduler.start()

app = FastAPI(title="DailyBachat API")

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    os.makedirs(os.path.join(UPLOAD_DIR, "business_logos"))

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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
app.include_router(admin_router.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(payment_router.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(whatsapp_router, prefix="/api/v1/whatsapp", tags=["whatsapp"])

@app.get("/")
async def root():
    return {"message": "Welcome to DailyBachat API"}
