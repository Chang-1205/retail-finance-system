import psycopg2
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def insert_sample_data():
    """Tạo dữ liệu mẫu cho biểu đồ"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT"),
            sslmode="require"
        )
        cur = conn.cursor()
        
        # Tạo 5 Phiếu Thu với số tiền lớn (vài chục triệu)
        print("📝 Đang tạo Phiếu Thu...")
        thu_data = [
            (datetime(2026, 4, 16, 9, 30), 25000000, 1, 1, 1, 1, "HOÀN THÀNH", "Thu từ đơn hàng lớn"),
            (datetime(2026, 4, 16, 10, 45), 18500000, 2, 2, 2, 1, "HOÀN THÀNH", "Thu qua website"),
            (datetime(2026, 4, 16, 14, 20), 42300000, 1, 3, 3, 1, "HOÀN THÀNH", "Thu từ Shopee"),
            (datetime(2026, 4, 16, 15, 15), 31700000, 2, 1, 1, 1, "HOÀN THÀNH", "Thu từ cửa hàng khác"),
            (datetime(2026, 4, 16, 16, 40), 28900000, 1, 2, 2, 1, "HOÀN THÀNH", "Thu từ TikTok Shop"),
        ]
        
        for ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, trang_thai, ghi_chu in thu_data:
            cur.execute(
                """INSERT INTO giao_dich_thu (ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, trang_thai, ghi_chu) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, trang_thai, ghi_chu)
            )
        
        # Tạo 5 Phiếu Chi với số tiền vài triệu
        print("📝 Đang tạo Phiếu Chi...")
        chi_data = [
            (datetime(2026, 4, 16, 11, 0), 5200000, 1, 2, 1, "ĐÃ DUYỆT", 2, "Chi phí nhập hàng"),
            (datetime(2026, 4, 16, 12, 30), 3450000, 2, 1, 1, "ĐÃ DUYỆT", 2, "Chi phí lương nhân viên"),
            (datetime(2026, 4, 16, 13, 45), 2800000, 3, 2, 1, "CHỜ DUYỆT", None, "Chi phí tiếp thị"),
            (datetime(2026, 4, 16, 14, 50), 4100000, 4, 3, 1, "CHỜ DUYỆT", None, "Chi phí vận hành"),
            (datetime(2026, 4, 16, 15, 30), 1900000, 1, 1, 1, "ĐÃ DUYỆT", 2, "Chi phí hành chính"),
        ]
        
        for ngay_tao, so_tien, loai_chi_id, pttt_id, nguoi_tao_id, trang_thai, nguoi_duyet_id, ghi_chu in chi_data:
            cur.execute(
                """INSERT INTO giao_dich_chi (ngay_tao, so_tien, loai_chi_id, pttt_id, nguoi_tao_id, trang_thai, nguoi_duyet_id, ly_do_tu_choi) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (ngay_tao, so_tien, loai_chi_id, pttt_id, nguoi_tao_id, trang_thai, nguoi_duyet_id, ghi_chu)
            )
        
        conn.commit()
        print("✅ Đã tạo thành công 5 Phiếu Thu và 5 Phiếu Chi!")
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    insert_sample_data()
