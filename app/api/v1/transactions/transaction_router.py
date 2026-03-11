from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionInDB, TransactionUpdate

router = APIRouter()

@router.post("/", response_model=TransactionInDB)
async def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    # Placeholder: In real app, get user_id from token
    user_id = "test_user" 
    db_transaction = Transaction(**transaction.dict(), user_id=user_id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.get("/", response_model=List[TransactionInDB])
async def list_transactions(db: Session = Depends(get_db)):
    user_id = "test_user"
    return db.query(Transaction).filter(Transaction.user_id == user_id).all()

@router.get("/{transaction_id}", response_model=TransactionInDB)
async def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    user_id = "test_user"
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str, db: Session = Depends(get_db)):
    user_id = "test_user"
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(db_transaction)
    db.commit()
    return {"message": "Transaction deleted"}

