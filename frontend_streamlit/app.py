import streamlit as st
import pandas as pd
import requests
import re
import plotly.express as px
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Hệ thống Quản trị Tài chính", layout="wide")

# TỪ ĐIỂN ÁNH XẠ (ĐỂ VIỆT HÓA THEO GÓP Ý CỦA NAM)
MAP_LOAI_CHI_UI = {"NHAPHANG": "Nhập hàng", "MARKETING": "Quảng cáo & Sự kiện", "LUONG": "Lương & Thưởng", "VANHANH": "Vận hành"}
MAP_LOAI_CHI_DB = {v: k for k, v in MAP_LOAI_CHI_UI.items()}

if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None, "full_name": None})

# ======================
# LOGIN UI
# ======================
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>ĐĂNG NHẬP HỆ THỐNG</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Đăng nhập", use_container_width=True):
                try:
                    res = requests.post(f"{API_URL}/api/auth/login", json={"username": u.strip().lower(), "password": p.strip()})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.update({"logged_in": True, "role": data["role"], "username": data["username"], "full_name": data["full_name"]})
                        st.rerun()
                    else:
                        st.error("Sai thông tin đăng nhập!")
                except Exception as e:
                    st.error(f"Lỗi chi tiết: {e}")
    st.stop()

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.markdown(f"**👤 {st.session_state.full_name}**")
    st.caption(f"Role: {st.session_state.role}")
    st.divider()
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.title("📊 HỆ THỐNG ĐIỀU HÀNH TÀI CHÍNH (API-Driven)")

# Hàm hỗ trợ hiển thị UI Duyệt/Từ chối chung cho Kế Toán và Quản Lý
def render_phe_duyet_ui():
    st.subheader("✅ Xử lý Phê Duyệt Chi Phí")
    res = requests.get(f"{API_URL}/api/chi")
    if res.status_code == 200:
        df = pd.DataFrame(res.json())
        if not df.empty:
            df_cho = df[df['trang_thai'] == 'CHỜ DUYỆT']
            if df_cho.empty:
                st.info("Không có phiếu chi nào đang chờ duyệt.")
            for _, r in df_cho.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    ten_loai = MAP_LOAI_CHI_UI.get(r['ma_loai'], r['ma_loai'])
                    c1.markdown(f"**Mã Phiếu: #{r['id']}** | Hạng mục: **{ten_loai}**")
                    c1.markdown(f"Người đề xuất: `{r['nguoi_de_xuat']}` | Ghi chú: *{r['ghi_chu']}*")
                    c1.markdown(f"Số tiền: <span style='color:red; font-size:18px; font-weight:bold;'>{r['so_tien']:,.0f} VNĐ</span>", unsafe_allow_html=True)
                    
                    with c2.popover("Xử lý", use_container_width=True):
                        if st.button("✅ Duyệt phiếu", key=f"d_{r['id']}", use_container_width=True):
                            requests.put(f"{API_URL}/api/chi/status", json={"id": r['id'], "trang_thai": "ĐÃ DUYỆT", "nguoi_duyet": st.session_state.username})
                            st.rerun()
                        st.divider()
                        ly_do = st.text_input("Lý do từ chối (Bắt buộc)", key=f"ld_{r['id']}")
                        if st.button("❌ Từ chối", key=f"t_{r['id']}", type="primary", use_container_width=True):
                            if ly_do.strip() == "":
                                st.error("Vui lòng nhập lý do!")
                            else:
                                requests.put(f"{API_URL}/api/chi/status", json={"id": r['id'], "trang_thai": "TỪ CHỐI", "nguoi_duyet": st.session_state.username, "ly_do": ly_do})
                                st.rerun()

# ======================
# ROLE: BANHANG
# ======================
if st.session_state.role == "BANHANG":
    t1, t2 = st.tabs(["🛒 Lập Phiếu Thu", "📝 Tạo Phiếu Chi"])
    
    with t1:
        with st.form("thu_form"):
            c1, c2 = st.columns(2)
            tien_str = c1.text_input("Số tiền thu (Tự động format)", value="0")
            try:
                tien = float(re.sub(r'[^\d]', '', tien_str))
                c1.info(f"Xác nhận: **{tien:,.0f} VNĐ**")
            except:
                tien = 0
            
            kenh = c1.selectbox("Kênh bán hàng", ["POS", "WEB", "APP"])
            pt = c2.selectbox("Phương thức thanh toán", ["TIỀN MẶT", "CHUYỂN KHOẢN", "QUẸT THẺ"])
            note = c2.text_input("Ghi chú")
            
            if st.form_submit_button("Lưu Phiếu Thu") and tien > 0:
                payload = {"so_tien": tien, "ma_kenh": kenh, "phuong_thuc": pt, "nguoi_nhap": st.session_state.username, "ghi_chu": note}
                r = requests.post(f"{API_URL}/api/thu", json=payload)
                data_r = r.json()
                st.success(f"Tạo thành công! Mã phiếu thu: #{data_r.get('id', 'N/A')} - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                
    with t2:
        with st.form("chi_form"):
            loai_ui = st.selectbox("Hạng mục chi", list(MAP_LOAI_CHI_UI.values()))
            tien_chi = st.number_input("Số tiền (VNĐ)", min_value=0.0, step=100000.0)
            note_chi = st.text_input("Ghi chú/Lý do chi")
            if st.form_submit_button("Gửi Yêu Cầu") and tien_chi > 0:
                payload = {"ma_loai": MAP_LOAI_CHI_DB[loai_ui], "so_tien": tien_chi, "nguoi_de_xuat": st.session_state.username, "ghi_chu": note_chi}
                r = requests.post(f"{API_URL}/api/chi", json=payload)
                st.success(f"Đã gửi yêu cầu lên cấp trên! Mã phiếu: #{r.json().get('id')}")

# ======================
# ROLE: KETOAN
# ======================
elif st.session_state.role == "KETOAN":
    tab1, tab2, tab3 = st.tabs(["Xử lý Phê duyệt", "Sổ cái Giao dịch", "Import Excel"])
    
    with tab1:
        render_phe_duyet_ui()

    with tab2:
        # Lấy dữ liệu Thu & Chi để quản lý
        df_thu = pd.DataFrame(requests.get(f"{API_URL}/api/thu").json())
        df_chi = pd.DataFrame(requests.get(f"{API_URL}/api/chi").json())
        
        c1, c2 = st.columns(2)
        voi_loai = c1.selectbox("Xem bảng dữ liệu", ["Giao dịch Chi", "Giao dịch Thu"])
        
        # BỘ LỌC CHUNG CHO SỔ CÁI
        if voi_loai == "Giao dịch Chi" and not df_chi.empty:
            trang_thai_loc = c2.selectbox("Lọc Trạng thái", ["Tất cả", "ĐÃ DUYỆT", "CHỜ DUYỆT", "TỪ CHỐI"])
            if trang_thai_loc != "Tất cả":
                df_chi = df_chi[df_chi["trang_thai"] == trang_thai_loc]
            
            st.dataframe(
                df_chi,
                column_config={
                    "id": "Mã Phiếu", "ngay_tao": "Ngày", "ma_loai": "Hạng mục",
                    "so_tien": st.column_config.NumberColumn("Số tiền", format="%d ₫"),
                    "nguoi_de_xuat": "Người đề xuất", "trang_thai": "Trạng thái", "ghi_chu": "Ghi chú chi tiết"
                },
                use_container_width=True
            )
            
        elif voi_loai == "Giao dịch Thu" and not df_thu.empty:
            st.dataframe(
                df_thu,
                column_config={
                    "id": "Mã Phiếu", "ngay_tao": "Ngày", "ma_kenh": "Kênh",
                    "so_tien": st.column_config.NumberColumn("Số tiền", format="%d ₫"),
                    "phuong_thuc": "Phương thức", "nguoi_nhap": "Người tạo", "ghi_chu": "Ghi chú"
                },
                use_container_width=True
            )

    with tab3:
        st.subheader("Nhập liệu hàng loạt (Thu/Chi) qua Excel")
        st.markdown("*Lưu ý: Cấu trúc file Excel cần có các cột: `loai_giao_dich` (THU/CHI), `so_tien`, `ma_kenh_hoac_loai` (POS/WEB/NHAPHANG...), `ghi_chu`.*")
        uploaded_file = st.file_uploader("Kéo thả file .xlsx vào đây", type=["xlsx"])
        if uploaded_file is not None:
            try:
                df_ex = pd.read_excel(uploaded_file)
                st.write("Bản xem trước dữ liệu:")
                st.dataframe(df_ex.head())
                if st.button("Xác nhận Đẩy lên Hệ thống"):
                    count_thu, count_chi = 0, 0
                    for _, row in df_ex.iterrows():
                        if row['loai_giao_dich'] == 'THU':
                            payload = {"so_tien": row['so_tien'], "ma_kenh": row['ma_kenh_hoac_loai'], "phuong_thuc": "TIỀN MẶT", "nguoi_nhap": st.session_state.username, "ghi_chu": str(row.get('ghi_chu', ''))}
                            requests.post(f"{API_URL}/api/thu", json=payload)
                            count_thu += 1
                        elif row['loai_giao_dich'] == 'CHI':
                            payload = {"ma_loai": row['ma_kenh_hoac_loai'], "so_tien": row['so_tien'], "nguoi_de_xuat": st.session_state.username, "ghi_chu": str(row.get('ghi_chu', ''))}
                            requests.post(f"{API_URL}/api/chi", json=payload)
                            count_chi += 1
                    st.success(f"Đã import thành công {count_thu} giao dịch Thu và {count_chi} giao dịch Chi!")
            except Exception as e:
                st.error(f"Lỗi đọc file: {e}")

# ======================
# ROLE: QUANLY
# ======================
elif st.session_state.role == "QUANLY":
    t1, t2 = st.tabs(["📊 Dashboard Data Warehouse", "✅ Phê duyệt Chi phí"])
    
    with t1:
        st.subheader("Báo Cáo Data Warehouse (ETL)")
        res = requests.get(f"{API_URL}/api/dashboard")
        if res.status_code == 200:
            df_dw = pd.DataFrame(res.json())
            if not df_dw.empty:
                # Bộ lọc thời gian cho Quản lý
                df_dw['ngay'] = pd.to_datetime(df_dw['ngay'])
                c_loc1, c_loc2 = st.columns(2)
                start_date = c_loc1.date_input("Từ ngày", df_dw['ngay'].min())
                end_date = c_loc2.date_input("Đến ngày", df_dw['ngay'].max())
                
                # Lọc Data
                mask = (df_dw['ngay'].dt.date >= start_date) & (df_dw['ngay'].dt.date <= end_date)
                df_filtered = df_dw.loc[mask]

                # Thẻ KPI
                c1, c2, c3 = st.columns(3)
                c1.metric("Tổng Thu", f"{df_filtered['tong_thu'].sum():,.0f} ₫")
                c2.metric("Tổng Chi (Đã duyệt)", f"{df_filtered['tong_chi_da_duyet'].sum():,.0f} ₫")
                c3.metric("Lợi nhuận Thuần", f"{df_filtered['loi_nhuan'].sum():,.0f} ₫", 
                          delta="Có Lãi" if df_filtered['loi_nhuan'].sum() > 0 else "Lỗ")

                # Vẽ Biểu đồ 
                col_chart1, col_chart2 = st.columns([2, 1])
                with col_chart1:
                    fig_bar = px.bar(df_filtered, x="ngay", y=["tong_thu", "tong_chi_da_duyet"], barmode="group", title="Biến động Thu - Chi theo ngày", labels={"value": "VNĐ", "variable": "Hạng mục", "ngay": "Ngày"})
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with col_chart2:
                    # Biểu đồ cơ cấu (Theo góp ý của Nguyên)
                    df_pie = pd.DataFrame({
                        "Hạng mục": ["Tổng Thu", "Tổng Chi"],
                        "Giá trị": [df_filtered['tong_thu'].sum(), df_filtered['tong_chi_da_duyet'].sum()]
                    })
                    fig_pie = px.pie(df_pie, names="Hạng mục", values="Giá trị", title="Cơ cấu Dòng tiền", hole=0.4, color="Hạng mục", color_discrete_map={"Tổng Thu": "blue", "Tổng Chi": "red"})
                    st.plotly_chart(fig_pie, use_container_width=True)

                # Bảng dữ liệu đã Việt Hóa và Format
                st.markdown("##### Chi tiết Báo Cáo")
                
                # Hàm tô màu Lãi/Lỗ
                def color_profit(val):
                    color = 'green' if val == 'LÃI' else 'red' if val == 'LỖ' else 'black'
                    return f'color: {color}; font-weight: bold'

                st.dataframe(
                    df_filtered.style.map(color_profit, subset=['trang_thai_loi_nhuan']).format({"tong_thu": "{:,.0f} ₫", "tong_chi_da_duyet": "{:,.0f} ₫", "loi_nhuan": "{:,.0f} ₫", "ngay": lambda x: x.strftime('%d-%m-%Y')}),
                    use_container_width=True
                )
            else:
                st.warning("Data Warehouse trống. Cần chạy ETL trên Backend.")

    with t2:
        # Kéo hàm Phê duyệt chung (Quản lý duyệt cùng Kế toán trưởng)
        render_phe_duyet_ui()