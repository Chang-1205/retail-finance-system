from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_conn
from models import LoginRequest, ThuRequest, ChiRequest, UpdateStatusRequest

app = FastAPI(title="ERP Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT username, role, full_name FROM users WHERE username=%s AND password=%s", (req.username, req.password))
    user = cur.fetchone()
    conn.close()
    if user:
        return {"success": True, "username": user[0], "role": user[1], "full_name": user[2]}
    raise HTTPException(status_code=401, detail="Sai thông tin đăng nhập")

@app.get("/api/thu")
def get_thu():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, ngay_tao, so_tien, ma_kenh, phuong_thuc, nguoi_nhap, trang_thai, ghi_chu FROM giao_dich_thu ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "ma_kenh": r[3], "phuong_thuc": r[4], "nguoi_nhap": r[5], "trang_thai": r[6], "ghi_chu": r[7]} for r in rows]

@app.post("/api/thu")
def create_thu(req: ThuRequest):
    conn = get_conn(); cur = conn.cursor()
    # Thêm RETURNING id để lấy mã phiếu vừa tạo
    cur.execute("INSERT INTO giao_dich_thu (so_tien, ma_kenh, phuong_thuc, nguoi_nhap, ghi_chu) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (req.so_tien, req.ma_kenh, req.phuong_thuc, req.nguoi_nhap, req.ghi_chu))
    new_id = cur.fetchone()[0]
    conn.commit(); conn.close()
    return {"message": "Tạo phiếu thu thành công", "id": new_id}

@app.put("/api/thu/status")
def update_thu_status(req: UpdateStatusRequest):
    conn = get_conn(); cur = conn.cursor()
    extra_note = f" | Hủy do: {req.ly_do}" if req.ly_do else ""
    cur.execute("UPDATE giao_dich_thu SET trang_thai=%s, ghi_chu=CONCAT(ghi_chu, %s) WHERE id=%s", (req.trang_thai, extra_note, req.id))
    conn.commit(); conn.close()
    return {"message": "Cập nhật trạng thái thu thành công"}

@app.get("/api/chi")
def get_chi():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, ngay_tao, ma_loai, so_tien, nguoi_de_xuat, trang_thai, nguoi_duyet, ghi_chu FROM giao_dich_chi ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ngay_tao": str(r[1]), "ma_loai": r[2], "so_tien": float(r[3]), "nguoi_de_xuat": r[4], "trang_thai": r[5], "nguoi_duyet": r[6], "ghi_chu": r[7]} for r in rows]

@app.post("/api/chi")
def create_chi(req: ChiRequest):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO giao_dich_chi (ma_loai, so_tien, nguoi_de_xuat, ghi_chu) VALUES (%s,%s,%s,%s) RETURNING id",
                (req.ma_loai, req.so_tien, req.nguoi_de_xuat, req.ghi_chu))
    new_id = cur.fetchone()[0]
    conn.commit(); conn.close()
    return {"message": "Tạo phiếu chi thành công", "id": new_id}

@app.put("/api/chi/status")
def update_chi_status(req: UpdateStatusRequest):
    conn = get_conn(); cur = conn.cursor()
    extra_note = f" | Từ chối: {req.ly_do}" if req.ly_do else ""
    cur.execute("UPDATE giao_dich_chi SET trang_thai=%s, nguoi_duyet=%s, ghi_chu=CONCAT(ghi_chu, %s) WHERE id=%s", 
                (req.trang_thai, req.nguoi_duyet, extra_note, req.id))
    conn.commit(); conn.close()
    return {"message": "Xử lý duyệt chi thành công"}

@app.get("/api/dashboard")
def get_dashboard():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT ngay, tong_thu, tong_chi_da_duyet, loi_nhuan, trang_thai_loi_nhuan FROM fact_tai_chinh ORDER BY ngay DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"ngay": str(r[0]), "tong_thu": float(r[1]), "tong_chi_da_duyet": float(r[2]), "loi_nhuan": float(r[3]), "trang_thai_loi_nhuan": r[4]} for r in rows]