import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Hệ thống Quản trị Tài chính", layout="wide")

MAP_CUA_HANG = {"Cơ sở 01 - Cầu Giấy": 1, "Cơ sở 02 - Quận 1": 2, "Khác": 3}
MAP_KENH = {"POS Cửa hàng": 1, "Website": 2, "Sàn Thương mại điện tử": 3, "Khác": 4}
MAP_PTTT = {"Tiền mặt / Voucher": 1, "Chuyển khoản Ngân hàng": 2, "Thẻ Tín dụng / Ghi nợ": 3, "Khác": 4}
MAP_LOAI_CHI = {"Chi phí Nhập hàng": 1, "Chi phí Tiền lương": 2, "Chi phí Tiếp thị": 3, "Chi phí Vận hành": 4, "Khác": 5}

# ==========================================
# KHỞI TẠO BIẾN PHIÊN (SESSION STATE)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None, "full_name": None, "id": 1, "currency": "VND"})

def format_currency(value):
    return f"{value:,.0f} {st.session_state.currency}"

# Bộ xử lý hiển thị thông báo Toast sau khi tải lại trang
if "toast_msg" in st.session_state:
    st.toast(st.session_state.toast_msg, icon="✅")
    del st.session_state.toast_msg

# ==========================================
# CÁC HỘP THOẠI NỔI (MODAL DIALOGS)
# ==========================================
@st.dialog("Xác nhận Xử lý Chứng từ")
def confirm_approval_dialog(p_id, action, ly_do, nguoi_duyet_id):
    st.write(f"Thao tác hiện tại: **{'DUYỆT' if action == 'DUYET' else 'TỪ CHỐI'}** chứng từ mã PC-{p_id:05d}.")
    if action == "TUCHOI" and (ly_do is None or not ly_do.strip()):
        st.error("Yêu cầu nhập ghi chú lý do khi thực hiện từ chối chứng từ.")
    else:
        st.write("Vui lòng xác nhận để ghi nhận dữ liệu vào hệ thống.")
        c1, c2 = st.columns(2)
        if c1.button("Xác nhận", type="primary", use_container_width=True):
            status = "ĐÃ DUYỆT" if action == "DUYET" else "TỪ CHỐI"
            requests.put(f"{API_URL}/api/chi/status", json={"id": p_id, "trang_thai": status, "ly_do": ly_do, "nguoi_duyet_id": nguoi_duyet_id})
            st.session_state.toast_msg = "Xử lý chứng từ hoàn tất."
            st.rerun()
        if c2.button("Đóng", use_container_width=True):
            st.rerun()

@st.dialog("Xác nhận Hủy Chứng từ")
def confirm_void_dialog(p_id, loai_phieu, ly_do_huy, nguoi_huy_id):
    st.write(f"Thao tác hiện tại: **HỦY** chứng từ mã {p_id:05d}.")
    st.caption("Lưu ý: Thao tác này sẽ cập nhật trạng thái hệ thống thành 'ĐÃ HỦY' và không thể hoàn tác.")
    if not ly_do_huy.strip():
        st.error("Yêu cầu cung cấp diễn giải lý do hủy.")
    else:
        c1, c2 = st.columns(2)
        if c1.button("Xác nhận Hủy", type="primary", use_container_width=True):
            endpoint = "/api/thu/void" if "Thu" in loai_phieu else "/api/chi/void"
            requests.put(f"{API_URL}{endpoint}", json={"id": p_id, "ly_do": ly_do_huy, "nguoi_huy_id": nguoi_huy_id})
            st.session_state.toast_msg = "Hủy chứng từ thành công."
            st.rerun()
        if c2.button("Đóng", use_container_width=True):
            st.rerun()

# ==========================================
# GIAO DIỆN XÁC THỰC
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<h3 style='text-align: center; color: #1E3A8A;'>ĐĂNG NHẬP HỆ THỐNG</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Tên đăng nhập")
            p = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Truy cập", use_container_width=True):
                try:
                    res = requests.post(f"{API_URL}/api/auth/login", json={"username": u.strip(), "password": p.strip()})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.update({"logged_in": True, "role": data["role"], "username": data["username"], "full_name": data["full_name"], "id": data["id"]})
                        st.rerun()
                    else:
                        st.error("Thông tin xác thực không chính xác.")
                except Exception:
                    st.error("Mất kết nối đến máy chủ xử lý.")
    st.stop()

# ==========================================
# MENU ĐIỀU HƯỚNG BÊN TRÁI
# ==========================================
with st.sidebar:
    st.markdown(f"**Nhân sự: {st.session_state.full_name}**")
    st.caption(f"Chức vụ: {st.session_state.role}")
    st.session_state.currency = st.selectbox("Định dạng tiền tệ", ["VND", "USD"])
    st.divider()
    if st.button("Đăng xuất", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.title("HỆ THỐNG QUẢN TRỊ TÀI CHÍNH")

# ==========================================
# PHÂN HỆ 1: NHÂN VIÊN BÁN HÀNG
# Thực hiện nhập liệu dữ liệu giao dịch bán hàng hoặc yêu cầu phê duyệt các khoản chi tiêu tại cơ sở.
# ==========================================
if st.session_state.role == "BANHANG":
    t1, t2 = st.tabs(["Ghi nhận Doanh thu", "Đề xuất Chi phí"])
    
    with t1:
        with st.form("thu_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            tien = c1.number_input(f"Giá trị thu ({st.session_state.currency})", min_value=0.0, step=10000.0, format="%f")
            
            cua_hang = c1.selectbox("Đơn vị phát sinh", list(MAP_CUA_HANG.keys()))
            cua_hang_khac = c1.text_input("Ghi rõ tên đơn vị (Bắt buộc)") if cua_hang == "Khác" else ""
            
            kenh = c2.selectbox("Kênh phân phối", list(MAP_KENH.keys()))
            kenh_khac = c2.text_input("Ghi rõ tên kênh (Bắt buộc)") if kenh == "Khác" else ""
            
            pt = c2.selectbox("Phương thức thanh toán", list(MAP_PTTT.keys()))
            pt_khac = c2.text_input("Ghi rõ phương thức (Bắt buộc)") if pt == "Khác" else ""
            
            if st.form_submit_button("Lưu dữ liệu", type="primary"):
                if tien <= 0:
                    st.error("Yêu cầu nhập giá trị lớn hơn 0.")
                elif cua_hang == "Khác" and not cua_hang_khac.strip():
                    st.error("Yêu cầu cung cấp thông tin tên đơn vị phát sinh.")
                elif kenh == "Khác" and not kenh_khac.strip():
                    st.error("Yêu cầu cung cấp thông tin kênh phân phối.")
                elif pt == "Khác" and not pt_khac.strip():
                    st.error("Yêu cầu cung cấp thông tin phương thức thanh toán.")
                else:
                    ghi_chu_list = []
                    if cua_hang == "Khác": ghi_chu_list.append(f"Đơn vị: {cua_hang_khac}")
                    if kenh == "Khác": ghi_chu_list.append(f"Kênh: {kenh_khac}")
                    if pt == "Khác": ghi_chu_list.append(f"Thanh toán: {pt_khac}")
                    
                    payload = {"so_tien": tien, "cua_hang_id": MAP_CUA_HANG[cua_hang], "kenh_id": MAP_KENH[kenh], "pttt_id": MAP_PTTT[pt], "nguoi_tao_id": st.session_state.id, "ghi_chu": " | ".join(ghi_chu_list)}
                    r = requests.post(f"{API_URL}/api/thu", json=payload)
                    if r.status_code == 200: 
                        st.session_state.toast_msg = f"Ghi nhận thành công. Mã tham chiếu: PT-{r.json().get('id'):05d}"
                        st.rerun()

    with t2:
        with st.form("chi_form", clear_on_submit=False):
            loai_chi = st.selectbox("Hạng mục chi phí", list(MAP_LOAI_CHI.keys()))
            loai_chi_khac = st.text_input("Ghi rõ tên hạng mục (Bắt buộc)") if loai_chi == "Khác" else ""
            
            tien_chi = st.number_input(f"Giá trị đề xuất ({st.session_state.currency})", min_value=0.0, step=10000.0, format="%f")
            
            pt_chi = st.selectbox("Hình thức thanh toán", list(MAP_PTTT.keys()))
            pt_chi_khac = st.text_input("Ghi rõ hình thức thanh toán (Bắt buộc)") if pt_chi == "Khác" else ""
            
            note_chi = st.text_input("Diễn giải nội dung chi")
            
            if st.form_submit_button("Chuyển phê duyệt"):
                if tien_chi <= 0:
                    st.error("Yêu cầu nhập giá trị đề xuất lớn hơn 0.")
                elif loai_chi == "Khác" and not loai_chi_khac.strip():
                    st.error("Yêu cầu cung cấp thông tin hạng mục chi phí.")
                elif pt_chi == "Khác" and not pt_chi_khac.strip():
                    st.error("Yêu cầu cung cấp thông tin hình thức thanh toán.")
                else:
                    ghi_chu_chi = [note_chi] if note_chi.strip() else []
                    if loai_chi == "Khác": ghi_chu_chi.append(f"Hạng mục: {loai_chi_khac}")
                    if pt_chi == "Khác": ghi_chu_chi.append(f"Thanh toán: {pt_chi_khac}")
                    
                    payload = {"loai_chi_id": MAP_LOAI_CHI[loai_chi], "so_tien": tien_chi, "pttt_id": MAP_PTTT[pt_chi], "nguoi_tao_id": st.session_state.id, "ghi_chu": " | ".join(ghi_chu_chi)}
                    r = requests.post(f"{API_URL}/api/chi", json=payload)
                    if r.status_code == 200: 
                        st.session_state.toast_msg = f"Đã chuyển yêu cầu đến Kế toán. Mã hệ thống: PC-{r.json().get('id'):05d}"
                        st.rerun()

# ==========================================
# PHÂN HỆ 2: NHÂN VIÊN KẾ TOÁN
# Quản lý danh mục chi phí, thực hiện đối soát dữ liệu thu đa kênh, kiểm tra và phê duyệt luồng tiền ra.
# ==========================================
elif st.session_state.role == "KETOAN":
    tabs = st.tabs(["Xét duyệt Chứng từ", "Xử lý Sai sót", "Nạp Dữ liệu Hệ thống", "Quản lý Danh mục"])
    
    with tabs[0]:
        st.subheader("Trình tự Xét duyệt Chứng từ")
        ds_chi = requests.get(f"{API_URL}/api/chi/pending").json()
        if not ds_chi: st.caption("Hệ thống không ghi nhận chứng từ chờ xử lý.")
        for p in ds_chi:
            with st.expander(f"Mã tham chiếu: PC-{p['id']:05d} | Phân loại: {p['ten_loai']} | Đề xuất: {p['nguoi_de_xuat']} | Giá trị: {format_currency(p['so_tien'])}"):
                c_a, c_b = st.columns([3, 1])
                ly_do = c_a.text_input("Ghi chú xử lý:", key=f"lydo_{p['id']}", value=p['ghi_chu'])
                
                col1, col2 = c_b.columns(2)
                # Gọi thẳng hộp thoại, truyền đủ 4 tham số (ID phiếu, Hành động, Lý do, ID Kế toán)
                if col1.button("Duyệt", key=f"btn_duyet_{p['id']}", use_container_width=True): 
                    confirm_approval_dialog(p['id'], "DUYET", ly_do, st.session_state.id)
                if col2.button("Từ chối", key=f"btn_tuchoi_{p['id']}", use_container_width=True): 
                    confirm_approval_dialog(p['id'], "TUCHOI", ly_do, st.session_state.id)

        st.divider()
        st.subheader("Danh sách chứng từ đã xử lý")
        ds_processed = requests.get(f"{API_URL}/api/chi/processed").json()
        if ds_processed:
            df_proc = pd.DataFrame(ds_processed)
            df_proc['so_tien'] = df_proc['so_tien'].apply(format_currency)
            df_proc.columns = ["Mã hệ thống", "Thời gian", "Giá trị", "Trạng thái", "Nhân sự xử lý", "Ghi chú"]
            st.dataframe(df_proc, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Trình tự Điều chỉnh Sai sót")
        loai_phieu = st.radio("Đối tượng xử lý", ["Chứng từ Doanh thu", "Chứng từ Chi phí"], horizontal=True)
        api_url_active = f"{API_URL}/api/thu/active" if "Thu" in loai_phieu else f"{API_URL}/api/chi/active"
        ds_active = requests.get(api_url_active).json()
        
        options = {f"Mã phiếu {p['id']:05d} - Giá trị: {format_currency(p['so_tien'])} - Ngày: {p['ngay_tao'][:10]}": p for p in ds_active}
        selected = st.selectbox("Lựa chọn chứng từ cần điều chỉnh", ["-- Lựa chọn --"] + list(options.keys()))
        
        if selected != "-- Lựa chọn --":
            p = options[selected]
            st.info(f"**Bản ghi:** ID {p['id']:05d} | Giá trị: {format_currency(p['so_tien'])} | Chi tiết: {p['thong_tin']}")
            ly_do_huy = st.text_input("Diễn giải lý do hủy (Bắt buộc)", key="lydohuy")
            
            # Gọi hộp thoại nổi, truyền đủ 4 tham số
            if st.button("Thực thi Hủy chứng từ", type="primary"):
                confirm_void_dialog(p['id'], loai_phieu, ly_do_huy, st.session_state.id)

        st.divider()
        st.subheader("Lịch sử chứng từ đã bị hủy")
        ds_void = requests.get(f"{API_URL}/api/voided").json()
        if ds_void:
            df_void = pd.DataFrame(ds_void)
            df_void['so_tien'] = df_void['so_tien'].apply(format_currency)
            df_void.columns = ["Phân loại", "Mã tham chiếu", "Giá trị", "Diễn giải"]
            st.dataframe(df_void, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("Nạp Dữ liệu Đối soát Hệ thống")
        st.caption("Cấu trúc tệp yêu cầu (.csv, .xlsx): loai_giao_dich (THU/CHI), so_tien, ma_kenh_hoac_loai (1,2,3), ghi_chu.")
        uploaded_file = st.file_uploader("Lựa chọn tệp dữ liệu", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                st.dataframe(df.head(10), use_container_width=True)
                if st.button("Thực thi nạp dữ liệu", type="primary"):
                    payload = []
                    for _, row in df.iterrows():
                        payload.append({
                            "loai_giao_dich": str(row['loai_giao_dich']), "so_tien": float(row['so_tien']),
                            "ma_kenh_hoac_loai": int(row['ma_kenh_hoac_loai']), "pttt_id": 1, 
                            "nguoi_tao_id": st.session_state.id, "ghi_chu": str(row.get('ghi_chu', 'Import đối soát tự động'))
                        })
                    res = requests.post(f"{API_URL}/api/import", json={"data": payload})
                    if res.status_code == 200: 
                        st.session_state.toast_msg = "Nạp dữ liệu vào hệ thống hoàn tất."
                        st.rerun()
            except Exception:
                st.error("Lỗi trích xuất tệp dữ liệu. Vui lòng kiểm tra lại định dạng.")
    
    with tabs[3]:
        st.subheader("Quản lý Danh mục Hệ thống")
        sub_tabs = st.tabs(["Cửa hàng", "Kênh bán", "Phương thức TT", "Loại chi phí"])
        
        with sub_tabs[0]:
            res = requests.get(f"{API_URL}/api/dim_cua_hang")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                st.dataframe(df, use_container_width=True)
        
        with sub_tabs[1]:
            res = requests.get(f"{API_URL}/api/dim_kenh_ban")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                st.dataframe(df, use_container_width=True)
        
        with sub_tabs[2]:
            res = requests.get(f"{API_URL}/api/dim_phuong_thuc_tt")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                st.dataframe(df, use_container_width=True)
        
        with sub_tabs[3]:
            res = requests.get(f"{API_URL}/api/dim_loai_chi")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                st.dataframe(df, use_container_width=True)

# ==========================================
# PHÂN HỆ 3: QUẢN LÝ CẤP CAO
# Truy cập hệ thống để khai thác các báo cáo tài chính, theo dõi Dashboard dòng tiền theo thời gian thực nhằm ra quyết định chiến lược.
# ==========================================
elif st.session_state.role == "QUANLY":
    tabs = st.tabs(["Báo cáo Tổng quan", "Chi tiết Thu", "Chi tiết Chi", "Quản lý Người dùng"])
    
    with tabs[0]:
        st.subheader("Báo cáo Quản trị (Data Warehouse)")
        c_title, c_btn = st.columns([4, 1])
        c_title.caption("Dữ liệu được trích xuất trực tiếp từ phân hệ phân tích OLAP.")
        if c_btn.button("Tải lại bộ đệm", use_container_width=True): st.rerun()

        res_dw = requests.get(f"{API_URL}/api/dashboard")
        if res_dw.status_code == 200:
            df_dw = pd.DataFrame(res_dw.json())
            if not df_dw.empty:
                total_thu = df_dw['tong_thu'].sum()
                total_chi = df_dw['tong_chi_da_duyet'].sum()
                total_ln = df_dw['loi_nhuan'].sum()
                ty_suat = (total_ln / total_thu * 100) if total_thu > 0 else 0
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Tổng Doanh Thu", format_currency(total_thu))
                k2.metric("Tổng Chi Phí", format_currency(total_chi))
                k3.metric("Lợi Nhuận Thuần", format_currency(total_ln))
                k4.metric("Tỷ suất Lợi nhuận", f"{ty_suat:.1f}%")
                
                st.divider()
                st.markdown("**Biểu đồ Khảo sát Dòng tiền**")
                fig_line = px.line(df_dw, x='ngay', y=['tong_thu', 'tong_chi_da_duyet'], labels={'value': 'Giá trị', 'ngay': 'Kỳ báo cáo', 'variable': 'Chỉ tiêu'}, markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
                
                st.markdown("**Biểu đồ Lợi nhuận Theo Ngày**")
                fig_bar = px.bar(df_dw, x='ngay', y='loi_nhuan', title='Lợi nhuận', labels={'loi_nhuan': 'Lợi nhuận', 'ngay': 'Ngày'})
                st.plotly_chart(fig_bar, use_container_width=True)
                
                st.markdown("**Phân bố Trạng thái Kinh doanh**")
                status_counts = df_dw['trang_thai_loi_nhuan'].value_counts()
                fig_pie = px.pie(values=status_counts.values, names=status_counts.index, title='Trạng thái Lợi nhuận')
                st.plotly_chart(fig_pie, use_container_width=True)
                
                st.markdown("**Bảng Tổng hợp Sổ cái**")
                df_dw_display = df_dw.copy()
                for col in ['tong_thu', 'tong_chi_da_duyet', 'loi_nhuan']: df_dw_display[col] = df_dw_display[col].apply(format_currency)
                df_dw_display.columns = ["Kỳ báo cáo", "Doanh thu", "Chi phí", "Lợi nhuận", "Trạng thái"]
                st.dataframe(df_dw_display, use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có dữ liệu phân tích. Vui lòng thực thi luồng ETL.")
    
    with tabs[1]:
        st.subheader("Chi tiết Giao dịch Thu")
        res = requests.get(f"{API_URL}/api/thu/active")
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Không có dữ liệu.")
    
    with tabs[2]:
        st.subheader("Chi tiết Giao dịch Chi")
        res = requests.get(f"{API_URL}/api/chi/active")
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Không có dữ liệu.")
    
    with tabs[3]:
        st.subheader("Quản lý Người dùng")
        res = requests.get(f"{API_URL}/api/users")
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Không có dữ liệu.")