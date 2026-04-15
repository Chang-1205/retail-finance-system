import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_etl():
    print("\n[HỆ THỐNG] Tiến trình ETL đang khởi chạy...")
    try:
        conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), port=os.getenv("DB_PORT"))
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE fact_tai_chinh RESTART IDENTITY;")
       
        etl_query = """
        INSERT INTO fact_tai_chinh (ngay_bao_cao, tong_thu, tong_chi, loi_nhuan, trang_thai_kd)
        WITH Thu AS (
            SELECT DATE(ngay_tao) as ngay, SUM(so_tien) as tong_thu FROM giao_dich_thu WHERE trang_thai = 'HOÀN THÀNH' GROUP BY DATE(ngay_tao)
        ),
        Chi AS (
            SELECT DATE(ngay_tao) as ngay, SUM(so_tien) as tong_chi FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT' GROUP BY DATE(ngay_tao)
        ),
        NgayGD AS (
            SELECT DATE(ngay_tao) as ngay FROM giao_dich_thu WHERE trang_thai = 'HOÀN THÀNH' UNION SELECT DATE(ngay_tao) as ngay FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT'
        )
        SELECT n.ngay, COALESCE(t.tong_thu, 0), COALESCE(c.tong_chi, 0), (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)),
            CASE WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) > 0 THEN 'LÃI' WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) < 0 THEN 'LỖ' ELSE 'HÒA VỐN' END
        FROM NgayGD n LEFT JOIN Thu t ON n.ngay = t.ngay LEFT JOIN Chi c ON n.ngay = c.ngay;
        """
        cur.execute(etl_query)
        conn.commit()
        print(f"[THÀNH CÔNG] Đã đồng bộ {cur.rowcount} bản ghi vào Data Warehouse.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[LỖI HỆ THỐNG] {e}")

if __name__ == "__main__":
    run_etl()