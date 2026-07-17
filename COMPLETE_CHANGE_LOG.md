# 用户管理系统 — 全量变更日志

> **项目周期**: 2026年7月8日 — 2026年7月17日  
> **总提交数**: 33 次  
> **报告总数**: 17 份  
> **修复漏洞**: 30+ 项  

---

## 一、项目时间线总览

### 第一阶段：基础功能搭建（7月8日）

```
提交: 97659e0 → 7609933 → ae9dcd1
目标: 搭建 Flask 基础框架，实现核心 CRUD 功能
```

#### 1.1 登录功能（97659e0）

**实现**:
- Flask 基础框架，`/login`、`/logout`、`/` 路由
- USERS 内存字典（admin/alice）
- 密码明文存储 + `==` 比对
- Jinja2 模板继承体系

**缺陷记录**:
| 问题 | 严重度 | 说明 |
|------|--------|------|
| SQL 注入 | 🔴 | 搜索/注册使用 f-string 拼接 SQL |
| 密码明文 | 🔴 | USERS 字典中明文存储 |
| CSRF 无防护 | 🟡 | 所有表单无 Token |
| Secret Key 硬编码 | 🟡 | `"dev-key-2025"` |
| 路径遍历 | 🔴 | `/page?name=../app.py` 无校验 |
| 存储型 XSS | 🔴 | 上传 `.html` 可执行 JS |
| 越权 | 🟡 | 任意用户可访问 profile |
| 暴力破解 | 🟡 | 登录无频率限制 |

**文件**: `app.py`、`index.html`、`login.html`、`base.html`、`style.css`

#### 1.2 注册 + 搜索功能（97659e0）

**实现**: SQLite 数据库、`/register`、`/search` 路由、`register.html`

**缺陷**: 注册和搜索 SQL 使用 f-string 拼接，存在 SQL 注入

---

### 第二阶段：头像上传 + 第一轮安全修复（7月9日）

```
提交: 7609933
目标: 文件上传功能 + 基础漏洞修复
```

#### 2.1 上传功能

**实现**: `/upload` 路由、`upload.html`、`static/uploads/` 目录、16MB 限制

**修复**:
| 问题 | 修复方式 |
|------|---------|
| 路径穿越 | `os.path.basename()` 截断 |
| 同名覆盖 | `os.path.exists()` 检查 |
| 超长文件名 | 截断至 200 字符 |
| 保存异常 | try/except 捕获 |

---

### 第三阶段：第二轮安全修复 + 个人中心/充值（7月10日）

```
提交: 4967ae1 → 002f109 → ca53dc1 → c29b49b → e97bbbd → 696230c → 07cd2e4
目标: 安全加固 + 新增个人中心、充值功能
```

#### 3.1 全面安全加固（4967ae1）

| 修复项 | 技术方案 |
|--------|---------|
| 存储型 XSS | HTML 文件自动重命名为 `.txt` |
| CSRF 防护 | 所有 POST 表单添加 `csrf_token` 校验 |
| 登录频率限制 | 同一 IP 10秒内最多 5 次 |
| 安全响应头 | X-Frame-Options / X-Content-Type-Options / X-XSS-Protection / Referrer-Policy |
| CSRF Token 轮转 | 登录后重新生成 |

#### 3.2 个人中心 + 充值（002f109）

**实现**: `/profile`、`/recharge` 路由、`profile.html`、`balance` 字段

**故意保留漏洞**: IDOR 水平越权、负值充值、SQL 注入

#### 3.3 充值功能 Bug 修复（ca53dc1）

| Bug | 修复 |
|-----|------|
| 充值无 CSRF | 添加 Token 校验 |
| 非数字金额崩溃 | `float()` 转换 + 异常捕获 |
| 余额科学计数法 | `"%.2f"\|format()` |

---

### 第四阶段：动态页面加载 + 全面 SQL 注入修复（7月13日）

```
提交: 0039bf5 → 7b23115 → 6f2a6d2 → 5823d5d → e3b7ab8 → 913dbbf → aa945df → 7594e93 → 32acd10
目标: 动态页面 + 全面安全审计
```

#### 4.1 动态页面加载（0039bf5）

**实现**: `/page?name=help` 路由、`pages/help.html`

**故意保留漏洞**: 路径遍历（`../app.py` 可读任意文件）

#### 4.2 全面 SQL 注入修复（7b23115）

| 位置 | 修复前 | 修复后 |
|------|--------|--------|
| 搜索 | `f"...LIKE '%{keyword}%'"` | `LIKE ?` 参数化 |
| 注册 | `f"VALUES ('{username}')"` | `VALUES (?)` 参数化 |
| 个人中心 | `f"WHERE id = {user_id}"` | `WHERE id = ?` 参数化 |
| 充值 | `f"balance + {amount}"` | `balance + ?` 参数化 |

#### 4.3 负值充值禁止（6f2a6d2）

充值金额增加 `amount > 0` 校验。

#### 4.4 统一数据源 + 密码哈希（5823d5d）

| 变更 | 说明 |
|------|------|
| USERS 字典删除 | SQLite 成为唯一数据源 |
| 密码哈希 | scrypt 哈希存储 |
| 登录双验证 | 同时支持 USERS 字典和 SQLite |
| 注册错误保护 | 不泄露 SQL 细节 |
| Secret Key | 硬编码改为 `secrets.token_hex(32)` |

#### 4.5 代码评审改进（e3b7ab8）

| 改进项 | 说明 |
|--------|------|
| 首页路径遍历 | `/?page=../app.py` 添加白名单 |
| 登录校验 | profile/recharge 添加 session 检查 |
| 密码策略 | ≥6位 + 数字 + 字母 |
| 邮箱/手机验证 | 正则格式校验 |
| Session 超时 | 2小时配置 |
| requirements.txt | 新建依赖管理 |
| .env.example | 环境变量模板 |
| 帮助页密码 | 移除明文显示 |

#### 4.6 Bug 修复（913dbbf → aa945df → 7594e93）

| Bug | 修复 |
|-----|------|
| role 字段缺失 | 数据库添加 role 列 |
| 余额格式 | 统一 `¥` 前缀 + 2位小数 |
| 越权充值 | `row[1] != username` 校验 |
| profile 硬编码 | `/profile?user_id=1` 改为 `/profile` |
| 越权访问 profile | `row[1] != username` 拦截 |

---

### 第五阶段：密码修改功能 + 最终安全审计（7月14日）

```
提交: da322ca → c23d05f → 59bf4e3 → d9af85d → e7f122f → bed6698
目标: 密码修改 + 最终安全审计
```

#### 5.1 日志系统完善（da322ca）

`print()` 全部替换为 `logging` 模块（8 处）。

#### 5.2 密码修改功能（c23d05f → 59bf4e3）

**实现**: `/change-password` 路由、profile.html 修改密码表单

**首次实现缺陷**: 无 CSRF、可改任意用户、无确认密码、无强度校验

**修复**:
| 问题 | 修复 |
|------|------|
| 无 CSRF | 添加 `csrf_token` 校验 |
| 越权改密 | `target_user != username` 拦截 |
| 无确认密码 | 添加 `confirm_password` 对比 |
| 无强度校验 | ≥6位 + 数字 + 字母 |

#### 5.3 功能独立报告（bed6698）

新增 5 份功能报告 + 1 份索引：

```
REPORT_FEATURE_LOGIN.md
REPORT_FEATURE_REGISTER_SEARCH.md
REPORT_FEATURE_UPLOAD.md
REPORT_FEATURE_PROFILE_RECHARGE.md
REPORT_INDEX.md（总索引）
```

---

### 第六阶段：URL 抓取功能 + 安全修复（7月15日）

```
提交: e32f723 → c7462f1 → 4d979de → e87a55b → 9b56fad → d788959
目标: URL 抓取 + SSRF 防护
```

#### 6.1 URL 抓取功能（e32f723）

**实现**: `/fetch-url` 路由、首页表单、分块读取

**故意保留漏洞**: SSRF、file:// 协议、无限制 URL

#### 6.2 修复（c7462f1 → 4d979de → e87a55b）

| 问题 | 严重度 | 修复 |
|------|--------|------|
| 内存耗尽 | 🔴 | `resp.read()` 改为分块读取（5120 字节） |
| file:// 不显示 | 🟡 | 模板条件修复 |
| 日志注入 | 🟡 | URL 截断至 200 字符 |
| SSRF | 🔴 | `is_safe_url()` 协议白名单 + 内网黑名单 |
| file:// 协议 | 🔴 | 仅允许 http/https |

---

### 第七阶段：Ping 诊断功能 + 命令注入修复（7月16日）

```
提交: 86f9d0b → 93ae879
目标: Ping 功能 + 命令注入防护
```

#### 7.1 Ping 功能（86f9d0b）

**实现**: `/ping` 路由、`ping.html`、控制台风格 UI

**故意保留漏洞**: 命令注入（`shell=True` + f-string）

#### 7.2 命令注入修复（93ae879）

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| shell=True | 任意命令执行 | 参数列表方式 |
| 输入校验 | 无 | `is_valid_ping_target()` 白名单 |
| 特殊字符 | 不拦截 | `;` `|` `$` 全部拦截 |

---

### 第八阶段：XML 导入 + XXE 修复（7月17日）

```
提交: e13ae28 → e3245aa → 786d29a → 71bfe65
目标: XML 导入 + XXE 防护 + 架构优化
```

#### 8.1 XML 导入（e13ae28）

**实现**: `/xml-import` 路由、`xml_import.html`、XML 解析 JSON 输出

**故意保留漏洞**: XXE（实体读取任意文件）

#### 8.2 XXE 修复（e3245aa）

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 文件读取 | `open(filepath)` 读取任意文件 | 检测 DTD 直接拒绝 |
| 源码泄露 | `file:///app.py` 可读 | 拦截 |
| /etc/passwd 泄露 | 可读系统密码 | 拦截 |

#### 8.3 审计报告修复（786d29a）

| 修复项 | 问题 | 修复 |
|--------|------|------|
| XML CSRF | 无 Token 验证 | 添加 `csrf_token` |
| urllib.parse | 未导入导致 /fetch-url 瘫痪 | `import urllib.parse` |
| XSS risk | `\|safe` 过滤器 | 移除，help.html 改为纯文本 |
| Ping Windows | 固定 `-c` 参数不兼容 | `platform.system()` 切换 |
| help.html 过时 | "暂不支持修改密码" | 更新说明 |

#### 8.4 架构优化（71bfe65）

| 改进项 | 说明 |
|--------|------|
| login redirect | 成功后 `render_template` 改为 `redirect("/")` |
| 单元测试 | 新增 `test_app.py`，16 项全覆盖 |
| CSRF 轮转 | 登录后 `secrets.token_hex(16)` 轮转 |

---

## 二、漏洞修复统计

### 按类型统计

| 漏洞类型 | 发现数 | 已修复 | 说明 |
|---------|--------|--------|------|
| **SQL 注入** | 4 处 | ✅ 全部修复 | 参数化查询 `?` |
| **路径遍历** | 3 处 | ✅ 全部修复 | basename + 白名单 |
| **存储型 XSS** | 1 处 | ✅ 已修复 | .txt 重命名 |
| **CSRF 无防护** | 6 处 | ✅ 全部覆盖 | csrf_token 验证 |
| **水平越权** | 3 处 | ✅ 全部拦截 | row[1] != username |
| **命令注入** | 1 处 | ✅ 已修复 | shell=False + 白名单 |
| **XXE** | 1 处 | ✅ 已修复 | DTD 拒绝 |
| **SSRF** | 1 处 | ✅ 已修复 | 协议白名单 + 内网黑名单 |
| **暴力破解** | 1 处 | ✅ 已修复 | 10秒/5次限制 |
| **日志注入** | 1 处 | ✅ 已修复 | 截断至 200 字符 |
| **内存耗尽** | 1 处 | ✅ 已修复 | 分块读取 |
| **密码明文** | 1 处 | ✅ 已修复 | scrypt 哈希 |
| **Secret Key** | 1 处 | ✅ 已修复 | secrets.token_hex(32) |

### 按严重度统计

| 严重度 | 数量 | 占比 |
|--------|------|------|
| 🔴 高危 | 10 | 38% |
| 🟡 中危 | 12 | 46% |
| 🟢 低危 | 4 | 15% |
| **合计** | **26** | **100%** |

---

## 三、功能演进

```
初始（7月8日）
├── 登录 + 注册 + 搜索

第一轮迭代（7月9日）
├── + 头像上传
├── └── 路径穿越/XSS/Cookie 修复

第二轮迭代（7月10日）
├── + 个人中心 + 充值
├── └── CSRF/频率限制/安全头 修复

第三轮迭代（7月13日）
├── + 动态页面加载
├── └── 全面 SQL 注入修复 + USERS 字典移除

第四轮迭代（7月14日）
├── + 密码修改
├── └── 最终安全审计（26项）

第五轮迭代（7月15日）
├── + URL 抓取
├── └── SSRF 修复 + 内存安全

第六轮迭代（7月16日）
├── + Ping 诊断
├── └── 命令注入修复

第七轮迭代（7月17日）
├── + XML 导入
├── └── XXE 修复 + 单元测试
```

---

## 四、报告清单

| 文件名 | 大小 | 分类 | 说明 |
|--------|------|------|------|
| `SUMMARY.md` | 5.9K | 总结 | 项目完整总结 |
| `CHANGELOG_20260710.md` | 7.1K | 日志 | 7月10日单日变更 |
| `REPORT_INDEX.md` | 6.1K | 索引 | **全部报告导航** |
| `REPORT_FEATURE_LOGIN.md` | 1.4K | 功能 | 登录实现 |
| `REPORT_FEATURE_REGISTER_SEARCH.md` | 1.2K | 功能 | 注册+搜索实现 |
| `REPORT_FEATURE_UPLOAD.md` | 1.3K | 功能 | 上传实现 |
| `REPORT_FEATURE_PROFILE_RECHARGE.md` | 1.4K | 功能 | 个人中心+充值 |
| `REPORT_URL_FETCH_FEATURE.md` | 8.5K | 功能 | URL 抓取实现 |
| `REPORT_URL_FETCH_FIX_PROCESS.md` | 8.0K | 修复 | URL 抓取修复过程 |
| `VULNERABILITY_REPORT.md` | 7.2K | 安全 | SQL 注入历史分析 |
| `SECURITY_GUIDE.md` | 18K | 安全 | Burp Suite 联动测试 |
| `SECURITY_PAGE_LOADING.md` | 7.8K | 安全 | 路径遍历修复 |
| `SECURITY_PASSWORD_CHANGE.md` | 9.6K | 安全 | 改密安全分析 |
| `SECURITY_URL_FETCH_FIX.md` | 3.5K | 安全 | URL 抓取安全修复 |
| `SECURITY_PING_FIX.md` | 8.5K | 安全 | Ping 命令注入修复 |
| `SECURITY_XML_XXE_FIX.md` | 9.2K | 安全 | XXE 漏洞修复 |
| `SECURITY_AUDIT_FINAL.md` | 11K | 安全 | **最终安全审计（26项）** |
| `FEATURE_PROFILE_RECHARGE.md` | 9.2K | 功能 | 个人中心独立文档 |

---

## 五、代码演进

| 指标 | 初始版本 | 最终版本 | 变化 |
|------|---------|---------|------|
| 文件数 | 5 | 25+ | +20 |
| app.py 行数 | ~60 | 800+ | +740 |
| 路由数 | 3 | 12 | +9 |
| 模板数 | 3 | 7 | +4 |
| 安全报告数 | 0 | 12 | +12 |
| f-string SQL | 4 | 0 | -4 |
| CSRF 验证 | 0 | 6 | +6 |
| print() 日志 | 9 | 0 | -9 |

---

*报告生成日期: 2026年7月17日*  
*总提交数: 33 次 | 最后提交: 71bfe65*
