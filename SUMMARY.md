# 用户管理系统 — 项目开发总结报告

> **日期**: 2026年7月10日  
> **项目**: 用户信息管理平台  
> **技术栈**: Python Flask + SQLite + HTML/CSS  
> **GitHub**: https://github.com/renegade-blast/web-homework77

---

## 一、今日开发内容总览

今日在原有登录、注册、搜索功能基础上，完成了 **头像上传**、**个人中心**、**充值功能** 的开发，并进行了两轮安全审计与漏洞修复。

| 时间段 | 工作内容 | 涉及文件 |
|--------|---------|---------|
| 上午 | 新增头像上传功能 + Bug修复 | `app.py`, `upload.html`, `style.css` |
| 下午 | 安全审计第一轮（SQL注入/路径穿越等） | `app.py`, `VULNERABILITY_REPORT.md` |
| 下午 | 新增个人中心 + 充值功能 | `app.py`, `profile.html` |
| 下午 | 安全审计第二轮（XSS/CSRF/频率限制） | `app.py`, 所有模板文件 |
| 下午 | 推送 GitHub | 全部文件 |

---

## 二、功能模块完成情况

### ✅ 已完成功能（共 7 项）

| # | 功能 | 路由 | 说明 |
|---|------|------|------|
| 1 | **用户登录** | `GET/POST /login` | USERS 字典验证，密码哈希比对，session 存储 |
| 2 | **用户注册** | `GET/POST /register` | SQLite 入库，f-string 拼接 SQL |
| 3 | **用户搜索** | `GET /search` | 模糊搜索用户名/邮箱，表格展示结果 |
| 4 | **头像上传** | `GET/POST /upload` | 保存到 `static/uploads/`，原始文件名，图片预览 |
| 5 | **个人中心** | `GET /profile?user_id=X` | 查看任意用户资料（ID/用户名/邮箱/手机/余额） |
| 6 | **充值** | `POST /recharge` | 修改余额（金额可正可负） |
| 7 | **退出登录** | `GET /logout` | 清除 session |

### 📄 页面模板（共 6 个）

| 模板 | 说明 |
|------|------|
| `base.html` | 基础模板，导航栏（个人中心/上传头像/退出/注册/登录） |
| `index.html` | 首页（用户信息 + 搜索框 + 结果表格） |
| `login.html` | 登录表单 |
| `register.html` | 注册表单 |
| `upload.html` | 文件上传 + 预览 |
| `profile.html` | 个人中心 + 充值表单 |

---

## 三、安全审计记录

### 第一轮：发现并修复 6 个漏洞

| # | 漏洞 | 修复方式 |
|---|------|---------|
| 1 | 路径穿越（上传 `../../evil.txt`） | `os.path.basename()` 截断 |
| 2 | 同名文件静默覆盖 | `os.path.exists()` 检查 |
| 3 | 超长文件名崩溃 | 截断至 200 字符 + try/except |
| 4 | 文件保存失败无处理 | try/except 捕获异常 |
| 5 | 注册空用户名/密码 | 非空校验 |
| 6 | 未登录搜索仍执行 SQL | 增加登录拦截 |

### 第二轮：发现并修复 5 个漏洞

| # | 漏洞 | 修复方式 |
|---|------|---------|
| 1 | **存储型 XSS**（上传 `.html` 含 JS） | 自动重命名为 `.txt` |
| 2 | **CSRF 跨站请求伪造**（所有表单无 Token） | 添加 `csrf_token` 验证 |
| 3 | **登录暴力破解**（无频率限制） | 同一 IP 10秒/5次限制 |
| 4 | **缺少安全响应头** | `X-Frame-Options` / `X-Content-Type-Options` 等 |
| 5 | **CSRF Token 每次刷新** | `if not in session` 条件生成 |

### 第三轮：个人中心/充值 Bug 修复

| # | Bug | 修复方式 |
|---|-----|---------|
| 1 | 充值路由无 CSRF 验证 | 添加 Token 校验 |
| 2 | 非数字金额 `amount=abc` 崩溃 | `float()` 转换 + 异常捕获 |
| 3 | 余额显示科学计数法 | `"%.2f"|format()` 格式化 |

### 已修复的安全漏洞（迭代历史）

| 漏洞 | 修复版本 | 修复方式 |
|------|---------|---------|
| **SQL 注入** ✅ | v2 | 全部 f-string 改为参数化查询 `?` |
| **水平越权 IDOR** ✅ | v3 | profile 路由添加 `row[1] != username` 校验 |
| **充值负值** ✅ | v3 | `amount <= 0` 正数校验 |
| **未授权访问** ✅ | v3 | profile/recharge 添加登录拦截 |
| **路径遍历** ✅ | v2 | 正则白名单 `^[a-zA-Z0-9_\-]+$` |
| **存储型 XSS** ✅ | v2 | HTML 上传自动重命名为 `.txt` |
| **CSRF 无防护** ✅ | v2 | 所有 POST 表单添加 Token 验证 |
| **登录暴力破解** ✅ | v2 | 同一 IP 10 秒内最多 5 次 |

---

## 四、项目文件结构

```
/workspace/user-management/
├── app.py                          # Flask 主应用
├── data/users.db                   # SQLite 数据库（自动生成）
├── static/
│   ├── css/style.css               # 样式文件
│   └── uploads/                    # 上传文件目录
├── templates/
│   ├── base.html                   # 基础模板（导航栏）
│   ├── index.html                  # 首页
│   ├── login.html                  # 登录页
│   ├── register.html               # 注册页
│   ├── upload.html                 # 上传页
│   └── profile.html                # 个人中心
├── VULNERABILITY_REPORT.md         # SQL 注入漏洞分析报告
├── SUMMARY.md                      # 项目总结报告
└── .gitignore
```

---

## 五、API 接口汇总

| 路由 | 方法 | 功能 | 需登录 | 注入风险 |
|------|------|------|--------|---------|
| `/` | GET | 首页 + 搜索 | 部分 | ✅ |
| `/login` | GET/POST | 登录 | 否 | ❌ |
| `/register` | GET/POST | 注册 | 否 | ✅ |
| `/search` | GET | 搜索用户 | 是 | ✅ |
| `/upload` | GET/POST | 上传头像 | 是 | ❌ |
| `/profile` | GET | 个人中心 | 否 | ✅ |
| `/recharge` | POST | 充值 | 否 | ✅ |
| `/logout` | GET | 退出 | 是 | ❌ |

---

## 六、Git 提交记录

```
ca53dc1 → 修复充值功能Bug: CSRF校验+金额格式验证
002f109 → 新增个人中心和充值功能
4967ae1 → 修复第二轮安全漏洞: XSS/CSRF/频率限制/响应头
ae9dcd1 → 添加项目总结报告 SUMMARY.md
7609933 → 新增头像上传功能 + 修复路径穿越等Bug
97659e0 → 用户管理系统 - 登录/注册/搜索功能
```

---

*项目地址: https://github.com/renegade-blast/web-homework77*  
*完成日期: 2026年7月10日*
