from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryInDB, CategoryUpdate

router = APIRouter()

@router.post("/", response_model=CategoryInDB)
async def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    # Placeholder: In real app, get user_id from token
    user_id = "test_user" 
    db_category = Category(**category.dict(), user_id=user_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/", response_model=List[CategoryInDB])
async def list_categories(db: Session = Depends(get_db)):
    user_id = "test_user"
    return db.query(Category).filter(Category.user_id == user_id).all()

@router.put("/{category_id}", response_model=CategoryInDB)
@router.patch("/{category_id}", response_model=CategoryInDB)
async def update_category(category_id: int, category: CategoryUpdate, db: Session = Depends(get_db)):
    user_id = "test_user"
    db_category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    user_id = "test_user"
    db_category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted"}
