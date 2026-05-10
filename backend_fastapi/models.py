from pydantic import BaseModel, validator
from typing import Optional, List

ALLOWED_CURRENCIES = {"VND", "USD"}

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
    currency: str = "VND"
    kenh_mo_ta: Optional[str] = None
    pttt_mo_ta: Optional[str] = None
    voucher_percentage: Optional[int] = None
    mo_ta_giao_dich: Optional[str] = None
    tra_cham_tra_gop: Optional[str] = None

    @validator("so_tien")
    def so_tien_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Giá trị phải lớn hơn 0")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        if v is None:
            return "VND"
        currency = v.strip().upper()
        if currency not in ALLOWED_CURRENCIES:
            raise ValueError("Đơn vị tiền tệ chỉ chấp nhận VND hoặc USD")
        return currency

class WebhookTransaction(BaseModel):
    platform: Optional[str] = "Webhook"
    order_id: Optional[str] = None
    amount: float
    store_id: Optional[int] = 1
    channel_id: Optional[int] = 1
    payment_method_id: Optional[int] = 1
    note: Optional[str] = ""
    currency: str = "VND"

    @validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Giá trị phải lớn hơn 0")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        if v is None:
            return "VND"
        currency = v.strip().upper()
        if currency not in ALLOWED_CURRENCIES:
            raise ValueError("Đơn vị tiền tệ chỉ chấp nhận VND hoặc USD")
        return currency

class CategoryCreateRequest(BaseModel):
    name: str

class ChiRequest(BaseModel):
    loai_chi_id: int
    so_tien: float
    cua_hang_id: Optional[int] = None
    kenh_id: Optional[int] = None
    pttt_id: int
    nguoi_tao_id: int
    ghi_chu: Optional[str] = ""
    currency: str = "VND"
    kenh_mo_ta: Optional[str] = None
    pttt_mo_ta: Optional[str] = None
    voucher_percentage: Optional[int] = None
    mo_ta_giao_dich: Optional[str] = None
    tra_cham_tra_gop: Optional[str] = None

    @validator("so_tien")
    def so_tien_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Giá trị phải lớn hơn 0")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        if v is None:
            return "VND"
        currency = v.strip().upper()
        if currency not in ALLOWED_CURRENCIES:
            raise ValueError("Đơn vị tiền tệ chỉ chấp nhận VND hoặc USD")
        return currency

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
    currency: str = "VND"

class BulkImportRequest(BaseModel):
    data: List[BulkImportItem]