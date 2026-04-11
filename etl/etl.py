import os
import psycopg2
from dotenv import load_dotenv

# Load cấu hình Supabase từ file .env
load_dotenv(".env")

def run_etl():
    print("🚀 Bắt đầu chạy luồng ETL tổng hợp dữ liệu...")
    try:
        # Tự động kết nối thẳng vào Supabase
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        
        # 1. Dọn dẹp kho Data Warehouse cũ
        cur.execute("TRUNCATE TABLE fact_tai_chinh;")
        
        # 2. Tổng hợp Thu - Chi và đẩy vào Kho
        etl_query = """
        INSERT INTO fact_tai_chinh (ngay, tong_thu, tong_chi_da_duyet, loi_nhuan, trang_thai_loi_nhuan)
        WITH Thu AS (
            SELECT ngay_tao, SUM(so_tien) as tong_thu 
            FROM giao_dich_thu 
            GROUP BY ngay_tao
        ),
        Chi AS (
            SELECT ngay_tao, SUM(so_tien) as tong_chi 
            FROM giao_dich_chi 
            WHERE trang_thai = 'ĐÃ DUYỆT'
            GROUP BY ngay_tao
        ),
        NgayGD AS (
            SELECT ngay_tao FROM giao_dich_thu
            UNION
            SELECT ngay_tao FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT'
        )
        SELECT 
            n.ngay_tao,
            COALESCE(t.tong_thu, 0) as tong_thu,
            COALESCE(c.tong_chi, 0) as tong_chi_da_duyet,
            (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) as loi_nhuan,
            CASE 
                WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) > 0 THEN 'LÃI'
                WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) < 0 THEN 'LỖ'
                ELSE 'HÒA VỐN'
            END as trang_thai_loi_nhuan
        FROM NgayGD n
        LEFT JOIN Thu t ON n.ngay_tao = t.ngay_tao
        LEFT JOIN Chi c ON n.ngay_tao = c.ngay_tao;
        """
        cur.execute(etl_query)
        conn.commit()
        
        print("✅ Chạy ETL thành công! Dữ liệu đã được nạp đầy vào Data Warehouse.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Lỗi ETL: {e}")

if __name__ == "__main__":
    run_etl()