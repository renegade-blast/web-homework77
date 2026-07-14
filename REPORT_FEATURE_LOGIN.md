# 登录功能 — 独立实现报告

> **对应需求**: 新建全新的文件夹，生成简易用户信息管理平台的登录功能
> **实现提交**: `97659e0`
> **实现日期**: 2026年7月8日

---

## 一、需求概述

使用 Python Flask 框架，实现一个简易用户信息管理平台的登录功能，包含用户数据存储、登录验证、会话管理、页面模板和样式。

## 二、实现内容

### 2.1 后端路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首页，从 session 获取当前用户信息 |
| `/login` | GET/POST | 登录表单 + 验证 |
| `/logout` | GET | 清除 session 并跳转 |

### 2.2 用户数据

```python
USERS = {
    "admin": {"username": "admin", "password": "admin123", ...},
    "alice": {"username": "alice", "password": "alice2025", ...}
}
```

### 2.3 页面模板

| 文件 | 说明 |
|------|------|
| `base.html` | 基础模板，导航栏 |
| `index.html` | 首页，显示用户信息 |
| `login.html` | 登录表单 |

## 三、涉及文件

```
app.py                  # Flask 主应用
templates/base.html     # 基础模板
templates/index.html    # 首页
templates/login.html    # 登录页
static/css/style.css    # 样式
```

## 四、初始安全状态

- 密码明文存储和比对
- 密码传递到模板并显示在页面上
- 登录页 HTML 注释泄露默认账号
- Secret Key 硬编码 `"dev-key-2025"`
