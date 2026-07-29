import os
import sys
import shutil
import io
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st

# 🔥 إضافة مكتبة التجميل
from streamlit_extras.app_logo import add_logo
from streamlit_extras.colored_header import colored_header
from streamlit_extras.stylable_container import stylable_container

from database import (
    init_db, log_activity, verify_user, 
    get_all_users, get_all_folders, get_subfolders, 
    get_connection, hash_password
)
from translations import TRANSLATIONS

st.set_page_config(page_title="نظام ضبط ومشاركة الوثائق - أعمال الشاطئ", layout="wide", initial_sidebar_state="expanded")

# =============================================================
# 🔥 إعدادات الشعار (نص) والأيقونة والـ Footer
# =============================================================

# 1. إعداد أيقونة المتصفح (تاج التبويبة) - لو مش موجودة مش هتظهر
st.markdown("""
<link rel="icon" type="image/x-icon" href="static/favicon.ico">
""", unsafe_allow_html=True)

# 2. إعدادات تنسيق النص والـ Footer
st.markdown("""
    <style>
    /* إخفاء عناصر Streamlit الافتراضية */
    header {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
    
    /* ✅ تنسيق نص مجموعة أعمال الشاطئ (بدلاً من الشعار) */
    .brand-text-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 40px;
        margin-bottom: 5px;
    }
    .brand-text {
        font-size: 38px;
        font-weight: 700;
        letter-spacing: 2px;
        background: linear-gradient(135deg, #f5af19 0%, #f12711 100%); /* تدرج ذهبي/نحاسي */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    
    /* ✅ تنسيق الـ Footer (تحت الصفحة) */
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background: rgba(17, 24, 39, 0.95); /* خلفية داكنة شفافة */
        color: #a0a0a0;
        text-align: center;
        padding: 12px 0;
        font-size: 14px;
        font-weight: 400;
        border-top: 1px solid #2d3748;
        z-index: 999;
        backdrop-filter: blur(5px);
    }
    .custom-footer span {
        color: #d4af37; /* لون ذهبي للنص المهم */
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================

init_db()

if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.allowed = []
    st.session_state.role = "User"

# =============================================================
# 🔥 ميزة جديدة: تسجيل الدخول التلقائي عن طريق الرابط (?guest=username)
# =============================================================
query_params = st.query_params
guest_login = query_params.get("guest", None)

if guest_login:
    # لو الرابط فيه ?guest=اسم_مستخدم، حاول نسجل دخوله فوراً
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status FROM users WHERE username = ? AND role = 'Guest'", (guest_login,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[7] == 'active':  # لو المستخدم موجود ونشط
        st.session_state.logged_in = True
        st.session_state.user = row[0]
        st.session_state.allowed = row[1].split(",") if row[1] else []
        st.session_state.role = row[2] if row[2] else "Guest"
        log_activity(guest_login, "LOGIN_AUTO", "", "System", "Auto-logged in via link")
# =============================================================

top_col1, top_col2, top_col3 = st.columns([6, 2, 2])
with top_col3:
    lang_choice = st.selectbox("🌐 Language / اللغة", ["العربية", "English"], key="top_lang_select")
    st.session_state.lang = 'en' if lang_choice == "English" else 'ar'

t = TRANSLATIONS[st.session_state.lang]

# ----------------------------------------------------
# تسجيل الدخول (مع النص المزين)
# ----------------------------------------------------
if not st.session_state.logged_in:
    
    # عرض نص "مجموعة أعمال الشاطئ" بشكل مزين
    st.markdown("""
    <div class="brand-text-container">
        <div class="brand-text">مجموعة أعمال الشاطئ</div>
    </div>
    """, unsafe_allow_html=True)
    
    colored_header(
        label=t["login_title"],
        description="",
        color_name="blue-70"
    )
    username_input = st.text_input(t["username"])
    password_input = st.text_input(t["password"], type="password")
    
    if st.button(t["login_btn"]):
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

# ----------------------------------------------------
# الواجهة الرئيسية
# ----------------------------------------------------
else:
    with top_col2:
        st.write(f"👨‍💼 **{t['welcome']}, {st.session_state.user}**")
        if st.button(t["logout"]):
            log_activity(st.session_state.user, "LOGOUT", "", "System", "Logged out")
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.allowed = []
            st.session_state.role = "User"
            st.rerun()

    is_guest = (st.session_state.role == "Guest")
    is_admin = (st.session_state.role == "Admin" or st.session_state.user == "admin")
    is_manager = (st.session_state.role == "Manager")

    files_screen_title = t["nav_files_guest"] if is_guest else t["nav_files"]
    
    # تحديد اسم التبويبة الأولى والصلاحيات
    if is_guest:
        # ===================== التعديل هنا =====================
        main_title = "📄 الوثائق والملفات العامة"  # الشاشة اليمنى للضيف
        files_screen_title = "📂 قاعدة الملفات"    # الشاشة الشمال للضيف
        # =======================================================
    else:
        main_title = t["nav_main_user"]  # ملفات ومراسلات لباقي المستخدمين
    
    nav_options = [main_title, files_screen_title]
    if is_admin or is_manager:
        nav_options.append(t["nav_users"])
    if is_admin:
        nav_options.append(t["nav_master"])
    nav_options.append(t["nav_reports"])
        
    selected_screen = st.radio(t["nav_selector"], nav_options, horizontal=True)
    st.divider()

    # ----------------------------------------------------
    # 1. الشاشة الرئيسية (وثائق ومراسلات - حسب الصلاحية)
    # ----------------------------------------------------
    if selected_screen == main_title:
        st.title(main_title)
        
        # ===== حالــة الضيف (عرض ملفات فقط) =====
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

        # ===== حالــة المستخدمين العاديين (مراسلات + بيانات + إرسال) =====
        else:
            st.subheader("📤 إرسال ملف لزميل")
            with st.form("send_file_form", clear_on_submit=True):
                # قائمة المستخدمين النشطين (ما عدا نفسي والضيف)
                active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user and u[2] != "Guest"]
                
                if not active_users:
                    st.warning("لا يوجد مستخدمين نشطين لإرسال الملفات إليهم حالياً.")
                else:
                    # بدل ما يظهر افتراضي، نبدأ بـ "اختر..."
                    recipient = st.selectbox(t["send_to"], ["--- اختر المستخدم ---"] + active_users)
                    msg = st.text_area(t["your_message"])
                    uploaded_file = st.file_uploader(t["choose_file"], key="send_file_upload")
                    
                    if st.form_submit_button(t["send_now"]):
                        if uploaded_file is not None and recipient and recipient != "--- اختر المستخدم ---":
                            
                            # بداية شريط التقدم
                            progress_bar = st.progress(0, "جارٍ تجهيز الإرسال...")
                            
                            # إنشاء مجلد للمستلم إذا لم يكن موجوداً
                            user_folder = os.path.join("storage", "UserFiles", recipient)
                            os.makedirs(user_folder, exist_ok=True)
                            
                            progress_bar.progress(30, "جارٍ رفع الملف وتخزينه...")
                            
                            file_path = os.path.join(user_folder, uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            progress_bar.progress(70, "جارٍ تسجيل العملية في قاعدة البيانات...")
                            
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO user_files (filename, sender_username, recipient_username, message, file_path, timestamp)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (uploaded_file.name, st.session_state.user, recipient, msg, file_path, now_str))
                                conn.commit()
                            
                            progress_bar.progress(100, "تم الإرسال بنجاح!")
                            progress_bar.empty()
                            
                            log_activity(st.session_state.user, "SEND_FILE", uploaded_file.name, recipient, f"Sent file to {recipient}")
                            st.success(f"✅ تم إرسال الملف `{uploaded_file.name}` إلى {recipient} بنجاح!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("يرجى اختيار مستلم صحيح ورفع ملف أولاً.")
            
            st.divider()
            
            st.subheader("📥 الملفات والمراسلات الواردة إلي")
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT filename, sender_username, message, file_path, timestamp 
                    FROM user_files 
                    WHERE recipient_username = ?
                    ORDER BY timestamp DESC
                """, (st.session_state.user,))
                inbox = cursor.fetchall()
            
            if inbox:
                for f_name, sender, msg, f_path, time_str in inbox:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        col1.markdown(f"📄 **{f_name}**")
                        col2.caption(f"👤 {sender} | 🕒 {time_str}")
                        if msg:
                            col2.caption(f"📝 {msg}")
                        
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                col3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_inbox_{f_name}")
                        else:
                            col3.caption("الملف غير موجود")
            else:
                st.info(t["no_inbox"])

        # =============================================================
        # 🔥 زر التنظيف (للأدمن فقط - جديد)
        # =============================================================
        if is_admin:
            st.divider()
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("🧹 تنظيف الملفات المفقودة (حذف السجلات غير الموجودة)"):
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
                            st.success(f"✅ تم حذف {deleted_count} سجل غير صحيح من قائمة الملفات.")
                            st.rerun()
                        else:
                            st.info("ℹ️ لا توجد ملفات مفقودة حالياً.")
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء التنظيف: {e}")

    # ----------------------------------------------------
    # 2. إدارة الملفات والمجلدات (نسخة ويندوز إكسبلورر)
    # ----------------------------------------------------
    elif selected_screen == files_screen_title:
        st.title(files_screen_title)
        
        # ====== البحث والفلترة ======
        st.subheader("🔍 " + t["search_title"])
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        search_keyword = f_col1.text_input(t["search_input"], "").strip().lower()
        
        with get_connection() as conn_u:
            cur_u = conn_u.cursor()
            cur_u.execute("SELECT username FROM users WHERE status = 'active'")
            usernames_list = [r[0] for r in cur_u.fetchall()]

        selected_user_filter = f_col2.selectbox(t["filter_user"], [t["all_option"]] + usernames_list, key="user_filter")
        selected_main_folder_filter = f_col3.selectbox(t["filter_main"], [t["all_option"]] + get_all_folders(), key="main_folder_filter")
        file_extension_filter = f_col4.selectbox(t["filter_ext"], [t["all_option"], "pdf", "txt", "xlsx", "xls", "docx", "png", "jpg"], key="ext_filter")
        
        st.divider()

        # ====== متصفح الملفات (Windows Explorer Style) ======
        
        # 1. إعدادات الـ Session State للتنقل بين المجلدات
        if 'nav_path' not in st.session_state:
            st.session_state.nav_path = [] # قائمة لتخزين مسار المجلد الحالي (مثلاً ['Main', 'SubFolder'])
        
        # 2. دوال مساعدة للتنقل
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

        # 3. تحديد المجلد الحالي بناءً على المسار
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

        # 4. عرض أزرار التنقل (مثل شريط العنوان في ويندوز)
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

        # 5. دالة لعرض الملفات
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
                c2.caption(f"👨‍💼 {uploader} | 📅 {time_str}")
                
                f_path = os.path.join("storage", current_folder_path, f_name)
                if os.path.exists(f_path):
                    with open(f_path, "rb") as f:
                        c3.download_button("⬇️ تحميل", f, file_name=f_name, key=f"dl_ex_{row_id}", use_container_width=True)
                
                can_delete_file = (not is_guest) and (st.session_state.nav_path[0] in st.session_state.allowed or is_admin)
                if can_delete_file:
                    if c4.button("🗑️", key=f"del_ex_{row_id}", use_container_width=True):
                        st.session_state[f"confirm_ex_{row_id}"] = True

                    if st.session_state.get(f"confirm_ex_{row_id}", False):
                        st.warning(t["confirm_del"])
                        cy, cn = st.columns(2)
                        if cy.button("✅ نعم", key=f"yes_ex_{row_id}"):
                            dest_path = os.path.join("storage", "Deleted", f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{f_name}")
                            if os.path.exists(f_path):
                                shutil.move(f_path, dest_path)
                            
                            now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE id = ?",
                                               (st.session_state.user, now_t, row_id))
                                conn.commit()
                            
                            log_activity(st.session_state.user, "DELETE_FILE", f_name, current_folder_path, "Soft deleted file")
                            del st.session_state[f"confirm_ex_{row_id}"]
                            st.success(t["delete_success"])
                            st.rerun()
                        if cn.button("❌ إلغاء", key=f"cancel_ex_{row_id}"):
                            del st.session_state[f"confirm_ex_{row_id}"]
                            st.rerun()

        # 6. منطق العرض حسب الحالة
        if current_display_folder == "ROOT":
            st.subheader("📁 المجلدات الرئيسية")
            allowed_folders = get_all_folders() if is_admin else st.session_state.allowed
            
            if selected_main_folder_filter != t["all_option"]:
                if selected_main_folder_filter in allowed_folders:
                    allowed_folders = [selected_main_folder_filter]
                else:
                    allowed_folders = []

            for folder in allowed_folders:
                if st.button(f"📂 {folder}", key=f"btn_enter_{folder}", use_container_width=True):
                    go_to_folder(folder, None)
                    st.rerun()
                    
        else:
            # نحن داخل مجلد (رئيسي أو فرعي)
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, uploaded_by, timestamp FROM file_logs WHERE folder = ? AND status = 'active' ORDER BY timestamp DESC", (current_display_folder_tag,))
                files_in_folder = cursor.fetchall()
                
                sub_folders_in_current = []
                if len(st.session_state.nav_path) == 1:
                    sub_folders_in_current = get_subfolders(current_display_folder)

            def check_file_filter(f_name, uploader):
                if search_keyword and search_keyword not in f_name.lower(): return False
                if selected_user_filter != t["all_option"] and selected_user_filter != uploader: return False
                if file_extension_filter != t["all_option"] and not f_name.lower().endswith(f".{file_extension_filter.lower()}"): return False
                return True

            filtered_files = [f for f in files_in_folder if check_file_filter(f[1], f[2])]

            # 1. عرض المجلدات الفرعية
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

            # 2. عرض الملفات
            st.markdown(f"##### 📄 ملفات المجلد `{current_display_folder}`:")
            render_explorer_files(filtered_files, current_display_folder_tag)

        # ====== رفع الملفات (داخل المكان الحالي فقط) ======
        if not is_guest:
            st.divider()
            st.subheader("📤 " + t["upload_section"])
            
            if current_display_folder != "ROOT":
                current_parent = st.session_state.nav_path[0]
                can_upload_here = (current_parent in st.session_state.allowed or is_admin)

                if can_upload_here:
                    st.caption(f"📂 سيتم رفع الملف في المسار الحالي: **{current_display_folder_tag}**")
                    uploaded_file = st.file_uploader(t["choose_file"], key="upload_main_file")
                    
                    if st.button("📤 تنفيذ الرفع وتسجيل العملية"):
                        if uploaded_file is not None:
                            target_dir = os.path.join("storage", current_display_folder_tag)
                            target_file_path = os.path.join(target_dir, uploaded_file.name)
                            
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT id FROM file_logs WHERE folder = ? AND filename = ? AND status = 'active'", (current_display_folder_tag, uploaded_file.name))
                                existing_record = cursor.fetchone()

                            file_truly_exists = existing_record is not None and os.path.exists(target_file_path)

                            if file_truly_exists:
                                st.warning("⚠️ هذا الملف موجود مسبقاً في هذا المجلد. سيتم استبداله.")
                            
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
                            st.error("❌ يجب عليك اختيار ملف أولاً قبل الضغط على زر الرفع.")
                else:
                    st.info("❌ ليس لديك صلاحية للرفع في هذا المجلد.")
            else:
                st.info("📁 اذهب إلى أحد المجلدات أولاً لرفع ملفاتك.")

        # ====== القسم 4: إنشاء المجلدات للمدراء ======
        st.markdown("---")
        if is_admin or is_manager:
            st.subheader("📂 إدارة المجلدات")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                with st.expander("📁 إنشاء مجلد رئيسي جديد"):
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
                with st.expander("➕ إنشاء مجلد فرعي داخل مجلد رئيسي"):
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

            with st.expander("⚙️ إدارة المجلدات (تعديل الاسم / نقل للمحذوفات)"):
                m_tab1, m_tab2 = st.tabs(["✏️ إعادة تسمية مجلد", "🗑️ نقل للمحذوفات"])
                
                with m_tab1:
                    m_type = st.radio("نوع المجلد المراد تعديله", ["رئيسي", "فرعي"], horizontal=True, key="ren_type")
                    if m_type == "رئيسي":
                        # إذا كان المستخدم مدير (وليس أدمن)، لا يسمح له بتعديل الاسم الرئيسي
                        if is_admin:
                            cur_m = st.selectbox("اختر المجلد الرئيسي", get_all_folders(), key="ren_m_sel")
                            ren_m_input = st.text_input("الاسم الجديد للمجلد الرئيسي", key="ren_m_input").strip()
                            if st.button("حفظ الاسم الجديد الرئيسي"):
                                if ren_m_input and cur_m:
                                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
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
                                    log_activity(st.session_state.user, "RENAME_FOLDER", "", ren_m_input, f"Renamed main folder from {cur_m} to {ren_m_input}")
                                    st.success("✅ تم تحديث اسم المجلد وبصمته بنجاح!")
                                    st.rerun()
                        else:
                            st.info("🚫 المدير ليس لديه صلاحية لتعديل اسم المجلد الرئيسي (فقط الأدمن).")
                    else:
                        cur_parent = st.selectbox("اختر المجلد الرئيسي التابع له", get_all_folders(), key="ren_sub_p_sel")
                        sub_list = get_subfolders(cur_parent)
                        if sub_list:
                            cur_s = st.selectbox("اختر المجلد الفرعي", sub_list, key="ren_sub_sel")
                            ren_s_input = st.text_input("الاسم الجديد للفرعي", key="ren_s_input").strip()
                            if st.button("حفظ الاسم الجديد للفرعي"):
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
                                    log_activity(st.session_state.user, "RENAME_SUBFOLDER", "", new_tag, f"Renamed subfolder from {cur_s} to {ren_s_input}")
                                    st.success("✅ تم تحديث المجلد الفرعي بنجاح!")
                                    st.rerun()
                        else:
                            st.caption("هذا المجلد لا يحتوي على مجلدات فرعية لتعديلها.")

                with m_tab2:
                    del_m_type = st.radio("نوع المجلد المراد حذفه ونقله للمحذوفات", ["رئيسي (بكل محتوياته)", "فرعي فقط"], horizontal=True, key="del_m_type")
                    now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if del_m_type == "رئيسي (بكل محتوياته)":
                        # إذا كان المستخدم مدير (وليس أدمن)، لا يسمح له بحذف الرئيسي
                        if is_admin:
                            target_del_m = st.selectbox("اختر المجلد الرئيسي للحذف", get_all_folders(), key="target_del_m")
                            if st.button("⚠️ نقل المجلد الرئيسي للمحذوفات", type="primary"):
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE custom_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder_name = ?", (st.session_state.user, now_t, target_del_m))
                                    cursor.execute("UPDATE sub_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE parent_folder = ?", (st.session_state.user, now_t, target_del_m))
                                    cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder LIKE ?", (st.session_state.user, now_t, f"{target_del_m}%"))
                                    conn.commit()
                                log_activity(st.session_state.user, "DELETE_FOLDER_SOFT", "", target_del_m, "Main folder soft deleted with contents")
                                st.success(f"✅ تم نقل المجلد {target_del_m} إلى المحذوفات بنجاح.")
                                st.rerun()
                        else:
                            st.info("🚫 المدير ليس لديه صلاحية لحذف مجلد رئيسي (فقط الأدمن).")
                    else:
                        p_for_sub_del = st.selectbox("اختر المجلد الرئيسي", get_all_folders(), key="p_for_sub_del")
                        subs_to_del = get_subfolders(p_for_sub_del)
                        if subs_to_del:
                            target_del_sub = st.selectbox("اختر الفرعي للحذف", subs_to_del, key="target_del_sub")
                            if st.button("⚠️ نقل الفرعي للمحذوفات", type="primary"):
                                tag_sub = f"{p_for_sub_del} / {target_del_sub}"
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE sub_folders SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE parent_folder = ? AND sub_folder_name = ?", (st.session_state.user, now_t, p_for_sub_del, target_del_sub))
                                    cursor.execute("UPDATE file_logs SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE folder = ?", (st.session_state.user, now_t, tag_sub))
                                    conn.commit()
                                log_activity(st.session_state.user, "DELETE_SUBFOLDER_SOFT", "", tag_sub, "Subfolder soft deleted")
                                st.success(f"✅ تم نقل الفرعي {target_del_sub} إلى المحذوفات بنجاح.")
                                st.rerun()
                        else:
                            st.caption("هذا المجلد لا يحتوي على مجلدات فرعية لحذفها.")

    # ----------------------------------------------------
    # 3. إدارة المستخدمين
    # ----------------------------------------------------
    elif selected_screen == t["nav_users"] and (is_admin or is_manager):
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
            <svg width="55" height="55" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="32" cy="32" r="30" fill="url(#user_grad)"/>
                <path d="M32 16C24.82 16 19 21.82 19 29C19 36.18 24.82 42 32 42C39.18 42 45 36.18 45 29C45 21.82 39.18 16 32 16ZM32 37.5C27.31 37.5 23.5 33.69 23.5 29C23.5 24.31 27.31 20.5 32 20.5C36.69 20.5 40.5 24.31 40.5 29C40.5 33.69 36.69 37.5 32 37.5Z" fill="white"/>
                <path d="M17 50C17 42.5 23.72 36.5 32 36.5C40.28 36.5 47 42.5 47 50H42C42 45.2 37.52 41.5 32 41.5C26.48 41.5 22 45.2 22 50H17Z" fill="white"/>
                <defs>
                    <linearGradient id="user_grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#FF5E62;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#FF9966;stop-opacity:1" />
                    </linearGradient>
                </defs>
            </svg>
            <h1 style="margin: 0; padding: 0; display: inline-block;">لوحة تحكم المستخدمين</h1>
        </div>
        """, unsafe_allow_html=True)
        
        all_users_data = get_all_users()
        active_users_data = [u for u in all_users_data if u[7] == 'active']
        deleted_users_data = [u for u in all_users_data if u[7] == 'deleted']

        display_users = active_users_data if is_admin else [u for u in active_users_data if u[0] == st.session_state.user or u[3] == st.session_state.user]
        display_deleted_users = deleted_users_data if is_admin else [u for u in deleted_users_data if u[3] == st.session_state.user]

        uc1, uc2, uc3 = st.columns(3)
        u_search = uc1.text_input(t["filter_user_search"], "").strip().lower()
        u_role_f = uc2.selectbox(t["filter_role"], [t["all_option"], "Admin", "Manager", "User", "Guest"])
        u_creator_f = uc3.selectbox(t["filter_creator"], [t["all_option"]] + list(set([u[3] for u in active_users_data if u[3]])))

        st.divider()

        table_rows = []
        for u_name, u_folders, u_role, u_creator, u_created_at, u_updated_at, u_changes, u_status, _, _ in display_users:
            if u_search and u_search not in u_name.lower(): continue
            if u_role_f != t["all_option"] and u_role != u_role_f: continue
            if u_creator_f != t["all_option"] and u_creator != u_creator_f: continue
            
            table_rows.append({
                "اسم المستخدم": u_name,
                "نوع المستخدم": u_role,
                "المجلدات المسموحة": u_folders,
                "أنشأه": u_creator or 'System',
                "تاريخ الإنشاء": u_created_at or '-'
            })

        if table_rows:
            df_display = pd.DataFrame(table_rows)
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "اسم المستخدم": st.column_config.TextColumn("👨‍💼 اسم المستخدم", width="medium"),
                    "نوع المستخدم": st.column_config.TextColumn("🛡️ نوع المستخدم", width="small"),
                    "المجلدات المسموحة": st.column_config.TextColumn("📁 المجلدات المسموحة", width="large"),
                    "أنشأه": st.column_config.TextColumn("📌 أنشأه", width="small"),
                    "تاريخ الإنشاء": st.column_config.TextColumn("📅 تاريخ الإنشاء", width="medium"),
                }
            )
            
            st.markdown("##### ⚙️ إجراءات المستخدمين")
            u_names_list = [r["اسم المستخدم"] for r in table_rows if (is_admin and r["اسم المستخدم"] != "admin") or (is_manager and r["أنشأه"] == st.session_state.user and r["اسم المستخدم"] != st.session_state.user)]
            if u_names_list:
                c_del1, c_del2 = st.columns([2, 1])
                target_del_u = c_del1.selectbox("اختر مستخدم للحذف:", u_names_list, key="sel_del_u_list")
                if c_del2.button("🗑️ حذف المستخدم المحدد", key="btn_del_selected_u"):
                    st.session_state[f"confirm_u_{target_del_u}"] = True

                if st.session_state.get(f"confirm_u_{target_del_u}", False):
                    st.warning(t["confirm_del_user"].format(name=target_del_u))
                    dy, dn = st.columns(2)
                    if dy.button(t["yes_del"], key=f"y_u_{target_del_u}"):
                        now_t = datetime.now().strftime("%Y-%m-%d %H:%M")
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET status = 'deleted', deleted_by = ?, deleted_at = ? WHERE username = ?", (st.session_state.user, now_t, target_del_u))
                            conn.commit()
                        log_activity(st.session_state.user, "DELETE_USER", target_del_u, "Users", "User soft deleted")
                        del st.session_state[f"confirm_u_{target_del_u}"]
                        st.success(t["user_deleted_success"])
                        st.rerun()
                    if dn.button(t["cancel_del"], key=f"n_u_{target_del_u}"):
                        del st.session_state[f"confirm_u_{target_del_u}"]
                        st.rerun()
        else:
            st.info("لا يوجد مستخدمون يطابقون خيارات البحث.")

        st.divider()

        # ============= إنشاء التبويبات =============
        if is_admin:
            # الأدمن يشوف ٤ تبويبات (إضافة، تعديل، محذوفون، إعدادات خاصة)
            tab_add, tab_edit, tab_deleted_list, tab_admin_settings = st.tabs([
                t["user_add_tab"], t["user_edit_tab"], t["user_deleted_list_tab"], "⚙️ إعدادات الأدمن (تغيير البيانات)"
            ])
        else:
            # المدراء يشوفوا ٣ تبويبات بس
            tab_add, tab_edit, tab_deleted_list = st.tabs([t["user_add_tab"], t["user_edit_tab"], t["user_deleted_list_tab"]])

        # ============= تبويبة إضافة مستخدم =============
        with tab_add:
            with st.form("user_add_form", clear_on_submit=True):
                new_u = st.text_input(t["username"])
                new_p = st.text_input(t["password"], type="password")
                role_opts = ["Admin", "Manager", "User", "Guest"] if is_admin else ["User", "Guest"]
                selected_role = st.selectbox(t["role_label"], role_opts)
                selected_allowed = st.multiselect(t["allowed_folders_label"], get_all_folders(), default=["Main"])
                
                if st.form_submit_button(t["save_user_btn"]) and new_u and new_p:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                INSERT INTO users (username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
                            """, (new_u, hash_password(new_p), ",".join(selected_allowed), selected_role, st.session_state.user, now_str, now_str, f"Created on {now_str}"))
                            conn.commit()
                            log_activity(st.session_state.user, "CREATE_USER", new_u, "Users", "New user created")
                            st.success(t["user_saved_success"].format(name=new_u))
                        except Exception:
                            st.error("اسم المستخدم موجود مسبقاً!")

        # ============= تبويبة تعديل مستخدم (باقي المستخدمين) =============
        with tab_edit:
            editable_users = [u[0] for u in display_users if u[0] != "admin"]
            edit_user_options = ["-- اختر مستخدم --"] + editable_users
            
            if "edit_target_user" not in st.session_state:
                st.session_state.edit_target_user = "-- اختر مستخدم --"

            target_u = st.selectbox(
                "اختر اسم المستخدم للتعديل:",
                edit_user_options,
                key="edit_user_select"
            )
            
            user_current_data = None
            if target_u and target_u != "-- اختر مستخدم --":
                user_current_data = verify_user(target_u, "")
            
            with st.form("user_edit_form"):
                st.text_input("اسم المستخدم (للتعديل)", value=target_u if target_u != "-- اختر مستخدم --" else "", disabled=True)
                
                edit_p = st.text_input(t["password"], type="password", help="اتركه فارغاً إذا لا تريد تغييره")
                
                role_list = ["Admin", "Manager", "User", "Guest"]
                if user_current_data:
                    idx = role_list.index(user_current_data["role"]) if user_current_data["role"] in role_list else 2
                else:
                    idx = 2
                
                selected_edit_role = st.selectbox(t["role_label"], role_list, index=idx)
                
                default_allowed = user_current_data["allowed_folders"] if user_current_data else ["Main"]
                selected_edit_allowed = st.multiselect(
                    t["allowed_folders_label"], 
                    get_all_folders(), 
                    default=default_allowed
                )
                
                if st.form_submit_button("حفظ تعديلات المستخدم"):
                    if target_u and target_u != "-- اختر مستخدم --":
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        folders_str = ",".join(selected_edit_allowed)
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            if edit_p.strip():
                                cursor.execute("UPDATE users SET password = ?, allowed_folders = ?, role = ?, updated_at = ? WHERE username = ?",
                                               (hash_password(edit_p.strip()), folders_str, selected_edit_role, now_str, target_u))
                            else:
                                cursor.execute("UPDATE users SET allowed_folders = ?, role = ?, updated_at = ? WHERE username = ?",
                                               (folders_str, selected_edit_role, now_str, target_u))
                            conn.commit()
                        log_activity(st.session_state.user, "EDIT_USER", target_u, "Users", "User permissions updated")
                        st.success(t["user_saved_success"].format(name=target_u))
                        st.rerun()
                    else:
                        st.error("يرجى اختيار مستخدم أولاً من القائمة!")

        # ============= تبويبة المستخدمين المحذوفين =============
        with tab_deleted_list:
            if not display_deleted_users:
                st.info("لا توجد حسابات محذوفة حالياً.")
            else:
                for du in display_deleted_users:
                    with st.container(border=True):
                        st.markdown(f"🗑️ **المستخدم:** `{du[0]}` | ❌ **حذفه:** `{du[8] or 'Unknown'}` | 📅 **تاريخ الحذف:** `{du[9] or '-'}`")

        # ============= تبويبة إعدادات الأدمن (للأدمن فقط) =============
        if is_admin:
            with tab_admin_settings:
                st.subheader("🔐 تغيير بيانات الدخول للأدمن")
                
                with st.form("admin_settings_form", clear_on_submit=True):
                    old_pass = st.text_input("كلمة المرور الحالية", type="password")
                    new_user = st.text_input("اسم المستخدم الجديد (اختياري - اتركه فارغاً إذا لا تريد تغييره)")
                    new_pass = st.text_input("كلمة المرور الجديدة", type="password")
                    confirm_pass = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
                    
                    if st.form_submit_button("تحديث بيانات الأدمن"):
                        # التحقق من صحة البيانات
                        if not old_pass:
                            st.error("❌ يجب كتابة كلمة المرور الحالية أولاً.")
                        elif new_pass and new_pass != confirm_pass:
                            st.error("❌ كلمة المرور الجديدة وتأكيدها غير متطابقين.")
                        else:
                            # التحقق من الباسورد القديم
                            user_data = verify_user("admin", old_pass)
                            if not user_data:
                                st.error("❌ كلمة المرور الحالية غير صحيحة.")
                            else:
                                with get_connection() as conn:
                                    cursor = conn.cursor()
                                    
                                    # 1. تغيير اسم المستخدم (لو مش فارغ)
                                    if new_user and new_user.strip() and new_user != "admin":
                                        # التحقق إن الاسم الجديد مش مكرر
                                        cursor.execute("SELECT username FROM users WHERE username = ?", (new_user.strip(),))
                                        if cursor.fetchone():
                                            st.error(f"❌ اسم المستخدم '{new_user}' موجود مسبقاً.")
                                        else:
                                            cursor.execute("UPDATE users SET username = ? WHERE username = 'admin'", (new_user.strip(),))
                                            st.success(f"✅ تم تغيير اسم المستخدم إلى: {new_user.strip()}")
                                            st.session_state.user = new_user.strip()
                                    
                                    # 2. تغيير كلمة المرور (لو كتب باسورد جديد)
                                    if new_pass:
                                        hashed_new = hash_password(new_pass)
                                        target_user = new_user.strip() if new_user and new_user.strip() else "admin"
                                        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new, target_user))
                                        st.success("✅ تم تغيير كلمة المرور بنجاح!")
                                    
                                    conn.commit()
                                st.success("تم تحديث البيانات بنجاح!")
                                time.sleep(1)
                                st.rerun()

    # ----------------------------------------------------
    # 4. لوحة التحكم والتحكم في المحذوفات للمدير العام
    # ----------------------------------------------------
    elif selected_screen == t["nav_master"] and is_admin:
        st.title(t["nav_master"])
        st.subheader("📊 سجل العمليات والتتبع الشامل (Excel Export)")
        with get_connection() as conn:
            df_audit = pd.read_sql_query("""
                SELECT username as 'المستخدم', action_type as 'نوع العملية', 
                       target_file as 'الملف/العنصر', target_folder as 'المجلد', 
                       timestamp as 'التاريخ والوقت', details as 'التفاصيل' 
                FROM activity_logs ORDER BY id DESC
            """, conn)

        if not df_audit.empty:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_audit.to_excel(writer, index=False, sheet_name='سجل العمليات')
            excel_buffer.seek(0)

            st.download_button("📥 تحميل سجل العمليات كملف Excel منظم", data=excel_buffer, file_name=f"Operations_Log_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.dataframe(df_audit.head(15), use_container_width=True)

        st.divider()
        st.subheader("♻️ سلة المحذوفات المتقدمة (إدارة المجلدات والملفات المحذوفة)")
        m_del_tab, f_del_tab = st.tabs(["📁 المجلدات المحذوفة | Deleted Folders", "📄 الملفات المحذوفة | Deleted Files"])
        
        with m_del_tab:
            deleted_mains = get_all_folders(include_deleted=True)
            if deleted_mains:
                st.markdown("##### 📁 المجلدات الرئيسية المحذوفة:")
                for m_folder, del_by, del_at in deleted_mains:
                    col_dm1, col_dm2, col_dm3 = st.columns([3, 1, 1])
                    col_dm1.markdown(f"🗑️ **{m_folder}** (حذفه: `{del_by}` - `{del_at}`)")
                    if col_dm2.button("♻️ استرجاع المجلد", key=f"rec_m_{m_folder}"):
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE custom_folders SET status = 'active' WHERE folder_name = ?", (m_folder,))
                            cursor.execute("UPDATE sub_folders SET status = 'active' WHERE parent_folder = ?", (m_folder,))
                            cursor.execute("UPDATE file_logs SET status = 'active' WHERE folder LIKE ?", (f"{m_folder}%",))
                            conn.commit()
                        log_activity(st.session_state.user, "RESTORE_FOLDER", "", m_folder, "Main folder restored")
                        st.success(f"تم استرجاع المجلد {m_folder} بنجاح.")
                        st.rerun()
                        
                    if col_dm3.button("🗑️ حذف نهائي", key=f"hard_del_m_{m_folder}", type="primary"):
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM custom_folders WHERE folder_name = ?", (m_folder,))
                            cursor.execute("DELETE FROM sub_folders WHERE parent_folder = ?", (m_folder,))
                            cursor.execute("DELETE FROM file_logs WHERE folder LIKE ?", (f"{m_folder}%",))
                            conn.commit()
                        target_dir_path = os.path.join("storage", m_folder)
                        if os.path.exists(target_dir_path):
                            shutil.rmtree(target_dir_path)
                        log_activity(st.session_state.user, "HARD_DELETE_FOLDER", "", m_folder, "Main folder permanently deleted")
                        st.error(f"تم الحذف النهائي للمجلد {m_folder}.")
                        st.rerun()
            else:
                st.info("لا توجد مجلدات رئيسية محذوفة.")

        with f_del_tab:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, folder, deleted_by, deleted_at FROM file_logs WHERE status = 'deleted'")
                del_files_rows = cursor.fetchall()

            if del_files_rows:
                for f_id, f_name, f_folder, d_by, d_at in del_files_rows:
                    fc1, fc2, fc3 = st.columns([3, 1, 1])
                    fc1.markdown(f"📄 **{f_name}** (`{f_folder}`) - (حذفه: `{d_by}` في `{d_at}`)")
                    if fc2.button("♻️ استرجاع الملف", key=f"rec_f_{f_id}"):
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE file_logs SET status = 'active' WHERE id = ?", (f_id,))
                            conn.commit()
                        log_activity(st.session_state.user, "RESTORE_FILE", f_name, f_folder, "File restored")
                        st.success(f"تم استرجاع الملف {f_name}.")
                        st.rerun()
                    if fc3.button("🗑️ حذف نهائي", key=f"hard_del_f_{f_id}", type="primary"):
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM file_logs WHERE id = ?", (f_id,))
                            conn.commit()
                        log_activity(st.session_state.user, "HARD_DELETE_FILE", f_name, f_folder, "File permanently deleted")
                        st.error(f"تم حذف {f_name} نهائياً.")
                        st.rerun()
            else:
                st.info("لا توجد ملفات محذوفة.")

    # ----------------------------------------------------
    # 5. لوحة التقارير والرقابة
    # ----------------------------------------------------
    elif selected_screen == t["nav_reports"]:
        st.title(t["reports_title"])
        
        if is_admin:
            with st.expander("📦 أرشيف التقارير المنتهية (للأدمن فقط)", expanded=False):
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, title, description, created_by, created_at FROM reports WHERE status = 'archived' ORDER BY created_at DESC")
                    archived_reports = cursor.fetchall()
                
                if archived_reports:
                    for r_id, r_title, r_desc, r_creator, r_date in archived_reports:
                        col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
                        col_a1.markdown(f"📄 **{r_title}** (بواسطة: {r_creator} | {r_date})")
                        if col_a2.button("♻️ استرجاع التقرير", key=f"restore_{r_id}"):
                            with get_connection() as conn:
                                conn.cursor().execute("UPDATE reports SET status = 'active' WHERE id = ?", (r_id,))
                                conn.commit()
                            st.success("تم استرجاع التقرير بنجاح.")
                            st.rerun()
                        if col_a3.button("🗑️ حذف نهائي", key=f"hard_del_{r_id}", type="primary"):
                            with get_connection() as conn:
                                conn.cursor().execute("DELETE FROM reports WHERE id = ?", (r_id,))
                                conn.cursor().execute("DELETE FROM report_items WHERE report_id = ?", (r_id,))
                                conn.cursor().execute("DELETE FROM report_viewers WHERE report_id = ?", (r_id,))
                                conn.commit()
                            st.error("تم حذف التقرير وكل بياناته نهائياً.")
                            st.rerun()
                else:
                    st.caption("لا توجد تقارير مؤرشفة حالياً.")
            st.divider()

        if is_admin or is_manager:
            with st.expander("➕ إنشاء تقرير جديد", expanded=False):
                with st.form("create_report_form", clear_on_submit=True):
                    r_title = st.text_input("عنوان التقرير")
                    r_desc = st.text_area("وصف التقرير والمطلوب منه")
                    all_active_users = [u[0] for u in get_all_users() if u[7] == 'active' and u[0] != st.session_state.user]
                    selected_viewers = st.multiselect("اختر المستخدمين الذين سيُسمح لهم بمشاهدة هذا التقرير:", all_active_users)
                    if st.form_submit_button("إنشاء التقرير"):
                        if r_title.strip():
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            with get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO reports (title, description, created_by, created_at, is_public) VALUES (?, ?, ?, ?, ?)", (r_title.strip(), r_desc.strip(), st.session_state.user, now_str, 0))
                                report_id = cursor.lastrowid
                                for viewer in selected_viewers:
                                    cursor.execute("INSERT INTO report_viewers (report_id, viewer_username) VALUES (?, ?)", (report_id, viewer))
                                conn.commit()
                            log_activity(st.session_state.user, "CREATE_REPORT", r_title, "Reports", "New report created")
                            st.success(f"تم إنشاء التقرير: {r_title}")
                            st.rerun()
                        else:
                            st.error("يرجى كتابة عنوان للتقرير.")
            st.divider()

        # تحديد التقارير التي سيتم عرضها
        if is_admin:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, description, created_by, created_at FROM reports WHERE status = 'active' ORDER BY created_at DESC")
                reports_list = cursor.fetchall()
        else:
            with get_connection() as conn:
                cursor = conn.cursor()
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
            st.info(" لا توجد تقارير نشطة حالياً.")
        
        for r_id, r_title, r_desc, r_creator, r_date in reports_list:
            with st.expander(f"📄 {r_title} (بواسطة: {r_creator} | {r_date})", expanded=False):
                st.caption(r_desc if r_desc else "لا يوجد وصف.")
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT i.id, i.title, i.assigned_to_username, i.status, 
                               i.file_name, i.uploaded_by, i.uploaded_at, i.created_at,
                               i.approved_by, i.approved_at
                        FROM report_items i
                        WHERE i.report_id = ?
                        ORDER BY i.id ASC
                    """, (r_id,))
                    all_items = cur.fetchall()
                
                if all_items:
                    st.markdown("##### 📋 بنود التقرير:")
                    for item in all_items:
                        (i_id, i_title, i_user, i_stat, i_file, i_up_by, i_up_at, i_created, i_app_by, i_app_at) = item
                        
                        if is_guest:
                            status_icon = ""
                        else:
                            if i_stat == "pending":
                                status_icon = "⏳ في انتظار الرفع"
                            elif i_stat == "uploaded":
                                status_icon = "📤 تم الرفع (في انتظار المراجعة)"
                            else:
                                status_icon = "✅ مقبول"
                        
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            col1.markdown(f"**{i_title}**")
                            
                            if is_guest:
                                col1.caption("")
                            elif i_stat != "approved" and i_user:
                                col1.caption(f"مطلوب من: {i_user}")
                            
                            if is_guest:
                                col2.caption("")
                            elif i_stat == "pending":
                                col2.warning(status_icon)
                                st.caption(f"⏱️ طلب في: {i_created}")
                            elif i_stat == "uploaded":
                                col2.info(status_icon)
                                st.caption(f"⏱️ طلب في: {i_created} | 📤 رفع في: {i_up_at}")
                            elif i_stat == "approved":
                                col2.success(status_icon)
                                st.caption(f"⏱️ طلب في: {i_created} | 📤 رفع في: {i_up_at} | ✅ قبول في: {i_app_at}")

                            if i_file and os.path.exists(os.path.join("storage", "Reports", str(i_id), i_file)):
                                file_full_path = os.path.join("storage", "Reports", str(i_id), i_file)
                                with open(file_full_path, "rb") as f:
                                    st.download_button(
                                        label=f"📥 تحميل الملف: {i_file}",
                                        data=f,
                                        file_name=i_file,
                                        key=f"dl_item_{i_id}"
                                    )
                            
                            can_approve = False
                            if is_admin:
                                can_approve = True
                            elif r_creator == st.session_state.user:
                                can_approve = True
                            elif st.session_state.user in [v[0] for v in get_all_users() if v[7] == 'active']:
                                with get_connection() as conn_check:
                                    c_check = conn_check.cursor()
                                    c_check.execute("SELECT COUNT(*) FROM report_viewers WHERE report_id = ? AND viewer_username = ?", (r_id, st.session_state.user))
                                    if c_check.fetchone()[0] > 0:
                                        can_approve = True

                            if i_stat == "uploaded" and can_approve and not is_guest:
                                if st.button(f"✅ قبول هذا البند", key=f"app_{i_id}"):
                                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                    with get_connection() as conn:
                                        c = conn.cursor()
                                        c.execute("UPDATE report_items SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?", 
                                                  (st.session_state.user, now_str, i_id))
                                        conn.commit()
                                    st.success("تم قبول البند بنجاح!")
                                    st.rerun()
                            
                            if i_stat != "approved" and i_user == st.session_state.user and not is_guest:
                                uploaded_file = st.file_uploader(f"📤 رفع الملف الخاص بهذا البند", key=f"upl_{i_id}")
                                if st.button(f"رفع وتحديث الحالة", key=f"btn_up_{i_id}"):
                                    if uploaded_file is not None:
                                        report_folder = os.path.join("storage", "Reports", str(i_id))
                                        os.makedirs(report_folder, exist_ok=True)
                                        file_path = os.path.join(report_folder, uploaded_file.name)
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file.getbuffer())
                                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                        with get_connection() as conn:
                                            c = conn.cursor()
                                            c.execute("UPDATE report_items SET status = 'uploaded', file_name = ?, file_path = ?, uploaded_by = ?, uploaded_at = ? WHERE id = ?",
                                                      (uploaded_file.name, file_path, st.session_state.user, now_str, i_id))
                                            conn.commit()
                                        st.success("✅ تم رفع الملف وتحديث الحالة بنجاح! في انتظار مراجعة المدير.")
                                        st.rerun()
                                    else:
                                        st.error("❌ لم يتم اختيار ملف. يرجى اختيار ملف أولاً.")
                            
                can_add_item = False
                if is_admin or r_creator == st.session_state.user:
                    can_add_item = True
                
                if can_add_item and not is_guest:
                    st.divider()
                    with st.form(key=f"add_item_{r_id}"):
                        st.markdown("➕ إضافة بند/مهمة للتقرير")
                        item_title = st.text_input("عنوان البند/المهمة")
                        assign_user = st.selectbox("اختر الموظف المكلف بتنفيذ هذا البند", [u[0] for u in get_all_users() if u[7] == 'active'])
                        if st.form_submit_button("إضافة البند"):
                            if item_title.strip():
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                with get_connection() as conn:
                                    c = conn.cursor()
                                    c.execute("INSERT INTO report_items (report_id, title, assigned_to_username, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                                              (r_id, item_title.strip(), assign_user, now_str))
                                    conn.commit()
                                st.success("تم إضافة البند وتكليف الموظف به!")
                                st.rerun()
                            else:
                                st.error("يرجى كتابة عنوان للبند.")
                
                if (is_admin or r_creator == st.session_state.user) and not is_guest:
                    st.divider()
                    if st.button(f"🏁 إنهاء وأرشفة التقرير - {r_title}", key=f"complete_{r_id}", type="primary"):
                        with get_connection() as conn:
                            c = conn.cursor()
                            c.execute("UPDATE reports SET status = 'archived' WHERE id = ?", (r_id,))
                            conn.commit()
                        st.success("تم أرشفة التقرير. يمكن للأدمن استعادته من قسم الأرشيف.")
                        st.rerun()

# =============================================================
# 🔥 الـ Footer الخاص بأسفل الصفحة (يظهر في كل الصفحات)
# =============================================================
st.markdown("""
<div class="custom-footer">
    جميع الحقوق محفوظة &copy; <span>مجموعة أعمال الشاطئ</span> - فريق البرمجة ونظم المعلومات
</div>
""", unsafe_allow_html=True)