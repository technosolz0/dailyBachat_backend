from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    icon: Optional[int] = None # codePoint
    color: Optional[str] = None # HEX string

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[int] = None
    color: Optional[str] = None

class CategoryInDB(CategoryBase):
    id: int
    user_id: str

    class Config:
        orm_mode = True
