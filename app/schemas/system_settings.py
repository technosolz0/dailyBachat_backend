from pydantic import BaseModel

from typing import List

class SystemSettingBase(BaseModel):
    key: str
    value: str

class SystemSettingResponse(SystemSettingBase):
    pass

class PremiumAmountUpdate(BaseModel):
    amount: int

class PremiumFeature(BaseModel):
    icon: str
    title: str
    subtitle: str

class PremiumFeaturesUpdate(BaseModel):
    features: List[PremiumFeature]

