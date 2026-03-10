from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas.transaction import TransactionCreate, TransactionInDB
from app.core import security
import random
from datetime import datetime

router = APIRouter()

# Mock DB
transactions_db = []

@router.post("/", response_model=TransactionInDB)
async def create_transaction(transaction: TransactionCreate):
    # TODO: Get current user ID from token
    user_id = "test_user_123" 
    
    new_transaction = TransactionInDB(
        **transaction.dict(),
        id="trans_" + str(random.randint(10000, 99999)),
        user_id=user_id,
        created_at=datetime.utcnow()
    )
    transactions_db.append(new_transaction)
    return new_transaction

@router.get("/", response_model=List[TransactionInDB])
async def list_transactions():
    return transactions_db

@router.get("/{transaction_id}", response_model=TransactionInDB)
async def get_transaction(transaction_id: str):
    for trans in transactions_db:
        if trans.id == transaction_id:
            return trans
    raise HTTPException(status_code=404, detail="Transaction not found")

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str):
    global transactions_db
    transactions_db = [t for t in transactions_db if t.id != transaction_id]
    return {"message": "Transaction deleted"}
