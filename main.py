# 기존
class ChargeData(BaseModel):
    message: str

# 변경
class ChargeData(BaseModel):
    message: str
    server_id: str = ""
    pw: str = ""
