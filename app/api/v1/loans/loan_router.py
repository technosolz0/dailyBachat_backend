import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.loan import Loan
from app.schemas.loan import LoanCreate, LoanInDB, LoanUpdate
from app.core.security import get_current_user_id

router = APIRouter()

@router.post("/", response_model=LoanInDB)
async def create_loan(
    loan: LoanCreate, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    loan_dict = loan.dict()
    loan_dict['user_id'] = user_id
    if not loan_dict.get('id'):
        loan_dict['id'] = str(uuid.uuid4())
    
    db_loan = Loan(**loan_dict)
    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan

@router.get("/", response_model=List[LoanInDB])
async def list_loans(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return db.query(Loan).filter(Loan.user_id == user_id).all()

@router.get("/{loan_id}", response_model=LoanInDB)
async def get_loan(
    loan_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_loan = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == user_id).first()
    if not db_loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return db_loan

@router.put("/{loan_id}", response_model=LoanInDB)
async def update_loan(
    loan_id: str, 
    loan: LoanUpdate, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_loan = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == user_id).first()
    if not db_loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    update_data = loan.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_loan, key, value)
    
    db.commit()
    db.refresh(db_loan)
    return db_loan

@router.delete("/{loan_id}")
async def delete_loan(
    loan_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_loan = db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == user_id).first()
    if not db_loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    db.delete(db_loan)
    db.commit()
    return {"message": "Loan deleted"}
