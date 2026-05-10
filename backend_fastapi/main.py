import random
import sys
import os
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_conn
from models import LoginRequest, ThuRequest, ChiRequest, UpdateStatusRequest, VoidRequest, BulkImportRequest, WebhookTransaction, CategoryCreateRequest

# Add parent directory to sys.path to import etl module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.etl import run_etl

app = FastAPI(title="Hệ thống ERP Finance API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def assert_category_update_allowed(role: str | None):
    if role not in ("KETOAN", "QUANLY"):
        raise HTTPException(status_code=403, detail="Chỉ KẾ TOÁN hoặc QUẢN LÝ mới được cập nhật danh mục.")

@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role, full_name FROM users WHERE username=%s AND password=%s", (req.username, req.password))
        user = cur.fetchone()
        conn.close()
    except psycopg2.Error as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi kết nối cơ sở dữ liệu: {exc.pgerror or exc}")

    if user:
        return {"success": True, "id": user[0], "username": user[1], "role": user[2], "full_name": user[3]}
    raise HTTPException(status_code=401, detail="Thông tin đăng nhập không hợp lệ")

@app.post("/api/thu")
def create_thu(req: ThuRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu, trang_thai, currency, kenh_mo_ta, pttt_mo_ta, voucher_percentage, mo_ta_giao_dich, tra_cham_tra_gop) VALUES (%s,%s,%s,%s,%s,%s,'CHỜ DUYỆT',%s,%s,%s,%s,%s,%s) RETURNING id",
        (req.so_tien, req.cua_hang_id, req.kenh_id, req.pttt_id, req.nguoi_tao_id, req.ghi_chu, req.currency, req.kenh_mo_ta, req.pttt_mo_ta, req.voucher_percentage, req.mo_ta_giao_dich, req.tra_cham_tra_gop)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"message": "Tạo chứng từ thành công", "id": new_id}


def build_order_id(platform: str, order_id: str | None):
    if order_id:
        return order_id
    return f"{platform[:3].upper()}-{random.randint(100000, 999999)}"


def record_webhook_transaction(platform: str, req: WebhookTransaction):
    conn = get_conn()
    cur = conn.cursor()
    order_id = build_order_id(platform, req.order_id)
    ghi_chu = f"[Webhook {platform}] Đơn {order_id}: {req.note}"
    cur.execute(
        "INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu, trang_thai, currency) VALUES (%s,%s,%s,%s,%s,%s,'HOÀN THÀNH', %s) RETURNING id",
        (
            req.amount,
            req.store_id or 1,
            req.channel_id or 1,
            req.payment_method_id or 1,
            1,
            ghi_chu,
            req.currency
        )
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return new_id

@app.post("/api/webhook/transaction")
def webhook_transaction(req: WebhookTransaction):
    new_id = record_webhook_transaction(req.platform, req)
    return {"message": "Giao dịch webhook đã được ghi nhận", "id": new_id}

@app.post("/api/webhook/shopee")
def webhook_shopee(req: WebhookTransaction):
    req.platform = "Shopee"
    req.channel_id = req.channel_id or 2
    req.payment_method_id = req.payment_method_id or 1
    new_id = record_webhook_transaction("Shopee", req)
    return {"message": "Giao dịch Shopee đã được ghi nhận", "id": new_id}

@app.post("/api/webhook/momo")
def webhook_momo(req: WebhookTransaction):
    req.platform = "Momo"
    req.channel_id = req.channel_id or 3
    req.payment_method_id = req.payment_method_id or 2
    new_id = record_webhook_transaction("Momo", req)
    return {"message": "Giao dịch Momo đã được ghi nhận", "id": new_id}

@app.post("/api/chi")
def create_chi(req: ChiRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO giao_dich_chi (loai_chi_id, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, trang_thai, ly_do_tu_choi, currency, kenh_mo_ta, pttt_mo_ta, voucher_percentage, mo_ta_giao_dich, tra_cham_tra_gop) VALUES (%s,%s,%s,%s,%s,%s,'CHỜ DUYỆT',%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (
            req.loai_chi_id,
            req.so_tien,
            req.cua_hang_id,
            req.kenh_id,
            req.pttt_id,
            req.nguoi_tao_id,
            req.ghi_chu,
            req.currency,
            req.kenh_mo_ta,
            req.pttt_mo_ta,
            req.voucher_percentage,
            req.mo_ta_giao_dich,
            req.tra_cham_tra_gop
        )
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
        SELECT c.id, c.ngay_tao, c.so_tien, l.ten_loai, u.full_name, c.ly_do_tu_choi, d.ten_cua_hang, k.ten_kenh, c.currency
        FROM giao_dich_chi c
        JOIN dim_loai_chi l ON c.loai_chi_id = l.id
        JOIN users u ON c.nguoi_tao_id = u.id
        LEFT JOIN dim_cua_hang d ON c.cua_hang_id = d.id
        LEFT JOIN dim_kenh_ban k ON c.kenh_id = k.id
        WHERE c.trang_thai = 'CHỜ DUYỆT' ORDER BY c.ngay_tao DESC
    """)
    rows = [
        {
            "id": r[0],
            "ngay_tao": str(r[1]),
            "so_tien": float(r[2]),
            "ten_loai": r[3],
            "nguoi_de_xuat": r[4],
            "ghi_chu": r[5],
            "cua_hang": r[6],
            "kenh": r[7],
            "currency": r[8] or 'VND'
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows

@app.get("/api/chi/processed")
def get_processed_chi():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.ngay_tao, c.so_tien, c.trang_thai, u.full_name, c.ly_do_tu_choi, c.currency
        FROM giao_dich_chi c JOIN users u ON c.nguoi_duyet_id = u.id
        WHERE c.trang_thai IN ('ĐÃ DUYỆT', 'TỪ CHỐI') ORDER BY c.ngay_tao DESC LIMIT 50
    """)
    rows = [
        {
            "id": r[0],
            "ngay_tao": str(r[1]),
            "so_tien": float(r[2]),
            "trang_thai": r[3],
            "nguoi_duyet": r[4],
            "ghi_chu": r[5],
            "currency": r[6] or 'VND'
        }
        for r in cur.fetchall()
    ]
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

@app.get("/api/thu/pending")
def get_pending_thu():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.ngay_tao, t.so_tien, d.ten_cua_hang, k.ten_kenh, p.ten_phuong_thuc, u.full_name, t.ghi_chu, t.currency "
        "FROM giao_dich_thu t "
        "LEFT JOIN dim_cua_hang d ON t.cua_hang_id = d.id "
        "LEFT JOIN dim_kenh_ban k ON t.kenh_id = k.id "
        "LEFT JOIN dim_phuong_thuc_tt p ON t.pttt_id = p.id "
        "LEFT JOIN users u ON t.nguoi_tao_id = u.id "
        "WHERE t.trang_thai = 'CHỜ DUYỆT' ORDER BY t.ngay_tao DESC"
    )
    rows = [{
        "id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "cua_hang": r[3], "kenh": r[4], "pttt": r[5], "nguoi_tao": r[6], "ghi_chu": r[7], "currency": r[8] or 'VND'
    } for r in cur.fetchall()]
    conn.close()
    return rows

@app.put("/api/thu/status")
def update_thu_status(req: UpdateStatusRequest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE giao_dich_thu SET trang_thai=%s, ly_do_huy=%s, nguoi_duyet_id=%s WHERE id=%s", (req.trang_thai, req.ly_do, req.nguoi_duyet_id, req.id))
    conn.commit()
    conn.close()
    return {"message": "Xử lý chứng từ thu thành công"}

@app.get("/api/thu/processed")
def get_processed_thu():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.ngay_tao, t.so_tien, t.trang_thai, u.full_name, t.ghi_chu, t.currency "
        "FROM giao_dich_thu t LEFT JOIN users u ON t.nguoi_duyet_id = u.id "
        "WHERE t.trang_thai IN ('ĐÃ DUYỆT', 'TỪ CHỐI') ORDER BY t.ngay_tao DESC LIMIT 50"
    )
    rows = [
        {
            "id": r[0],
            "ngay_tao": str(r[1]),
            "so_tien": float(r[2]),
            "trang_thai": r[3],
            "nguoi_duyet": r[4],
            "ghi_chu": r[5],
            "currency": r[6] or 'VND'
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows

@app.get("/api/voided")
def get_voided_records():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 'Thu' as loai, id, so_tien, currency, ly_do_huy FROM giao_dich_thu WHERE trang_thai='ĐÃ HỦY' 
        UNION 
        SELECT 'Chi' as loai, id, so_tien, currency, ly_do_huy FROM giao_dich_chi WHERE trang_thai='ĐÃ HỦY'
    """)
    rows = [
        {"loai": r[0], "id": r[1], "so_tien": float(r[2]), "currency": r[3] or 'VND', "ly_do": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return rows

@app.post("/api/import")
def bulk_import(req: BulkImportRequest):
    conn = get_conn()
    cur = conn.cursor()
    for item in req.data:
        if str(item.loai_giao_dich).upper() == 'THU':
            cur.execute(
                "INSERT INTO giao_dich_thu (so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu, trang_thai) VALUES (%s, 1, %s, %s, %s, %s, 'CHỜ DUYỆT')",
                (item.so_tien, item.ma_kenh_hoac_loai, item.pttt_id, item.nguoi_tao_id, item.ghi_chu)
            )
        else:
            cur.execute(
                "INSERT INTO giao_dich_chi (loai_chi_id, so_tien, pttt_id, nguoi_tao_id, trang_thai, ly_do_tu_choi) VALUES (%s, %s, %s, %s, 'CHỜ DUYỆT', %s)",
                (item.ma_kenh_hoac_loai, item.so_tien, item.pttt_id, item.nguoi_tao_id, item.ghi_chu)
            )
    conn.commit()
    conn.close()
    return {"message": f"Nạp thành công {len(req.data)} bản ghi vào hệ thống."}

@app.get("/api/dashboard")
def get_dashboard(start_date: str = None, end_date: str = None):
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT ngay_bao_cao, tong_thu, tong_chi, loi_nhuan, trang_thai_kd FROM fact_tai_chinh"
    conditions = []
    params = []
    if start_date:
        conditions.append("ngay_bao_cao >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("ngay_bao_cao <= %s")
        params.append(end_date)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ngay_bao_cao DESC"
    cur.execute(query, params)
    rows = [{"ngay": str(r[0]), "tong_thu": float(r[1]), "tong_chi_da_duyet": float(r[2]), "loi_nhuan": float(r[3]), "trang_thai_loi_nhuan": r[4]} for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/dashboard/last_update")
def get_dashboard_last_update():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MAX(ngay_bao_cao) FROM fact_tai_chinh")
    row = cur.fetchone()
    conn.close()
    return {"latest_update": str(row[0]) if row and row[0] else None}

@app.post("/api/etl")
def run_etl_endpoint():
    try:
        run_etl()
        return {"message": "ETL đã được thực thi thành công"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/thu/range")
def get_thu_range(start_date: str = None, end_date: str = None, start_time: str = "00:00", end_time: str = "23:59"):
    conn = get_conn()
    cur = conn.cursor()
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Yêu cầu start_date và end_date")
    start_stamp = f"{start_date} {start_time}"
    end_stamp = f"{end_date} {end_time}"
    cur.execute(
        "SELECT t.id, t.ngay_tao, t.so_tien, d.ten_cua_hang, k.ten_kenh, p.ten_phuong_thuc, u.full_name, t.ghi_chu, t.trang_thai "
        "FROM giao_dich_thu t "
        "LEFT JOIN dim_cua_hang d ON t.cua_hang_id = d.id "
        "LEFT JOIN dim_kenh_ban k ON t.kenh_id = k.id "
        "LEFT JOIN dim_phuong_thuc_tt p ON t.pttt_id = p.id "
        "LEFT JOIN users u ON t.nguoi_tao_id = u.id "
        "WHERE t.ngay_tao BETWEEN %s AND %s ORDER BY t.ngay_tao DESC",
        (start_stamp, end_stamp)
    )
    rows = [{
        "id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "cua_hang": r[3], "kenh": r[4], "pttt": r[5], "nguoi_tao": r[6], "ghi_chu": r[7], "trang_thai": r[8]
    } for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/chi/range")
def get_chi_range(start_date: str = None, end_date: str = None, start_time: str = "00:00", end_time: str = "23:59"):
    conn = get_conn()
    cur = conn.cursor()
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Yêu cầu start_date và end_date")
    start_stamp = f"{start_date} {start_time}"
    end_stamp = f"{end_date} {end_time}"
    cur.execute(
        "SELECT c.id, c.ngay_tao, c.so_tien, l.ten_loai, p.ten_phuong_thuc, u.full_name, c.ly_do_tu_choi, c.trang_thai "
        "FROM giao_dich_chi c "
        "LEFT JOIN dim_loai_chi l ON c.loai_chi_id = l.id "
        "LEFT JOIN dim_phuong_thuc_tt p ON c.pttt_id = p.id "
        "LEFT JOIN users u ON c.nguoi_tao_id = u.id "
        "WHERE c.ngay_tao BETWEEN %s AND %s ORDER BY c.ngay_tao DESC",
        (start_stamp, end_stamp)
    )
    rows = [{
        "id": r[0], "ngay_tao": str(r[1]), "so_tien": float(r[2]), "loai_chi": r[3], "pttt": r[4], "nguoi_tao": r[5], "ly_do_tu_choi": r[6], "trang_thai": r[7]
    } for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/thu/top_stores")
def get_top_stores(start_date: str = None, end_date: str = None, limit: int = 3):
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT d.ten_cua_hang, SUM(t.so_tien) as total FROM giao_dich_thu t LEFT JOIN dim_cua_hang d ON t.cua_hang_id = d.id"
    conditions = []
    params = []
    if start_date:
        conditions.append("t.ngay_tao >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("t.ngay_tao <= %s")
        params.append(end_date + ' 23:59:59')
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY d.ten_cua_hang ORDER BY total DESC LIMIT %s"
    params.append(limit)
    cur.execute(query, params)
    rows = [{"cua_hang": r[0], "tong_thu": float(r[1])} for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/chi/top_items")
def get_top_chi_items(start_date: str = None, end_date: str = None, limit: int = 3):
    conn = get_conn()
    cur = conn.cursor()
    query = "SELECT l.ten_loai, SUM(c.so_tien) as total FROM giao_dich_chi c LEFT JOIN dim_loai_chi l ON c.loai_chi_id = l.id WHERE c.trang_thai = 'ĐÃ DUYỆT'"
    params = []
    if start_date:
        query += " AND c.ngay_tao >= %s"
        params.append(start_date)
    if end_date:
        query += " AND c.ngay_tao <= %s"
        params.append(end_date + ' 23:59:59')
    query += " GROUP BY l.ten_loai ORDER BY total DESC LIMIT %s"
    params.append(limit)
    cur.execute(query, params)
    rows = [{"loai_chi": r[0], "tong_chi": float(r[1])} for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/generate_random_transactions")
def generate_random_transactions():
    import random
    from datetime import datetime
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.now().date()
    # Generate 20 thu
    for _ in range(20):
        so_tien = random.randint(100000, 5000000)  # 100k to 5M
        cua_hang_id = random.randint(1, 3)
        kenh_id = random.randint(1, 4)
        pttt_id = random.randint(1, 4)
        nguoi_tao_id = random.randint(1, 3)
        ghi_chu = f"Giao dịch ngẫu nhiên ngày {today}"
        cur.execute("INSERT INTO giao_dich_thu (ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu, trang_thai) VALUES (%s, %s, %s, %s, %s, %s, %s, 'HOÀN THÀNH')",
                    (datetime.combine(today, datetime.min.time()), so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, ghi_chu))
    # Generate 10 chi
    for _ in range(10):
        so_tien = random.randint(50000, 2000000)  # 50k to 2M
        loai_chi_id = random.randint(1, 5)
        pttt_id = random.randint(1, 4)
        nguoi_tao_id = random.randint(1, 3)
        ghi_chu = f"Chi phí ngẫu nhiên ngày {today}"
        cur.execute("INSERT INTO giao_dich_chi (ngay_tao, so_tien, loai_chi_id, pttt_id, nguoi_tao_id, trang_thai, nguoi_duyet_id, ly_do_tu_choi) VALUES (%s, %s, %s, %s, %s, 'ĐÃ DUYỆT', 2, %s)",
                    (datetime.combine(today, datetime.min.time()), so_tien, loai_chi_id, pttt_id, nguoi_tao_id, ghi_chu))
    conn.commit()
    conn.close()
    return {"message": "Đã tạo 20 phiếu thu và 10 phiếu chi ngẫu nhiên cho ngày hôm nay."}

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

@app.post("/api/dim_cua_hang")
def create_dim_cua_hang(req: CategoryCreateRequest, role: str | None = None):
    assert_category_update_allowed(role)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dim_cua_hang WHERE ten_cua_hang = %s", (req.name,))
    row = cur.fetchone()
    if row:
        dim_id = row[0]
    else:
        cur.execute("INSERT INTO dim_cua_hang (ten_cua_hang) VALUES (%s) RETURNING id", (req.name,))
        dim_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    return {"id": dim_id, "ten_cua_hang": req.name}

@app.post("/api/dim_kenh_ban")
def create_dim_kenh_ban(req: CategoryCreateRequest, role: str | None = None):
    assert_category_update_allowed(role)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dim_kenh_ban WHERE ten_kenh = %s", (req.name,))
    row = cur.fetchone()
    if row:
        dim_id = row[0]
    else:
        cur.execute("INSERT INTO dim_kenh_ban (ten_kenh) VALUES (%s) RETURNING id", (req.name,))
        dim_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    return {"id": dim_id, "ten_kenh": req.name}

@app.post("/api/dim_phuong_thuc_tt")
def create_dim_phuong_thuc_tt(req: CategoryCreateRequest, role: str | None = None):
    assert_category_update_allowed(role)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dim_phuong_thuc_tt WHERE ten_phuong_thuc = %s", (req.name,))
    row = cur.fetchone()
    if row:
        dim_id = row[0]
    else:
        cur.execute("INSERT INTO dim_phuong_thuc_tt (ten_phuong_thuc) VALUES (%s) RETURNING id", (req.name,))
        dim_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    return {"id": dim_id, "ten_phuong_thuc": req.name}

@app.post("/api/dim_loai_chi")
def create_dim_loai_chi(req: CategoryCreateRequest, role: str | None = None):
    assert_category_update_allowed(role)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM dim_loai_chi WHERE ten_loai = %s", (req.name,))
    row = cur.fetchone()
    if row:
        dim_id = row[0]
    else:
        cur.execute("INSERT INTO dim_loai_chi (ten_loai) VALUES (%s) RETURNING id", (req.name,))
        dim_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    return {"id": dim_id, "ten_loai": req.name}
