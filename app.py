import os
import re
import logging
import sqlite3
import secrets
import time
import subprocess
import platform
import urllib.request
import urllib.error
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 应用配置
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# 登录频率限制
LOGIN_ATTEMPTS = {}


def check_login_rate_limit(ip):
    """同一 IP 10 秒内最多 5 次"""
    now = time.time()
    if ip in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < 10]
        if len(LOGIN_ATTEMPTS[ip]) >= 5:
            return False
        LOGIN_ATTEMPTS[ip].append(now)
    else:
        LOGIN_ATTEMPTS[ip] = [now]
    return True


def get_db_path():
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "users.db")


def init_db():
    """初始化数据库 — 唯一用户数据源"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            email TEXT,
            phone TEXT,
            balance REAL DEFAULT 0
        )
    """)
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

    # 默认用户 — 密码已哈希
    for user in [
        ("admin", "admin123", "admin", "admin@example.com", "13800138000", 99999),
        ("alice", "alice2025", "user", "alice@example.com", "13900139001", 100),
    ]:
        c.execute("SELECT id FROM users WHERE username = ?", (user[0],))
        if not c.fetchone():
            hashed = generate_password_hash(user[1])
            c.execute("INSERT INTO users (username, password, role, email, phone, balance) VALUES (?, ?, ?, ?, ?, ?)",
                      (user[0], hashed, user[2], user[3], user[4], user[5]))
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成: data/users.db 已创建")


def get_safe_user_info(username):
    """从 SQLite 查询用户信息（含id，不含密码）"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, username, role, email, phone, balance FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "role": row[2], "email": row[3], "phone": row[4], "balance": row[5]}
    return None


def get_user_by_id(uid):
    """根据 ID 查询用户"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, username, email, phone, balance FROM users WHERE id = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return row


def is_safe_page_name(name):
    """校验页面名称是否合法"""
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name))


def validate_email(email):
    """简单邮箱格式校验"""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def validate_phone(phone):
    """中国手机号格式校验"""
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ───────────────── 首页 ─────────────────


@app.route("/")
def index():
    username = session.get("username")
    user_info = get_safe_user_info(username) if username else None

    # 搜索
    keyword = (request.args.get("keyword", "") or "").strip()
    search_results = None
    if keyword and username:
        if len(keyword) > 100:
            keyword = keyword[:100]
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        sql = "SELECT id, username, email, phone FROM users WHERE username LIKE ? OR email LIKE ?"
        param = f"%{keyword}%"
        try:
            c.execute(sql, (param, param))
            search_results = c.fetchall()
        except Exception as e:
            logger.error(f"SQL查询错误: {e}")
            search_results = []
        conn.close()

    # 动态页面（与 /page 路由保持一致的正则校验）
    page_content = None
    page_name = request.args.get("page", "")
    if page_name:
        if not is_safe_page_name(page_name):
            page_content = "<p style='color:#e53e3e;'>页面名称包含非法字符</p>"
        else:
            if len(page_name) > 50:
                page_name = page_name[:50]
            try:
                page_path = os.path.join(app.root_path, "pages", page_name)
                if os.path.exists(page_path):
                    with open(page_path, "r", encoding="utf-8") as f:
                        page_content = f.read()
                else:
                    page_path_html = page_path + ".html"
                    if os.path.exists(page_path_html):
                        with open(page_path_html, "r", encoding="utf-8") as f:
                            page_content = f.read()
                    else:
                        page_content = "<p style='color:#e53e3e;'>页面不存在</p>"
            except Exception as e:
                logger.error(f"页面加载错误: {e}")
                page_content = "<p style='color:#e53e3e;'>页面加载失败</p>"

    return render_template("index.html", user_info=user_info, keyword=keyword,
                           search_results=search_results, page_content=page_content)


# ───────────────── 登录 ─────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("login.html", error="表单已过期，请刷新后重试")

        client_ip = request.remote_addr or "unknown"
        if not check_login_rate_limit(client_ip):
            return render_template("login.html", error="登录过于频繁，请 10 秒后再试")

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template("login.html", error="用户名和密码不能为空")
        if len(username) > 50 or len(password) > 128:
            return render_template("login.html", error="输入内容过长")

        # 从 SQLite 验证（唯一数据源）
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session.permanent = True
            session["username"] = username
            # 登录成功后轮转 CSRF Token
            session["csrf_token"] = secrets.token_hex(16)
            user_info = get_safe_user_info(username)
            return render_template("index.html", user_info=user_info)

        return render_template("login.html", error="用户名或密码错误")

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("login.html", csrf_token=session["csrf_token"])


# ───────────────── 注册 ─────────────────


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("register.html", error="表单已过期，请刷新后重试")

        username = (request.form.get("username", "") or "").strip()
        password = request.form.get("password", "") or ""
        email = (request.form.get("email", "") or "").strip()
        phone = (request.form.get("phone", "") or "").strip()

        # 基础验证
        if not username:
            return render_template("register.html", error="用户名不能为空")
        if len(username) > 50:
            return render_template("register.html", error="用户名过长")
        if not password:
            return render_template("register.html", error="密码不能为空")
        if len(password) > 128:
            return render_template("register.html", error="密码过长")
        if len(email) > 100:
            return render_template("register.html", error="邮箱过长")
        if len(phone) > 20:
            return render_template("register.html", error="手机号过长")

        # 密码强度校验
        if len(password) < 6:
            return render_template("register.html", error="密码长度至少 6 位")
        if not re.search(r'\d', password):
            return render_template("register.html", error="密码必须包含数字")
        if not re.search(r'[a-zA-Z]', password):
            return render_template("register.html", error="密码必须包含字母")

        # 邮箱格式校验
        if email and not validate_email(email):
            return render_template("register.html", error="邮箱格式无效")
        # 手机号格式校验
        if phone and not validate_phone(phone):
            return render_template("register.html", error="手机号格式无效（需为11位中国手机号）")

        hashed_pwd = generate_password_hash(password)

        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        sql = "INSERT INTO users (username, password, role, email, phone) VALUES (?, ?, ?, ?, ?)"
        try:
            c.execute(sql, (username, hashed_pwd, "user", email, phone))
            conn.commit()
            conn.close()
            return render_template("login.html", error="注册成功，请登录")
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="用户名已存在")
        except Exception as e:
            logger.error(f"注册错误: {e}")
            conn.close()
            return render_template("register.html", error="注册失败，请稍后重试")

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("register.html", csrf_token=session["csrf_token"])


# ───────────────── 搜索 ─────────────────


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return redirect("/")

    username = session.get("username")
    if not username:
        return redirect("/login")

    if len(keyword) > 100:
        keyword = keyword[:100]

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    sql = "SELECT id, username, email, phone FROM users WHERE username LIKE ? OR email LIKE ?"
    param = f"%{keyword}%"
    try:
        c.execute(sql, (param, param))
        results = c.fetchall()
    except Exception as e:
        logger.error(f"SQL错误: {e}")
        results = []
    conn.close()

    user_info = get_safe_user_info(username)
    return render_template("index.html", user_info=user_info, keyword=keyword, search_results=results)


# ───────────────── 上传 ─────────────────


@app.route("/upload", methods=["GET", "POST"])
def upload():
    username = session.get("username")
    if not username:
        return redirect("/login")

    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", "")
        if not csrf_token or csrf_token != session.get("csrf_token"):
            return render_template("upload.html", error="表单已过期，请刷新后重试", csrf_token=session.get("csrf_token", ""))

        upload_dir = os.path.join(app.root_path, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        file = request.files.get("file")
        if not file or not file.filename:
            return render_template("upload.html", error="请选择一个文件", csrf_token=session.get("csrf_token", ""))

        original_filename = file.filename
        filename = os.path.basename(original_filename)
        if not filename:
            return render_template("upload.html", error="文件名无效", csrf_token=session.get("csrf_token", ""))
        if filename != original_filename:
            logger.info(f"文件名已规范化: '{original_filename}' → '{filename}'")
        if len(filename) > 200:
            filename = filename[-200:]

        filepath = os.path.join(upload_dir, filename)
        if os.path.exists(filepath):
            return render_template("upload.html", error=f"文件 {filename} 已存在，请重命名后重试", csrf_token=session.get("csrf_token", ""))

        try:
            file.save(filepath)
        except Exception as e:
            logger.error(f"上传错误: {e}")
            return render_template("upload.html", error="文件保存失败，请重试", csrf_token=session.get("csrf_token", ""))

        ext = os.path.splitext(filename)[1].lower()
        if ext in [".html", ".htm", ".shtml", ".xhtml", ".svg"]:
            safe_filename = filename + ".txt"
            safe_filepath = os.path.join(upload_dir, safe_filename)
            os.rename(filepath, safe_filepath)
            file_url = f"/static/uploads/{safe_filename}"
            return render_template("upload.html", success=True, filename=safe_filename, file_url=file_url,
                                   warning="检测到 HTML 文件，已自动重命名为 .txt 以防止 XSS 攻击",
                                   csrf_token=session.get("csrf_token", ""))

        file_url = f"/static/uploads/{filename}"
        return render_template("upload.html", success=True, filename=filename, file_url=file_url,
                               csrf_token=session.get("csrf_token", ""))

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return render_template("upload.html", csrf_token=session["csrf_token"])


# ───────────────── 个人中心 ─────────────────


@app.route("/profile")
def profile():
    username = session.get("username")
    if not username:
        return redirect("/login")

    # 默认查看自己的资料，也可通过 ?user_id= 查看（IDOR 已验证自己只能看自己）
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        user_info = get_safe_user_info(username)
        if not user_info:
            return redirect("/logout")
        uid = user_info["id"]
    else:
        if not user_id.isdigit():
            return render_template("profile.html", error="无效的用户 ID")
        uid = int(user_id)
        if uid < 1 or uid > 1000000:
            return render_template("profile.html", error="用户 ID 超出有效范围")

    row = get_user_by_id(uid)
    if not row:
        return render_template("profile.html", error=f"用户不存在（ID: {uid}）")

    # 只能查看自己的资料
    if row[1] != username:
        return redirect("/")

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)

    user_data = {"id": row[0], "username": row[1], "email": row[2], "phone": row[3], "balance": row[4]}
    return render_template("profile.html", user=user_data, csrf_token=session["csrf_token"])


# ───────────────── 充值 ─────────────────


@app.route("/recharge", methods=["POST"])
def recharge():
    username = session.get("username")
    if not username:
        return redirect("/login")

    csrf_token = request.form.get("csrf_token", "")
    if not csrf_token or csrf_token != session.get("csrf_token"):
        return redirect("/profile")

    user_id = request.form.get("user_id", "").strip()
    amount = request.form.get("amount", "").strip()
    if not user_id or not amount or not user_id.isdigit():
        return redirect("/")
    uid = int(user_id)
    if uid < 1 or uid > 1000000:
        return redirect("/")

    # 验证用户存在且只能给自己充值
    row = get_user_by_id(uid)
    if not row or row[1] != username:
        return redirect("/profile")

    try:
        amount = float(amount)
    except ValueError:
        return redirect(f"/profile?user_id={uid}")

    if amount <= 0:
        return redirect(f"/profile?user_id={uid}")
    if amount > 99999999:
        return redirect(f"/profile?user_id={uid}")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    sql = "UPDATE users SET balance = balance + ? WHERE id = ?"
    try:
        c.execute(sql, (amount, uid))
        conn.commit()
    except Exception as e:
        logger.error(f"充值错误: {e}")
    conn.close()

    return redirect(f"/profile?user_id={uid}")


# ───────────────── 动态页面 ─────────────────


@app.route("/page")
def page():
    name = request.args.get("name", "")
    if not name:
        return redirect("/")

    page_content = None
    try:
        if not is_safe_page_name(name):
            page_content = "<p style='color:#e53e3e;'>页面名称包含非法字符</p>"
        else:
            if len(name) > 50:
                name = name[:50]
            page_path = os.path.join(app.root_path, "pages", name)
            if os.path.exists(page_path):
                with open(page_path, "r", encoding="utf-8") as f:
                    page_content = f.read()
            else:
                page_path_html = page_path + ".html"
                if os.path.exists(page_path_html):
                    with open(page_path_html, "r", encoding="utf-8") as f:
                        page_content = f.read()
                else:
                    page_content = "<p style='color:#e53e3e;'>页面不存在</p>"
    except Exception as e:
        print(f"[页面加载错误] {e}")
        page_content = "<p style='color:#e53e3e;'>页面加载失败</p>"

    user_info = get_safe_user_info(session.get("username"))
    return render_template("index.html", user_info=user_info, page_content=page_content)


# ───────────────── 修改密码 ─────────────────


@app.route("/change-password", methods=["POST"])
def change_password():
    username = session.get("username")
    if not username:
        return redirect("/login")

    # CSRF 验证
    csrf_token = request.form.get("csrf_token", "")
    if not csrf_token or csrf_token != session.get("csrf_token"):
        logger.warning(f"密码修改CSRF失败: session_token='{session.get('csrf_token','')}', form_token='{csrf_token}'")
        return redirect("/profile")

    # 只允许修改自己的密码
    target_user = request.form.get("username", "").strip()
    if target_user != username:
        logger.warning(f"越权修改密码被拦截: 操作者={username}, 目标={target_user}")
        return redirect("/profile")

    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not new_password or not confirm_password:
        logger.warning("密码修改: 密码为空")
        return redirect("/profile")
    if new_password != confirm_password:
        logger.warning("密码修改: 两次密码不一致")
        return redirect("/profile")

    # 密码强度校验
    if len(new_password) < 6:
        logger.warning("密码修改: 密码过短")
        return redirect("/profile")
    if not re.search(r'\d', new_password):
        logger.warning("密码修改: 缺少数字")
        return redirect("/profile")
    if not re.search(r'[a-zA-Z]', new_password):
        logger.warning("密码修改: 缺少字母")
        return redirect("/profile")

    hashed_pwd = generate_password_hash(new_password)

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    sql = "UPDATE users SET password = ? WHERE username = ?"
    logger.info(f"密码修改: 操作者={username}")
    try:
        c.execute(sql, (hashed_pwd, username))
        conn.commit()
        logger.info(f"密码修改成功: {username}")
    except Exception as e:
        logger.error(f"密码修改失败: {e}")
    conn.close()

    return redirect("/profile")


# ───────────────── URL 抓取 ─────────────────


def is_safe_url(url):
    """检查 URL 是否安全：仅允许 http/https、禁止内网地址"""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"):
        return False
    if hostname.startswith("10."):
        return False
    if hostname.startswith("172."):
        try:
            second = int(hostname.split(".")[1])
            if 16 <= second <= 31:
                return False
        except (IndexError, ValueError):
            pass
    if hostname.startswith("192.168."):
        return False
    if hostname.startswith("169.254."):
        return False
    if hostname.startswith("100."):
        try:
            second = int(hostname.split(".")[1])
            if 64 <= second <= 127:
                return False
        except (IndexError, ValueError):
            pass
    return True


@app.route("/fetch-url", methods=["POST"])
def fetch_url():
    username = session.get("username")
    if not username:
        return redirect("/login")

    url = request.form.get("url", "").strip()
    if not url:
        user_info = get_safe_user_info(username)
        return render_template("index.html", user_info=user_info, fetch_error="请输入 URL")

    fetch_status = None
    fetch_content = None
    fetch_error = None

    try:
        if not is_safe_url(url):
            fetch_error = "不支持的协议或禁止访问的地址"
        else:
            log_url = url[:200] + "..." if len(url) > 200 else url
            logger.info(f"URL抓取: {username} 请求 {log_url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            fetch_status = resp.status
            max_size = 5120
            chunks = []
            total_read = 0
            while total_read < max_size:
                chunk = resp.read(min(1024, max_size - total_read))
                if not chunk:
                    break
                chunks.append(chunk)
                total_read += len(chunk)
            raw = b"".join(chunks)
            try:
                fetch_content = raw.decode("utf-8")[:5000]
            except UnicodeDecodeError:
                fetch_content = f"[二进制内容，共 {total_read} 字节]"
            logger.info(f"URL抓取成功: {log_url} → 状态码 {fetch_status}")
    except urllib.error.HTTPError as e:
        fetch_status = e.code
        fetch_content = str(e.reason)[:5000]
        fetch_error = f"HTTP 错误: {e.code}"
    except urllib.error.URLError as e:
        fetch_error = f"URL 错误: {e.reason}"
    except Exception as e:
        fetch_error = f"请求失败: {str(e)[:200]}"

    user_info = get_safe_user_info(username)
    return render_template("index.html", user_info=user_info,
                           fetch_url=url, fetch_status=fetch_status,
                           fetch_content=fetch_content, fetch_error=fetch_error)


# ───────────────── Ping 诊断 ─────────────────


def is_valid_ping_target(target):
    """校验 Ping 目标：只允许 IP 地址或合法域名"""
    # 允许 IP v4 地址
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, target):
        # 验证每个段在 0-255 范围
        parts = target.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            return True

    # 允许合法域名（字母、数字、点、中划线）
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    if re.match(domain_pattern, target):
        return True

    return False


@app.route("/ping", methods=["GET", "POST"])
def ping():
    username = session.get("username")
    if not username:
        return redirect("/login")

    ping_result = None
    ping_error = None

    if request.method == "POST":
        target = request.form.get("ip", "").strip()
        if not target:
            ping_error = "请输入 IP 地址或域名"
        elif not is_valid_ping_target(target):
            ping_error = "无效的 IP 地址或域名格式"
        else:
            logger.info(f"Ping: {username} 请求 {target}")
            try:
                # 使用参数列表方式，禁用 shell=True 防止命令注入
                output = subprocess.check_output(
                    ["ping", "-c", "3", target],
                    timeout=30,
                    stderr=subprocess.STDOUT
                )
                ping_result = output.decode("utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                ping_error = "Ping 超时（30 秒）"
            except subprocess.CalledProcessError as e:
                ping_result = e.output.decode("utf-8", errors="replace")
                ping_error = f"Ping 失败，返回码: {e.returncode}"
            except Exception as e:
                ping_error = f"执行错误: {str(e)}"

    return render_template("ping.html", ping_result=ping_result, ping_error=ping_error)


# ───────────────── 退出 ─────────────────


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ───────────────── 启动 ─────────────────


if __name__ == "__main__":
    init_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
