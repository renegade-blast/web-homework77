import os
import sqlite3
import secrets
import time
import mimetypes
from flask import Flask, render_template, request, redirect, session, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Session 安全配置
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key-2025"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)

# 登录频率限制
LOGIN_ATTEMPTS = {}


def check_login_rate_limit(ip):
    """简单登录频率限制：同一 IP 10 秒内最多 5 次"""
    now = time.time()
    if ip in LOGIN_ATTEMPTS:
        # 清理过期记录
        LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < 10]
        if len(LOGIN_ATTEMPTS[ip]) >= 5:
            return False
        LOGIN_ATTEMPTS[ip].append(now)
    else:
        LOGIN_ATTEMPTS[ip] = [now]
    return True


@app.after_request
def add_security_headers(response):
    """添加安全响应头"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# 用户数据库 - 密码使用哈希存储
USERS = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": {
        "username": "alice",
        "password": generate_password_hash("alice2025"),
        "role": "user",
        "email": "alice@example.com",
        "phone": "13900139001",
        "balance": 100
    }
}


def get_db_path():
    """获取数据库文件路径"""
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "users.db")


def init_db():
    """初始化数据库，创建 users 表并插入默认用户"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 创建 users 表
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            balance REAL DEFAULT 0
        )
    """)

    # 兼容旧数据库：如果 balance 列不存在则添加
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 插入默认用户（使用 INSERT OR IGNORE 防止重复）
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES ('admin', 'admin123', 'admin@example.com', '13800138000', 99999)")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES ('alice', 'alice2025', 'alice@example.com', '13900139001', 100)")

    conn.commit()
    conn.close()
    print("[数据库初始化完成] data/users.db 已创建，默认用户已插入")


def get_safe_user_info(username):
    """返回不含密码字段的用户信息"""
    user = USERS.get(username)
    if user:
        return {k: v for k, v in user.items() if k != "password"}
    return None


@app.route("/")
def index():
    username = session.get("username")
    user_info = None
    if username:
        user_info = get_safe_user_info(username)

    # 获取搜索关键词和结果（如果有）
    keyword = (request.args.get("keyword", "") or "").strip()
    search_results = None
    if keyword and username:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # f-string 字符串拼接 SQL 查询
        sql = f"SELECT id, username, email, phone FROM users WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
        print(f"[SQL] {sql}")
        try:
            c.execute(sql)
            search_results = c.fetchall()
        except Exception as e:
            print(f"[SQL错误] {e}")
            search_results = []
        conn.close()

    return render_template("index.html", user_info=user_info, keyword=keyword, search_results=search_results)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # CSRF 验证
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("login.html", error="表单已过期，请刷新后重试")

        # 登录频率限制
        client_ip = request.remote_addr or "unknown"
        if not check_login_rate_limit(client_ip):
            return render_template("login.html", error="登录过于频繁，请 10 秒后再试")

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        # 输入验证 - 非空检查
        if not username or not password:
            return render_template("login.html", error="用户名和密码不能为空")

        # 输入验证 - 长度限制
        if len(username) > 50 or len(password) > 128:
            return render_template("login.html", error="输入内容过长")

        # 安全密码比对（使用哈希而非明文 ==）
        user = USERS.get(username)
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            user_info = get_safe_user_info(username)
            return render_template("index.html", user_info=user_info)

        # 通用错误提示（不明确告知是用户名还是密码错误）
        return render_template("login.html", error="用户名或密码错误")

    # 生成 CSRF Token（如果未存在）
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("login.html", csrf_token=session["csrf_token"])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # CSRF 验证
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("register.html", error="表单已过期，请刷新后重试")

        username = (request.form.get("username", "") or "").strip()
        password = request.form.get("password", "") or ""
        email = (request.form.get("email", "") or "").strip()
        phone = (request.form.get("phone", "") or "").strip()

        # 输入验证
        if not username:
            return render_template("register.html", error="用户名不能为空")
        if len(username) > 50:
            return render_template("register.html", error="用户名过长")
        if not password:
            return render_template("register.html", error="密码不能为空")

        # 使用 f-string 字符串拼接插入数据库
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        sql = f"INSERT INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
        print(f"[SQL] {sql}")
        try:
            c.execute(sql)
            conn.commit()
            print(f"[注册成功] 用户 {username} 已添加到数据库")
            conn.close()
            return render_template("login.html", error="注册成功，请登录")
        except Exception as e:
            print(f"[SQL错误] {e}")
            conn.close()
            return render_template("register.html", error=f"注册失败：{e}")

    # 生成 CSRF Token（如果未存在）
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("register.html", csrf_token=session["csrf_token"])


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return redirect("/")

    username = session.get("username")
    if not username:
        return redirect("/login")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # f-string 字符串拼接 SQL 查询
    sql = f"SELECT id, username, email, phone FROM users WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
    print(f"[SQL] {sql}")
    try:
        c.execute(sql)
        results = c.fetchall()
    except Exception as e:
        print(f"[SQL错误] {e}")
        results = []
    conn.close()

    username = session.get("username")
    user_info = None
    if username:
        user_info = get_safe_user_info(username)

    return render_template("index.html", user_info=user_info, keyword=keyword, search_results=results)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    username = session.get("username")
    if not username:
        return redirect("/login")

    if request.method == "POST":
        # CSRF 验证
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("upload.html", error="表单已过期，请刷新后重试", csrf_token=session.get("csrf_token", ""))

        upload_dir = os.path.join(app.root_path, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file = request.files.get("file")
        if not file or not file.filename:
            return render_template("upload.html", error="请选择一个文件", csrf_token=session.get("csrf_token", ""))

        # 防止路径穿越：只取文件名部分，忽略目录路径
        original_filename = file.filename
        filename = os.path.basename(original_filename)
        if not filename:
            return render_template("upload.html", error="文件名无效", csrf_token=session.get("csrf_token", ""))

        # 如果文件名因路径穿越被修改，提示用户
        if filename != original_filename:
            print(f"[上传] 文件名已规范化: '{original_filename}' → '{filename}'")

        # 超长文件名截断
        if len(filename) > 200:
            filename = filename[-200:]

        filepath = os.path.join(upload_dir, filename)

        # 检查同名文件
        if os.path.exists(filepath):
            return render_template("upload.html", error=f"文件 {filename} 已存在，请重命名后重试", csrf_token=session.get("csrf_token", ""))

        try:
            file.save(filepath)
        except Exception as e:
            print(f"[上传错误] {e}")
            return render_template("upload.html", error="文件保存失败，请重试", csrf_token=session.get("csrf_token", ""))

        # 防止存储型 XSS：将 HTML 文件扩展名改为 .txt 后缀
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".html", ".htm", ".shtml", ".xhtml", ".svg"]:
            safe_filename = filename + ".txt"
            safe_filepath = os.path.join(upload_dir, safe_filename)
            os.rename(filepath, safe_filepath)
            file_url = f"/static/uploads/{safe_filename}"
            print(f"[上传] 检测到 HTML 文件，已重命名为 {safe_filename}")
            return render_template("upload.html", success=True, filename=safe_filename, file_url=file_url,
                                   warning="检测到 HTML 文件，已自动重命名为 .txt 以防止 XSS 攻击",
                                   csrf_token=session.get("csrf_token", ""))

        file_url = f"/static/uploads/{filename}"
        print(f"[上传] {username} 上传了文件: {filename}")
        return render_template("upload.html", success=True, filename=filename, file_url=file_url,
                               csrf_token=session.get("csrf_token", ""))

    # 生成 CSRF Token（如果未存在）
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("upload.html", csrf_token=session["csrf_token"])


@app.route("/profile")
def profile():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return redirect("/")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # f-string 字符串拼接 SQL 查询
    sql = f"SELECT id, username, email, phone, balance FROM users WHERE id = {user_id}"
    print(f"[SQL] {sql}")
    try:
        c.execute(sql)
        user = c.fetchone()
    except Exception as e:
        print(f"[SQL错误] {e}")
        user = None
    conn.close()

    if not user:
        return render_template("profile.html", error=f"用户不存在（ID: {user_id}）")

    # 生成 CSRF Token（如果未存在）
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)

    user_data = {
        "id": user[0],
        "username": user[1],
        "email": user[2],
        "phone": user[3],
        "balance": user[4]
    }
    return render_template("profile.html", user=user_data, csrf_token=session["csrf_token"])


@app.route("/recharge", methods=["POST"])
def recharge():
    user_id = request.form.get("user_id", "")
    amount = request.form.get("amount", "0")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # f-string 字符串拼接 SQL 更新
    sql = f"UPDATE users SET balance = balance + {amount} WHERE id = {user_id}"
    print(f"[SQL] {sql}")
    try:
        c.execute(sql)
        conn.commit()
    except Exception as e:
        print(f"[SQL错误] {e}")
    conn.close()

    return redirect(f"/profile?user_id={user_id}")


@app.route("/logout")
def logout():
    session.clear()  # 彻底清除所有 session 数据
    return redirect("/")


if __name__ == "__main__":
    init_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
