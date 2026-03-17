from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionInDB, TransactionUpdate

router = APIRouter()

import uuid

@router.post("/", response_model=TransactionInDB)
async def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    transaction_data = transaction.dict()
    if not transaction_data.get('id'):
        transaction_data['id'] = str(uuid.uuid4())
    
    db_transaction = Transaction(**transaction_data)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.get("/", response_model=List[TransactionInDB])
async def list_transactions(user_id: str, type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if type:
        query = query.filter(Transaction.type == type)
    return query.all()

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

