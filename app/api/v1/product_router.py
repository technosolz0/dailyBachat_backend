from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
import uuid
from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter()

def get_current_user_id(x_user_id: str = Header(...)):
    return x_user_id

@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create business profile first")
        
    db_product = Product(
        id=str(uuid.uuid4()),
        business_id=profile.id,
        **product.dict()
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    search: str = None,
    min_price: float = None,
    max_price: float = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        return []
    
    query = db.query(Product).filter(Product.business_id == profile.id)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
        
    return query.all()

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Business profile not found")
        
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == profile.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Business profile not found")
        
    db_product = db.query(Product).filter(Product.id == product_id, Product.business_id == profile.id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    for key, value in product_update.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
        
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Business profile not found")
        
    db_product = db.query(Product).filter(Product.id == product_id, Product.business_id == profile.id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}
