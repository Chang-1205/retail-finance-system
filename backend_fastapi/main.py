from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_conn
from models import LoginRequest, ThuRequest, ChiRequest, UpdateStatusRequest, VoidRequest, BulkImportRequest

app = FastAPI(title="Hệ thống ERP Finance API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, full_name FROM users WHERE username=%s AND password=%s", (req.username, req.password))
    user = cur.fetchone()
    conn.close()
    if user: return {"success": True, "id": user[0], "username": user[1], "role": user[2], "full_name": user[3]}
    raise HTTPException(status_code=401, detail="Thông tin đăng nhập không hợp lệ")

@app.post("/api/thu")
def create_thu(req: ThuRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (req.so_tien, req.cua_hang_id, req.kenh_id, req.pttt_id, req.nguoi_tao_id, req.ghi_chu)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"message": "Tạo chứng từ thành công", "id": new_id}

@app.post("/api/chi")
def create_chi(req: ChiRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO giao_dich_chi (loai_chi_id, so_tien, pttt_id, nguoi_tao_id, trang_thai, ly_do_tu_choi) VALUES (%s,%s,%s,%s,'CHỜ DUYỆT',%s) RETURNING id",
        (req.loai_chi_id, req.so_tien, req.pttt_id, req.nguoi_tao_id, req.ghi_chu)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"message": "Tạo chứng từ thành công", "id": new_id}

@app.get("/api/chi/pending")
def get_pending_chi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.ngay_tao, c.so_tien, l.ten_loai, u.full_name, c.ly_do_tu_choi
        FROM giao_dich_chi c JOIN dim_loai_chi l ON c.loai_chi_id = l.id JOIN users u ON c.nguoi_tao_id = u.id
        WHERE c.trang_thai = 'CHỜ DUYỆT' ORDER BY c.ngay_tao DESC
    """)
    rows = [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "ten_loai": r[3], "nguoi_de_xuat": r[4], "ghi_chu": r[5]} for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/chi/processed")
def get_processed_chi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.ngay_tao, c.so_tien, c.trang_thai, u.full_name, c.ly_do_tu_choi
        FROM giao_dich_chi c JOIN users u ON c.nguoi_duyet_id = u.id
        WHERE c.trang_thai IN ('ĐÃ DUYỆT', 'TỪ CHỐI') ORDER BY c.ngay_tao DESC LIMIT 50
    """)
    rows = [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "trang_thai": r[3], "nguoi_duyet": r[4], "ghi_chu": r[5]} for r in cur.fetchall()]
    conn.close()
    return rows

@app.put("/api/chi/status")
def update_chi_status(req: UpdateStatusRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE giao_dich_chi SET trang_thai=%s, ly_do_tu_choi=%s, nguoi_duyet_id=%s WHERE id=%s", (req.trang_thai, req.ly_do, req.nguoi_duyet_id, req.id))
    conn.commit()
    conn.close()
    return {"message": "Xử lý chứng từ thành công"}

@app.get("/api/thu/active")
def get_active_thu():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ngay_tao, so_tien, cua_hang_id FROM giao_dich_thu WHERE trang_thai = 'HOÀN THÀNH' ORDER BY ngay_tao DESC")
    rows = [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "thong_tin": f"Mã Đơn vị {r[3]}"} for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/chi/active")
def get_active_chi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ngay_tao, so_tien, loai_chi_id FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT' ORDER BY ngay_tao DESC")
    rows = [{"id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "thong_tin": f"Mã Hạng mục {r[3]}"} for r in cur.fetchall()]
    conn.close()
    return rows

@app.put("/api/thu/void")
def void_thu(req: VoidRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE giao_dich_thu SET trang_thai='ĐÃ HỦY', ly_do_huy=%s, nguoi_huy_id=%s WHERE id=%s", (req.ly_do, req.nguoi_huy_id, req.id))
    conn.commit()
    conn.close()
    return {"message": "Đã hủy chứng từ thu"}

@app.put("/api/chi/void")
def void_chi(req: VoidRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE giao_dich_chi SET trang_thai='ĐÃ HỦY', ly_do_huy=%s, nguoi_huy_id=%s WHERE id=%s", (req.ly_do, req.nguoi_huy_id, req.id))
    conn.commit()
    conn.close()
    return {"message": "Đã hủy chứng từ chi"}

@app.get("/api/voided")
def get_voided_records():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 'Thu' as loai, id, so_tien, ly_do_huy FROM giao_dich_thu WHERE trang_thai='ĐÃ HỦY' UNION SELECT 'Chi' as loai, id, so_tien, ly_do_huy FROM giao_dich_chi WHERE trang_thai='ĐÃ HỦY'")
    rows = [{"loai": r[0], "id": r[1], "so_tien": float(r[2]), "ly_do": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/import")
def bulk_import(req: BulkImportRequest):
    conn = get_conn()
    cur = conn.cursor()
    for item in req.data:
        if str(item.loai_giao_dich).upper() == 'THU':
            cur.execute("INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu) VALUES (%s, 1, %s, %s, %s, %s)",
                        (item.so_tien, item.ma_kenh_hoac_loai, item.pttt_id, item.nguoi_tao_id, item.ghi_chu))
        else:
            cur.execute("INSERT INTO giao_dich_chi (loai_chi_id, so_tien, pttt_id, nguoi_tao_id, trang_thai, ly_do_tu_choi) VALUES (%s, %s, %s, %s, 'ĐÃ DUYỆT', %s)",
                        (item.ma_kenh_hoac_loai, item.so_tien, item.pttt_id, item.nguoi_tao_id, item.ghi_chu))
    conn.commit()
    conn.close()
    return {"message": f"Nạp thành công {len(req.data)} bản ghi."}

@app.get("/api/dashboard")
def get_dashboard():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT ngay_bao_cao, tong_thu, tong_chi, loi_nhuan, trang_thai_kd FROM fact_tai_chinh ORDER BY ngay_bao_cao DESC")
    rows = [{"ngay": str(r[0]), "tong_thu": float(r[1]), "tong_chi_da_duyet": float(r[2]), "loi_nhuan": float(r[3]), "trang_thai_loi_nhuan": r[4]} for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/users")
def get_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, full_name FROM users")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "role": r[2], "full_name": r[3]} for r in rows]

@app.get("/api/dim_cua_hang")
def get_dim_cua_hang():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ten_cua_hang FROM dim_cua_hang")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ten_cua_hang": r[1]} for r in rows]

@app.get("/api/dim_kenh_ban")
def get_dim_kenh_ban():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ten_kenh FROM dim_kenh_ban")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ten_kenh": r[1]} for r in rows]

@app.get("/api/dim_phuong_thuc_tt")
def get_dim_phuong_thuc_tt():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ten_phuong_thuc FROM dim_phuong_thuc_tt")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ten_phuong_thuc": r[1]} for r in rows]

@app.get("/api/dim_loai_chi")
def get_dim_loai_chi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ten_loai FROM dim_loai_chi")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ten_loai": r[1]} for r in rows]