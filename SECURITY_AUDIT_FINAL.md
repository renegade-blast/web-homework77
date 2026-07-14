# 🔒 用户管理系统 — 安全审计最终报告

> **项目名称**: 用户信息管理平台  
> **审计日期**: 2026年7月14日  
> **代码版本**: `59bf4e3`（最新提交）  
> **仓库地址**: https://github.com/renegade-blast/web-homework77  

---

## 📋 报告目录

1. [审计范围](#1)
2. [漏洞修复清单](#2)
3. [功能回归测试结果](#3)
4. [攻击验证 POC](#4)
5. [项目安全状态总评](#5)

---

<h2 id="1">一、审计范围</h2>

本次审计覆盖项目全部 **7 个功能模块、8 个路由、所有模板及配置文件**，从以下维度进行安全评估：

| 维度 | 检查项 |
|------|--------|
| **注入攻击** | SQL 注入、路径遍历、XSS |
| **认证与授权** | 登录校验、水平越权、未授权访问 |
| **会话管理** | CSRF 防护、Session 安全、Token 轮转 |
| **输入验证** | 密码强度、邮箱/手机格式、金额边界 |
| **配置安全** | Secret Key、密码存储、日志、安全响应头 |

### 1.1 审计模块清单

| 模块 | 路由 | 审计重点 |
|------|------|---------|
| 登录 | `POST /login` | SQL注入、CSRF、频率限制 |
| 注册 | `POST /register` | SQL注入、密码强度、输入校验 |
| 搜索 | `GET /search` | SQL注入、权限控制 |
| 文件上传 | `POST /upload` | 路径穿越、存储型XSS |
| 个人中心 | `GET /profile` | 水平越权、未授权访问 |
| 充值 | `POST /recharge` | 越权操作、金额溢出 |
| 修改密码 | `POST /change-password` | CSRF、越权改密、原密码校验 |
| 动态页面 | `GET /page`、`/?page=` | 路径遍历、内容注入 |

---

<h2 id="2">二、漏洞修复清单</h2>

### 2.1 🔴 高危漏洞

| 序号 | 漏洞类型 | 位置 | 严重程度 | 修复方式 |
|------|---------|------|---------|---------|
| 1 | SQL 注入 | 搜索 `LIKE '%{keyword}%'` | 🔴 高 | 参数化查询 `?` 占位符 |
| 2 | SQL 注入 | 注册 `VALUES ('{username}')` | 🔴 高 | 参数化查询 `?` 占位符 |
| 3 | SQL 注入 | 个人中心 `WHERE id = {uid}` | 🔴 高 | 参数化查询 `?` 占位符 |
| 4 | SQL 注入 | 充值 `balance + {amount}` | 🔴 高 | 参数化查询 `?` 占位符 |
| 5 | 路径遍历 + 任意文件读取 | `/page?name=../app.py` | 🔴 高 | 正则白名单 `^[a-zA-Z0-9_\-]+$` |
| 6 | 路径遍历 + 任意文件读取 | `/?page=../app.py` | 🔴 高 | 正则白名单 `^[a-zA-Z0-9_\-]+$` |
| 7 | 存储型 XSS | 上传 `evil.html` | 🔴 高 | HTML 文件自动重命名为 `.txt` |

### 2.2 🟡 中危漏洞

| 序号 | 漏洞类型 | 位置 | 严重程度 | 修复方式 |
|------|---------|------|---------|---------|
| 8 | 水平越权 IDOR | `/profile?user_id=X` | 🟡 中 | `row[1] != username` 拦截 |
| 9 | 越权充值 | `/recharge user_id=2` | 🟡 中 | `row[1] != username` 拦截 |
| 10 | 越权改密 | `/change-password username=alice` | 🟡 中 | `target_user != username` 拦截 |
| 11 | 未授权访问 | profile/recharge/改密 | 🟡 中 | 添加 `session.get("username")` 校验 |
| 12 | 登录暴力破解 | 登录接口 | 🟡 中 | 同一 IP 10 秒内最多 5 次 |
| 13 | CSRF 无防护 | 登录/注册/上传/充值/改密 | 🟡 中 | 全部添加 `csrf_token` 验证 |
| 14 | 弱密码策略 | 注册/改密 | 🟡 中 | ≥6位 + 包含数字 + 包含字母 |

### 2.3 🟢 低危加固项

| 序号 | 加固项 | 修复前 | 修复后 |
|------|--------|--------|--------|
| 15 | Secret Key | 硬编码 `"dev-key-2025"` | `secrets.token_hex(32)` |
| 16 | 密码存储 | SQLite 明文 | scrypt 哈希 |
| 17 | CSRF Token 轮转 | 永不轮转 | 登录后轮转 |
| 18 | Session 超时 | 永久有效 | 2小时配置 |
| 19 | 安全响应头 | 无 | X-Frame-Options / X-Content-Type-Options / X-XSS-Protection / Referrer-Policy |
| 20 | 日志系统 | `print()` 输出 | `logging` 模块（含时间/级别） |
| 21 | 邮箱格式校验 | 无 | 正则 `^[^@]+@[^@]+\.[^@]+$` |
| 22 | 手机号格式校验 | 无 | 正则 `^1[3-9]\d{9}$` |
| 23 | 充值金额上限 | 无限制 | 单次 ≤ 99999999 |
| 24 | 用户 ID 范围 | 无限制 | 1 ≤ uid ≤ 1000000 |
| 25 | 文件上传大小 | 无限制 | `MAX_CONTENT_LENGTH=16MB` |
| 26 | 同名文件覆盖 | 无声覆盖 | `os.path.exists()` 检查并提示 |

> **修复统计**: 共 **26 项**安全修复，其中 🔴 高危 7 项、🟡 中危 7 项、🟢 低危 12 项

---

<h2 id="3">三、功能回归测试结果</h2>

### 3.1 全量 14 项测试

```
序号  测试项                        预期结果    实际结果    状态
─────────────────────────────────────────────────────────────────
 1    admin 登录                   成功       返回首页    ✅ 通过
 2    SQL 注入 (OR 1=1)            无结果     无搜索结    ✅ 拦截
 3    路径遍历 (../app.py)         拦截       非法字符    ✅ 拦截
 4    未登录访问 /profile           302 跳转   302 跳转   ✅ 通过
 5    越权查看 alice 资料           302 跳转   302 跳转   ✅ 通过
 6    越权给 alice 充值             拦截       余额不变   ✅ 拦截
 7    越权修改 alice 密码           拦截       原密码可用 ✅ 拦截
 8    修改密码（正常流程）          成功       新密码登录 ✅ 通过
 9    修改密码（无 CSRF Token）     拒绝       302 跳转   ✅ 通过
10    修改密码（两次密码不一致）     拒绝       原密码可用 ✅ 拦截
11    修改密码（弱密码 123）        拒绝       原密码可用 ✅ 拦截
12    alice 登录（原密码验证）      成功       欢迎回来   ✅ 通过
13    密码哈希存储                  全部哈希   scrypt     ✅ 通过
14    登出后访问 /profile           302 跳转   302 跳转   ✅ 通过
```

### 3.2 密码修改功能专项测试

```
完整流程: admin 登录 → 获取 CSRF → 修改密码 → 新密码登录

  ➜ 有 CSRF Token:         ✅ 修改成功，新密码可登录
  ➜ 无 CSRF Token:         ✅ 拒绝（302 跳转）
  ➜ 修改 alice 密码:        ✅ 拒绝（alice 原密码仍可用）
  ➜ 两次密码不一致:         ✅ 拒绝（原密码可用）
  ➜ 弱密码 "123":          ✅ 拒绝（原密码可用）
  ➜ 密码强度 "abcdef"      ✅ 拒绝（缺少数字）
  ➜ 密码强度 "123456"      ✅ 拒绝（缺少字母）
```

---

<h2 id="4">四、攻击验证 POC</h2>

### 4.1 SQL 注入拦截

```bash
# 攻击 payload
curl -b "session=X" "http://localhost:5000/search?keyword=%27%20OR%201%3D1%20--"

# 构造的恶意 SQL（修复前）
SELECT * FROM users WHERE username LIKE '%' OR 1=1 --%'

# 实际的参数化查询（修复后）
SELECT ... FROM users WHERE username LIKE ?  -- 参数: %' OR 1=1 --%

# 结果: 无搜索结果 ✅（注入被参数化查询拦截）
```

### 4.2 路径遍历拦截

```bash
# 攻击 payload
curl "http://localhost:5000/page?name=../app.py"

# 修复前: 返回 app.py 全部源码（约 500 行）
# 修复后:

# 结果: 页面名称包含非法字符 ✅
```

### 4.3 越权充值拦截

```bash
# 攻击流程: admin 给 alice 充值 99999 元
csrf=$(curl -b "session=admin" "http://localhost:5000/profile" | \
  grep -oP 'csrf_token" value="\K[^"]+')
curl -b "session=admin" -X POST "http://localhost:5000/recharge" \
  -d "user_id=2&amount=99999&csrf_token=$csrf"

# 结果: alice 余额仍为 100.0（未被修改）✅
```

### 4.4 越权改密拦截

```bash
# 攻击流程: admin 把 alice 的密码改成 Hacked123
csrf=$(curl -b "session=admin" "http://localhost:5000/profile" | \
  grep -oP 'csrf_token" value="\K[^"]+')
curl -b "session=admin" -X POST "http://localhost:5000/change-password" \
  -d "username=alice&new_password=Hacked123&confirm_password=Hacked123&csrf_token=$csrf"

# 尝试用 alice 原密码登录
curl -X POST "http://localhost:5000/login" \
  -d "username=alice&password=alice2025"

# 结果: alice 原密码仍可登录 ✅（越权改密被拦截）
```

---

<h2 id="5">五、项目安全状态总评</h2>

### 5.1 安全评分

| 评定维度 | 状态 | 评分 | 备注 |
|---------|------|------|------|
| **功能完整性** | ✅ 全部实现 | ⭐⭐⭐⭐⭐ | 7 个功能模块全部完成 |
| **SQL 注入防护** | ✅ 全部修复 | ⭐⭐⭐⭐⭐ | 0 处 f-string SQL 残留 |
| **CSRF 防护** | ✅ 全部覆盖 | ⭐⭐⭐⭐⭐ | 5 个 POST 路由均有 Token 验证 |
| **路径遍历防护** | ✅ 全部修复 | ⭐⭐⭐⭐⭐ | `/page` 和 `/?page=` 双白名单 |
| **XSS 防护** | ✅ 已修复 | ⭐⭐⭐⭐ | HTML 上传→.txt + 安全响应头 |
| **越权防护** | ✅ 已拦截 | ⭐⭐⭐⭐⭐ | profile/recharge/改密三层校验 |
| **密码安全** | ✅ 已加固 | ⭐⭐⭐⭐⭐ | scrypt 哈希 + 强度策略 |
| **会话安全** | ✅ 已加固 | ⭐⭐⭐⭐ | HttpOnly + SameSite + 2h 超时 + Token轮转 |
| **输入校验** | ✅ 已完善 | ⭐⭐⭐⭐ | 邮箱/手机/金额/ID/关键词 边界检查 |
| **认证覆盖** | ✅ 全部路由 | ⭐⭐⭐⭐⭐ | 所有敏感路由有登录校验 |
| **日志系统** | ✅ 已迁移 | ⭐⭐⭐ | `print()` → `logging` 完成 |
| **项目工程化** | 🟡 基础 | ⭐⭐⭐ | 有 requirements.txt、.env.example、.gitignore |

### 5.2 已消灭的漏洞清单

```
❌ SQL 注入（4 处）        → ✅ 参数化查询
❌ 路径遍历（2 处）        → ✅ 正则白名单
❌ 存储型 XSS（1 处）      → ✅ .txt 重命名
❌ CSRF 无防护（5 处）     → ✅ csrf_token 全覆盖
❌ 水平越权（3 处）        → ✅ 身份校验拦截
❌ 未授权访问（3 处）      → ✅ session 校验
❌ 暴力破解（1 处）        → ✅ 速率限制
❌ 密码明文存储（1 处）    → ✅ scrypt 哈希
❌ Secret Key 硬编码（1处）→ ✅ 随机生成
❌ 日志泄露（9 处 print）  → ✅ logging 模块
```

### 5.3 最终结论

```
  🔒 安全状态: ✅ 全部漏洞已修复
  📊 修复总数: 26 项（高危 7 + 中危 7 + 低危 12）
  🧪 测试总数: 14 项，通过率 100%
  🔑 密码存储: scrypt 哈希
  🚫 f-string SQL: 0 处残留
  📝 日志系统: logging 模块
  ⏰ 审计日期: 2026-07-14
```

---

*本报告由自动化安全测试工具生成，所有测试结果可复现*  
*报告文件: `SECURITY_AUDIT_FINAL.md` | 仓库: https://github.com/renegade-blast/web-homework77*
