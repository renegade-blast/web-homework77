# 用户管理系统 — 项目总结报告

> **课程**: Web 安全与开发  
> **项目名称**: 用户信息管理平台  
> **技术栈**: Python Flask + SQLite + HTML/CSS  
> **GitHub**: https://github.com/renegade-blast/web-homework77

---

## 一、项目概述

本系统是一个基于 Python Flask 框架开发的简易用户信息管理平台，实现了用户注册、登录、信息展示、搜索、头像上传等核心功能。项目采用前端 HTML/CSS + 后端 Flask 的架构模式，数据存储使用 SQLite 数据库。

---

## 二、功能模块

### 1. 用户登录 (`/login`)
- 支持 GET（显示表单）和 POST（提交验证）
- 使用预置的 `USERS` 字典存储用户数据
- 密码使用 `werkzeug.security` 进行哈希比对
- 登录成功后用户信息存入 session
- 默认账号：
  - `admin / admin123`（管理员，余额 99999）
  - `alice / alice2025`（普通用户，余额 100）

### 2. 用户注册 (`/register`)
- 支持 GET（显示表单）和 POST（提交注册）
- 注册信息写入 SQLite 数据库 `data/users.db`
- 启动时自动调用 `init_db()` 初始化数据库
- 数据库字段：id、username（唯一）、password、email、phone
- 使用 `INSERT OR IGNORE` 防止重复插入默认用户

### 3. 用户搜索 (`/search`)
- 通过 URL 参数 `?keyword=xxx` 搜索用户
- 支持按用户名和邮箱模糊搜索
- 搜索结果以表格形式展示（ID、用户名、邮箱、手机）
- 必须登录后才能搜索

### 4. 头像上传 (`/upload`)
- 支持 GET（显示表单）和 POST（上传文件）
- 文件保存到 `static/uploads/` 目录
- 保留原始文件名（不重命名）
- 上传后显示图片预览和访问 URL
- 限制最大 16MB
- 路径穿越防护（`os.path.basename`）
- 同名文件检测（禁止覆盖）

### 5. 退出登录 (`/logout`)
- 清除 session 数据后重定向到首页

---

## 三、页面模板

| 模板文件 | 说明 |
|----------|------|
| `base.html` | 基础模板，导航栏（品牌名 + 登录/注册/上传/退出链接） |
| `index.html` | 首页（用户信息展示 + 搜索框 + 结果表格） |
| `login.html` | 登录表单 |
| `register.html` | 注册表单 |
| `upload.html` | 文件上传 + 预览 |

所有页面统一风格：蓝色渐变导航栏、卡片式布局、圆角阴影设计。

---

## 四、项目文件结构

```
/workspace/user-management/
├── app.py                      # Flask 主应用（199 行）
├── data/users.db               # SQLite 数据库（自动生成）
├── static/
│   ├── css/style.css           # 样式文件
│   └── uploads/                # 上传文件目录
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页
│   ├── login.html              # 登录页
│   ├── register.html           # 注册页
│   └── upload.html             # 上传页
├── VULNERABILITY_REPORT.md     # SQL 注入漏洞分析报告
└── .gitignore
```

---

## 五、运行方式

```bash
# 安装依赖
pip install flask werkzeug

# 启动应用
cd /workspace/user-management
python app.py

# 访问 http://localhost:5000
```

---

## 六、安全漏洞分析（作业重点）

### 存在漏洞

本项目中**故意保留了 SQL 注入漏洞**用于教学演示。具体位于：

**注入点 1 — 搜索功能（第 92/186 行）**
```python
sql = f"SELECT ... WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
```

**注入点 2 — 注册功能（第 155 行）**
```python
sql = f"INSERT INTO users VALUES ('{username}', '{password}', '{email}', '{phone}')"
```

### 攻击演示

```bash
# OR 永真注入 → 爆全部用户
keyword=' OR 1=1 --

# UNION 注入 → 窃取密码
keyword=' UNION SELECT 1,group_concat(username||':'||password),3,4 FROM users --

# INSERT 注入 → 注册任意数据
username=hacker')--
```

### 修复方案

使用参数化查询（`?` 占位符）替代 f-string 拼接：
```python
# ✅ 安全写法
sql = "SELECT * FROM users WHERE username LIKE ?"
c.execute(sql, (f"%{keyword}%",))
```

详细漏洞分析见 `VULNERABILITY_REPORT.md`。

---

## 七、已修复的 Bug

| Bug | 说明 | 修复方式 |
|-----|------|---------|
| 路径穿越 | 文件名含 `../` 逃逸 uploads 目录 | `os.path.basename()` 截断路径 |
| 超长文件名 | 500 字符文件名导致崩溃 | 截断至 200 字符 + try/except |
| 同名覆盖 | 上传同名文件无声覆盖 | `os.path.exists()` 检查并提示 |
| 保存失败 | 磁盘满/权限错误抛 500 | try/except 捕获异常 |

---

## 八、API 接口汇总

| 路由 | 方法 | 功能 | 需要登录 |
|------|------|------|---------|
| `/` | GET | 首页（用户信息 + 搜索） | 部分功能需要 |
| `/login` | GET/POST | 用户登录 | 否 |
| `/register` | GET/POST | 用户注册 | 否 |
| `/search` | GET | 搜索用户 | 是 |
| `/upload` | GET/POST | 上传头像 | 是 |
| `/logout` | GET | 退出登录 | 是 |

---

*项目日期: 2026年7月*  
*提交于: https://github.com/renegade-blast/web-homework77*
