# 安全审计最终报告

> **项目**: 用户信息管理平台  
> **审计日期**: 2026-07-14  
> **代码版本**: `c23d05f` + `da322ca`  
> **仓库**: https://github.com/renegade-blast/web-homework77  

---

## 一、审计范围

全量代码审计，覆盖 7 个功能模块、8 个路由、所有模板文件和配置文件。

| 模块 | 路由 | 审计项 |
|------|------|--------|
| 登录 | `POST /login` | SQL注入、CSRF、频率限制、认证绕过 |
| 注册 | `POST /register` | SQL注入、密码强度、输入校验 |
| 搜索 | `GET /search` | SQL注入、权限控制 |
| 上传 | `POST /upload` | 路径穿越、XSS、文件类型 |
| 个人中心 | `GET /profile` | 水平越权、未授权访问 |
| 充值 | `POST /recharge` | 越权操作、金额校验 |
| 修改密码 | `POST /change-password` | CSRF、越权、原密码校验 |
| 动态页面 | `GET /page`、`/?page=` | 路径遍历、XSS |

---

## 二、已修复漏洞清单

### 2.1 SQL 注入（4 处）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| 搜索 `LIKE '%{keyword}%'` | f-string 拼接 | `LIKE ?` 参数化查询 |
| 注册 `VALUES ('{username}')` | f-string 拼接 | `VALUES (?)` 参数化查询 |
| 个人中心 `WHERE id = {uid}` | f-string 拼接 | `WHERE id = ?` 参数化查询 |
| 充值 `balance + {amount}` | f-string 拼接 | `balance + ?` 参数化查询 |

### 2.2 路径遍历（2 处）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| `/page?name=../app.py` | 无校验 | 白名单 `^[a-zA-Z0-9_\-]+$` |
| `/?page=../app.py` | 无校验 | 同上白名单 |

### 2.3 存储型 XSS（1 处）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| 上传 `evil.html` | 保存原始文件 | 自动重命名为 `.txt` |

### 2.4 CSRF 防护（5 处）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| 登录表单 | 无 Token | `csrf_token` 隐藏字段 |
| 注册表单 | 无 Token | `csrf_token` 隐藏字段 |
| 上传表单 | 无 Token | `csrf_token` 隐藏字段 |
| 充值表单 | 无 Token | `csrf_token` 隐藏字段 |
| 修改密码 | 无 Token | `csrf_token` 隐藏字段 |

### 2.5 权限控制（4 处）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| 个人中心越权 | 可看任意用户 | `row[1] != username` 拦截 |
| 充值越权 | 可充任意用户 | `row[1] != username` 拦截 |
| 改密越权 | 可改任意用户 | `target_user != username` 拦截 |
| 未授权访问 | 无需登录 | 全部添加 `session.get("username")` 检查 |

### 2.6 输入验证（6 项）

| 校验项 | 位置 | 规则 |
|--------|------|------|
| 密码强度 | 注册/改密 | ≥6位 + 数字 + 字母 |
| 邮箱格式 | 注册 | `^[^@]+@[^@]+\.[^@]+$` |
| 手机格式 | 注册 | `^1[3-9]\d{9}$` |
| 充值金额 | 充值 | `> 0` 且 `≤ 99999999` |
| 用户 ID | 个人中心 | `1 ≤ uid ≤ 1000000` |
| 页面名称 | `/page` | 白名单 `^[a-zA-Z0-9_\-]+$` |

### 2.7 其他安全加固

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| Secret Key | 硬编码 `"dev-key-2025"` | `secrets.token_hex(32)` |
| 密码存储 | 明文 | scrypt 哈希 |
| 日志 | `print()` → 控制台 | `logging` 模块 |
| Session 超时 | 永久有效 | 2小时 |
| 安全响应头 | 无 | X-Frame-Options / X-Content-Type-Options / X-XSS-Protection / Referrer-Policy |
| CSRF Token 轮转 | 永不 | 登录后轮转 |

---

## 三、最终测试结果

```
测试项                          状态
─────────────────────────────────────────────
admin 登录                      ✅ 通过
SQL 注入（OR 1=1）              ✅ 拦截
路径遍历（../app.py）            ✅ 拦截
未登录访问 profile              ✅ 302 跳转登录页
越权查看 profile                 ✅ 302 跳转
越权充值                         ✅ 拦截（alice 余额不变）
越权修改密码                     ✅ 拦截（alice 原密码可用）
修改密码（完整 CSRF 验证）       ✅ 成功
新密码登录                       ✅ 成功
密码不一致                       ✅ 拦截（原密码可用）
弱密码拒绝                       ✅ 拦截（原密码可用）
密码全部哈希存储                 ✅ scrypt
```

### 3.1 密码修改功能专项测试

```
admin 登录 → 获取 CSRF → 修改密码 → 新密码登录
  → 有CSRF Token:  ✅ 成功
  → 无CSRF Token:  ✅ 拒绝（302）
  → 修改他人密码:  ✅ 拒绝（alice 原密码仍可用）
  → 两次密码不一致:  ✅ 拒绝
  → 弱密码(123):    ✅ 拒绝
  → 密码强度校验:   ✅ 执行（≥6位+数字+字母）
```

---

## 四、攻击测试验证

### 4.1 SQL 注入

```bash
# 搜索注入（应返回无结果）
curl -b "session=X" "http://localhost:5000/search?keyword=%27%20OR%201%3D1%20--"
# 结果: 无搜索结果（注入被参数化查询拦截）✅
```

### 4.2 路径遍历

```bash
# 页面遍历（应返回非法字符）
curl "http://localhost:5000/page?name=../app.py"
# 结果: 页面名称包含非法字符 ✅
```

### 4.3 越权充值

```bash
# admin 给 alice 充值（应被拦截）
csrf=$(curl -b "session=X" "http://localhost:5000/profile" | grep -oP 'csrf_token" value="\K[^"]+')
curl -b "session=X" -X POST "http://localhost:5000/recharge" -d "user_id=2&amount=999&csrf_token=$csrf"
# 结果: alice 余额不变（100.0）✅
```

### 4.4 越权改密

```bash
# admin 修改 alice 密码（应被拦截）
csrf=$(curl -b "session=X" "http://localhost:5000/profile" | grep -oP 'csrf_token" value="\K[^"]+')
curl -b "session=X" -X POST "http://localhost:5000/change-password" \
  -d "username=alice&new_password=Hacked123&confirm_password=Hacked123&csrf_token=$csrf"
# 结果: alice 原密码 alice2025 仍可登录 ✅
```

---

## 五、最终项目状态

| 维度 | 状态 | 说明 |
|------|------|------|
| 功能完整性 | ✅ 7/7 | 登录/注册/搜索/上传/个人中心/充值/改密 |
| SQL 注入 | ✅ 全部修复 | 0 处 f-string SQL 残留 |
| CSRF 防护 | ✅ 全部覆盖 | 5 个 POST 路由均有 Token 验证 |
| 路径遍历 | ✅ 全部修复 | 白名单正则 + 上传 basename |
| XSS | ✅ 已修复 | HTML 上传→.txt + 安全头 |
| 越权 | ✅ 已拦截 | profile/recharge/change-password |
| 密码安全 | ✅ 哈希+强度 | scrypt + ≥6位+数字+字母 |
| 会话安全 | ✅ 已加固 | HttpOnly + SameSite + 2小时超时 |
| 日志 | ✅ 已完善 | print→logging 迁移完成 |
| 认证 | ✅ 已覆盖 | 所有敏感路由有登录校验 |

---

*最终安全审计报告 — 2026年7月14日*
