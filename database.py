import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "system_logs.db"

def get_connection():
    """اتصال بسيط بدون WAL"""
    return sqlite3.connect(DB_NAME, timeout=10)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # ===== الجداول الأساسية =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            folder TEXT,
            uploaded_by TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'active',
            deleted_by TEXT,
            deleted_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            allowed_folders TEXT,
            role TEXT DEFAULT 'User',
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            changes_log TEXT,
            status TEXT DEFAULT 'active',
            deleted_by TEXT,
            deleted_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action_type TEXT,
            target_file TEXT,
            target_folder TEXT,
            timestamp TEXT,
            details TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_folders (
            folder_name TEXT PRIMARY KEY,
            status TEXT DEFAULT 'active',
            deleted_by TEXT,
            deleted_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sub_folders (
            parent_folder TEXT,
            sub_folder_name TEXT,
            status TEXT DEFAULT 'active',
            deleted_by TEXT,
            deleted_at TEXT,
            PRIMARY KEY (parent_folder, sub_folder_name)
        )
    ''')
    
    # تحديث الجداول القديمة
    for table in ["custom_folders", "sub_folders"]:
        for col, col_type in [("status", "TEXT DEFAULT 'active'"), ("deleted_by", "TEXT"), ("deleted_at", "TEXT")]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except:
                pass
    
    # ===== الجداول الجديدة (التقارير) =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',  -- active, archived
            is_public INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_viewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            viewer_username TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY(viewer_username) REFERENCES users(username) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            assigned_to_username TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, uploaded, approved
            created_at TEXT,
            file_name TEXT,
            file_path TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT,
            approved_by TEXT,
            approved_at TEXT,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
    ''')
    
    # ===== جـدول جـديـد: الملفات الشخصية والمرسلة =====
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            sender_username TEXT NOT NULL,
            recipient_username TEXT NOT NULL,
            message TEXT,
            file_path TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # محاولة إضافة الأعمدة المفقودة
    for col in ["created_at", "approved_by", "approved_at"]:
        try:
            cursor.execute(f"ALTER TABLE report_items ADD COLUMN {col} TEXT")
        except:
            pass

    # ============================================================
    # 🆕 الجداول الجديدة المطلوبة للصلاحيات والضيوف
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL,
            username TEXT NOT NULL,
            UNIQUE(folder_path, username)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guest_folders (
            username TEXT PRIMARY KEY,
            guest_folder TEXT NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
        )
    ''')
    
    # ============================================================
    # بيانات افتراضية (المستخدمين والمجلدات)
    # ============================================================
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO users (username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("admin", hash_password("123"), "Accounting,Quality,Stores,Training,Main", "Admin", "System", now_str, now_str, "Initial Admin", "active"))
        cursor.execute("INSERT INTO users (username, password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("walid", hash_password("123"), "Accounting,Main", "Manager", "admin", now_str, now_str, "Initial Manager", "active"))
    
    cursor.execute("SELECT COUNT(*) FROM custom_folders")
    if cursor.fetchone()[0] == 0:
        for d in ['Accounting', 'Quality', 'Stores', 'Training', 'Main']:
            cursor.execute("INSERT OR IGNORE INTO custom_folders (folder_name, status) VALUES (?, 'active')", (d,))
            
            # ✅ منح صلاحيات افتراضية للأدمن والمستخدمين الحاليين على المجلدات القديمة
            cursor.execute("SELECT username FROM users WHERE status = 'active' AND role != 'guest'")
            for u_row in cursor.fetchall():
                try:
                    cursor.execute("INSERT OR IGNORE INTO folder_permissions (folder_path, username) VALUES (?, ?)", (d, u_row[0]))
                except:
                    pass

    # ============================================================
    # 🚨 تم إزالة الكود اللي كان بيخلي كل المستخدمين يشوفوا كل المجلدات
    # ============================================================
    
    conn.commit()
    conn.close()
    
    os.makedirs(os.path.join("storage", "Deleted"), exist_ok=True)
    os.makedirs(os.path.join("storage", "Reports"), exist_ok=True)
    os.makedirs(os.path.join("storage", "UserFiles"), exist_ok=True)

def log_activity(username, action_type, target_file, target_folder, details=""):
    """تسجيل النشاط - نسخة بسيطة وآمنة"""
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (username, action_type, target_file, target_folder, timestamp, details) VALUES (?, ?, ?, ?, ?, ?)",
            (username, action_type, target_file, target_folder, now_str, details)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        try:
            with open("error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - ERROR: {e}\n")
        except:
            pass

def verify_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_p = hash_password(password)
    cursor.execute("SELECT password, allowed_folders, role, created_by, created_at, updated_at, changes_log, status FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[7] == 'active':
        stored_pass = row[0]
        if stored_pass == hashed_p or stored_pass == password:
            return {
                "password": stored_pass,
                "allowed_folders": row[1].split(",") if row[1] else [],
                "role": row[2] if row[2] else ("Admin" if username == "admin" else "User"),
                "created_by": row[3], "created_at": row[4], "updated_at": row[5], "changes_log": row[6]
            }
    return None

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, allowed_folders, role, created_by, created_at, updated_at, changes_log, status, deleted_by, deleted_at FROM users")
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_folders(include_deleted=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_deleted:
        cursor.execute("SELECT folder_name, deleted_by, deleted_at FROM custom_folders WHERE status = 'deleted'")
        result = cursor.fetchall()
    else:
        cursor.execute("SELECT folder_name FROM custom_folders WHERE status = 'active'")
        result = [r[0] for r in cursor.fetchall()]
    conn.close()
    return result

def get_subfolders(parent_folder, include_deleted=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_deleted:
        cursor.execute("SELECT sub_folder_name, deleted_by, deleted_at FROM sub_folders WHERE parent_folder = ? AND status = 'deleted'", (parent_folder,))
        result = cursor.fetchall()
    else:
        cursor.execute("SELECT sub_folder_name FROM sub_folders WHERE parent_folder = ? AND status = 'active'", (parent_folder,))
        result = [r[0] for r in cursor.fetchall()]
    conn.close()
    return result

# ============================================================
# 🆕 دوال جديدة لجداول الصلاحيات والضيوف
# ============================================================

def get_folder_permissions(folder_path):
    """جلب قائمة المستخدمين المسموح لهم برؤية مجلد معين"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM folder_permissions WHERE folder_path = ?", (folder_path,))
    result = [r[0] for r in cursor.fetchall()]
    conn.close()
    return result

def update_folder_permissions(folder_path, allowed_users):
    """تحديث صلاحيات مجلد معين"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM folder_permissions WHERE folder_path = ?", (folder_path,))
    for user in allowed_users:
        cursor.execute("INSERT OR IGNORE INTO folder_permissions (folder_path, username) VALUES (?, ?)", (folder_path, user))
    conn.commit()
    conn.close()

def get_user_viewable_folders(username, is_admin=False):
    """جلب المجلدات التي يمكن للمستخدم رؤيتها بناءً على صلاحياته (للأدمن والمستخدمين العاديين)"""
    conn = get_connection()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute("SELECT folder_name FROM custom_folders WHERE status = 'active'")
    else:
        cursor.execute("""
            SELECT DISTINCT cf.folder_name 
            FROM custom_folders cf
            JOIN folder_permissions fp ON cf.folder_name = fp.folder_path
            WHERE cf.status = 'active' AND fp.username = ?
        """, (username,))
    result = [r[0] for r in cursor.fetchall()]
    conn.close()
    return result

def get_guest_folder(username):
    """جلب المجلد الخاص بالضيف"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT guest_folder FROM guest_folders WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None