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




-- Bổ sung trạng thái cho bảng Thu để hỗ trợ tính năng Hủy/Điều chỉnh
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS trang_thai VARCHAR(20) DEFAULT 'HOÀN THÀNH';
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS ly_do_huy TEXT;
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS nguoi_huy_id INT REFERENCES users(id);

-- Bổ sung cột lưu vết người hủy cho bảng Chi
ALTER TABLE giao_dich_chi ADD COLUMN IF NOT EXISTS ly_do_huy TEXT;
ALTER TABLE giao_dich_chi ADD COLUMN IF NOT EXISTS nguoi_huy_id INT REFERENCES users(id);



-- 1. Bổ sung cột ghi chú cho bảng Thu (để lưu thông tin khi chọn "Khác")
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS ghi_chu TEXT;

-- 2. Thêm danh mục "Khác" vào các bảng nền
INSERT INTO dim_cua_hang (ten_cua_hang) VALUES ('Khác'); 
INSERT INTO dim_kenh_ban (ten_kenh) VALUES ('Khác'); 
INSERT INTO dim_phuong_thuc_tt (ten_phuong_thuc) VALUES ('Khác'); 
INSERT INTO dim_loai_chi (ten_loai) VALUES ('Khác'); 

-- 3. Nạp dữ liệu giả lập cho tháng 04/2026 (Thời gian thực)
INSERT INTO giao_dich_thu (ngay_tao, so_tien, cua_hang_id, kenh_id, pttt_id, nguoi_tao_id, trang_thai) VALUES
('2026-04-10 08:30:00', 2500000, 1, 1, 1, 1, 'HOÀN THÀNH'),
('2026-04-11 14:15:00', 5400000, 2, 2, 2, 1, 'HOÀN THÀNH'),
('2026-04-12 09:45:00', 1200000, 1, 3, 3, 1, 'HOÀN THÀNH'),
('2026-04-13 16:20:00', 8900000, 2, 1, 3, 1, 'HOÀN THÀNH'),
('2026-04-14 10:10:00', 3200000, 1, 2, 2, 1, 'HOÀN THÀNH'),
('2026-04-15 09:00:00', 4500000, 2, 3, 1, 1, 'HOÀN THÀNH');

INSERT INTO giao_dich_chi (ngay_tao, so_tien, loai_chi_id, pttt_id, nguoi_tao_id, trang_thai, nguoi_duyet_id) VALUES
('2026-04-10 10:00:00', 1500000, 1, 2, 1, 'ĐÃ DUYỆT', 2),
('2026-04-11 11:30:00', 800000, 2, 1, 1, 'ĐÃ DUYỆT', 2),
('2026-04-12 15:00:00', 3000000, 3, 2, 1, 'TỪ CHỐI', 2),
('2026-04-13 09:15:00', 500000, 4, 1, 1, 'ĐÃ DUYỆT', 2),
('2026-04-14 14:20:00', 1200000, 1, 3, 1, 'CHỜ DUYỆT', NULL),
('2026-04-15 08:45:00', 2000000, 2, 2, 1, 'CHỜ DUYỆT', NULL);


-- 1. Bổ sung trạng thái và thông tin hủy cho bảng Thu
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS trang_thai VARCHAR(20) DEFAULT 'HOÀN THÀNH';
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS ly_do_huy TEXT;
ALTER TABLE giao_dich_thu ADD COLUMN IF NOT EXISTS nguoi_huy_id INT REFERENCES users(id);

-- 2. Bổ sung thông tin hủy cho bảng Chi
ALTER TABLE giao_dich_chi ADD COLUMN IF NOT EXISTS ly_do_huy TEXT;
ALTER TABLE giao_dich_chi ADD COLUMN IF NOT EXISTS nguoi_huy_id INT REFERENCES users(id);

-- 3. Cập nhật lại những dòng cũ (nếu có) bị null trạng thái thành HOÀN THÀNH
UPDATE giao_dich_thu SET trang_thai = 'HOÀN THÀNH' WHERE trang_thai IS NULL;