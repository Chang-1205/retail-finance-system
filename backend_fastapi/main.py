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
    cur.execute("SELECT id, username, role, full_name FROM users WHERE username=%s AND password=%s", (req.username, req.password))
    user = cur.fetchone()
    conn.close()
    if user:
        return {"success": True, "id": user[0], "username": user[1], "role": user[2], "full_name": user[3]}
    raise HTTPException(status_code=401, detail="Sai thông tin đăng nhập")


@app.get("/api/thu")
def get_thu():
    conn = get_conn(); cur = conn.cursor()
    # Join với các bảng dimension để lấy tên thay vì ID
    query = """
        SELECT t.id, t.ngay_tao, t.so_tien, 
               ch.ten_cua_hang, k.ten_kenh, p.ten_phuong_thuc, 
               u.full_name, 'Đã thu' as trang_thai, '' as ghi_chu
        FROM giao_dich_thu t
        JOIN dim_cua_hang ch ON t.cua_hang_id = ch.id
        JOIN dim_kenh_ban k ON t.kenh_id = k.id
        JOIN dim_phuong_thuc_tt p ON t.pttt_id = p.id
        JOIN users u ON t.nguoi_tao_id = u.id
        ORDER BY t.id DESC
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), 
             "ma_kenh": r[4], "phuong_thuc": r[5], "nguoi_nhap": r[6], 
             "trang_thai": r[7], "ghi_chu": r[8]} for r in rows]


@app.post("/api/thu")
def create_thu(req: ThuRequest):
    conn = get_conn(); cur = conn.cursor()
    
    # Mapping từ frontend values sang database values
    kenh_mapping = {"POS": "POS Cửa hàng", "WEB": "Website", "APP": "Shopee/Tiktok"}
    pttt_mapping = {"TIỀN MẶT": "Tiền mặt/Voucher", "CHUYỂN KHOẢN": "Chuyển khoản (QR)", "QUẸT THẺ": "Thẻ tín dụng"}
    
    db_kenh = kenh_mapping.get(req.ma_kenh, req.ma_kenh)
    db_pttt = pttt_mapping.get(req.phuong_thuc, req.phuong_thuc)
    
    # Tìm ID từ tên
    cur.execute("SELECT id FROM dim_kenh_ban WHERE ten_kenh = %s", (db_kenh,))
    kenh_id = cur.fetchone()
    if not kenh_id: raise HTTPException(status_code=400, detail="Kênh bán không tồn tại")
    
    cur.execute("SELECT id FROM dim_phuong_thuc_tt WHERE ten_phuong_thuc = %s", (db_pttt,))
    pttt_id = cur.fetchone()
    if not pttt_id: raise HTTPException(status_code=400, detail="Phương thức thanh toán không tồn tại")
    
    cur.execute("SELECT id FROM users WHERE username = %s", (req.nguoi_nhap,))
    user_id = cur.fetchone()
    if not user_id: raise HTTPException(status_code=400, detail="Người dùng không tồn tại")
    
    # Chọn cửa hàng mặc định (có thể mở rộng sau)
    cua_hang_id = 1  # Default to first store
    
    # Thêm RETURNING id để lấy mã phiếu vừa tạo
    cur.execute("INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (req.so_tien, cua_hang_id, kenh_id[0], pttt_id[0], user_id[0]))
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
    # Join với các bảng dimension để lấy tên thay vì ID
    query = """
        SELECT c.id, c.ngay_tao, l.ten_loai, c.so_tien, 
               u1.full_name as nguoi_de_xuat, c.trang_thai,
               COALESCE(u2.full_name, '') as nguoi_duyet, c.ly_do_tu_choi
        FROM giao_dich_chi c
        JOIN dim_loai_chi l ON c.loai_chi_id = l.id
        JOIN users u1 ON c.nguoi_tao_id = u1.id
        LEFT JOIN users u2 ON c.nguoi_duyet_id = u2.id
        ORDER BY c.id DESC
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ngay_tao": str(r[1]), "ma_loai": r[2], "so_tien": float(r[3]), 
             "nguoi_de_xuat": r[4], "trang_thai": r[5], "nguoi_duyet": r[6], 
             "ghi_chu": r[7]} for r in rows]


@app.post("/api/chi")
def create_chi(req: ChiRequest):
    conn = get_conn(); cur = conn.cursor()
    
    # Mapping từ frontend values sang database values
    loai_mapping = {
        "NHAPHANG": "Chi phí Nhập hàng", 
        "MARKETING": "Chi phí Marketing", 
        "LUONG": "Chi phí Lương", 
        "VANHANH": "Chi phí Vận hành"
    }
    
    db_loai = loai_mapping.get(req.ma_loai, req.ma_loai)
    
    # Tìm ID từ tên
    cur.execute("SELECT id FROM dim_loai_chi WHERE ten_loai = %s", (db_loai,))
    loai_id = cur.fetchone()
    if not loai_id: raise HTTPException(status_code=400, detail="Loại chi không tồn tại")
    
    cur.execute("SELECT id FROM users WHERE username = %s", (req.nguoi_de_xuat,))
    user_id = cur.fetchone()
    if not user_id: raise HTTPException(status_code=400, detail="Người dùng không tồn tại")
    
    # Chọn phương thức thanh toán mặc định (có thể mở rộng sau)
    pttt_id = 1  # Default to first payment method
    
    cur.execute("INSERT INTO giao_dich_chi (loai_chi_id, so_tien, pttt_id, nguoi_tao_id, ly_do_tu_choi) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (loai_id[0], req.so_tien, pttt_id, user_id[0], req.ghi_chu))
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