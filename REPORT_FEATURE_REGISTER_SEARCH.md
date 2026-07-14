# 注册 + 搜索功能 — 独立实现报告

> **对应需求**: 在登录功能基础上增加用户注册和搜索功能
> **实现提交**: `002f109`
> **实现日期**: 2026年7月8日

---

## 一、需求概述

在已有的登录功能基础上，新增用户注册和用户搜索功能，保持原有登录功能不变。

## 二、新增内容

### 2.1 后端路由

| 路由 | 方法 | 功能 |
|------|------|------|
| `/register` | GET/POST | 注册表单 + SQLite 入库 |
| `/search` | GET | 用户名/邮箱模糊搜索 |

### 2.2 数据库

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    phone TEXT
);
```

### 2.3 页面模板

| 文件 | 说明 |
|------|------|
| `register.html` | 注册表单 |
| `index.html` | 新增搜索框和结果表格 |

## 三、安全缺陷

- SQL 注入：使用 f-string 拼接 SQL 语句
- 注册 SQL: `f"INSERT INTO users VALUES ('{username}', '{password}', '{email}', '{phone}')"`
- 搜索 SQL: `f"SELECT ... WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"`
