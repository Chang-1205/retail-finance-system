# import os
# import psycopg2
# import pandas as pd
# from dotenv import load_dotenv

# load_dotenv()  # Load .env from project root

# def get_payment_value(order_id):
#     """Get payment value for an order from payments CSV"""
#     try:
#         payments_df = pd.read_csv('olist_order_payments_dataset.csv')
#         order_payments = payments_df[payments_df['order_id'] == order_id]
#         if not order_payments.empty:
#             return order_payments['payment_value'].sum()
#     except:
#         pass
#     return 0

# def get_pttt_id(cur, payment_type):
#     """Get payment method ID from database"""
#     cur.execute("SELECT id FROM dim_phuong_thuc_tt WHERE ten_phuong_thuc = %s", (payment_type,))
#     result = cur.fetchone()
#     return result[0] if result else 1

# def map_payment_type(order_id):
#     """Map payment type from CSV to database format"""
#     try:
#         payments_df = pd.read_csv('olist_order_payments_dataset.csv')
#         order_payments = payments_df[payments_df['order_id'] == order_id]
#         if not order_payments.empty:
#             payment_type = order_payments['payment_type'].iloc[0]
#             # Map CSV payment types to database payment types
#             mapping = {
#                 'credit_card': 'Thẻ tín dụng',
#                 'boleto': 'Chuyển khoản (QR)',
#                 'voucher': 'Tiền mặt/Voucher',
#                 'debit_card': 'Thẻ tín dụng'
#             }
#             return mapping.get(payment_type, 'Tiền mặt/Voucher')
#     except:
#         pass
#     return 'Tiền mặt/Voucher'

# def import_csv_data():
#     print("🚀 BẮT ĐẦU IMPORT DỮ LIỆU TỪ CSV...")

#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), port=os.getenv("DB_PORT")
#         )
#         cur = conn.cursor()

#         # Import orders data
#         print("📦 Đang import dữ liệu orders...")
#         orders_df = pd.read_csv('olist_orders_dataset.csv')

#         # Filter only delivered orders
#         delivered_orders = orders_df[orders_df['order_status'] == 'delivered'].copy()

#         # Convert timestamps
#         delivered_orders['order_purchase_timestamp'] = pd.to_datetime(delivered_orders['order_purchase_timestamp'])

#         thu_count = 0
#         for _, order in delivered_orders.iterrows():
#             # Get payment value from payments file
#             payment_value = get_payment_value(order['order_id'])
#             if payment_value == 0:
#                 continue  # Skip if no payment found

#             # Map payment type based on payment data
#             payment_type = map_payment_type(order['order_id'])

#             # Insert thu record
#             cur.execute("""
#                 INSERT INTO giao_dich_thu (ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id)
#                 VALUES (%s, %s, %s, %s, %s, %s)
#             """, (
#                 order['order_purchase_timestamp'],
#                 payment_value,
#                 1,  # Default store
#                 (thu_count % 3) + 1,  # Cycle through channels: POS, Website, Shopee
#                 get_pttt_id(cur, payment_type),
#                 1  # Default user (banhang_01)
#             ))
#             thu_count += 1

#             if thu_count % 1000 == 0:
#                 print(f"📊 Đã import {thu_count} giao dịch...")

#         print(f"✅ Đã import {thu_count} giao dịch thu từ orders")

#         conn.commit()
#         cur.close()
#         conn.close()

#         print("🎉 HOÀN TẤT IMPORT DỮ LIỆU TỪ CSV!")

#     except Exception as e:
#         print(f"❌ Lỗi import: {e}")

# def run_etl():
#     """Run ETL to populate fact table"""
#     print("\n🔄 Đang chạy ETL...")
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
#             user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), port=os.getenv("DB_PORT")
#         )
#         cur = conn.cursor()

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
#         rows_inserted = cur.rowcount
#         conn.commit()

#         print(f"✅ ETL hoàn tất! Đã tạo {rows_inserted} bản ghi báo cáo.")
#         cur.close()
#         conn.close()
#     except Exception as e:
#         print(f"❌ Lỗi ETL: {e}")

# if __name__ == "__main__":
#     import_csv_data()
#     run_etl()