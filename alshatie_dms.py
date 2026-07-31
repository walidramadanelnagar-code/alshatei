import os
import sys
import shutil
import io
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st

from database import (
    init_db, log_activity, verify_user, 
    get_all_users, get_all_folders, get_subfolders, 
    get_connection, hash_password
)
from translations import TRANSLATIONS

st.set_page_config(page_title="نظام ضبط ومشاركة الوثائق - أعمال الشاطئ", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<link rel="icon" type="image/x-icon" href="static/favicon.ico">
""", unsafe_allow_html=True)

# =============================================================
# 🎨 إعدادات اللغة
# =============================================================
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

# =============================================================
# 🎨 التصميم النهائي (نسخة الترجمة النظيفة)
# =============================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    header {{visibility: hidden !important;}}
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden !important;}}
    .stDeployButton {{display: none !important;}}
    [data-testid="stStatusWidget"] {{visibility: hidden !important;}}
    
    html, body, .stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, div, span, p {{
        font-family: 'Cairo', sans-serif !important;
    }}
    
    .stApp {{ background-color: #f1f5f9 !important; }}
    
    section[data-testid="stSidebar"] {{ display: none !important; }}
    
    /* ✅ تنسيق أزرار التنقل (شكل الأزرار الأفقية) */
    .stRadio > div {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }}
    .stRadio > div[role="radiogroup"] {{
        flex-direction: row !important;
    }}
    .stRadio label {{
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1px solid transparent !important;
        transition: 0.3s !important;
        margin: 0 !important;
    }}
    .stRadio label:hover {{
        background-color: #e2e8f0 !important;
    }}
    .stRadio div[data-testid="stMarkdownContainer"] p {{
        color: #ffffff !important;
        background-color: #2563eb !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
    }}
    .stRadio div[role="radiogroup"] input {{
        display: none !important;
    }}

    /* ✅ تنسيق الكروت البيضاء (لكل الشاشات) */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextInput),
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea),
    div[data-testid="stVerticalBlock"] > div:has(div.stSelectbox),
    div[data-testid="stVerticalBlock"] > div:has(div.stFileUploader),
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError,
    .stExpander, .stTabs {{
        background-color: #ffffff !important;
        padding: 16px !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        border: 1px solid #e2e8f0 !important;
        margin-bottom: 15px !important;
    }}

    h1, h2, h3, h4, h5, h6 {{ color: #2563eb !important; font-weight: 700 !important; }}
    .stApp, .stMarkdown, .stCaption, .stDataFrame,
    .stMetric, .stColumns, .stContainer, .stEmpty,
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stFileUploader label, .stRadio label, .stCheckbox label {{
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"], .stNumberInput input, .stDateInput input,
    .stTimeInput input {{
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }}

    /* ✅ الأزرار (أزرق ونص أبيض) */
    .stButton button {{
        color: #ffffff !important;
        background-color: #2563eb !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: 0.3s;
    }}
    .stButton button:hover {{ background-color: #1d4ed8 !important; transform: translateY(-2px); }}
    
    .stButton button[kind="secondary"],
    .stButton button:not([kind]) {{ background-color: #1e293b !important; }}

    .custom-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: rgba(255, 255, 255, 0.9);
        text-align: center;
        padding: 12px 0;
        font-size: 14px;
        border-top: 1px solid #e2e8f0;
        z-index: 999;
    }}
    .custom-footer span {{ color: #2563eb; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
""", unsafe_allow_html=True)

# =============================================================
# قاعدة البيانات
# =============================================================
def update_db_schema():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE user_files ADD COLUMN deleted_by_sender INTEGER DEFAULT 0")
        conn.commit()
        conn.close()
    except:
        pass
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE user_files ADD COLUMN deleted_by_recipient INTEGER DEFAULT 0")
        conn.commit()
        conn.close()
    except:
        pass

update_db_schema()
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.allowed = []
    st.session_state.role = "User"

# =============================================================
# st.query_params
# =============================================================
query_params = st.query_params
guest_login = query_params.get("guest")

if guest_login:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status FROM users WHERE username = ? AND role = 'guest'", (guest_login,))
    row = cursor.fetchone()
    conn.close()
    if row and row[7] == 'active':
        st.session_state.logged_in = True
        st.session_state.user = row[0]
        st.session_state.allowed = row[1].split(",") if row[1] else []
        st.session_state.role = row[2] if row[2] else "guest"
        log_activity(guest_login, "LOGIN_AUTO", "", "System", "Auto-logged in via link")

if not st.session_state.logged_in:
    st.markdown("""
    <div style="display: flex; justify-content: center; margin-top: 40px; margin-bottom: 20px;">
        <h1 style="font-size: 42px; font-weight: 700; color: #2563eb;">مجموعة أعمال الشاطئ</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <h1 style='text-align: center; font-size: 34px;'>
        <i class="fas fa-lock-open" style="color: #2563eb; margin-right: 10px;"></i> 
        تسجيل الدخول للنظام
    </h1>
    <div style='width: 100px; height: 3px; background: #2563eb; margin: 10px auto 30px auto; border-radius: 2px;'></div>
    """, unsafe_allow_html=True)
    
    username_input = st.text_input("اسم المستخدم")
    password_input = st.text_input("كلمة المرور", type="password")
    
    if st.button("تسجيل الدخول", type="primary"):
        user_data = verify_user(username_input, password_input)
        if user_data:
            st.session_state.logged_in = True
            st.session_state.user = username_input
            st.session_state.allowed = user_data["allowed_folders"]
            st.session_state.role = user_data["role"]
            log_activity(username_input, "LOGIN", "", "System", "Logged into system")
            st.rerun()
        else:
            st.error("خطأ في بيانات الدخول / Invalid Credentials")

else:
    t = TRANSLATIONS[st.session_state.lang]

    is_guest = (st.session_state.role == "guest")
    is_admin = (st.session_state.role == "Admin" or st.session_state.user == "admin")
    is_manager = (st.session_state.role == "Manager")

    if is_guest:
        main_title = "📄 " + t['nav_files_guest']
        files_screen_title = "📂 " + t['nav_files']
    else:
        main_title = "📂 " + t['nav_main_user']
        files_screen_title = "📁 " + t['nav_files']
    
    # ✅ ترتيب الشاشات: (الملفات -> الملفات -> التقارير -> المستخدمين -> التحكم)
    nav_options = [main_title, files_screen_title]
    nav_options.append(t['nav_reports'])
    if is_admin or is_manager:
        nav_options.append("👤 " + t['nav_users'])
    if is_admin:
        nav_options.append("⚙️ " + t['nav_master'])

    # ✅ الرأس والتنقل
    col_logo, col_controls = st.columns([3, 2])
    with col_logo:
        st.markdown(f"""
        <div style="margin-top: 5px;">
            <h2 style="font-size: 24px; color: #0f172a; margin-bottom: 0;">{t['app_title']}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_controls:
        col_lang, col_btn = st.columns([2, 1])
        with col_lang:
            lang_choice = st.selectbox("🌐 اللغة", ["العربية", "English"], index=0 if st.session_state.lang == 'ar' else 1)
            if lang_choice == "العربية" and st.session_state.lang != 'ar':
                st.session_state.lang = 'ar'
                st.rerun()
            elif lang_choice == "English" and st.session_state.lang != 'en':
                st.session_state.lang = 'en'
                st.rerun()
        with col_btn:
            if st.button(t['logout'], use_container_width=True):
                log_activity(st.session_state.user, "LOGOUT", "", "System", "Logged out")
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.allowed = []
                st.session_state.role = "User"
                st.rerun()

    selected_screen = st.radio("", nav_options, index=0, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ----------------------------------------------------
    # 1. الشاشة الرئيسية
    # ----------------------------------------------------
    if selected_screen == main_title:
        st.title(main_title)
        
        if is_guest:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT filename, file_path, timestamp 
                    FROM user_files 
                    WHERE recipient_username = ?
                    ORDER BY timestamp DESC
                """, (st.session_state.user,))
                guest_files = cursor.fetchall()
            
            if guest_files:
                for f_name, f_path, time_str in guest_files:
                    col1, col2 = st.columns([4, 1])
                    col1.markdown(f"📄 **{f_name}**")
                    col2.caption(f"{time_str}")
                    if os.path.exists(f_path):
                        with open(f_path, "rb") as f:
                            st.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_guest_{f_name}")
                    else:
                        st.caption("الملف غير موجود")
            else:
                st.info(t['no_inbox'])

        else:
            st.subheader(t['send_title'])
            with st.form("send_file_form", clear_on_submit=True):
                active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user and u[2] != "Guest"]
                
                if not active_users:
                    st.warning(t['no_active_users'])
                else:
                    recipient = st.selectbox(t['send_to'], ["--- اختر المستخدم ---"] + active_users)
                    msg = st.text_area(t['your_message'])
                    uploaded_file = st.file_uploader(t['choose_file'], type=None, help="200 MB كحد أقصى.")
                    
                    if st.form_submit_button(t['send_now']):
                        if uploaded_file and recipient and recipient != "--- اختر المستخدم ---":
                            progress_bar = st.progress(0, t['sending'])
                            user_folder = os.path.join("storage", "UserFiles", recipient)
                            os.makedirs(user_folder, exist_ok=True)
                            file_path = os.path.join(user_folder, uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO user_files (filename, sender_username, recipient_username, message, file_path, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (uploaded_file.name, st.session_state.user, recipient, msg, file_path, now_str))
                                conn.commit()
                            progress_bar.empty()
                            st.success(f"✅ {t['send_success']} {recipient}!")
                            st.rerun()
                        else:
                            st.error(t['send_error'])
            
            st.divider()
            st.subheader(t['inbox_title'])
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, sender_username, message, file_path, timestamp, deleted_by_sender, deleted_by_recipient FROM user_files WHERE recipient_username = ? AND deleted_by_recipient = 0 ORDER BY timestamp DESC", (st.session_state.user,))
                inbox = cursor.fetchall()
            if inbox:
                for row in inbox:
                    (msg_id, f_name, sender, msg, f_path, time_str, del_s, del_r) = row
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        col1.markdown(f"📄 **{f_name}**")
                        col2.caption(f"👤 {sender} | 🕒 {time_str}")
                        if msg: col2.caption(f"📝 {msg}")
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                col3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_inbox_{msg_id}")
                        else:
                            col3.caption(t['file_not_found'])
                        if st.button(t['delete_btn'], key=f"del_msg_{msg_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE user_files SET deleted_by_recipient = 1 WHERE id = ?", (msg_id,))
                                conn.commit()
                            st.success(t['delete_success'])
                            st.rerun()
            else:
                st.info(t['no_inbox'])

            st.divider()
            st.subheader(t['sent_title'])
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, recipient_username, message, file_path, timestamp, deleted_by_sender, deleted_by_recipient FROM user_files WHERE sender_username = ? AND deleted_by_sender = 0 ORDER BY timestamp DESC", (st.session_state.user,))
                sent_items = cursor.fetchall()
            if sent_items:
                for row in sent_items:
                    (msg_id, f_name, recipient, msg, f_path, time_str, del_s, del_r) = row
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        col1.markdown(f"📄 **{f_name}** ({t['to_label']} {recipient})")
                        col2.caption(f"🕒 {time_str}")
                        if msg: col2.caption(f"📝 {msg}")
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                col3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_sent_{msg_id}")
                        else:
                            col3.caption(t['file_not_found'])
                        if st.button(t['delete_btn'], key=f"del_sent_{msg_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE user_files SET deleted_by_sender = 1 WHERE id = ?", (msg_id,))
                                conn.commit()
                            st.success(t['delete_success'])
                            st.rerun()
            else:
                st.info(t['no_sent'])

    # ----------------------------------------------------
    # 2. إدارة الملفات والمجلدات
    # ----------------------------------------------------
    elif selected_screen == files_screen_title:
        st.title(files_screen_title)
        
        st.subheader(t['search_title'])
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        search_keyword = f_col1.text_input(t['search_input'], "").strip().lower()
        
        with get_connection() as conn_u:
            cur_u = conn_u.cursor()
            cur_u.execute("SELECT username FROM users WHERE status = 'active'")
            usernames_list = [r[0] for r in cur_u.fetchall()]

        selected_user_filter = f_col2.selectbox(t['filter_user'], [t['all_option']] + usernames_list, key="user_filter")
        selected_main_folder_filter = f_col3.selectbox(t['filter_main'], [t['all_option']] + get_all_folders(), key="main_folder_filter")
        file_extension_filter = f_col4.selectbox(t['filter_ext'], [t['all_option'], "pdf", "txt", "xlsx", "xls", "docx", "png", "jpg"], key="ext_filter")
        
        st.divider()

        if 'nav_path' not in st.session_state:
            st.session_state.nav_path = []
        
        def go_to_folder(folder_name, parent_name):
            if parent_name:
                if not st.session_state.nav_path or st.session_state.nav_path[-1] != parent_name:
                    st.session_state.nav_path = [parent_name]
                st.session_state.nav_path.append(folder_name)
            else:
                st.session_state.nav_path = [folder_name]

        def go_back():
            if st.session_state.nav_path:
                st.session_state.nav_path.pop()

        def go_home():
            st.session_state.nav_path = []

        current_display_folder = None
        current_display_folder_tag = None
        
        if not st.session_state.nav_path:
            current_display_folder = "ROOT"
        elif len(st.session_state.nav_path) == 1:
            current_display_folder = st.session_state.nav_path[0]
            current_display_folder_tag = current_display_folder
        else:
            parent = st.session_state.nav_path[0]
            sub = st.session_state.nav_path[1]
            current_display_folder = sub
            current_display_folder_tag = f"{parent} / {sub}"

        col_nav1, col_nav2, col_nav3 = st.columns([1, 8, 1])
        with col_nav1:
            if st.button("🏠 الرئيسية", disabled=(not st.session_state.nav_path)):
                go_home()
                st.rerun()
        with col_nav2:
            if st.session_state.nav_path:
                st.caption(f"📂 المسار الحالي: **{' > '.join(st.session_state.nav_path)}**")
        with col_nav3:
            if st.button("⬅️ رجوع", disabled=(not st.session_state.nav_path)):
                go_back()
                st.rerun()

        st.markdown("---")

        def render_explorer_files(files_list, current_folder_path):
            if not files_list:
                st.caption("📭 هذا المجلد فارغ.")
                return
            
            for row_id, f_name, uploader, time_str in files_list:
                c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
                
                ext = os.path.splitext(f_name)[1].lower()
                icon = "📄"
                if ext in ['.pdf']: icon = "📕"
                elif ext in ['.xlsx', '.xls']: icon = "📊"
                elif ext in ['.docx', '.doc']: icon = "📝"
                elif ext in ['.png', '.jpg', '.jpeg', '.gif']: icon = "🖼️"
                elif ext in ['.zip', '.rar']: icon = "📦"
                
                c1.markdown(f"{icon} **{f_name}**")
                c2.caption(f"👤 {uploader} | 📅 {time_str}")
                
                f_path = os.path.join("storage", current_folder_path, f_name)
                if os.path.exists(f_path):
                    with open(f_path, "rb") as f:
                        c3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_ex_{row_id}", use_container_width=True)
                
                can_delete_file = (not is_guest) and (st.session_state.nav_path[0] in st.session_state.allowed or is_admin)
                if can_delete_file:
                    if c4.button("🗑️", key=f"del_ex_{row_id}", use_container_width=True):
                        st.session_state[f"confirm_ex_{row_id}"] = True

                    if st.session_state.get(f"confirm_ex_{row_id}", False):
                        st.warning("هل أنت متأكد من الحذف؟")
                        cy, cn = st.columns(2)
                        if cy.button("✅ نعم", key=f"yes_ex_{row_id}"):
                            dest_path = os.path.join("storage", "Deleted", f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{f_name}")
                            if os.path.exists(f_path): shutil.move(f_path, dest_path)
                            
                            now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE id = ?",
                                               (st.session_state.user, now_t, row_id))
                                conn.commit()
                            
                            log_activity(st.session_state.user, "DELETE_FILE", f_name, current_folder_path, "Soft deleted file")
                            del st.session_state[f"confirm_ex_{row_id}"]
                            st.success("تم حذف الملف بنجاح.")
                            st.rerun()
                        if cn.button("❌ إلغاء", key=f"cancel_ex_{row_id}"):
                            del st.session_state[f"confirm_ex_{row_id}"]
                            st.rerun()

        if current_display_folder == "ROOT":
            st.subheader("📁 المجلدات الرئيسية")
            allowed_folders = get_all_folders() if is_admin else st.session_state.allowed
            
            if selected_main_folder_filter != "الكل":
                if selected_main_folder_filter in allowed_folders:
                    allowed_folders = [selected_main_folder_filter]
                else:
                    allowed_folders = []

            for folder in allowed_folders:
                if st.button(f"📂 {folder}", key=f"btn_enter_{folder}", use_container_width=True):
                    go_to_folder(folder, None)
                    st.rerun()
                    
        else:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, uploaded_by, timestamp FROM file_logs WHERE folder = ? AND status = 'active' ORDER BY timestamp DESC", (current_display_folder_tag,))
                files_in_folder = cursor.fetchall()
                
                sub_folders_in_current = []
                if len(st.session_state.nav_path) == 1:
                    sub_folders_in_current = get_subfolders(current_display_folder)

            def check_file_filter(f_name, uploader):
                if search_keyword and search_keyword not in f_name.lower(): return False
                if selected_user_filter != "الكل" and selected_user_filter != uploader: return False
                if file_extension_filter != "الكل" and not f_name.lower().endswith(f".{file_extension_filter.lower()}"): return False
                return True

            filtered_files = [f for f in files_in_folder if check_file_filter(f[1], f[2])]

            if sub_folders_in_current:
                st.markdown("##### 📂 المجلدات الفرعية:")
                col_sub1, col_sub2, col_sub3 = st.columns(3)
                for idx, sub in enumerate(sub_folders_in_current):
                    if idx % 3 == 0: 
                        with col_sub1:
                            if st.button(f"📁 {sub}", key=f"btn_sub_{sub}", use_container_width=True):
                                go_to_folder(sub, current_display_folder)
                                st.rerun()
                    elif idx % 3 == 1:
                        with col_sub2:
                            if st.button(f"📁 {sub}", key=f"btn_sub_{sub}", use_container_width=True):
                                go_to_folder(sub, current_display_folder)
                                st.rerun()
                    else:
                        with col_sub3:
                            if st.button(f"📁 {sub}", key=f"btn_sub_{sub}", use_container_width=True):
                                go_to_folder(sub, current_display_folder)
                                st.rerun()
                st.markdown("---")

            st.markdown(f"##### 📄 ملفات المجلد `{current_display_folder}`:")
            render_explorer_files(filtered_files, current_display_folder_tag)

        if not is_guest:
            st.divider()
            st.subheader(t['upload_section'])
            
            if current_display_folder != "ROOT":
                current_parent = st.session_state.nav_path[0]
                can_upload_here = (current_parent in st.session_state.allowed or is_admin)

                if can_upload_here:
                    st.caption(f"📂 سيتم رفع الملف في المسار الحالي: **{current_display_folder_tag}**")
                    uploaded_file = st.file_uploader(t['choose_file'], key="upload_main_file")
                    
                    if st.button(t['upload_file_btn']):
                        if uploaded_file is not None:
                            target_dir = os.path.join("storage", current_display_folder_tag)
                            target_file_path = os.path.join(target_dir, uploaded_file.name)
                            
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT id FROM file_logs WHERE folder = ? AND filename = ? AND status = 'active'", (current_display_folder_tag, uploaded_file.name))
                                existing_record = cursor.fetchone()

                            file_truly_exists = existing_record is not None and os.path.exists(target_file_path)

                            if file_truly_exists:
                                st.warning("⚠️ هذا الملف موجود مسبقاً. سيتم استبداله.")
                            
                            progress_bar = st.progress(0, "جارٍ تجهيز الرفع...")
                            os.makedirs(target_dir, exist_ok=True)
                            progress_bar.progress(30, "جارٍ رفع الملف...")
                            file_content = uploaded_file.getbuffer()
                            progress_bar.progress(60, "جارٍ رفع الملف...")
                            with open(target_file_path, "wb") as f:
                                f.write(file_content)
                            progress_bar.progress(85, "جارٍ تسجيل العملية...")
                            now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                if file_truly_exists:
                                    cursor.execute("UPDATE file_logs SET uploaded_by = ?, timestamp = ? WHERE id = ?", (st.session_state.user, now_time, existing_record[0]))
                                    log_activity(st.session_state.user, "REPLACE_FILE", uploaded_file.name, current_display_folder_tag, "Replaced file")
                                    msg = f"✅ تم استبدال الملف `{uploaded_file.name}` بنجاح!"
                                else:
                                    cursor.execute("INSERT INTO file_logs (filename, folder, uploaded_by, timestamp, status) VALUES (?, ?, ?, ?, 'active')", (uploaded_file.name, current_display_folder_tag, st.session_state.user, now_time))
                                    log_activity(st.session_state.user, "UPLOAD_FILE", uploaded_file.name, current_display_folder_tag, "Uploaded new file")
                                    msg = f"✅ تم رفع الملف `{uploaded_file.name}` بنجاح!"
                                conn.commit()
                            progress_bar.progress(100, "جارٍ تحديث الواجهة...")
                            progress_bar.empty()
                            st.success(msg)
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(t['upload_error'])
                else:
                    st.info(t['folder_permission'])
            else:
                st.info(t['folder_empty'])

        st.markdown("---")
        if is_admin or is_manager:
            st.subheader(t['manage_folders'])
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("📁 " + t['create_folder'])
                with st.container(border=True):
                    with st.form("create_main_folder_form", clear_on_submit=True):
                        new_m = st.text_input("اسم المجلد الرئيسي الجديد").strip()
                        if st.form_submit_button("إنشاء"):
                            if new_m:
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute("INSERT INTO custom_folders (folder_name, status) VALUES (?, 'active')", (new_m,))
                                        conn.commit()
                                        os.makedirs(os.path.join("storage", new_m), exist_ok=True)
                                        log_activity(st.session_state.user, "CREATE_FOLDER", "", new_m, "Created main folder")
                                        st.success(f"تم إنشاء المجلد: {new_m}")
                                        st.rerun()
                                    except Exception:
                                        st.error("المجلد موجود مسبقاً!")

            with col_f2:
                st.markdown("➕ " + t['create_sub'])
                with st.container(border=True):
                    with st.form("create_sub_folder_form", clear_on_submit=True):
                        allowed_p = get_all_folders() if is_admin else st.session_state.allowed
                        p_choice = st.selectbox("اختر المجلد الرئيسي", allowed_p)
                        new_sub = st.text_input("اسم المجلد الفرعي الجديد").strip()
                        if st.form_submit_button("إنشاء الفرعي"):
                            if new_sub and p_choice:
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute("INSERT INTO sub_folders (parent_folder, sub_folder_name, status) VALUES (?, ?, 'active')", (p_choice, new_sub))
                                        conn.commit()
                                        os.makedirs(os.path.join("storage", p_choice, new_sub), exist_ok=True)
                                        log_activity(st.session_state.user, "CREATE_SUBFOLDER", "", f"{p_choice}/{new_sub}", "Created subfolder")
                                        st.success(f"تم إنشاء الفرعي: {new_sub}")
                                        st.rerun()
                                    except Exception:
                                        st.error("المجلد الفرعي موجود مسبقاً!")

            st.markdown("⚙️ " + t['manage_folders'])
            with st.container(border=True):
                m_tab1, m_tab2 = st.tabs(["✏️ " + t['rename_tab'], "🗑️ " + t['delete_tab']])
                
                with m_tab1:
                    m_type = st.radio("نوع المجلد", ["رئيسي", "فرعي"], horizontal=True, key="ren_type")
                    if m_type == "رئيسي":
                        if is_admin:
                            cur_m = st.selectbox("اختر المجلد الرئيسي", get_all_folders(), key="ren_m_sel")
                            ren_m_input = st.text_input("الاسم الجديد").strip()
                            if st.button("حفظ الاسم الجديد"):
                                if ren_m_input and cur_m:
                                    with get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE custom_folders SET folder_name = ? WHERE folder_name = ?", (ren_m_input, cur_m))
                                        cursor.execute("UPDATE sub_folders SET parent_folder = ? WHERE parent_folder = ?", (ren_m_input, cur_m))
                                        cursor.execute("UPDATE file_logs SET folder = REPLACE(folder, ?, ?) WHERE folder LIKE ?", (cur_m, ren_m_input, f"{cur_m}%"))
                                        conn.commit()
                                    old_path = os.path.join("storage", cur_m)
                                    new_path = os.path.join("storage", ren_m_input)
                                    if os.path.exists(old_path):
                                        os.rename(old_path, new_path)
                                    st.success("✅ تم تحديث اسم المجلد.")
                                    st.rerun()
                        else:
                            st.info("فقط الأدمن يمكنه تعديل المجلد الرئيسي.")
                    else:
                        cur_parent = st.selectbox("المجلد الرئيسي", get_all_folders(), key="ren_sub_p_sel")
                        sub_list = get_subfolders(cur_parent)
                        if sub_list:
                            cur_s = st.selectbox("المجلد الفرعي", sub_list, key="ren_sub_sel")
                            ren_s_input = st.text_input("الاسم الجديد").strip()
                            if st.button("حفظ الاسم الجديد"):
                                if ren_s_input and cur_s:
                                    with get_connection() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE sub_folders SET sub_folder_name = ? WHERE parent_folder = ? AND sub_folder_name = ?", (ren_s_input, cur_parent, cur_s))
                                        old_tag = f"{cur_parent} / {cur_s}"
                                        new_tag = f"{cur_parent} / {ren_s_input}"
                                        cursor.execute("UPDATE file_logs SET folder = ? WHERE folder = ?", (new_tag, old_tag))
                                        conn.commit()
                                    old_path = os.path.join("storage", cur_parent, cur_s)
                                    new_path = os.path.join("storage", cur_parent, ren_s_input)
                                    if os.path.exists(old_path):
                                        os.rename(old_path, new_path)
                                    st.success("✅ تم تحديث المجلد الفرعي.")
                                    st.rerun()
                        else:
                            st.caption("لا يوجد مجلدات فرعية.")

                with m_tab2:
                    del_m_type = st.radio("نوع المجلد", ["رئيسي (بكل محتوياته)", "فرعي فقط"], horizontal=True, key="del_m_type")
                    now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if del_m_type == "رئيسي (بكل محتوياته)":
                        if is_admin:
                            target_del_m = st.selectbox("المجلد الرئيسي للحذف", get_all_folders(), key="target_del_m")
                            if st.button("⚠️ نقل للمحذوفات", type="primary"):
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE custom_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder_name = ?", (st.session_state.user, now_t, target_del_m))
                                    cursor.execute("UPDATE sub_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE parent_folder = ?", (st.session_state.user, now_t, target_del_m))
                                    cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder LIKE ?", (st.session_state.user, now_t, f"{target_del_m}%"))
                                    conn.commit()
                                st.success(f"✅ تم نقل المجلد {target_del_m} إلى المحذوفات.")
                                st.rerun()
                        else:
                            st.info("فقط الأدمن يمكنه الحذف.")
                    else:
                        p_for_sub_del = st.selectbox("المجلد الرئيسي", get_all_folders(), key="p_for_sub_del")
                        subs_to_del = get_subfolders(p_for_sub_del)
                        if subs_to_del:
                            target_del_sub = st.selectbox("المجلد الفرعي", subs_to_del, key="target_del_sub")
                            if st.button("⚠️ نقل للمحذوفات", type="primary"):
                                tag_sub = f"{p_for_sub_del} / {target_del_sub}"
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE sub_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE parent_folder = ? AND sub_folder_name = ?", (st.session_state.user, now_t, p_for_sub_del, target_del_sub))
                                    cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder = ?", (st.session_state.user, now_t, tag_sub))
                                    conn.commit()
                                st.success(f"✅ تم نقل الفرعي {target_del_sub} إلى المحذوفات.")
                                st.rerun()
                        else:
                            st.caption("لا يوجد مجلدات فرعية.")

    # ----------------------------------------------------
    # 3. التقارير والرقابة (الآن في المركز الثالث)
    # ----------------------------------------------------
    elif selected_screen == t['nav_reports']:
        st.title("📊 " + t['nav_reports'])
        
        # ✅ الحل النهائي: العنوان فوق، والـ expander فارغ
        if is_admin:
            st.markdown(f"**{t['restore_msg']}**")
            with st.expander(""):
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, title, created_by, created_at FROM reports WHERE status = 'archived' ORDER BY created_at DESC")
                    archived_reports = cursor.fetchall()
                if archived_reports:
                    for r_id, r_title, r_creator, r_date in archived_reports:
                        col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
                        col_a1.markdown(f"📄 **{r_title}**")
                        if col_a2.button("♻️ استرجاع", key=f"restore_{r_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE reports SET status = 'active' WHERE id = ?", (r_id,))
                                conn.commit()
                            st.success("تم استرجاع التقرير.")
                            st.rerun()
                        if col_a3.button("🗑️ حذف نهائي", key=f"hard_del_{r_id}", type="primary"):
                            with get_connection() as conn:
                                conn.cursor().execute("DELETE FROM reports WHERE id = ?", (r_id,))
                                conn.cursor().execute("DELETE FROM report_items WHERE report_id = ?", (r_id,))
                                conn.cursor().execute("DELETE FROM report_viewers WHERE report_id = ?", (r_id,))
                                conn.commit()
                            st.error("تم الحذف النهائي.")
                            st.rerun()
                else:
                    st.caption("لا توجد تقارير مؤرشفة.")

        if is_admin or is_manager:
            st.markdown(f"**{t['create_report']}**")
            with st.expander(""):
                with st.form("create_report_form", clear_on_submit=True):
                    r_title = st.text_input("عنوان التقرير")
                    r_desc = st.text_area("وصف التقرير")
                    all_active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user]
                    selected_viewers = st.multiselect("المستخدمين المسموح لهم بالمشاهدة:", all_active_users)
                    if st.form_submit_button("إنشاء"):
                        if r_title.strip():
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO reports (title, description, created_by, created_at, is_public) VALUES (?, ?, ?, ?, ?)", (r_title.strip(), r_desc.strip(), st.session_state.user, now_str, 0))
                                report_id = cursor.lastrowid
                                for viewer in selected_viewers:
                                    cursor.execute("INSERT INTO report_viewers (report_id, viewer_username) VALUES (?, ?)", (report_id, viewer))
                                conn.commit()
                            st.success(f"تم إنشاء التقرير: {r_title}")
                            st.rerun()
                        else:
                            st.error("يرجى كتابة عنوان.")

        with get_connection() as conn:
            cursor = conn.cursor()
            if is_admin:
                cursor.execute("SELECT id, title, description, created_by, created_at FROM reports WHERE status = 'active' ORDER BY created_at DESC")
            else:
                cursor.execute("""
                    SELECT DISTINCT r.id, r.title, r.description, r.created_by, r.created_at 
                    FROM reports r 
                    LEFT JOIN report_items i ON r.id = i.report_id
                    LEFT JOIN report_viewers v ON r.id = v.report_id
                    WHERE r.status = 'active' 
                    AND (r.created_by = ? OR i.assigned_to_username = ? OR v.viewer_username = ?)
                """, (st.session_state.user, st.session_state.user, st.session_state.user))
            reports_list = cursor.fetchall()

        if not reports_list:
            st.info("لا توجد تقارير نشطة.")
        
        for r_id, r_title, r_desc, r_creator, r_date in reports_list:
            st.markdown(f"**{r_title}**")
            with st.expander(""):
                st.caption(r_desc if r_desc else "لا يوجد وصف.")
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT id, title, assigned_to_username, status, file_name, uploaded_by, uploaded_at, created_at, approved_by, approved_at FROM report_items WHERE report_id = ? ORDER BY id ASC", (r_id,))
                    all_items = cur.fetchall()
                
                if all_items:
                    for item in all_items:
                        (i_id, i_title, i_user, i_stat, i_file, i_up_by, i_up_at, i_created, i_app_by, i_app_at) = item
                        
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            col1.markdown(f"**{i_title}**")
                            if i_stat == "pending":
                                col2.warning("⏳ في انتظار الرفع")
                            elif i_stat == "uploaded":
                                col2.info("📤 تم الرفع")
                            else:
                                col2.success("✅ مقبول")

                            if i_file and os.path.exists(os.path.join("storage", "Reports", str(i_id), i_file)):
                                with open(os.path.join("storage", "Reports", str(i_id), i_file), "rb") as f:
                                    st.download_button("📥 تحميل", f, file_name=i_file, key=f"dl_item_{i_id}")
                            
                            can_approve = is_admin or r_creator == st.session_state.user
                            if i_stat == "uploaded" and can_approve:
                                if st.button(f"✅ قبول", key=f"app_{i_id}"):
                                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                    with get_connection() as conn:
                                        conn.cursor().execute("UPDATE report_items SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?", (st.session_state.user, now_str, i_id))
                                        conn.commit()
                                    st.success("تم قبول البند.")
                                    st.rerun()
                            
                            if i_stat != "approved" and i_user == st.session_state.user:
                                uploaded_file = st.file_uploader(f"رفع ملف", key=f"upl_{i_id}")
                                if st.button(f"رفع وتحديث", key=f"btn_up_{i_id}"):
                                    if uploaded_file:
                                        folder = os.path.join("storage", "Reports", str(i_id))
                                        os.makedirs(folder, exist_ok=True)
                                        path = os.path.join(folder, uploaded_file.name)
                                        with open(path, "wb") as f:
                                            f.write(uploaded_file.getbuffer())
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                        with get_connection() as conn:
                                            conn.cursor().execute("UPDATE report_items SET status = 'uploaded', file_name = ?, file_path = ?, uploaded_by = ?, uploaded_at = ? WHERE id = ?", (uploaded_file.name, path, st.session_state.user, now_str, i_id))
                                            conn.commit()
                                        st.success("تم رفع الملف.")
                                        st.rerun()
                                    else:
                                        st.error("اختر ملف أولاً.")
                
                can_add_item = is_admin or r_creator == st.session_state.user
                if can_add_item:
                    st.divider()
                    with st.form(key=f"add_item_{r_id}"):
                        item_title = st.text_input("عنوان البند")
                        assign_user = st.selectbox("الموظف المكلف", [u[0] for u in get_all_users() if u[7] == 'active'])
                        if st.form_submit_button("إضافة"):
                            if item_title.strip():
                                with get_connection() as conn:
                                    conn.cursor().execute("INSERT INTO report_items (report_id, title, assigned_to_username, status, created_at) VALUES (?, ?, ?, 'pending', ?)", (r_id, item_title.strip(), assign_user, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                st.success("تم إضافة البند.")
                                st.rerun()
                            else:
                                st.error("اكتب عنواناً للبند.")

                if is_admin or r_creator == st.session_state.user:
                    st.markdown("---")
                    if st.button(f"🏁 إنهاء وأرشفة", key=f"complete_{r_id}", type="primary"):
                        with get_connection() as conn:
                            conn.cursor().execute("UPDATE reports SET status = 'archived' WHERE id = ?", (r_id,))
                            conn.commit()
                        st.success("تم أرشفة التقرير.")
                        st.rerun()

    # ----------------------------------------------------
    # 4. إدارة المستخدمين (الآن في المركز الرابع)
    # ----------------------------------------------------
    elif selected_screen == t['nav_users'] and (is_admin or is_manager):
        st.title("👤 " + t['nav_users'])
        
        all_users_data = get_all_users()
        active_users_data = [u for u in all_users_data if u[7] == 'active']
        deleted_users_data = [u for u in all_users_data if u[7] == 'deleted']

        display_users = active_users_data if is_admin else [u for u in active_users_data if u[0] == st.session_state.user or u[3] == st.session_state.user]
        display_deleted_users = deleted_users_data if is_admin else [u for u in deleted_users_data if u[3] == st.session_state.user]

        uc1, uc2, uc3 = st.columns(3)
        u_search = uc1.text_input(t['filter_user_search'], "").strip().lower()
        u_role_f = uc2.selectbox(t['filter_role'], [t['all_option'], "Admin", "Manager", "User", "Guest"])
        u_creator_f = uc3.selectbox(t['filter_creator'], [t['all_option']] + list(set([u[3] for u in active_users_data if u[3]])))

        st.divider()

        table_rows = []
        for u_name, u_folders, u_role, u_creator, u_created_at, u_updated_at, u_changes, u_status, _, _ in display_users:
            if u_search and u_search not in u_name.lower(): continue
            if u_role_f != "الكل" and u_role != u_role_f: continue
            if u_creator_f != "الكل" and u_creator != u_creator_f: continue
            
            table_rows.append({
                "اسم المستخدم": u_name,
                "نوع المستخدم": u_role,
                "المجلدات": u_folders,
                "أنشأه": u_creator or 'System',
                "تاريخ الإنشاء": u_created_at or '-'
            })

        if table_rows:
            df_display = pd.DataFrame(table_rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            u_names_list = [r["اسم المستخدم"] for r in table_rows if (is_admin and r["اسم المستخدم"] != "admin") or (is_manager and r["أنشأه"] == st.session_state.user and r["اسم المستخدم"] != st.session_state.user)]
            if u_names_list:
                c_del1, c_del2 = st.columns([2, 1])
                target_del_u = c_del1.selectbox("اختر مستخدم للحذف:", u_names_list, key="sel_del_u_list")
                if c_del2.button("🗑️ حذف", key="btn_del_selected_u"):
                    st.session_state[f"confirm_u_{target_del_u}"] = True

                if st.session_state.get(f"confirm_u_{target_del_u}", False):
                    st.warning(f"هل أنت متأكد من حذف المستخدم `{target_del_u}`؟")
                    dy, dn = st.columns(2)
                    if dy.button("✅ نعم", key=f"y_u_{target_del_u}"):
                        now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE username = ?", (st.session_state.user, now_t, target_del_u))
                            conn.commit()
                        del st.session_state[f"confirm_u_{target_del_u}"]
                        st.success("تم حذف المستخدم.")
                        st.rerun()
                    if dn.button("❌ إلغاء", key=f"n_u_{target_del_u}"):
                        del st.session_state[f"confirm_u_{target_del_u}"]
                        st.rerun()
        else:
            st.info("لا يوجد مستخدمون يطابقون البحث.")

        st.divider()

        if is_admin:
            tab_add, tab_edit, tab_deleted_list, tab_admin_settings = st.tabs(["➕ " + t['user_add_tab'], "✏️ " + t['user_edit_tab'], "🗑️ " + t['user_deleted_list_tab'], "⚙️ " + t['admin_settings_tab']])
        else:
            tab_add, tab_edit, tab_deleted_list = st.tabs(["➕ " + t['user_add_tab'], "✏️ " + t['user_edit_tab'], "🗑️ " + t['user_deleted_list_tab']])

        with tab_add:
            with st.form("user_add_form", clear_on_submit=True):
                new_u = st.text_input(t['username'])
                new_p = st.text_input(t['password'], type="password")
                role_opts = ["Admin", "Manager", "User", "Guest"] if is_admin else ["User", "Guest"]
                selected_role = st.selectbox(t['role_label'], role_opts)
                selected_allowed = st.multiselect(t['allowed_folders_label'], get_all_folders(), default=["Main"])
                
                if st.form_submit_button(t['save_user_btn']):
                    if new_u and new_p:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO users (username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')", (new_u, hash_password(new_p), ",".join(selected_allowed), selected_role, st.session_state.user, now_str, now_str, f"Created on {now_str}"))
                                conn.commit()
                                st.success(t['user_saved_success'].format(name=new_u))
                                st.rerun()
                            except Exception:
                                st.error("اسم المستخدم موجود مسبقاً!")
                    else:
                        st.error("يرجى تعبئة الحقول.")

        with tab_edit:
            editable_users = [u[0] for u in display_users if u[0] != "admin"]
            edit_user_options = ["-- اختر مستخدم --"] + editable_users
            
            target_u = st.selectbox("اختر المستخدم للتعديل:", edit_user_options, key="edit_user_select")
            
            user_current_data = None
            if target_u and target_u != "-- اختر مستخدم --":
                user_current_data = verify_user(target_u, "")
            
            with st.form("user_edit_form"):
                st.text_input("اسم المستخدم", value=target_u if target_u != "-- اختر مستخدم --" else "", disabled=True)
                edit_p = st.text_input(t['edit_password'], type="password", help="اتركه فارغاً إذا لا تريد تغييره")
                role_list = ["Admin", "Manager", "User", "Guest"]
                idx = role_list.index(user_current_data["role"]) if user_current_data and user_current_data["role"] in role_list else 2
                selected_edit_role = st.selectbox(t['role_label'], role_list, index=idx)
                default_allowed = user_current_data["allowed_folders"] if user_current_data else ["Main"]
                selected_edit_allowed = st.multiselect(t['allowed_folders_label'], get_all_folders(), default=default_allowed)
                
                if st.form_submit_button(t['save_edit_btn']):
                    if target_u and target_u != "-- اختر مستخدم --":
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        folders_str = ",".join(selected_edit_allowed)
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            if edit_p.strip():
                                cursor.execute("UPDATE users SET password = ?, allowed_folders = ?, role = ?, updated_at = ? WHERE username = ?", (hash_password(edit_p.strip()), folders_str, selected_edit_role, now_str, target_u))
                            else:
                                cursor.execute("UPDATE users SET allowed_folders = ?, role = ?, updated_at = ? WHERE username = ?", (folders_str, selected_edit_role, now_str, target_u))
                            conn.commit()
                        st.success(t['user_saved_success'].format(name=target_u))
                        st.rerun()
                    else:
                        st.error("يرجى اختيار مستخدم.")

        with tab_deleted_list:
            if not display_deleted_users:
                st.info("لا توجد حسابات محذوفة.")
            else:
                for du in display_deleted_users:
                    with st.container(border=True):
                        st.markdown(f"🗑️ **{du[0]}** (حذف بواسطة: {du[8] or 'Unknown'} في {du[9] or '-'})")

        if is_admin:
            with tab_admin_settings:
                st.subheader("🔐 تغيير بيانات الأدمن")
                with st.form("admin_settings_form", clear_on_submit=True):
                    old_pass = st.text_input(t['admin_change_pass'], type="password")
                    new_user = st.text_input(t['admin_new_user'], help="اتركه فارغاً إذا لا تريد تغييره")
                    new_pass = st.text_input(t['admin_new_pass'], type="password")
                    confirm_pass = st.text_input(t['admin_confirm_pass'], type="password")
                    
                    if st.form_submit_button(t['admin_update_btn']):
                        if not old_pass:
                            st.error("يجب كتابة كلمة المرور الحالية.")
                        elif new_pass and new_pass != confirm_pass:
                            st.error("كلمة المرور الجديدة غير متطابقة.")
                        else:
                            user_data = verify_user("admin", old_pass)
                            if not user_data:
                                st.error("كلمة المرور الحالية غير صحيحة.")
                            else:
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    if new_user and new_user.strip() and new_user != "admin":
                                        cursor.execute("SELECT username FROM users WHERE username = ?", (new_user.strip(),))
                                        if cursor.fetchone():
                                            st.error(f"اسم المستخدم '{new_user}' موجود مسبقاً.")
                                        else:
                                            cursor.execute("UPDATE users SET username = ? WHERE username = 'admin'", (new_user.strip(),))
                                            st.session_state.user = new_user.strip()
                                    if new_pass:
                                        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(new_pass), new_user.strip() if new_user.strip() else "admin"))
                                    conn.commit()
                                st.success("تم تحديث البيانات.")
                                st.rerun()

    # ----------------------------------------------------
    # 5. لوحة التحكم الرئيسية (الآن في المركز الخامس)
    # ----------------------------------------------------
    elif selected_screen == t['nav_master'] and is_admin:
        st.title("⚙️ " + t['nav_master'])
        
        st.subheader("📊 سجل العمليات")
        with get_connection() as conn:
            df_audit = pd.read_sql_query("SELECT username, action_type, target_file, target_folder, timestamp, details FROM activity_logs ORDER BY id DESC", conn)

        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("♻️ سلة المحذوفات")
        m_del_tab, f_del_tab = st.tabs(["📁 المجلدات", "📄 الملفات"])
        
        with m_del_tab:
            deleted_mains = get_all_folders(include_deleted=True)
            if deleted_mains:
                for m_folder, del_by, del_at in deleted_mains:
                    col_dm1, col_dm2, col_dm3 = st.columns([3, 1, 1])
                    col_dm1.markdown(f"🗑️ **{m_folder}**")
                    if col_dm2.button("♻️ استرجاع", key=f"rec_m_{m_folder}"):
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE custom_folders SET status = 'active' WHERE folder_name = ?", (m_folder,))
                            cursor.execute("UPDATE sub_folders SET status = 'active' WHERE parent_folder = ?", (m_folder,))
                            cursor.execute("UPDATE file_logs SET status = 'active' WHERE folder LIKE ?", (f"{m_folder}%",))
                            conn.commit()
                        st.success("تم استرجاع المجلد.")
                        st.rerun()
                    if col_dm3.button("🗑️ حذف نهائي", key=f"hard_del_m_{m_folder}", type="primary"):
                        with get_connection() as conn:
                            conn.cursor().execute("DELETE FROM custom_folders WHERE folder_name = ?", (m_folder,))
                            conn.cursor().execute("DELETE FROM sub_folders WHERE parent_folder = ?", (m_folder,))
                            conn.cursor().execute("DELETE FROM file_logs WHERE folder LIKE ?", (f"{m_folder}%",))
                            conn.commit()
                        shutil.rmtree(os.path.join("storage", m_folder), ignore_errors=True)
                        st.error("تم الحذف النهائي.")
                        st.rerun()
            else:
                st.info("لا توجد مجلدات محذوفة.")

        with f_del_tab:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, folder, deleted_by, deleted_at FROM file_logs WHERE status = 'deleted'")
                del_files_rows = cursor.fetchall()
            if del_files_rows:
                for f_id, f_name, f_folder, d_by, d_at in del_files_rows:
                    fc1, fc2, fc3 = st.columns([3, 1, 1])
                    fc1.markdown(f"📄 **{f_name}**")
                    if fc2.button("♻️ استرجاع", key=f"rec_f_{f_id}"):
                        with get_connection() as conn:
                            conn.cursor().execute("UPDATE file_logs SET status = 'active' WHERE id = ?", (f_id,))
                            conn.commit()
                        st.success("تم استرجاع الملف.")
                        st.rerun()
                    if fc3.button("🗑️ حذف نهائي", key=f"hard_del_f_{f_id}", type="primary"):
                        with get_connection() as conn:
                            conn.cursor().execute("DELETE FROM file_logs WHERE id = ?", (f_id,))
                            conn.commit()
                        st.error("تم الحذف النهائي.")
                        st.rerun()
            else:
                st.info("لا توجد ملفات محذوفة.")

# =============================================================
# الـ Footer
# =============================================================
st.markdown("""
<div class="custom-footer">
    جميع الحقوق محفوظة &copy; <span>مجموعة أعمال الشاطئ</span> - فريق البرمجة ونظم المعلومات
</div>
""", unsafe_allow_html=True)