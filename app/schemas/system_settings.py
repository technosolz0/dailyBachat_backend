from pydantic import BaseModel

class SystemSettingBase(BaseModel):
    key: str
    value: str

class SystemSettingResponse(SystemSettingBase):
    pass

class PremiumAmountUpdate(BaseModel):
    amount: int
