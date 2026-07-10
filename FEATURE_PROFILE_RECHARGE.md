# 个人中心 + 充值功能 — 独立变更说明

> **开发日期**: 2026年7月10日  
> **基础版本**: 已有登录 + 注册 + 搜索 + 头像上传功能  

---

## 一、功能概述

在已有功能基础上新增 **个人中心** 和 **充值** 两个功能，故意保留水平越权（IDOR）和 SQL 注入漏洞用于教学。

---

## 二、新增路由

### 2.1 个人中心 `GET /profile`

**文件**: `app.py` 第 329-364 行

```python
@app.route("/profile")
def profile():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return redirect("/")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # f-string 字符串拼接 SQL 查询（故意保留注入漏洞）
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
```

**功能特点**:
- 从 URL 参数 `user_id` 获取用户 ID
- 查询 SQLite 数据库中的用户资料
- 显示 ID、用户名、邮箱、手机、余额
- **无权限校验** — 可查看任意用户的资料

---

### 2.2 充值 `POST /recharge`

**文件**: `app.py` 第 367-386 行

```python
@app.route("/recharge", methods=["POST"])
def recharge():
    # CSRF 验证
    csrf_token = request.form.get("csrf_token", "")
    if not csrf_token or csrf_token != session.get("csrf_token"):
        uid = request.form.get("user_id", "")
        return redirect(f"/profile?user_id={uid}")

    user_id = request.form.get("user_id", "").strip()
    amount = request.form.get("amount", "").strip()

    if not user_id or not amount:
        return redirect("/")

    # 尝试转换金额为数字
    try:
        amount = float(amount)
    except ValueError:
        print(f"[充值错误] 无效金额: {amount}")
        return redirect(f"/profile?user_id={user_id}")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # f-string 字符串拼接 SQL 更新（故意保留注入漏洞）
    sql = f"UPDATE users SET balance = balance + {amount} WHERE id = {user_id}"
    print(f"[SQL] {sql}")
    try:
        c.execute(sql)
        conn.commit()
        print(f"[充值成功] user_id={user_id}, 金额={amount}")
    except Exception as e:
        print(f"[SQL错误] {e}")
    conn.close()

    return redirect(f"/profile?user_id={user_id}")
```

**功能特点**:
- 从表单接收 `user_id` 和 `amount`
- 余额更新逻辑：`balance = balance + amount`
- **无正负校验** — `amount=-99999` 可扣减余额
- 充值成功后重定向到个人中心

---

## 三、新增文件

### 3.1 `templates/profile.html`

**文件**: 全新创建，57 行

```html
{% extends "base.html" %}
{% block title %}用户管理系统 - 个人中心{% endblock %}

{% block content %}
    {% if error %}
        <!-- 错误状态：用户不存在 -->
        <div class="card">
            <div class="error-message">{{ error }}</div>
            <div class="action-bar">
                <a href="/" class="btn btn-primary">返回首页</a>
            </div>
        </div>
    {% else %}
        <!-- 用户信息展示卡片 -->
        <div class="card">
            <h2>个人中心</h2>
            <div class="user-info-list">
                <div class="info-item">
                    <span class="info-label">用户 ID</span>
                    <span class="info-value">{{ user.id }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">用户名</span>
                    <span class="info-value">{{ user.username }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">邮箱</span>
                    <span class="info-value">{{ user.email }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">手机</span>
                    <span class="info-value">{{ user.phone }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">余额</span>
                    <span class="info-value">¥{{ "%.2f"|format(user.balance) }}</span>
                </div>
            </div>
        </div>

        <!-- 充值表单卡片 -->
        <div class="card">
            <h2>充值</h2>
            <form method="post" action="/recharge">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="hidden" name="user_id" value="{{ user.id }}">
                <div class="form-group">
                    <label for="amount">充值金额</label>
                    <input type="number" id="amount" name="amount" class="form-input"
                           placeholder="请输入充值金额" step="0.01" required>
                </div>
                <button type="submit" class="btn btn-primary">充 值</button>
            </form>
        </div>
    {% endif %}
{% endblock %}
```

**模板结构**:
- 继承 `base.html`
- 上半部分：用户资料展示（ID / 用户名 / 邮箱 / 手机 / 余额）
- 下半部分：充值表单（金额输入框 + 充值按钮 + 隐藏字段）
- 错误状态：用户不存在时显示错误提示 + 返回按钮

---

## 四、数据库变更

### 4.1 新增 balance 字段

```sql
-- 建表时包含 balance
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    balance REAL DEFAULT 0    -- ← 新增
);

-- 兼容旧数据库
ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0;

-- 默认用户含余额
INSERT OR IGNORE INTO users (username, password, email, phone, balance)
VALUES ('admin', 'admin123', 'admin@example.com', '13800138000', 99999);

INSERT OR IGNORE INTO users (username, password, email, phone, balance)
VALUES ('alice', 'alice2025', 'alice@example.com', '13900139001', 100);
```

---

## 五、已有文件修改

### 5.1 `templates/base.html` — 导航栏

```html
{% if session.get('username') %}
    <span class="nav-welcome">欢迎，{{ session['username'] }}</span>
    <a href="/profile?user_id=1" class="nav-link">个人中心</a>  <!-- ← 新增 -->
    <a href="/upload" class="nav-link">上传头像</a>
    <a href="/logout" class="nav-link">退出</a>
```

### 5.2 `templates/index.html` — 首页快捷入口

```html
<div class="action-bar">
    <a href="/profile?user_id=1" class="btn btn-primary">个人中心</a>  <!-- ← 新增 -->
    <a href="/upload" class="btn btn-primary">上传头像</a>
    <a href="/logout" class="btn btn-secondary">退出登录</a>
</div>
```

---

## 六、漏洞说明（故意保留）

### 6.1 水平越权 IDOR

```
任何用户（甚至未登录）可通过修改 URL 参数查看任意用户资料：

  GET /profile?user_id=1  →  admin 的资料
  GET /profile?user_id=2  →  alice 的资料
  GET /profile?user_id=3  →  其他用户的资料

无任何权限校验，user_id 从 URL 直接获取（不从 session）。
```

### 6.2 SQL 注入（个人中心）

```
user_id 使用 f-string 拼接，可注入 SQL：

  GET /profile?user_id=1 OR 1=1
  → 生成 SQL: SELECT ... WHERE id = 1 OR 1=1
  → 返回所有用户

  GET /profile?user_id=1 UNION SELECT 2,3,4,5,6
  → UNION 查询注入
```

### 6.3 SQL 注入 + 负值充值

```
充值金额无正负校验：

  POST /recharge
  user_id=1&amount=-99999
  → 生成 SQL: UPDATE users SET balance = balance + -99999 WHERE id = 1
  → admin 余额减少 99999

金额字段同样可注入：
  amount=100-- 或 amount=(SELECT 1)
```

---

## 七、Bug 修复记录

### 第三轮修复（仅针对个人中心/充值）

| # | Bug | 行号 | 修复方式 |
|---|-----|------|---------|
| 1 | 充值路由缺少 CSRF 验证 | recharge 路由 | `csrf_token != session.get("csrf_token")` 校验 |
| 2 | `amount=abc` 非数字导致 SQL 崩溃 | recharge 路由 | `float(amount)` 转换 + try/except 捕获 |
| 3 | 余额科学计数法 `¥99999.0` | profile.html | `"%.2f"|format(user.balance)` 格式化为两位小数 |

---

## 八、新增代码统计

| 文件 | 操作 | 行数 | 目的 |
|------|------|------|------|
| `app.py` | 修改 | ~60 行 | profile + recharge 路由 + balance 字段支持 |
| `templates/profile.html` | **新增** | 57 行 | 个人中心页面 + 充值表单 |
| `templates/base.html` | 修改 | 1 行 | 导航栏「个人中心」链接 |
| `templates/index.html` | 修改 | 1 行 | 首页「个人中心」快捷入口 |

---

## 九、Git 提交记录（相关部分）

```
ca53dc1 → 修复充值功能Bug: CSRF校验+金额格式验证
002f109 → 新增个人中心和充值功能
```

---

*独立变更说明 — 2026年7月10日*
