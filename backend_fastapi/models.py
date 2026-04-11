from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class ThuRequest(BaseModel):
    so_tien: float
    ma_kenh: str
    phuong_thuc: str
    nguoi_nhap: str
    ghi_chu: str

class ChiRequest(BaseModel):
    ma_loai: str
    so_tien: float
    nguoi_de_xuat: str
    ghi_chu: str

class UpdateStatusRequest(BaseModel):
    id: int
    trang_thai: str
    nguoi_duyet: Optional[str] = None
    ly_do: Optional[str] = ""