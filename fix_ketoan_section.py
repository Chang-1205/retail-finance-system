from pathlib import Path
path = Path(r'c:\Users\trang\OneDrive\Desktop\Subjects\Nam04\QLy_UD\BTL\Cuoi_ky\Demo\retail-finance-system\frontend_streamlit\app.py')
text = path.read_text(encoding='utf-8')
start_marker = '        st.subheader("Trình tự Xét duyệt Chứng từ")'
end_marker = '\nelif st.session_state.role == "QUANLY":'
start = text.find(start_marker)
if start == -1:
    raise RuntimeError('start marker not found')
end = text.find(end_marker, start)
if end == -1:
    raise RuntimeError('end marker not found')
new_block = '''elif st.session_state.role == "KETOAN":
    tabs = st.tabs(["Xét duyệt Chứng từ", "Điều chỉnh Sai sót", "Nạp Dữ liệu", "Quản lý Danh mục"])

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
            if st.session_state.get('import_filename') != uploaded_file.name:
                st.session_state.import_preview = None
                st.session_state.import_df = None
                st.session_state.import_filename = uploaded_file.name
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
                        st.info("Tệp đã được tải lên và xác thực thành công. Nhấn 'Thực thi nạp dữ liệu' để hoàn tất.")
            except Exception as e:
                st.error(f"Lỗi trích xuất tệp dữ liệu. Vui lòng kiểm tra lại định dạng. ({e})")

        if st.session_state.get('import_preview') is not None:
            st.subheader("Xem trước dữ liệu")
            st.dataframe(st.session_state.import_preview, use_container_width=True)
            if st.button("Thực thi nạp dữ liệu", type="primary"):
                df = st.session_state.import_df
                payload = []
                error_rows = False
                for _, row in df.iterrows():
                    try:
                        payload.append({
                            "loai_giao_dich": str(row['loai_giao_dich']).strip(),
                            "so_tien": float(row['so_tien']),
                            "ma_kenh_hoac_loai": int(row['ma_kenh_hoac_loai']),
                            "pttt_id": 1,
                            "nguoi_tao_id": st.session_state.id,
                            "ghi_chu": str(row.get('ghi_chu', 'Import đối soát tự động'))
                        })
                    except Exception as parse_error:
                        st.error(f"Dòng dữ liệu không hợp lệ: {parse_error}")
                        error_rows = True
                        break
                if not error_rows:
                    res = requests.post(f"{API_URL}/api/import", json={"data": payload})
                    if res.status_code == 200:
                        st.success(res.json().get('message', 'Nạp dữ liệu vào hệ thống hoàn tất.'))
                        st.info("Dữ liệu đã được ghi nhận chính xác. Vui lòng bấm Tải lại dữ liệu để cập nhật các bảng tham chiếu nếu cần.")
                        st.balloons()
                        st.session_state.import_preview = None
                        st.session_state.import_df = None
                    else:
                        st.error(f"Lỗi server: {res.text}")

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
        
        with sub_tabs[0]:
            show_dim_table('api/dim_cua_hang', 'Cửa hàng')
        with sub_tabs[1]:
            show_dim_table('api/dim_kenh_ban', 'Kênh bán')
        with sub_tabs[2]:
            show_dim_table('api/dim_phuong_thuc_tt', 'Phương thức thanh toán')
        with sub_tabs[3]:
            show_dim_table('api/dim_loai_chi', 'Loại chi phí')

elif st.session_state.role == "QUANLY":
'''
path.write_text(text[:start] + new_block + text[end:], encoding='utf-8')
print('rewrite done')
