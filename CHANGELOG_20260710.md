# 2026年7月10日 — 开发变更日志

> **项目**: 用户信息管理平台  
> **基础版本**: 已有登录 + 注册 + 搜索功能  
> **今日新增**: 头像上传 + 个人中心 + 充值 + 安全修复  
> **GitHub**: https://github.com/renegade-blast/web-homework77

---

## 一、新增功能（3 项）

### 1.1 头像上传

| 项目 | 内容 |
|------|------|
| 路由 | `GET/POST /upload` |
| 文件 | `templates/upload.html` |
| 存储 | `static/uploads/`（保留原始文件名） |
| 预览 | 上传成功后显示图片预览和访问 URL |
| 限制 | `MAX_CONTENT_LENGTH = 16MB` |
| 新增代码 | app.py 第 254-326 行 |

**相关修改**: `app.py`、`templates/upload.html`（新增）、`templates/base.html`（导航栏添加链接）、`templates/index.html`（添加入口）、`static/css/style.css`（预览样式）

---

### 1.2 个人中心

| 项目 | 内容 |
|------|------|
| 路由 | `GET /profile?user_id=X` |
| 文件 | `templates/profile.html` |
| 展示 | ID、用户名、邮箱、手机、余额 |
| 权限 | 无权限校验，可查看任意用户 |
| 数据源 | SQLite 数据库（含 balance 字段） |
| 新增代码 | app.py 第 329-364 行 |

**相关修改**: `app.py`（新增路由）、`templates/profile.html`（新增）、`templates/base.html`（导航栏添加链接）、`templates/index.html`（添加入口）

---

### 1.3 充值

| 项目 | 内容 |
|------|------|
| 路由 | `POST /recharge` |
| 参数 | `user_id`、`amount`（表单 POST） |
| 逻辑 | `balance = balance + amount` |
| 校验 | 无正负校验 |
| 新增代码 | app.py 第 367-386 行 |

---

## 二、数据库变更

```sql
-- 原表结构（仅 4 字段）
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    phone TEXT
);

-- 新表结构（增加 balance 字段）
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    balance REAL DEFAULT 0  -- ← 新增
);

-- 兼容旧库：ALTER TABLE 添加列
ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0;
```

---

## 三、安全修复（3 轮）

### 第一轮：上传功能 Bug 修复

| # | 问题 | 文件行号 | 修复方式 |
|---|------|---------|---------|
| 1 | 路径穿越 `../../evil.txt` | upload 路由 | `os.path.basename()` 截断路径 |
| 2 | 同名文件静默覆盖 | upload 路由 | `os.path.exists()` 检查并提示 |
| 3 | 超长文件名（500字）崩溃 | upload 路由 | 截断至 200 字符 + try/except |
| 4 | 文件保存失败抛 500 | upload 路由 | try/except 捕获异常返回友好提示 |
| 5 | 注册空用户名/密码入库 | register 路由 | 非空校验 |
| 6 | 未登录搜索仍执行 SQL | search 路由 | `if not username: return redirect("/login")` |

### 第二轮：安全漏洞修复

| # | 漏洞 | CVSS 等级 | 修复方式 |
|---|------|-----------|---------|
| 1 | 存储型 XSS（上传 HTML 执行 JS） | 🔴 高 | HTML 文件自动重命名为 `.txt` |
| 2 | CSRF（所有表单无 Token） | 🟡 中 | 所有 POST 表单添加 Token 验证 |
| 3 | 登录暴力破解 | 🟡 中 | 同一 IP 10 秒内最多 5 次 |
| 4 | 缺少安全响应头 | 🟢 低 | X-Frame-Options / X-Content-Type-Options 等 |
| 5 | CSRF Token 每次 GET 都刷新 | 🟢 低 | `if not in session:` 条件生成 |

**涉及文件修改**:
- `app.py` — 新增 `import secrets, time`、`LOGIN_ATTEMPTS`、`check_login_rate_limit()`、`@app.after_request` 安全头
- `login.html` — 新增 `csrf_token` 隐藏字段
- `register.html` — 新增 `csrf_token` 隐藏字段
- `upload.html` — 新增 `csrf_token` 隐藏字段 + warning 提示
- `style.css` — 新增 `.warning-message` 样式

### 第三轮：个人中心/充值 Bug 修复

| # | Bug | 文件行号 | 修复方式 |
|---|-----|---------|---------|
| 1 | 充值路由无 CSRF 验证 | recharge 路由 | `if csrf_token != session.get("csrf_token")` |
| 2 | `amount=abc` 非数字崩溃 | recharge 路由 | `float(amount)` 转换 + try/except |
| 3 | 余额显示科学计数法 `¥99999.0` | profile.html | `"%.2f"|format(user.balance)` 格式化 |

---

## 四、故意保留的漏洞（未修复）

| 漏洞 | 位置 | 风险说明 | 利用难度 |
|------|------|---------|---------|
| **SQL 注入** | `search?keyword=` | f-string 拼接，`' OR 1=1 --` 可爆所有用户 | ⭐ 简单 |
| **SQL 注入** | `/register` | f-string 拼接，`hacker')--` 可闭合 INSERT | ⭐ 简单 |
| **SQL 注入** | `/profile?user_id=` | f-string 拼接，数字型注入 | ⭐ 简单 |
| **水平越权 IDOR** | `/profile?user_id=X` | 修改 URL 参数即可查看任意用户 | ⭐ 非常简单 |
| **充值负值** | `/recharge` | `amount=-99999` 减少余额 | ⭐ 非常简单 |
| **未授权访问** | `/profile` | 无需登录即可查看用户资料 | ⭐ 非常简单 |

---

## 五、新增/修改文件清单

| 文件 | 操作 | 行数 | 说明 |
|------|------|------|------|
| `app.py` | 修改 | 399 行 | 新增 upload/profile/recharge 路由 + 安全修复 |
| `templates/upload.html` | **新增** | 41 行 | 上传页面（文件选择 + 预览 + 错误提示） |
| `templates/profile.html` | **新增** | 57 行 | 个人中心 + 充值表单 |
| `templates/base.html` | 修改 | 30 行 | 导航栏添加「个人中心」「上传头像」链接 |
| `templates/index.html` | 修改 | 88 行 | 首页添加上传头像、个人中心快捷入口 |
| `templates/login.html` | 修改 | 24 行 | 新增 CSRF Token 隐藏字段 |
| `templates/register.html` | 修改 | 35 行 | 新增 CSRF Token 隐藏字段 |
| `static/css/style.css` | 修改 | 310+ 行 | 新增预览、提示框、警告样式 |
| `SECURITY_GUIDE.md` | **新增** | 592 行 | 安全测试与防御指南（含 Burp Suite 联动） |
| `SUMMARY.md` | 修改 | 146 行 | 更新项目总结报告 |
| `VULNERABILITY_REPORT.md` | 修改 | — | 更新漏洞报告 |

---

## 六、API 接口变更对比

```
昨日（7月9日）:
  GET/POST  /login
  GET/POST  /register
  GET       /search
  GET       /logout
  GET/POST  /upload        （新增 7月9日）

今日（7月10日）新增:
  GET       /profile       ← 新增
  POST      /recharge      ← 新增

今日安全优化:
  GET/POST  /login         ← 新增 CSRF Token + 频率限制
  GET/POST  /register      ← 新增 CSRF Token
  GET/POST  /upload        ← 新增 CSRF Token + XSS防护
  GET       /search        ← 新增未登录拦截
```

---

## 七、Git 提交记录（今日）

```
e97bbbd → 添加安全测试与防御指南 SECURITY_GUIDE.md
c29b49b → 更新项目总结报告 SUMMARY.md
ca53dc1 → 修复充值功能Bug: CSRF校验+金额格式验证
002f109 → 新增个人中心和充值功能
4967ae1 → 修复第二轮安全漏洞: XSS/CSRF/频率限制/响应头
7609933 → 新增头像上传功能 + 修复路径穿越等Bug
```

> **今日共 6 次提交**，从 `97659e0` 到 `e97bbbd`

---

*变更日期: 2026年7月10日*  
*项目地址: https://github.com/renegade-blast/web-homework77*
