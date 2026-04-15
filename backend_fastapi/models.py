from pydantic import BaseModel
from typing import Optional, List

class LoginRequest(BaseModel):
    username: str
    password: str

class ThuRequest(BaseModel):
    so_tien: float
    cua_hang_id: int
    kenh_id: int
    pttt_id: int
    nguoi_tao_id: int
    ghi_chu: Optional[str] = ""

class ChiRequest(BaseModel):
    loai_chi_id: int
    so_tien: float
    pttt_id: int
    nguoi_tao_id: int
    ghi_chu: Optional[str] = ""

class UpdateStatusRequest(BaseModel):
    id: int
    trang_thai: str
    nguoi_duyet_id: int
    ly_do: Optional[str] = ""

class VoidRequest(BaseModel):
    id: int
    ly_do: str
    nguoi_huy_id: int

class BulkImportItem(BaseModel):
    loai_giao_dich: str
    so_tien: float
    ma_kenh_hoac_loai: int
    pttt_id: int
    nguoi_tao_id: int
    ghi_chu: Optional[str] = "Import từ hệ thống"

class BulkImportRequest(BaseModel):
    data: List[BulkImportItem]