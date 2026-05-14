import os
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import re
import calendar
import time
from datetime import datetime, timedelta

API_URL = os.getenv("API_URL", "http://127.0.0.1:8002")

def parse_month_year(query: str):
    month_match = re.search(r'tháng\s*(\d{1,2})(?:[\/\s](\d{4}))?', query)
    if month_match:
        month = int(month_match.group(1))
        year = int(month_match.group(2)) if month_match.group(2) else datetime.now().year
        return year, month
    year_match = re.search(r'năm\s*(\d{4})', query)
    if year_match:
        return int(year_match.group(1)), None
    return None


def parse_top_count(query: str, default: int = 3):
    count_match = re.search(r'top\s*(\d+)', query)
    return int(count_match.group(1)) if count_match else default


def parse_natural_date(query: str, today: datetime):
    if "hôm nay" in query:
        return today, today
    if "hôm qua" in query:
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if "tháng này" in query:
        start = datetime(today.year, today.month, 1).date()
        end = today
        return start, end
    if "tháng trước" in query:
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month != 1 else today.year - 1
        start = datetime(prev_year, prev_month, 1).date()
        end = datetime(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1]).date()
        return start, end
    date_match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', query)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3))
        try:
            parsed_date = datetime(year, month, day).date()
            return parsed_date, parsed_date
        except ValueError:
            return None
    return None


def get_last_day(year: int, month: int):
    return calendar.monthrange(year, month)[1]

st.set_page_config(page_title="Hệ thống Quản trị Tài chính", layout="wide")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8001")

# Default values for categories (fallback if API fails)
MAP_CUA_HANG = {"CH 01 - Cầu Giấy, Hà Nội": 1, "CH 02 - Quận 1, Tp.HCM": 2, "Khác": 3}
MAP_KENH = {"Cửa hàng": 1, "Website": 2, "Sàn TMDT (Shopee, Lazada, Tiki)": 3, "MXH (FB, TikTok Shop)": 4, "Khác": 5}
MAP_PTTT = {"Tiền mặt": 1, "Chuyển khoản": 2, "Thẻ": 3, "Khác": 4}
MAP_LOAI_CHI = {"Chi phí vận hành cửa hàng": 1, "Chi phí nhân sự": 2, "Chi phí hàng hóa": 3, "Chi phí marketing & bán hàng": 4, "Chi phí tài chính": 5, "Chi phí quản lý & pháp lý": 6, "Chi phí khác": 7}

# Load danh mục từ database
def load_categories():
    try:
        # Load cửa hàng
        res = requests.get(f"{API_URL}/api/dim_cua_hang")
        if res.status_code == 200:
            try:
                cua_hang_data = res.json()
                global MAP_CUA_HANG
                MAP_CUA_HANG = {item['ten_cua_hang']: item['id'] for item in cua_hang_data}
            except requests.exceptions.JSONDecodeError:
                st.error("Lỗi parse JSON từ API dim_cua_hang")
        
        # Load kênh bán
        res = requests.get(f"{API_URL}/api/dim_kenh_ban")
        if res.status_code == 200:
            try:
                kenh_data = res.json()
                global MAP_KENH
                MAP_KENH = {item['ten_kenh']: item['id'] for item in kenh_data}
            except requests.exceptions.JSONDecodeError:
                st.error("Lỗi parse JSON từ API dim_kenh_ban")
        
        # Load phương thức thanh toán
        res = requests.get(f"{API_URL}/api/dim_phuong_thuc_tt")
        if res.status_code == 200:
            try:
                pttt_data = res.json()
                global MAP_PTTT
                MAP_PTTT = {item['ten_phuong_thuc']: item['id'] for item in pttt_data if item['ten_phuong_thuc'].lower() != 'voucher'}
            except requests.exceptions.JSONDecodeError:
                st.error("Lỗi parse JSON từ API dim_phuong_thuc_tt")
        
        # Load loại chi phí
        res = requests.get(f"{API_URL}/api/dim_loai_chi")
        if res.status_code == 200:
            try:
                loai_chi_data = res.json()
                global MAP_LOAI_CHI
                MAP_LOAI_CHI = {item['ten_loai']: item['id'] for item in loai_chi_data}
            except requests.exceptions.JSONDecodeError:
                st.error("Lỗi parse JSON từ API dim_loai_chi")
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        # Fallback to default values if API fails
        pass

# ==========================================
# KHỞI TẠO BIẾN PHIÊN (SESSION STATE)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None, "full_name": None, "id": 1, "currency": "VND"})

# Load categories after login
if st.session_state.logged_in and "categories_loaded" not in st.session_state:
    load_categories()
    st.session_state.categories_loaded = True

def format_currency(value, currency: str | None = None):
    currency = (currency or st.session_state.currency or "VND").upper()
    if currency == "USD":
        return f"{value:,.2f} {currency}"
    return f"{value:,.0f} {currency}"


def highlight_profit_cell(val):
    if isinstance(val, str) and '-' in val:
        return 'color: red; font-weight: bold;'
    return 'color: green; font-weight: bold;'


def create_dim_item(endpoint: str, name: str):
    try:
        res = requests.post(f"{API_URL}/{endpoint}", params={"role": st.session_state.role}, json={"name": name})
        if res.status_code == 200:
            return res.json().get('id')
    except Exception:
        pass
    return None


def render_floating_chat_icon():
    st.markdown(
        """
        <style>
        .floating-chat-button {position: fixed; bottom: 24px; right: 24px; z-index: 9999;}
        .floating-chat-button a {display:inline-flex; align-items:center; justify-content:center; width:60px; height:60px; border-radius:50%; background:#0b77cc; color:#fff; font-size:28px; text-decoration:none; box-shadow:0 12px 24px rgba(0,0,0,0.22);}
        .floating-chat-button a:hover {background:#0955a1;}
        </style>
        <div class="floating-chat-button"><a href="#chatbot">💬</a></div>
        """,
        unsafe_allow_html=True,
    )

# Bộ xử lý hiển thị thông báo Toast sau khi tải lại trang
if "toast_msg" in st.session_state:
    st.toast(st.session_state.toast_msg, icon="✅")
    del st.session_state.toast_msg

# ==========================================
# CÁC HỘP THOẠI NỔI (MODAL DIALOGS)
# ==========================================
@st.dialog("Xác nhận Xử lý Chứng từ")
def confirm_approval_dialog(p_id, loai_phieu, action, ly_do, nguoi_duyet_id):
    st.write(f"Thao tác hiện tại: **{'DUYỆT' if action == 'DUYET' else 'TỪ CHỐI'}** chứng từ mã {loai_phieu}-{p_id:05d}.")
    if ly_do is None or not ly_do.strip():
        st.error("Vui lòng nhập lý do xử lý chứng từ trước khi xác nhận.")
        if st.button("Đóng", use_container_width=True):
            st.rerun()
        return
    st.write("Vui lòng xác nhận để ghi nhận dữ liệu vào hệ thống.")
    c1, c2 = st.columns(2)
    if c1.button("Xác nhận", type="primary", use_container_width=True):
        status = "ĐÃ DUYỆT" if action == "DUYET" else "TỪ CHỐI"
        endpoint = "/api/thu/status" if loai_phieu == "THU" else "/api/chi/status"
        res = requests.put(f"{API_URL}{endpoint}", json={"id": p_id, "trang_thai": status, "ly_do": ly_do, "nguoi_duyet_id": nguoi_duyet_id})
        if res.status_code == 200:
            st.success("Xử lý chứng từ thành công.")
            st.session_state.toast_msg = "Xử lý chứng từ hoàn tất."
            st.rerun()
        else:
            st.error("Không thể cập nhật chứng từ. Vui lòng thử lại.")
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
            loai_upper = loai_phieu.upper() if isinstance(loai_phieu, str) else loai_phieu
            endpoint = "/api/thu/void" if "THU" in loai_upper else "/api/chi/void"
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
                    elif res.status_code == 401:
                        st.error("Thông tin xác thực không chính xác.")
                    else:
                        st.error(f"Lỗi máy chủ: {res.status_code} {res.reason}. Vui lòng kiểm tra backend đang chạy.")
                except requests.exceptions.RequestException:
                    st.error("Mất kết nối đến máy chủ xử lý. Vui lòng kiểm tra server backend và cổng API.")
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
            c1, c2, c3 = st.columns(3)
            tien = c1.number_input(f"Giá trị thu ({st.session_state.currency})", min_value=0.0, step=10000.0, format="%f")
            c1.caption("Nhập giá trị thu đã ghi nhận sau khi áp dụng voucher, nếu có.")

            cua_hang_options = [k for k in MAP_CUA_HANG.keys()]
            cua_hang = c1.selectbox("Đơn vị phát sinh", cua_hang_options)
            
            kenh_options = [k for k in MAP_KENH.keys()]
            kenh = c2.selectbox("Kênh phân phối", kenh_options)
            kenh_mo_ta = None
            if kenh == "Khác":
                kenh_mo_ta = c2.text_input("Mô tả kênh phân phối khác", placeholder="Ví dụ: doanh thu từ đầu tư, vốn góp, dịch vụ thuê...")
            
            pt_options = [k for k in MAP_PTTT.keys()]
            pt = c3.selectbox("Phương thức thanh toán", pt_options)
            pttt_mo_ta = None
            if pt == "Khác":
                pttt_mo_ta = c3.text_input("Mô tả phương thức thanh toán khác", placeholder="Ví dụ: PayPal, GG Pay, Thanh toán quốc tế...")
            
            voucher_options = ["Không áp dụng"] + [f"{i}%" for i in range(5, 101, 5)]
            voucher_selected = st.selectbox("Voucher", voucher_options)
            voucher_percentage = int(voucher_selected[:-1]) if voucher_selected != "Không áp dụng" else None
            if voucher_percentage is not None:
                st.caption("Số tiền thu đã là giá trị sau khi trừ voucher. Thông tin voucher dùng để kiểm soát.")
            
            mo_ta_giao_dich = st.text_area("Mô tả diễn giải (việc thu cho việc gì)", placeholder="Ví dụ: Thu từ bán hàng online, thu từ đầu tư...")
            
            tra_cham_check = st.checkbox("Có trả chậm/trả góp")
            tra_cham_tra_gop = None
            if tra_cham_check:
                tra_cham_tra_gop = st.text_area("Ghi chú trả chậm/trả góp", placeholder="Ví dụ: Trả chậm 3 tháng, trả góp 12 tháng...")
            
            if st.form_submit_button("Lưu dữ liệu", type="primary"):
                if tien <= 0:
                    st.error("Yêu cầu nhập giá trị lớn hơn 0.")
                elif kenh == "Khác" and not kenh_mo_ta:
                    st.error("Yêu cầu nhập mô tả kênh phân phối khác.")
                elif pt == "Khác" and not pttt_mo_ta:
                    st.error("Yêu cầu nhập mô tả phương thức thanh toán khác.")
                else:
                    cua_hang_id = MAP_CUA_HANG[cua_hang]
                    kenh_id = MAP_KENH[kenh]
                    pttt_id = MAP_PTTT[pt]
                    payload = {
                        "so_tien": tien,
                        "cua_hang_id": cua_hang_id,
                        "kenh_id": kenh_id,
                        "pttt_id": pttt_id,
                        "nguoi_tao_id": st.session_state.id,
                        "ghi_chu": "",
                        "currency": st.session_state.currency,
                        "kenh_mo_ta": kenh_mo_ta,
                        "pttt_mo_ta": pttt_mo_ta,
                        "voucher_percentage": voucher_percentage,
                        "mo_ta_giao_dich": mo_ta_giao_dich,
                        "tra_cham_tra_gop": tra_cham_tra_gop
                    }
                    try:
                        r = requests.post(f"{API_URL}/api/thu", json=payload)
                        if r.status_code == 200:
                            st.toast("Doanh thu đã được ghi nhận thành công và chuyển vào luồng xét duyệt.", icon="✅")
                            st.session_state.toast_msg = "Phiếu thu đã được gửi duyệt."
                            st.rerun()
                        else:
                            st.toast("Không thể lưu dữ liệu doanh thu. Vui lòng thử lại.", icon="⚠️")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Lỗi kết nối: {e}")

    with t2:
        with st.form("chi_form", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            tien_chi = c1.number_input(f"Giá trị chi ({st.session_state.currency})", min_value=0.0, step=10000.0, format="%f")
            c1.caption("Nhập giá trị chi đã ghi nhận sau khi áp dụng voucher, nếu có.")

            cua_hang_chi_options = [k for k in MAP_CUA_HANG.keys()]
            cua_hang_chi = c1.selectbox("Đơn vị phát sinh", cua_hang_chi_options)

            loai_chi_options = list(MAP_LOAI_CHI.keys())
            loai_chi = c1.selectbox("Hạng mục chi phí", loai_chi_options)
            
            mo_ta_noi_dung_chi = st.text_area("Mô tả nội dung chi", placeholder=f"Vui lòng mô tả rõ nội dung chi cho {loai_chi.lower()}")

            kenh_chi_options = [k for k in MAP_KENH.keys()]
            kenh_chi = c2.selectbox("Kênh phân phối", kenh_chi_options)
            kenh_mo_ta_chi = None
            if kenh_chi == "Khác":
                kenh_mo_ta_chi = c2.text_input("Mô tả kênh phân phối khác", placeholder="Ví dụ: chi phí từ đầu tư, vốn góp, dịch vụ thuê...")

            pt_chi_options = [k for k in MAP_PTTT.keys()]
            pt_chi = c3.selectbox("Phương thức thanh toán", pt_chi_options)
            pttt_mo_ta_chi = None
            if pt_chi == "Khác":
                pttt_mo_ta_chi = c3.text_input("Mô tả phương thức thanh toán khác", placeholder="Ví dụ: PayPal, GG Pay, Thanh toán quốc tế...")

            voucher_options_chi = ["Không áp dụng"] + [f"{i}%" for i in range(5, 101, 5)]
            voucher_selected_chi = st.selectbox("Voucher", voucher_options_chi)
            voucher_percentage_chi = int(voucher_selected_chi[:-1]) if voucher_selected_chi != "Không áp dụng" else None
            if voucher_percentage_chi is not None:
                st.caption("Số tiền chi đã là giá trị sau khi trừ voucher. Thông tin voucher dùng để kiểm soát.")

            mo_ta_giao_dich_chi = st.text_area("Mô tả diễn giải (việc chi cho việc gì)", placeholder="Ví dụ: Chi cho nhập hàng, chi cho lương nhân viên...")
            
            tra_cham_check_chi = st.checkbox("Có trả chậm/trả góp")
            tra_cham_tra_gop_chi = None
            if tra_cham_check_chi:
                tra_cham_tra_gop_chi = st.text_area("Ghi chú trả chậm/trả góp", placeholder="Ví dụ: Trả chậm 3 tháng, trả góp 12 tháng...")

            submitted = st.form_submit_button("Chuyển phê duyệt", type="primary")
            
            if submitted:
                if tien_chi <= 0:
                    st.error("Yêu cầu nhập giá trị đề xuất lớn hơn 0.")
                elif not mo_ta_noi_dung_chi or not mo_ta_noi_dung_chi.strip():
                    st.error("Yêu cầu nhập mô tả nội dung chi.")
                elif kenh_chi == "Khác" and not kenh_mo_ta_chi:
                    st.error("Yêu cầu nhập mô tả kênh phân phối khác.")
                elif pt_chi == "Khác" and not pttt_mo_ta_chi:
                    st.error("Yêu cầu nhập mô tả phương thức thanh toán khác.")
                else:
                    loai_chi_id = MAP_LOAI_CHI[loai_chi]
                    cua_hang_chi_id = MAP_CUA_HANG[cua_hang_chi]
                    kenh_id_chi = MAP_KENH[kenh_chi]
                    pttt_id_chi = MAP_PTTT[pt_chi]
                    final_note = mo_ta_noi_dung_chi.strip() if mo_ta_noi_dung_chi.strip() else ""

                    payload = {
                        "loai_chi_id": loai_chi_id,
                        "so_tien": tien_chi,
                        "cua_hang_id": cua_hang_chi_id,
                        "kenh_id": kenh_id_chi,
                        "pttt_id": pttt_id_chi,
                        "nguoi_tao_id": st.session_state.id,
                        "ghi_chu": final_note,
                        "currency": st.session_state.currency,
                        "kenh_mo_ta": kenh_mo_ta_chi,
                        "pttt_mo_ta": pttt_mo_ta_chi,
                        "voucher_percentage": voucher_percentage_chi,
                        "mo_ta_giao_dich": mo_ta_giao_dich_chi,
                        "tra_cham_tra_gop": tra_cham_tra_gop_chi
                    }
                    try:
                        r = requests.post(f"{API_URL}/api/chi", json=payload)
                        if r.status_code == 200:
                            st.toast("Đề xuất chi phí đã được gửi duyệt.", icon="✅")
                            st.session_state.toast_msg = "Phiếu chi đã được gửi duyệt."
                            st.rerun()
                        else:
                            st.toast("Không thể lưu dữ liệu đề xuất chi phí. Vui lòng thử lại.", icon="⚠️")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Lỗi kết nối: {e}")

elif st.session_state.role == "KETOAN":
    tabs = st.tabs(["Xét duyệt Chứng từ", "Điều chỉnh Sai sót", "Nạp Dữ liệu", "Quản lý Danh mục"])

    with tabs[0]:
        st.subheader("Xét duyệt Chứng từ Doanh thu và Chi phí")

        ds_thu = requests.get(f"{API_URL}/api/thu/pending").json()
        ds_chi = requests.get(f"{API_URL}/api/chi/pending").json()

        st.markdown("#### Phiếu thu chờ duyệt")
        if not ds_thu:
            st.caption("Hiện chưa có phiếu thu chờ duyệt.")
        for p in ds_thu:
            with st.expander(f"Mã tham chiếu: THU-{p['id']:05d} | Đơn vị: {p.get('cua_hang', 'Chưa có')} | Giá trị: {format_currency(p['so_tien'], p.get('currency'))}"):
                c_a, c_b = st.columns([3, 1])
                ly_do = c_a.text_input("Ghi chú xử lý:", key=f"lydo_thu_{p['id']}", value=p['ghi_chu'])
                col1, col2 = c_b.columns(2)
                if col1.button("Duyệt", key=f"btn_duyet_thu_{p['id']}", use_container_width=True):
                    confirm_approval_dialog(p['id'], "THU", "DUYET", ly_do, st.session_state.id)
                if col2.button("Từ chối", key=f"btn_tuchoi_thu_{p['id']}", use_container_width=True):
                    confirm_approval_dialog(p['id'], "THU", "TUCHOI", ly_do, st.session_state.id)

        st.markdown("#### Phiếu chi chờ duyệt")
        if not ds_chi:
            st.caption("Hiện chưa có phiếu chi chờ duyệt.")
        for p in ds_chi:
            with st.expander(f"Mã tham chiếu: PC-{p['id']:05d} | Loại: {p['ten_loai']} | Đơn vị: {p.get('cua_hang', 'Chưa có')} | Giá trị: {format_currency(p['so_tien'], p.get('currency'))}"):
                c_a, c_b = st.columns([3, 1])
                ly_do = c_a.text_input("Ghi chú xử lý:", key=f"lydo_chi_{p['id']}", value=p['ghi_chu'])
                col1, col2 = c_b.columns(2)
                if col1.button("Duyệt", key=f"btn_duyet_chi_{p['id']}", use_container_width=True):
                    confirm_approval_dialog(p['id'], "CHI", "DUYET", ly_do, st.session_state.id)
                if col2.button("Từ chối", key=f"btn_tuchoi_chi_{p['id']}", use_container_width=True):
                    confirm_approval_dialog(p['id'], "CHI", "TUCHOI", ly_do, st.session_state.id)

        st.divider()
        st.subheader("Danh sách chứng từ đã xử lý")
        ds_thu_processed = requests.get(f"{API_URL}/api/thu/processed").json()
        ds_chi_processed = requests.get(f"{API_URL}/api/chi/processed").json()
        if ds_thu_processed:
            st.markdown("**Phiếu thu đã xử lý**")
            df_thu_proc = pd.DataFrame(ds_thu_processed)
            df_thu_proc['so_tien'] = df_thu_proc.apply(lambda row: format_currency(row['so_tien'], row.get('currency')), axis=1)
            df_thu_proc = df_thu_proc.rename(columns={
                'id': 'Mã hệ thống',
                'ngay_tao': 'Thời gian',
                'so_tien': 'Giá trị',
                'trang_thai': 'Trạng thái',
                'nguoi_duyet': 'Nhân sự xử lý',
                'ghi_chu': 'Ghi chú',
                'currency': 'Tiền tệ'
            })
            st.dataframe(df_thu_proc[['Mã hệ thống', 'Thời gian', 'Giá trị', 'Tiền tệ', 'Trạng thái', 'Nhân sự xử lý', 'Ghi chú']], use_container_width=True, hide_index=True)
        if ds_chi_processed:
            st.markdown("**Phiếu chi đã xử lý**")
            df_chi_proc = pd.DataFrame(ds_chi_processed)
            df_chi_proc['so_tien'] = df_chi_proc.apply(lambda row: format_currency(row['so_tien'], row.get('currency')), axis=1)
            df_chi_proc = df_chi_proc.rename(columns={
                'id': 'Mã hệ thống',
                'ngay_tao': 'Thời gian',
                'so_tien': 'Giá trị',
                'trang_thai': 'Trạng thái',
                'nguoi_duyet': 'Nhân sự xử lý',
                'ghi_chu': 'Ghi chú',
                'currency': 'Tiền tệ'
            })
            st.dataframe(df_chi_proc[['Mã hệ thống', 'Thời gian', 'Giá trị', 'Tiền tệ', 'Trạng thái', 'Nhân sự xử lý', 'Ghi chú']], use_container_width=True, hide_index=True)
        if not ds_thu_processed and not ds_chi_processed:
            st.caption("Chưa có chứng từ đã xử lý để hiển thị.")

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
            df_void['so_tien'] = df_void.apply(lambda row: format_currency(row['so_tien'], row.get('currency')), axis=1)
            df_void = df_void.rename(columns={
                'loai': 'Phân loại',
                'id': 'Mã tham chiếu',
                'so_tien': 'Giá trị',
                'currency': 'Tiền tệ',
                'ly_do': 'Diễn giải'
            })
            st.dataframe(df_void[['Phân loại', 'Mã tham chiếu', 'Giá trị', 'Tiền tệ', 'Diễn giải']], use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("Nạp Dữ liệu Đối soát Hệ thống")
        st.caption("Cấu trúc tệp yêu cầu (.csv, .xlsx): loai_giao_dich (THU/CHI), so_tien, ma_kenh_hoac_loai (1,2,3), ghi_chu.")
        uploaded_file = st.file_uploader("Lựa chọn tệp dữ liệu", type=["csv", "xlsx"])
        
        if uploaded_file:
            if st.session_state.get('import_filename') != uploaded_file.name:
                st.session_state.import_preview = None
                st.session_state.import_df = None
                st.session_state.import_filename = uploaded_file.name
                st.session_state.import_upload_msg = None
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                if df.empty:
                    st.error("Tệp không có dữ liệu. Vui lòng kiểm tra lại nội dung.")
                else:
                    required_columns = {'loai_giao_dich', 'so_tien', 'ma_kenh_hoac_loai'}
                    if not required_columns.issubset(set(df.columns)):
                        st.error(f"Tệp thiếu cột bắt buộc: {', '.join(required_columns - set(df.columns))}")
                    else:
                        st.session_state.import_preview = df.head(10)
                        st.session_state.import_df = df
                        st.session_state.import_upload_msg = f"Tệp '{uploaded_file.name}' đã được tải lên thành công. Bạn có thể xem trước và nạp ngay vào hệ thống."
            except Exception as e:
                st.error(f"Lỗi trích xuất tệp dữ liệu. Vui lòng kiểm tra lại định dạng. ({e})")

        if st.session_state.get('import_upload_msg'):
            st.toast(st.session_state.import_upload_msg, icon="✅")
            del st.session_state.import_upload_msg

        if st.session_state.get('import_preview') is not None:
            st.subheader("Xem trước dữ liệu")
            st.dataframe(st.session_state.import_preview, use_container_width=True)
            if st.button("Thực thi nạp dữ liệu", type="primary"):
                df = st.session_state.import_df
                payload = []
                error_rows = []
                for idx, row in df.iterrows():
                    try:
                        loai_giao_dich = str(row['loai_giao_dich']).strip().upper()
                        if loai_giao_dich not in {'THU', 'CHI'}:
                            raise ValueError("Giá trị loai_giao_dich phải là THU hoặc CHI")
                        so_tien = float(row['so_tien'])
                        ma_kenh_hoac_loai = int(float(row['ma_kenh_hoac_loai']))
                        ghi_chu = str(row.get('ghi_chu', '')).strip() or 'Import đối soát tự động'
                        payload.append({
                            "loai_giao_dich": loai_giao_dich,
                            "so_tien": so_tien,
                            "ma_kenh_hoac_loai": ma_kenh_hoac_loai,
                            "pttt_id": 1,
                            "nguoi_tao_id": st.session_state.id,
                            "ghi_chu": ghi_chu
                        })
                    except Exception as parse_error:
                        error_rows.append((idx + 1, str(parse_error)))

                if error_rows:
                    error_text = "\n".join([f"Dòng {row}: {msg}" for row, msg in error_rows])
                    st.error(f"Có lỗi trong tệp nhập:\n{error_text}")
                else:
                    res = requests.post(f"{API_URL}/api/import", json={"data": payload})
                    if res.status_code == 200:
                        st.toast(res.json().get('message', 'Nạp dữ liệu vào hệ thống hoàn tất.'), icon="✅")
                        st.info("Dữ liệu đã được ghi nhận và chuyển vào hệ thống. Nếu cần, bấm Tải lại dữ liệu để làm mới danh mục.")
                        st.balloons()
                        st.session_state.import_preview = None
                        st.session_state.import_df = None
                        st.session_state.import_filename = None
                        st.session_state.import_upload_msg = None
                    else:
                        st.toast(f"Lỗi server: {res.text}", icon="⚠️")
    
    with tabs[3]:
        st.subheader("Quản lý Danh mục Hệ thống")
        if "category_last_refresh" not in st.session_state:
            st.session_state.category_last_refresh = datetime.now()
        c1, c2 = st.columns([4, 1])
        c1.markdown("<div style='background:#eef7ff; padding:10px; border-radius:10px;'>Danh mục hệ thống được làm mới từ database. Nếu bạn đã cập nhật dữ liệu, hãy nhấn nút Tải lại để nhận danh mục mới nhất.</div>", unsafe_allow_html=True)
        c2.write("")
        if c2.button("Tải lại dữ liệu", use_container_width=True):
            st.session_state.category_last_refresh = datetime.now()
            st.rerun()
        st.markdown(f"**Cập nhật lần cuối:** {st.session_state.category_last_refresh.strftime('%d/%m/%Y %H:%M:%S')}")
        sub_tabs = st.tabs(["Cửa hàng", "Kênh bán", "Phương thức TT", "Loại chi phí"])
        
        def show_dim_table(endpoint, title):
            res = requests.get(f"{API_URL}/{endpoint}")
            if res.status_code == 200:
                df = pd.DataFrame(res.json())
                if not df.empty:
                    df.columns = [c.replace('_', ' ').title() for c in df.columns]
                    styled = df.style.set_properties(**{
                        'background-color': '#ffffff',
                        'color': '#0b3d91',
                        'border-color': '#d2e3fc',
                        'font-size': '14px'
                    }).set_table_styles([
                        {'selector': 'th', 'props': [('background-color', '#0b77cc'), ('color', 'white'), ('font-weight', 'bold'), ('font-size','14px')]}
                    ])
                    st.dataframe(styled, use_container_width=True)
                else:
                    st.info(f"Không có dữ liệu {title}.")
            else:
                st.error(f"Không tải được {title}.")
        
        def add_category_form(endpoint, title, placeholder):
            with st.expander(f"➕ Thêm {title} mới"):
                with st.form(f"add_{endpoint.split('/')[-1]}", clear_on_submit=True):
                    name = st.text_input(f"Tên {title}", placeholder=placeholder)
                    if st.form_submit_button("Thêm mới", type="primary"):
                        if not name.strip():
                            st.error(f"Yêu cầu nhập tên {title}.")
                        else:
                            res = requests.post(f"{API_URL}/{endpoint}", json={"name": name.strip()}, 
                                              params={"role": st.session_state.role})
                            if res.status_code == 200:
                                st.success(f"Đã thêm {title} mới: {name.strip()}")
                                # Refresh categories for all users
                                load_categories()
                                st.session_state.category_last_refresh = datetime.now()
                                st.rerun()
                            else:
                                st.error(f"Không thể thêm {title}. {res.text}")
        
        with sub_tabs[0]:
            add_category_form('api/dim_cua_hang', 'Cửa hàng', 'Ví dụ: Cơ sở 03 - Hà Nội')
            show_dim_table('api/dim_cua_hang', 'Cửa hàng')
        with sub_tabs[1]:
            add_category_form('api/dim_kenh_ban', 'Kênh bán', 'Ví dụ: Website công ty')
            show_dim_table('api/dim_kenh_ban', 'Kênh bán')
        with sub_tabs[2]:
            add_category_form('api/dim_phuong_thuc_tt', 'Phương thức thanh toán', 'Ví dụ: Ví điện tử MoMo')
            show_dim_table('api/dim_phuong_thuc_tt', 'Phương thức thanh toán')
        with sub_tabs[3]:
            add_category_form('api/dim_loai_chi', 'Loại chi phí', 'Ví dụ: Chi phí Marketing')
            show_dim_table('api/dim_loai_chi', 'Loại chi')

elif st.session_state.role == "QUANLY":
    tabs = st.tabs(["Báo cáo Tổng quan", "Chi tiết Thu", "Chi tiết Chi", "Quản lý Người dùng", "Trợ lý AI", "Live Feed"])
    
    with tabs[0]:
        render_floating_chat_icon()
        st.subheader("Báo cáo Quản trị (Data Warehouse)")
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        period_type = col1.selectbox("Tổng hợp theo", ["Ngày", "Tháng", "Năm"], index=0)

        if period_type == "Ngày":
            start_date = col2.date_input("Từ ngày", value=datetime.now() - timedelta(days=30))
            end_date = col3.date_input("Đến ngày", value=datetime.now())
            show_hour = col4.checkbox("Lọc theo giờ (tùy chọn)", value=False)
            if show_hour:
                t1, t2 = st.columns(2)
                start_time_obj = t1.time_input("Bắt đầu", value=datetime.strptime("00:00", "%H:%M").time())
                end_time_obj = t2.time_input("Kết thúc", value=datetime.strptime("23:59", "%H:%M").time())
                if start_time_obj >= end_time_obj:
                    st.error("Giờ bắt đầu phải nhỏ hơn giờ kết thúc. Đã sử dụng mặc định 00:00 - 23:59.")
                    start_time = "00:00"
                    end_time = "23:59"
                else:
                    start_time = start_time_obj.strftime('%H:%M')
                    end_time = end_time_obj.strftime('%H:%M')
            else:
                start_time = "00:00"
                end_time = "23:59"
        elif period_type == "Tháng":
            month_start = col2.date_input("Tháng bắt đầu", value=datetime(datetime.now().year, datetime.now().month, 1).date())
            month_end = col3.date_input("Tháng kết thúc", value=datetime.now().date())
            start_date = month_start.replace(day=1)
            last_day = calendar.monthrange(month_end.year, month_end.month)[1]
            end_date = month_end.replace(day=last_day)
            start_time = "00:00"
            end_time = "23:59"
        else:
            years = [datetime.now().year - 2, datetime.now().year - 1, datetime.now().year]
            year_start = col2.selectbox("Năm bắt đầu", years, index=2)
            year_end = col3.selectbox("Năm kết thúc", years, index=2)
            start_date = datetime(year_start, 1, 1).date()
            end_date = datetime(year_end, 12, 31).date()
            start_time = "00:00"
            end_time = "23:59"

        filter_click = col4.button("Lọc dữ liệu")

        if st.button("Thực thi ETL", use_container_width=True):
            etl_res = requests.post(f"{API_URL}/api/etl")
            if etl_res.status_code == 200:
                st.success("ETL đã được thực thi thành công. Dữ liệu dashboard đã được cập nhật.")
                st.rerun()
            else:
                st.error(f"Không thể thực thi ETL: {etl_res.text}")

        c_title, c_btn = st.columns([4, 1])
        c_title.caption("Dữ liệu được trích xuất trực tiếp từ phân hệ phân tích OLAP.")
        last_update = requests.get(f"{API_URL}/api/dashboard/last_update")
        if last_update.status_code == 200 and last_update.json().get('latest_update'):
            c_title.markdown(f"<span style='color:#0b6623'>Dữ liệu OLAP cập nhật gần nhất: {last_update.json().get('latest_update')}</span>", unsafe_allow_html=True)
        if c_btn.button("Tải lại bộ đệm", use_container_width=True):
            st.rerun()

        if start_date > end_date:
            st.error("Khoảng thời gian không hợp lệ: ngày bắt đầu phải trước ngày kết thúc.")
        else:
            params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d'), "start_time": start_time, "end_time": end_time}
            res_dw = requests.get(f"{API_URL}/api/dashboard", params=params)
            if res_dw.status_code == 200:
                df_dw = pd.DataFrame(res_dw.json())
                if not df_dw.empty:
                    total_thu = df_dw['tong_thu'].sum()
                    total_chi = df_dw['tong_chi_da_duyet'].sum()
                    total_ln = df_dw['loi_nhuan'].sum()
                    ty_suat = (total_ln / total_thu * 100) if total_thu > 0 else 0

                    days_diff = (end_date - start_date).days + 1
                    prev_end = start_date - timedelta(days=1)
                    prev_start = prev_end - timedelta(days=days_diff - 1)
                    prev_params = {'start_date': prev_start.strftime('%Y-%m-%d'), 'end_date': prev_end.strftime('%Y-%m-%d')}
                    prev_res = requests.get(f"{API_URL}/api/dashboard", params=prev_params)
                    prev_total_thu = prev_total_chi = prev_total_ln = 0
                    if prev_res.status_code == 200:
                        prev_df = pd.DataFrame(prev_res.json())
                        if not prev_df.empty:
                            prev_total_thu = prev_df['tong_thu'].sum()
                            prev_total_chi = prev_df['tong_chi_da_duyet'].sum()
                            prev_total_ln = prev_df['loi_nhuan'].sum()

                    delta_thu = total_thu - prev_total_thu
                    delta_chi = total_chi - prev_total_chi
                    delta_ln = total_ln - prev_total_ln

                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Tổng Doanh Thu", format_currency(total_thu), delta=format_currency(delta_thu) if delta_thu != 0 else None)
                    k2.metric("Tổng Chi Phí", format_currency(total_chi), delta=format_currency(delta_chi) if delta_chi != 0 else None)
                    k3.metric("Lợi Nhuận Thuần", format_currency(total_ln), delta=format_currency(delta_ln) if delta_ln != 0 else None)
                    k4.metric("Tỷ suất Lợi nhuận", f"{ty_suat:.1f}%")
                    st.markdown(f"**Hiển thị dữ liệu từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}**")
                    st.markdown(f"<span style='color:#666'>Kỳ lọc: {period_type}. Tổng số bản ghi OLAP: {len(df_dw)}.</span>", unsafe_allow_html=True)
                    trend_color = '#147c16' if delta_ln >= 0 else '#b91c1c'
                    trend_label = 'tăng' if delta_ln >= 0 else 'giảm'
                    st.markdown(f"<div style='padding:10px; border-radius:10px; background:#f0fdf4; color:{trend_color};'>Kết quả nổi bật: lợi nhuận {trend_label} {format_currency(abs(delta_ln))} so với kỳ trước.</div>", unsafe_allow_html=True)

                    if filter_click:
                        st.subheader("📊 Dữ liệu đã lọc")
                        df_dw_display = df_dw.copy()
                        df_dw_display.columns = ['Ngày', 'Tổng Thu', 'Tổng Chi Đã Duyệt', 'Lợi nhuận', 'Trạng thái KD']
                        df_dw_display['Tổng Thu'] = df_dw_display['Tổng Thu'].apply(lambda x: format_currency(float(x)))
                        df_dw_display['Tổng Chi Đã Duyệt'] = df_dw_display['Tổng Chi Đã Duyệt'].apply(lambda x: format_currency(float(x)))
                        df_dw_display['Lợi nhuận'] = df_dw_display['Lợi nhuận'].apply(lambda x: format_currency(float(x)))
                        styled_dw = df_dw_display.style.map(highlight_profit_cell, subset=["Lợi nhuận"])
                        st.dataframe(styled_dw, use_container_width=True)
                        st.markdown("---")

                    last_update = requests.get(f"{API_URL}/api/dashboard/last_update")
                    update_info = ""
                    if last_update.status_code == 200 and last_update.json().get('latest_update'):
                        latest_update = datetime.fromisoformat(last_update.json()['latest_update'].replace('Z', '+00:00'))
                        update_info = f" | Cập nhật cuối: {latest_update.strftime('%d/%m/%Y %H:%M:%S')}"

                    st.markdown(f"**📈 Biểu đồ Khảo sát Dòng tiền** (Từ {start_date.strftime('%d/%m/%Y %H:%M')} đến {end_date.strftime('%d/%m/%Y %H:%M')}{update_info})")
                    fig_line = px.line(df_dw, x='ngay', y=['tong_thu', 'tong_chi_da_duyet'], labels={'value': 'Giá trị', 'ngay': 'Kỳ báo cáo', 'variable': 'Chỉ tiêu'}, markers=True)
                    fig_line.update_layout(transition={'duration': 500, 'easing': 'cubic-in-out'}, plot_bgcolor='#f9fbff')
                    st.plotly_chart(fig_line, use_container_width=True)
                    st.markdown(f"**📊 Biểu đồ Lợi nhuận Theo Ngày** (Từ {start_date.strftime('%d/%m/%Y %H:%M')} đến {end_date.strftime('%d/%m/%Y %H:%M')}{update_info})")
                    fig_bar = px.bar(df_dw, x='ngay', y='loi_nhuan', title='Lợi nhuận', labels={'loi_nhuan': 'Lợi nhuận', 'ngay': 'Ngày'}, color='loi_nhuan', color_continuous_scale=['red', 'green'])
                    fig_bar.update_traces(marker_line_width=0)
                    fig_bar.update_layout(transition={'duration': 500}, plot_bgcolor='#f9fbff')
                    st.plotly_chart(fig_bar, use_container_width=True)

                    if st.button("🔄 Tải lại dữ liệu biểu đồ", help="Cập nhật dữ liệu từ database mới nhất"):
                        st.rerun()

                    st.markdown("**Phân bố Trạng thái Kinh doanh**")
                    if 'trang_thai_kd' in df_dw.columns:
                        status_counts = df_dw['trang_thai_kd'].value_counts()
                        fig_pie = px.pie(values=status_counts.values, names=status_counts.index, title='Trạng thái Lợi nhuận')
                        st.plotly_chart(fig_pie, use_container_width=True)

                    st.markdown(f"<span style='color:#666'>Kỳ lọc: {period_type}. Tổng số bản ghi OLAP: {len(df_dw)}. Dữ liệu tự động cập nhật khi có giao dịch mới.</span>", unsafe_allow_html=True)
                    st.markdown("**Bảng Tổng hợp Sổ cái**")
                    df_dw_display = df_dw.copy()
                    for col in ['tong_thu', 'tong_chi_da_duyet', 'loi_nhuan']:
                        df_dw_display[col] = df_dw_display[col].apply(format_currency)
                    df_dw_display.columns = ["Kỳ báo cáo", "Doanh thu", "Chi phí", "Lợi nhuận", "Trạng thái"]
                    styled_dw = df_dw_display.style.map(highlight_profit_cell, subset=["Lợi nhuận"])
                    csv_report = df_dw.to_csv(index=False).encode('utf-8')
                    st.download_button("Tải xuống báo cáo Dashboard", csv_report, file_name=f"dashboard_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv", mime='text/csv')
                    st.dataframe(styled_dw, use_container_width=True, hide_index=True)
                    with st.expander("Chi tiết giao dịch thu đã lọc"):
                        raw_params = {"start_date": start_date.strftime('%Y-%m-%d'), "end_date": end_date.strftime('%Y-%m-%d'), "start_time": start_time, "end_time": end_time}
                        res_thu = requests.get(f"{API_URL}/api/thu/range", params=raw_params)
                        if res_thu.status_code == 200:
                            df_thu = pd.DataFrame(res_thu.json())
                            if not df_thu.empty:
                                df_thu_display = df_thu.copy()
                                df_thu_display['so_tien'] = df_thu_display['so_tien'].apply(format_currency)
                                st.dataframe(df_thu_display, use_container_width=True, hide_index=True)
                            else:
                                st.info("Không có giao dịch thu trong khoảng thời gian này.")
                        else:
                            st.error("Không tải được chi tiết giao dịch thu.")

                    with st.expander("Chi tiết giao dịch chi đã lọc"):
                        res_chi = requests.get(f"{API_URL}/api/chi/range", params=raw_params)
                        if res_chi.status_code == 200:
                            df_chi = pd.DataFrame(res_chi.json())
                            if not df_chi.empty:
                                df_chi_display = df_chi.copy()
                                df_chi_display['so_tien'] = df_chi_display['so_tien'].apply(format_currency)
                                st.dataframe(df_chi_display, use_container_width=True, hide_index=True)
                            else:
                                st.info("Không có giao dịch chi trong khoảng thời gian này.")
                        else:
                            st.error("Không tải được chi tiết giao dịch chi.")
                else:
                    st.info("Chưa có dữ liệu phân tích. Vui lòng thực thi luồng ETL.")
            else:
                st.error("Lỗi lấy dữ liệu dashboard từ server.")

    with tabs[1]:
        st.subheader("Chi tiết Giao dịch Thu")
        res = requests.get(f"{API_URL}/api/thu/active")
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty:
                csv_thu = df.to_csv(index=False).encode('utf-8')
                st.download_button("Xuất CSV Thu", csv_thu, file_name="thu_active.csv", mime='text/csv')
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Không có dữ liệu.")
    
    with tabs[2]:
        st.subheader("Chi tiết Giao dịch Chi")
        res = requests.get(f"{API_URL}/api/chi/active")
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty:
                csv_chi = df.to_csv(index=False).encode('utf-8')
                st.download_button("Xuất CSV Chi", csv_chi, file_name="chi_active.csv", mime='text/csv')
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
    
    with tabs[4]:
        st.markdown("<a id='chatbot'></a>", unsafe_allow_html=True)
        st.subheader("Trợ lý ảo Tài chính")
        st.caption("Hỏi trợ lý về doanh thu, chi phí, lợi nhuận, cửa hàng có doanh thu cao nhất/ thấp nhất và các xu hướng biến động.")
        
        st.subheader("Câu hỏi quản lý tài chính")
        st.info("Chọn câu hỏi bên dưới để quản lý chỉ việc sao chép và gửi cho trợ lý. Hệ thống sẽ lấy dữ liệu từ toàn bộ hệ thống.")
        questions = [
            "Tổng doanh thu hôm nay?",
            "Tổng chi phí hôm nay?",
            "Lợi nhuận ngày hôm nay?",
            "Cửa hàng nào có doanh thu cao nhất?",
            "Cửa hàng nào có doanh thu thấp nhất?",
            "Chi phí lớn nhất tháng này?",
            "Chi phí nhỏ nhất tháng này?",
            "Tỷ lệ chi phí trên doanh thu tháng này?",
            "Doanh thu theo kênh bán hàng?",
            "Chi phí theo loại?",
            "Dự báo doanh thu tháng tới?",
            "Xu hướng lợi nhuận 30 ngày gần nhất?"
        ]
        cols = st.columns(2)
        for i, q in enumerate(questions):
            col = cols[i % 2]
            if col.button(q, key=f"q_{i}"):
                # Simulate user input
                st.session_state.chat_history.append({"role": "user", "content": q})
                # Process query
                response = f"Đang xử lý câu hỏi: {q}"
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_file_name" not in st.session_state:
            st.session_state.chat_file_name = None

        uploaded_query_file = st.file_uploader("Tải lên tệp tham chiếu để trợ lý dùng khi trả lời (CSV/XLSX/TXT)", type=["csv", "xlsx", "txt"])
        if uploaded_query_file is not None:
            st.session_state.chat_file_name = uploaded_query_file.name
            st.toast(f"Đã tải lên tệp: {uploaded_query_file.name}", icon="✅")
            st.info("Bạn có thể hỏi ngay phía dưới. Trợ lý sẽ dùng thông tin tệp làm tham chiếu.")

        if st.session_state.chat_file_name:
            st.write(f"**Tệp tham chiếu:** {st.session_state.chat_file_name}")

        if not st.session_state.chat_history:
            st.info("Gợi ý: Hỏi ví dụ 'Doanh thu hôm nay là bao nhiêu?', 'Cửa hàng nào có doanh thu cao nhất?', 'Chi phí lớn nhất là gì?'")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_input = st.chat_input("Nhập câu hỏi của bạn hoặc hỏi về tệp vừa tải lên...")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)
            
            response = f"Đang xử lý: {user_input}"
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.write(response)



    with tabs[5]:
        st.subheader("Giao dịch Real-time (Live Feed)")
        st.caption("Theo dõi các giao dịch thu/chi mới nhất, tự động làm mới mỗi 5 giây.")
        
        placeholder = st.empty()
        
        if st.button("Làm mới ngay", key="refresh_live"):
            pass  # Will refresh below
        
        while True:
            try:
                # Get recent thu
                res_thu = requests.get(f"{API_URL}/api/thu/active")
                thu_data = res_thu.json() if res_thu.status_code == 200 else []
                
                # Get recent chi
                res_chi = requests.get(f"{API_URL}/api/chi/active")
                chi_data = res_chi.json() if res_chi.status_code == 200 else []
                
                # Combine and sort by time
                all_transactions = []
                for t in thu_data:
                    all_transactions.append({
                        "type": "Thu",
                        "time": t.get("ngay_tao", ""),
                        "amount": t.get("so_tien", 0),
                        "store": t.get("cua_hang", ""),
                        "channel": t.get("kenh", ""),
                        "status": t.get("trang_thai", "")
                    })
                for c in chi_data:
                    all_transactions.append({
                        "type": "Chi",
                        "time": c.get("ngay_tao", ""),
                        "amount": c.get("so_tien", 0),
                        "category": c.get("loai_chi", ""),
                        "status": c.get("trang_thai", "")
                    })
                
                # Sort by time descending
                all_transactions.sort(key=lambda x: x["time"], reverse=True)
                
                with placeholder.container():
                    if all_transactions:
                        df = pd.DataFrame(all_transactions[:20])  # Last 20
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Chưa có giao dịch nào.")
            
            except Exception as e:
                with placeholder.container():
                    st.error(f"Lỗi tải dữ liệu: {e}")
            
            time.sleep(5)
            st.rerun()