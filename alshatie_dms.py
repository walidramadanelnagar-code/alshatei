import os
import sys
import shutil
import io
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st

from streamlit_extras.stylable_container import stylable_container

from database import (
    init_db, log_activity, verify_user, 
    get_all_users, get_all_folders, get_subfolders, 
    get_connection, hash_password
)
from translations import TRANSLATIONS

st.set_page_config(page_title="نظام ضبط ومشاركة الوثائق - أعمال الشاطئ", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<link rel="icon" type="image/x-icon" href="static/favicon.ico">
""", unsafe_allow_html=True)

# =============================================================
# 🎨 إعدادات حجم ولون الخط
# =============================================================
if 'font_size' not in st.session_state:
    st.session_state.font_size = 'medium'
if 'font_color' not in st.session_state:
    st.session_state.font_color = '#1e293b'

# =============================================================
# 🎨 تنسيق الألوان والتصميم الاحترافي (النسخة النهائية)
# =============================================================
font_size_map = {
    "small": "14px",
    "medium": "17px",
    "large": "22px"
}
selected_font_size = font_size_map.get(st.session_state.font_size, "17px")
text_color = st.session_state.font_color

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    /* إخفاء العناصر المزعجة */
    header {{visibility: hidden !important;}}
    #MainMenu {{visibility: hidden !important;}}
    footer {{visibility: hidden !important;}}
    .stDeployButton {{display: none !important;}}
    [data-testid="stStatusWidget"] {{visibility: hidden !important;}}
    
    /* تعيين خط Cairo */
    html, body, .stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, div, span, p {{
        font-family: 'Cairo', sans-serif !important;
    }}
    
    /* الخلفية العامة */
    .stApp {{
        background-color: #f1f5f9 !important; 
    }}
    
    /* الشريط الجانبي */
    section[data-testid="stSidebar"] {{
        background-color: #ffffff !important;
        border-left: 1px solid #e2e8f0 !important;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02) !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: #0f172a !important;
    }}
    
    /* بطاقات الكروت (الخلفية البيضاء لكل جزء) */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextInput),
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea),
    div[data-testid="stVerticalBlock"] > div:has(div.stSelectbox),
    div[data-testid="stVerticalBlock"] > div:has(div.stFileUploader),
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {{
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
        margin-bottom: 15px !important;
        color: {text_color} !important;
    }}

    /* العناوين */
    h1, h2, h3, h4, h5, h6 {{
        color: #2563eb !important;
        font-weight: 700 !important;
    }}
    
    /* ✅ تطبيق حجم ولون النص على كل العناصر (حتى داخل الـ Uploader) */
    .stApp, .stMarkdown, .stCaption, .stDataFrame,
    .stMetric, .stColumns, .stContainer, .stEmpty,
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stFileUploader label, .stRadio label, .stCheckbox label,
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"],
    .stMultiSelect div[data-baseweb="select"], .stNumberInput input, .stDateInput input,
    .stTimeInput input, .stFileUploader div, .stFileUploader button {{
        color: {text_color} !important;
        font-size: {selected_font_size} !important;
        font-weight: 500 !important;
    }}
    
    /* ✅ إصلاح تداخل زر الرفع (Upload) */
    .stFileUploader div[data-testid="stFileUploadDropzone"] {{
        border: 1px dashed #94a3b8 !important;
        background-color: #f8fafc !important;
    }}
    .stFileUploader div[data-testid="stFileUploadDropzone"] small {{
        color: #64748b !important;
    }}
    .stFileUploader div[data-testid="stFileUploadDropzone"] button {{
        color: #2563eb !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        font-weight: 600 !important;
    }}

    /* الأزرار */
    .stButton button {{
        color: #ffffff !important;
        background-color: #2563eb !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2) !important;
    }}
    .stButton button:hover {{
        background-color: #1d4ed8 !important;
        transform: translateY(-2px) !important;
    }}
    
    .stButton button[kind="secondary"],
    .stButton button:not([kind]) {{
        background-color: #1e293b !important;
    }}
    .stButton button[kind="secondary"]:hover,
    .stButton button:not([kind]):hover {{
        background-color: #334155 !important;
    }}

    /* الفوتر */
    .custom-footer {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: rgba(255, 255, 255, 0.9);
        color: {text_color} !important;
        text-align: center;
        padding: 12px 0;
        font-size: 14px;
        border-top: 1px solid #e2e8f0;
        z-index: 999;
        backdrop-filter: blur(5px);
    }}
    .custom-footer span {{ color: #2563eb; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
""", unsafe_allow_html=True)

# =============================================================
# تحديث قاعدة البيانات
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

if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

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

t = TRANSLATIONS[st.session_state.lang]

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
    
    username_input = st.text_input(t["username"])
    password_input = st.text_input(t["password"], type="password")
    
    if st.button(t["login_btn"], type="primary"):
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
    # ✅ إعدادات الشريط الجانبي (أزرار التنقل)
    st.sidebar.markdown("## 🏢 لوحة التحكم")
    st.sidebar.markdown("---")
    
    nav_options = ["الرئيسية", "إدارة الملفات", "المستخدمين", "لوحة التحكم", "التقارير"]
    
    # استخدام st.button بدل الراديو
    for page in nav_options:
        if st.sidebar.button(page, use_container_width=True):
            st.session_state['current_page'] = page

    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = nav_options[0]

    selected_screen = st.session_state['current_page']
    
    # ✅ تخطيط الـ Header: اللوجو على الشمال، والإعدادات على اليمين
    col_logo, col_settings = st.columns([2.5, 1.5])
    
    with col_logo:
        st.markdown("""
        <div style="margin-top: 10px; margin-bottom: 10px;">
            <h1 style="font-size: 32px; color: #0f172a; margin-bottom: 0;">نظام <span style="color: #2563eb;">ضبط ومشاركة الوثائق</span></h1>
            <p style="color: #64748b; margin-top: 0; font-size: 14px;">المنصة المتكاملة لإدارة الملفات</p>
        </div>
        """, unsafe_allow_html=True)

    with col_settings:
        with st.container(border=True):
            c_s1, c_s2, c_s3 = st.columns([2, 2, 1])
            with c_s1:
                font_size_choice = st.selectbox("📏 الحجم", ["صغير", "متوسط", "كبير"], index=1, key="font_sel")
                st.session_state.font_size = {"صغير": "small", "متوسط": "medium", "كبير": "large"}[font_size_choice]
            with c_s2:
                font_color_choice = st.color_picker("🎨 اللون", st.session_state.font_color, key="color_pick")
                st.session_state.font_color = font_color_choice
            with c_s3:
                if st.button("تطبيق", type="primary", use_container_width=True):
                    st.success("تم التطبيق!")
                    st.rerun()

    # عرض اسم المستخدم وزر الخروج
    st.markdown(f"👨‍💼 **{t['welcome']}, {st.session_state.user}**", unsafe_allow_html=True)
    col_user, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button(t["logout"], use_container_width=True):
            log_activity(st.session_state.user, "LOGOUT", "", "System", "Logged out")
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.allowed = []
            st.session_state.role = "User"
            st.rerun()

    is_guest = (st.session_state.role == "guest")
    is_admin = (st.session_state.role == "Admin" or st.session_state.user == "admin")
    is_manager = (st.session_state.role == "Manager")

    # ----------------------------------------------------
    # 1. الشاشة الرئيسية
    # ----------------------------------------------------
    if selected_screen == "الرئيسية":
        st.title("📂 الملفات والمراسلات")
        
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
                st.info(t["no_inbox"])

        else:
            st.subheader("📤 إرسال ملف لزميل")
            with st.form("send_file_form", clear_on_submit=True):
                active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user and u[2] != "Guest"]
                if not active_users:
                    st.warning("لا يوجد مستخدمين نشطين.")
                else:
                    recipient = st.selectbox(t["send_to"], ["--- اختر المستخدم ---"] + active_users)
                    msg = st.text_area(t["your_message"])
                    uploaded_file = st.file_uploader("📎 **رفع ملف**", type=None, help="200 MB كحد أقصى.")
                    
                    if st.form_submit_button(t["send_now"]):
                        if uploaded_file and recipient and recipient != "--- اختر المستخدم ---":
                            progress_bar = st.progress(0, "جاري الإرسال...")
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
                            st.success(f"✅ تم إرسال الملف إلى {recipient}!")
                            st.rerun()
                        else:
                            st.error("يرجى اختيار مستلم ورفع ملف.")
            
            st.divider()
            st.subheader("📥 الوارد إلي")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, sender_username, message, file_path, timestamp FROM user_files WHERE recipient_username = ? AND deleted_by_recipient = 0 ORDER BY timestamp DESC", (st.session_state.user,))
                inbox = cursor.fetchall()
            if inbox:
                for msg_id, f_name, sender, msg, f_path, time_str in inbox:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        col1.markdown(f"📄 **{f_name}**")
                        col2.caption(f"👤 {sender} | 🕒 {time_str}")
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                col3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_in_{msg_id}")
                        if st.button(f"🗑️ حذف", key=f"del_{msg_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE user_files SET deleted_by_recipient = 1 WHERE id = ?", (msg_id,))
                                conn.commit()
                            st.rerun()
            else:
                st.info("لا توجد مراسلات واردة.")
            
            st.divider()
            st.subheader("📤 الصادر")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, recipient_username, message, file_path, timestamp FROM user_files WHERE sender_username = ? AND deleted_by_sender = 0 ORDER BY timestamp DESC", (st.session_state.user,))
                sent_items = cursor.fetchall()
            if sent_items:
                for msg_id, f_name, recipient, msg, f_path, time_str in sent_items:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        col1.markdown(f"📄 **{f_name}** (إلى: {recipient})")
                        col2.caption(f"🕒 {time_str}")
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                col3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_out_{msg_id}")
                        if st.button(f"🗑️ حذف", key=f"del_out_{msg_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE user_files SET deleted_by_sender = 1 WHERE id = ?", (msg_id,))
                                conn.commit()
                            st.rerun()
            else:
                st.info("لا توجد مراسلات صادرة.")

        if is_admin:
            st.divider()
            if st.button("🧹 تنظيف الملفات المفقودة"):
                try:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, file_path FROM user_files")
                        rows = cursor.fetchall()
                        deleted_count = 0
                        for row_id, f_path in rows:
                            if not os.path.exists(f_path):
                                cursor.execute("DELETE FROM user_files WHERE id = ?", (row_id,))
                                deleted_count += 1
                        conn.commit()
                    if deleted_count > 0:
                        st.success(f"✅ تم حذف {deleted_count} سجل غير صحيح.")
                        st.rerun()
                    else: st.info("لا توجد ملفات مفقودة.")
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")

    # ----------------------------------------------------
    # 2. إدارة الملفات والمجلدات
    # ----------------------------------------------------
    elif selected_screen == "إدارة الملفات":
        st.title("📂 إدارة ورفع الملفات")
        st.info("سيتم عرض مستكشف الملفات هنا قريباً.")
        
    # ----------------------------------------------------
    # 3. إدارة المستخدمين
    # ----------------------------------------------------
    elif selected_screen == "المستخدمين" and (is_admin or is_manager):
        st.title("👤 لوحة تحكم المستخدمين")
        st.info("سيتم عرض لوحة المستخدمين هنا قريباً.")
        
    # ----------------------------------------------------
    # 4. لوحة التحكم الرئيسية
    # ----------------------------------------------------
    elif selected_screen == "لوحة التحكم" and is_admin:
        st.title("⚙️ لوحة التحكم الرئيسية")
        st.info("سيتم عرض سجل العمليات هنا قريباً.")
        
    # ----------------------------------------------------
    # 5. لوحة التقارير والرقابة
    # ----------------------------------------------------
    elif selected_screen == "التقارير":
        st.title("📊 لوحة التقارير والرقابة")
        st.info("سيتم عرض التقارير هنا قريباً.")

# =============================================================
# 🔥 الـ Footer
# =============================================================
st.markdown("""
<div class="custom-footer">
    جميع الحقوق محفوظة &copy; <span>مجموعة أعمال الشاطئ</span> - فريق البرمجة ونظم المعلومات
</div>
""", unsafe_allow_html=True)