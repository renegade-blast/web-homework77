# Web 安全实训报告

## 用户信息管理平台开发与安全加固

---

| 项目 | 内容 |
|------|------|
| **实训项目** | 用户信息管理平台 |
| **技术栈** | Python Flask + SQLite + HTML/CSS |
| **实训周期** | 2026年7月8日 — 7月17日 |
| **代码仓库** | https://github.com/renegade-blast/web-homework77 |
| **总提交数** | 33 次 |

---

## 一、实训目的

1. 掌握 Python Flask Web 框架的基本开发流程
2. 理解常见 Web 安全漏洞的原理与攻击方式
3. 学习安全加固的通用方法和技术方案
4. 培养安全开发的编码习惯和意识

---

## 二、实训环境

| 工具/技术 | 版本 | 用途 |
|----------|------|------|
| Python | 3.13 | 运行时环境 |
| Flask | 3.0+ | Web 框架 |
| SQLite | 内置 | 数据库 |
| Werkzeug | 3.0+ | WSGI 工具集 |
| Jinja2 | 内置 | 模板引擎 |
| Burp Suite | — | 渗透测试（可选） |

---

## 三、项目实现

### 3.1 功能模块

| 功能 | 路由 | 说明 |
|------|------|------|
| 用户登录 | `POST /login` | SQLite 验证，密码哈希比对，session 存储 |
| 用户注册 | `POST /register` | SQLite 入库，密码强度校验，邮箱/手机格式验证 |
| 用户搜索 | `GET /search` | 模糊搜索用户名/邮箱，参数化查询 |
| 头像上传 | `POST /upload` | 文件保存，路径穿越防护，XSS 防护 |
| 个人中心 | `GET /profile` | 查看当前用户资料，CSRF 保护 |
| 充值 | `POST /recharge` | 余额充值，正数校验，身份校验 |
| 修改密码 | `POST /change-password` | CSRF 保护，原密码校验，强度校验 |
| URL 抓取 | `POST /fetch-url` | HTTP/HTTPS 抓取，SSRF 防护 |
| Ping 诊断 | `POST /ping` | 网络连通性测试，命令注入防护 |
| XML 导入 | `POST /xml-import` | XML 解析，XXE 防护 |
| 动态页面 | `GET /page` | 静态页面加载，路径遍历防护 |

### 3.2 项目结构

```
user_management/
├── app.py                      # 主应用（800+ 行）
├── test_app.py                 # 单元测试（16 项）
├── requirements.txt            # 依赖管理
├── .env.example                # 环境变量模板
├── data/users.db               # SQLite 数据库
├── pages/help.html             # 帮助页面
├── static/
│   ├── css/style.css           # 样式文件
│   └── uploads/                # 上传文件目录
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页
│   ├── login.html              # 登录页
│   ├── register.html           # 注册页
│   ├── upload.html             # 上传页
│   ├── profile.html            # 个人中心
│   ├── ping.html               # Ping 诊断
│   └── xml_import.html         # XML 导入
└── reports/                    # 安全报告
    ├── REPORT_INDEX.md         # 报告索引
    ├── SECURITY_AUDIT_FINAL.md # 最终安全审计
    └── ...
```

### 3.3 数据库设计

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,       -- scrypt 哈希存储
    role TEXT DEFAULT 'user',     -- admin / user
    email TEXT,                   -- 邮箱（格式验证）
    phone TEXT,                   -- 手机号（格式验证）
    balance REAL DEFAULT 0        -- 余额
);
```

### 3.4 关键技术实现

#### 3.4.1 密码安全存储

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 存储时：哈希
hashed_pwd = generate_password_hash(password)
c.execute("INSERT INTO users (password) VALUES (?)", (hashed_pwd,))

# 验证时：比对哈希
c.execute("SELECT password FROM users WHERE username = ?", (username,))
row = c.fetchone()
if row and check_password_hash(row[0], password):
    # 登录成功
```

#### 3.4.2 SQL 注入防护

```python
# ❌ 不安全：f-string 拼接
sql = f"SELECT * FROM users WHERE username = '{keyword}'"

# ✅ 安全：参数化查询
sql = "SELECT * FROM users WHERE username LIKE ?"
c.execute(sql, (f"%{keyword}%",))
```

#### 3.4.3 CSRF 防护

```python
# 生成 Token
session["csrf_token"] = secrets.token_hex(16)

# 验证 Token
csrf_token = request.form.get("csrf_token", "")
if csrf_token != session.get("csrf_token"):
    return "表单已过期"
```

---

## 四、安全漏洞分析与修复

### 4.1 SQL 注入（4 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| 搜索 `LIKE '%{keyword}%'` | `' OR 1=1 --` 爆全部用户 | 参数化查询 |
| 注册 `VALUES ('{username}')` | `hacker')--` 注入 INSERT | 参数化查询 |
| 个人中心 `WHERE id = {uid}` | `1 OR 1=1` 越权查询 | 参数化查询 + isdigit() |
| 充值 `balance + {amount}` | `100--` 注入 UPDATE | 参数化查询 |

### 4.2 路径遍历（3 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| `/page?name=../app.py` | 读取源码 | 正则白名单 `^[a-zA-Z0-9_\-]+$` |
| `/?page=../app.py` | 读取源码 | 同上白名单 |
| 上传 `../../evil.txt` | 逃逸 uploads 目录 | `os.path.basename()` |

### 4.3 命令注入（1 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| Ping `8.8.8.8; ls` | 执行任意命令 | `shell=False` + IP/域名白名单 |

### 4.4 XXE（1 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| XML 导入 `<!ENTITY xxe SYSTEM "file:///etc/passwd">` | 读取任意文件 | 检测 DTD 直接拒绝 |

### 4.5 SSRF（1 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| URL 抓取 `http://127.0.0.1:5000/` | 内网访问 | 协议白名单 + 内网黑名单 |

### 4.6 CSRF 无防护（6 处）

全部 6 个 POST 路由统一添加 `csrf_token` 隐藏字段 + session 校验。

### 4.7 水平越权（3 处）

| 位置 | 攻击方式 | 修复方案 |
|------|---------|---------|
| 个人中心 `?user_id=2` | 查看 alice 资料 | `row[1] != username` |
| 充值 `user_id=2` | 给 alice 充值 | `row[1] != username` |
| 改密 `username=alice` | 修改 alice 密码 | `target_user != username` |

---

## 五、攻击测试验证

### 5.1 SQL 注入测试

```bash
# 搜索注入（修复前：返回全部用户；修复后：无结果）
curl -b "session=X" "http://localhost:5000/search?keyword=%27%20OR%201%3D1%20--"
# 修复后结果: 无搜索结果（参数化查询拦截）✅
```

### 5.2 路径遍历测试

```bash
# 路径遍历（修复前：返回 app.py 源码；修复后：拦截）
curl "http://localhost:5000/page?name=../app.py"
# 修复后结果: 页面名称包含非法字符 ✅
```

### 5.3 命令注入测试

```bash
# 命令注入（修复前：执行 ls 命令；修复后：拦截）
curl -b "session=X" -X POST http://localhost:5000/ping -d "ip=8.8.8.8;ls"
# 修复后结果: 无效的 IP 地址或域名格式 ✅
```

### 5.4 XXE 测试

```bash
# XXE 读取 /etc/passwd（修复前：成功读取；修复后：拦截）
curl -b "session=X" -X POST http://localhost:5000/xml-import \
  --data-urlencode 'xml_data=<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <users><user><name>&xxe;</name><email>x@x.com</email></user></users>'
# 修复后结果: XML 中包含 DTD 实体声明，已拒绝处理 ✅
```

---

## 六、安全防护体系

### 6.1 防护架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户请求                               │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  第一层：传输安全                                        │
│  · X-Content-Type-Options: nosniff                      │
│  · X-Frame-Options: DENY                                │
│  · X-XSS-Protection: 1; mode=block                      │
│  · Referrer-Policy: strict-origin-when-cross-origin      │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  第二层：会话安全                                        │
│  · SESSION_COOKIE_HTTPONLY=True                         │
│  · SESSION_COOKIE_SAMESITE="Lax"                        │
│  · PERMANENT_SESSION_LIFETIME=2h                        │
│  · CSRF Token 验证                                      │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  第三层：认证安全                                        │
│  · 密码 scrypt 哈希                                     │
│  · 登录频率限制（10秒/5次）                               │
│  · Session 登录校验                                      │
│  · 密码强度策略（≥6位+数字+字母）                          │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  第四层：输入安全                                        │
│  · 参数化查询（防 SQL 注入）                              │
│  · 正则白名单（防路径遍历）                                │
│  · 参数列表（防命令注入）                                  │
│  · DTD 拒绝（防 XXE）                                    │
│  · 协议白名单 + 内网黑名单（防 SSRF）                      │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│  第五层：授权安全                                        │
│  · 身份校验（只能操作自己）                                │
│  · 越权拦截（row[1] != username）                         │
│  · 未登录拦截（302 跳转）                                 │
└─────────────────────────────────────────────────────────┘
```

### 6.2 安全配置

```python
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)
```

---

## 七、测试结果

### 7.1 单元测试（16 项全部通过）

```
test_app.py::TestAuth::test_login_page                ✅
test_app.py::TestAuth::test_login_success             ✅
test_app.py::TestAuth::test_login_wrong_password      ✅
test_app.py::TestAuth::test_login_empty_fields        ✅
test_app.py::TestRegister::test_register_page         ✅
test_app.py::TestRegister::test_register_success      ✅
test_app.py::TestRegister::test_register_duplicate    ✅
test_app.py::TestRegister::test_register_weak_password ✅
test_app.py::TestSecurity::test_sql_injection_search  ✅
test_app.py::TestSecurity::test_path_traversal_page   ✅
test_app.py::TestSecurity::test_page_not_found        ✅
test_app.py::TestSecurity::test_help_page             ✅
test_app.py::TestSecurity::test_unauthorized_profile  ✅
test_app.py::TestSecurity::test_csrf_login             ✅
test_app.py::TestPasswordChange::test_change_without_csrf ✅
test_app.py::TestPasswordChange::test_change_other_user ✅
```

### 7.2 安全测试验证

| 测试项 | 测试方法 | 结果 |
|--------|---------|------|
| SQL 注入 | `search?keyword=' OR 1=1 --` | ✅ 参数化查询拦截 |
| 路径遍历 | `page?name=../app.py` | ✅ 白名单拦截 |
| 命令注入 | `ping -d "ip=8.8.8.8;ls"` | ✅ 白名单拦截 |
| XXE | `xml-import` DTD 实体 | ✅ DTD 拒绝 |
| SSRF | `fetch-url http://127.0.0.1` | ✅ 内网黑名单拦截 |
| CSRF | POST 无 Token | ✅ 全部拦截 |
| 越权 | profile?user_id=2 | ✅ 身份校验拦截 |
| 未授权 | profile 未登录 | ✅ 302 跳转 |
| 暴力破解 | 连续 6 次错误登录 | ✅ 第 5 次拦截 |

---

## 八、实训总结

### 8.1 主要成果

1. **功能完整**: 实现了 9 个功能模块、12 个路由、7 个页面模板
2. **安全加固**: 修复了 26 项安全漏洞，覆盖 OWASP Top 10 中的 8 类
3. **测试覆盖**: 16 项单元测试全部通过
4. **文档完备**: 18 份报告涵盖功能说明、安全分析、修复记录

### 8.2 技术收获

| 知识点 | 掌握程度 |
|--------|---------|
| Flask Web 框架开发 | ⭐⭐⭐⭐⭐ |
| SQL 注入原理与参数化查询 | ⭐⭐⭐⭐⭐ |
| CSRF 防护机制 | ⭐⭐⭐⭐⭐ |
| 路径遍历与白名单策略 | ⭐⭐⭐⭐⭐ |
| 命令注入与 shell=False | ⭐⭐⭐⭐ |
| XXE 与 DTD 检测 | ⭐⭐⭐⭐ |
| SSRF 与内网防护 | ⭐⭐⭐⭐ |
| XSS 与输出编码 | ⭐⭐⭐⭐ |
| 水平越权与身份校验 | ⭐⭐⭐⭐⭐ |
| 密码安全与哈希存储 | ⭐⭐⭐⭐⭐ |

### 8.3 安全开发原则

```
1. 永远不要信任用户输入（白名单优于黑名单）
2. 永远使用参数化查询（防 SQL 注入）
3. 永远验证操作者身份（防越权）
4. 永远设置 CSRF Token（防跨站请求）
5. 永远不要用 shell=True（防命令注入）
6. 密码必须哈希存储（防泄露）
7. 日志不能记录敏感信息（防泄露）
8. 安全测试应该自动化（防回归）
```

---

*实训项目：用户信息管理平台*  
*实训周期：2026年7月8日 — 7月17日*  
*提交次数：33 次 | 测试用例：16 项 | 安全修复：26 项*
