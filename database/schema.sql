-- 1. LÀM SẠCH HỆ THỐNG
DROP TABLE IF EXISTS fact_tai_chinh CASCADE;
DROP TABLE IF EXISTS giao_dich_chi CASCADE;
DROP TABLE IF EXISTS giao_dich_thu CASCADE;
DROP TABLE IF EXISTS dim_loai_chi CASCADE;
DROP TABLE IF EXISTS dim_phuong_thuc_tt CASCADE;
DROP TABLE IF EXISTS dim_kenh_ban CASCADE;
DROP TABLE IF EXISTS dim_cua_hang CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 2. TẠO DANH MỤC (Dữ liệu nền)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20),
    full_name VARCHAR(100)
);

CREATE TABLE dim_cua_hang (id SERIAL PRIMARY KEY, ten_cua_hang VARCHAR(100));
CREATE TABLE dim_kenh_ban (id SERIAL PRIMARY KEY, ten_kenh VARCHAR(50));
CREATE TABLE dim_phuong_thuc_tt (id SERIAL PRIMARY KEY, ten_phuong_thuc VARCHAR(50));
CREATE TABLE dim_loai_chi (id SERIAL PRIMARY KEY, ten_loai VARCHAR(100));

-- 3. TẠO BẢNG GIAO DỊCH (OLTP)
CREATE TABLE giao_dich_thu (
    id SERIAL PRIMARY KEY,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    so_tien NUMERIC(15,2),
    cua_hang_id INT REFERENCES dim_cua_hang(id),
    kenh_id INT REFERENCES dim_kenh_ban(id),
    pttt_id INT REFERENCES dim_phuong_thuc_tt(id),
    nguoi_tao_id INT REFERENCES users(id)
);

CREATE TABLE giao_dich_chi (
    id SERIAL PRIMARY KEY,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    so_tien NUMERIC(15,2),
    loai_chi_id INT REFERENCES dim_loai_chi(id),
    pttt_id INT REFERENCES dim_phuong_thuc_tt(id),
    nguoi_tao_id INT REFERENCES users(id),
    trang_thai VARCHAR(20) DEFAULT 'CHỜ DUYỆT',
    ly_do_tu_choi TEXT,
    nguoi_duyet_id INT REFERENCES users(id)
);

-- 4. TẠO BẢNG KHO DỮ LIỆU (OLAP)
CREATE TABLE fact_tai_chinh (
    ngay_bao_cao DATE PRIMARY KEY,
    tong_thu NUMERIC(15,2) DEFAULT 0,
    tong_chi NUMERIC(15,2) DEFAULT 0,
    loi_nhuan NUMERIC(15,2) DEFAULT 0,
    trang_thai_kd VARCHAR(20)
);

-- 5. NẠP DỮ LIỆU NỀN TỰ ĐỘNG
INSERT INTO users (username, password, role, full_name) VALUES 
('banhang_01', 'hash_123', 'BANHANG', 'Nguyễn Bán Hàng'),
('ketoan_01', 'hash_123', 'KETOAN', 'Trần Kế Toán'),
('quanly_01', 'hash_123', 'QUANLY', 'Lê Quản Lý');

INSERT INTO dim_cua_hang (ten_cua_hang) VALUES ('CH 01 - Cầu Giấy'), ('CH 02 - Quận 1');
INSERT INTO dim_kenh_ban (ten_kenh) VALUES ('POS Cửa hàng'), ('Website'), ('Shopee/Tiktok');
INSERT INTO dim_phuong_thuc_tt (ten_phuong_thuc) VALUES ('Tiền mặt/Voucher'), ('Chuyển khoản (QR)'), ('Thẻ tín dụng');
INSERT INTO dim_loai_chi (ten_loai) VALUES ('Chi phí Nhập hàng'), ('Chi phí Lương'), ('Chi phí Marketing'), ('Chi phí Vận hành');