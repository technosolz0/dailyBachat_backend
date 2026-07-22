import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_
from app.core.database import get_db
from app.models.group_split import GroupSplit
from app.models.user import User
from app.schemas.group_split import GroupSplitCreate, GroupSplitInDB, GroupSplitUpdate
from app.core.security import get_current_user_id

router = APIRouter()

@router.post("/", response_model=GroupSplitInDB)
async def create_group_split(
    split: GroupSplitCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    split_dict = split.dict()
    split_dict['user_id'] = user_id
    if not split_dict.get('id'):
        split_dict['id'] = str(uuid.uuid4())
    
    # SQLAlchemy handles list of dicts directly into JSON column
    # Convert schemas in list to dictionary objects for SQL compatibility
    split_dict['members'] = [m.dict() for m in split.members]

    db_split = GroupSplit(**split_dict)
    db.add(db_split)
    db.commit()
    db.refresh(db_split)
    return db_split

@router.get("/", response_model=List[GroupSplitInDB])
async def list_group_splits(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # Fetch user's phone number to include splits they are added to by others
    current_user = db.query(User).filter(User.id == user_id).first()
    user_phone = current_user.phone_number if current_user else None

    # Retrieve group splits created by user
    splits = db.query(GroupSplit).filter(GroupSplit.user_id == user_id).all()
    
    # If the user has a phone number, search if they are a member of any other splits
    if user_phone:
        clean_phone = user_phone[-10:] if len(user_phone) >= 10 else user_phone
        
        all_splits = db.query(GroupSplit).all()
        for s in all_splits:
            if s.user_id == user_id:
                continue
            is_member = False
            for m in (s.members or []):
                m_phone = m.get('phone', '') if isinstance(m, dict) else getattr(m, 'phone', '')
                if m_phone and clean_phone in m_phone:
                    is_member = True
                    break
            if is_member and s not in splits:
                splits.append(s)

    # Sort descending
    splits.sort(key=lambda x: x.date or x.created_at, reverse=True)
    return splits

@router.get("/{split_id}", response_model=GroupSplitInDB)
async def get_group_split(
    split_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_split = db.query(GroupSplit).filter(GroupSplit.id == split_id).first()
    if not db_split:
        raise HTTPException(status_code=404, detail="Group split not found")
    return db_split

@router.put("/{split_id}", response_model=GroupSplitInDB)
@router.patch("/{split_id}", response_model=GroupSplitInDB)
async def update_group_split(
    split_id: str,
    split: GroupSplitUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_split = db.query(GroupSplit).filter(GroupSplit.id == split_id).first()
    if not db_split:
        raise HTTPException(status_code=404, detail="Group split not found")
    
    update_data = split.dict(exclude_unset=True)
    if 'members' in update_data and update_data['members'] is not None:
        update_data['members'] = [m.dict() for m in split.members]

    for key, value in update_data.items():
        setattr(db_split, key, value)
    
    db.commit()
    db.refresh(db_split)
    return db_split

@router.delete("/{split_id}")
async def delete_group_split(
    split_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_split = db.query(GroupSplit).filter(GroupSplit.id == split_id, GroupSplit.user_id == user_id).first()
    if not db_split:
        raise HTTPException(status_code=404, detail="Group split not found or unauthorized")
    
    db.delete(db_split)
    db.commit()
    return {"message": "Group split deleted successfully"}
