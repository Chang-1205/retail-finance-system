# import os
# import psycopg2
# from dotenv import load_dotenv

# load_dotenv()  # Load .env from project root

# def run_etl():
#     print("\n=======================================================")
#     print("🚀 ĐANG KHỞI ĐỘNG LUỒNG ETL TỔNG HỢP DỮ LIỆU DATA WAREHOUSE...")
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), port=os.getenv("DB_PORT")
#         )
#         cur = conn.cursor()
        
#         print("🧹 Đang dọn dẹp kho lưu trữ cũ (TRUNCATE)...")
#         cur.execute("TRUNCATE TABLE fact_tai_chinh RESTART IDENTITY;")
       
#         etl_query = """
#         INSERT INTO fact_tai_chinh (ngay_bao_cao, tong_thu, tong_chi, loi_nhuan, trang_thai_kd)
#         WITH Thu AS (
#             SELECT DATE(ngay_tao) as ngay, SUM(so_tien) as tong_thu FROM giao_dich_thu GROUP BY DATE(ngay_tao)
#         ),
#         Chi AS (
#             SELECT DATE(ngay_tao) as ngay, SUM(so_tien) as tong_chi FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT' GROUP BY DATE(ngay_tao)
#         ),
#         NgayGD AS (
#             SELECT DATE(ngay_tao) as ngay FROM giao_dich_thu UNION SELECT DATE(ngay_tao) as ngay FROM giao_dich_chi WHERE trang_thai = 'ĐÃ DUYỆT'
#         )
#         SELECT n.ngay, COALESCE(t.tong_thu, 0), COALESCE(c.tong_chi, 0),
#             (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) as loi_nhuan,
#             CASE 
#                 WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) > 0 THEN 'LÃI'
#                 WHEN (COALESCE(t.tong_thu, 0) - COALESCE(c.tong_chi, 0)) < 0 THEN 'LỖ'
#                 ELSE 'HÒA VỐN'
#             END
#         FROM NgayGD n LEFT JOIN Thu t ON n.ngay = t.ngay LEFT JOIN Chi c ON n.ngay = c.ngay;
#         """
#         cur.execute(etl_query)
#         rows_inserted = cur.rowcount # Lấy động số lượng bản ghi tổng hợp
#         conn.commit()
        
#         print(f"✅ ETL HOÀN TẤT! Đã đồng bộ thành công {rows_inserted} dòng báo cáo theo ngày.")
#         print("=======================================================\n")
#         cur.close()
#         conn.close()
#     except Exception as e:
#         print(f"❌ Lỗi xử lý ETL: {e}")

# if __name__ == "__main__":
#     run_etl()