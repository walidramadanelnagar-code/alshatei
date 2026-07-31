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
# 🎨 التصميم النهائي (إخفاء الـ uploader + زر مخصص)
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
    
    /* تنسيق أزرار التنقل */
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

    /* تنسيق الكروت */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextInput),
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea),
    div[data-testid="stVerticalBlock"] > div:has(div.stSelectbox),
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {{
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
    .stRadio label, .stCheckbox label {{
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"] {{
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
    }}

    /* ✅ إخفاء زر الرفع الأصلي (حتى لا يترك فراغ) */
    div[data-testid="stFileUploadDropzone"] {{
        display: none !important !important;
        height: 0px !important !important;
        width: 0px !important !important;
        padding: 0px !important !important;
        margin: 0px !important !important;
        border: none !important !important;
        overflow: hidden !important !important;
    }}

    /* ✅ الأزرار العادية */
    .stButton button {{
        color: #ffffff !important;
        background-color: #2563eb !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }}
    .stButton button:hover {{ background-color: #1d4ed8 !important; }}
    
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
        main_title = t['nav_files_guest']
        files_screen_title = t['nav_files']
    else:
        main_title = t['nav_main_user']
        files_screen_title = t['nav_files']
    
    nav_options = [main_title, files_screen_title] 
    nav_options.append(t['nav_reports'])
    if is_admin or is_manager:
        nav_options.append(t['nav_users'])
    if is_admin:
        nav_options.append(t['nav_master'])

    # ✅ رأس الصفحة
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

    # ✅ شريط التنقل
    selected_screen = st.radio("", nav_options, index=0, horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # =============================================================
    # 1. الشاشة الرئيسية
    # =============================================================
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
            # أولاً: الوارد
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
            # ثانياً: الصادر
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

            st.divider()
            # ثالثاً: إرسال ملف (حيلة الإخفاء الكامل + زر مخصص)
            st.subheader(t['send_title'])
            
            if 'selected_file' not in st.session_state:
                st.session_state.selected_file = None

            # تخطيط الـ Label والزر (جمب بعضهم)
            col_label, col_btn = st.columns([3, 1])
            with col_label:
                st.write(f"📎 **{t['choose_file']}**")
            with col_btn:
                if st.button("📤", use_container_width=True):
                    pass # سيتم تفعيله عند رفع الملف

            # الجزء المخفي (مش هيظهر أبداً)
            uploaded_file = st.file_uploader("", type=None, label_visibility="collapsed", key="hidden_uploader")
            if uploaded_file is not None:
                st.session_state.selected_file = uploaded_file
                st.success(f"✅ تم اختيار الملف: {uploaded_file.name}")

            # حقول الإدخال العادية
            with st.form("send_file_form", clear_on_submit=True):
                active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user and u[2] != "Guest"]
                if not active_users:
                    st.warning(t['no_active_users'])
                else:
                    recipient = st.selectbox(t['send_to'], [t['choose_user_placeholder']] + active_users)
                    msg = st.text_area(t['your_message'])
                    
                    if st.form_submit_button(t['send_now']):
                        if st.session_state.selected_file and recipient and recipient != t['choose_user_placeholder']:
                            progress_bar = st.progress(0, t['sending'])
                            user_folder = os.path.join("storage", "UserFiles", recipient)
                            os.makedirs(user_folder, exist_ok=True)
                            file_path = os.path.join(user_folder, st.session_state.selected_file.name)
                            with open(file_path, "wb") as f:
                                f.write(st.session_state.selected_file.getbuffer())
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO user_files (filename, sender_username, recipient_username, message, file_path, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state.selected_file.name, st.session_state.user, recipient, msg, file_path, now_str))
                                conn.commit()
                            progress_bar.empty()
                            st.success(f"✅ {t['send_success']} {recipient}!")
                            st.session_state.selected_file = None
                            st.rerun()
                        else:
                            st.error(t['send_error'])

    # =============================================================
    # 2. قاعدة الملفات
    # =============================================================
    elif selected_screen == files_screen_title:
        st.title(files_screen_title)
        st.info(t['restore_msg'])
        
    # =============================================================
    # 3. التقارير والرقابة
    # =============================================================
    elif selected_screen == t['nav_reports']:
        st.title(t['nav_reports'])
        st.info(t['restore_msg'])
        
    # =============================================================
    # 4. إدارة المستخدمين
    # =============================================================
    elif selected_screen == t['nav_users'] and (is_admin or is_manager):
        st.title(t['nav_users'])
        st.info(t['restore_msg'])
        
    # =============================================================
    # 5. لوحة التحكم الرئيسية
    # =============================================================
    elif selected_screen == t['nav_master'] and is_admin:
        st.title(t['nav_master'])
        st.info(t['restore_msg'])

# =============================================================
# الـ Footer
# =============================================================
st.markdown("""
<div class="custom-footer">
    جميع الحقوق محفوظة &copy; <span>مجموعة أعمال الشاطئ</span> - فريق البرمجة ونظم المعلومات
</div>
""", unsafe_allow_html=True)