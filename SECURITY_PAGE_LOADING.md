# 动态页面加载功能 — 安全分析报告

> **功能**: `/page?name=XXX` 动态加载 `pages/` 目录下的 HTML 文件  
> **漏洞类型**: 路径遍历 (Path Traversal)  
> **风险等级**: 🔴 严重  
> **报告日期**: 2026-07-13

---

## 一、功能概述

动态页面加载功能允许用户通过 URL 参数加载服务端文件：

```python
# 路由定义
@app.route("/page")
def page():
    name = request.args.get("name", "")    # 用户可控输入
    page_path = os.path.join(app.root_path, "pages", name)
    if os.path.exists(page_path):
        with open(page_path, "r") as f:
            page_content = f.read()
    return render_template("index.html", page_content=page_content)
```

原本设计目的是加载 `pages/help.html` 等静态页面，但由于 `name` 参数直接拼接到文件路径中，且**缺少任何合法性校验**，导致路径遍历漏洞。

---

## 二、漏洞分析

### 2.1 攻击向量

攻击者通过在 `name` 参数中插入 `../` 序列，可以突破 `pages/` 目录限制，读取服务器上的任意文件：

```bash
# 正常请求
GET /page?name=help             → 读取 pages/help.html

# 路径遍历攻击
GET /page?name=../app.py        → 读取 app.py 源码
GET /page?name=../../etc/passwd → 读取系统密码文件
GET /page?name=../.env          → 读取环境变量（含密钥）
```

### 2.2 影响范围

| 攻击类型 | 可读取的文件 | 危害 |
|---------|-------------|------|
| 源码泄露 | `app.py`、`templates/*` | 暴露业务逻辑、SQL 结构、密钥 |
| 配置泄露 | `.env`、`config.py` | 暴露数据库密码、API 密钥 |
| 系统文件 | `/etc/passwd`、`/proc/self/environ` | 系统信息收集 |
| 数据文件 | `data/users.db` | 用户数据泄露 |

### 2.3 攻击示例

```bash
# 读取 app.py 源码（泄露 SQL 语句、密钥、业务逻辑）
curl "http://localhost:5000/page?name=../app.py"

# 读取数据库
curl "http://localhost:5000/page?name=../data/users.db"

# 读取系统密码文件
curl "http://localhost:5000/page?name=../../../../etc/passwd"
```

---

## 三、修复方案

### 3.1 修复前代码

```python
# ❌ 漏洞代码 — 无任何校验
@app.route("/page")
def page():
    name = request.args.get("name", "")
    page_path = os.path.join(app.root_path, "pages", name)
    if os.path.exists(page_path):
        with open(page_path, "r") as f:
            page_content = f.read()
    return render_template("index.html", page_content=page_content)

# 用户输入 name=../app.py
# → os.path.join(".../pages", "../app.py")
# → ".../pages/../app.py"
# → ".../app.py"  （成功读取！）
```

### 3.2 修复后代码

```python
# ✅ 安全代码 — 正则白名单 + 长度限制
def is_safe_page_name(name):
    """校验页面名称是否合法：只允许字母、数字、下划线、中划线"""
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name))

@app.route("/page")
def page():
    name = request.args.get("name", "")
    if not name:
        return redirect("/")

    page_content = None
    try:
        # 正则白名单校验 — 拦截 ../ 和所有特殊字符
        if not is_safe_page_name(name):
            page_content = "<p style='color:#e53e3e;'>页面名称包含非法字符</p>"
        else:
            # 长度限制 — 防止 DoS
            if len(name) > 50:
                name = name[:50]
            page_path = os.path.join(app.root_path, "pages", name)
            # ... 正常读取
    except Exception as e:
        page_content = "<p style='color:#e53e3e;'>页面加载失败</p>"

    return render_template("index.html", page_content=page_content)
```

### 3.3 首页 `/` 路由的 `?page=` 参数也同步修复

首页同样支持 `/?page=help` 的页面加载功能，在修复前没有路径校验：

```python
# ❌ 修复前 — 首页路由也无校验
page_name = request.args.get("page", "")
page_path = os.path.join(app.root_path, "pages", page_name)  # 可穿越

# ✅ 修复后 — 与 /page 路由保持相同白名单
if not is_safe_page_name(page_name):
    page_content = "<p style='color:#e53e3e;'>页面名称包含非法字符</p>"
```

---

## 四、修复原理

### 4.1 白名单 vs 黑名单

```python
# ❌ 黑名单（不可靠） — 总有遗漏
if "../" in name:
    return "非法"

# ✅ 白名单（可靠） — 明确允许的范围
if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
    return "非法"
```

**为什么白名单优于黑名单？**
- 黑名单需要枚举所有可能的攻击向量（`../`、`..\\`、`%2e%2e%2f`、双编码等）
- 白名单只允许安全的字符，其余全部拒绝
- 路径遍历的攻击变种极多（URL 编码、Unicode、16 进制等），黑名单防不胜防

### 4.2 修复前后对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 校验方式 | 无校验 | 正则白名单 `^[a-zA-Z0-9_\-]+$` |
| `name=help` | ✅ 正常加载 | ✅ 正常加载 |
| `name=../app.py` | 🔴 读取 app.py 源码 | ✅ 返回"非法字符" |
| `name=../../etc/passwd` | 🔴 读取系统文件 | ✅ 返回"非法字符" |
| `name=.env` | 🔴 读取环境变量 | ✅ 返回"非法字符" |
| `name=`（空） | ✅ 跳转首页 | ✅ 跳转首页 |
| `name=`(超长 500 字符) | ⚠️ 可能异常 | ✅ 截断至 50 字符 |
| 首页 `/?page=../app.py` | 🔴 同样可穿越 | ✅ 同样白名单校验 |

---

## 五、完整攻击与防御演示

### 5.1 攻击过程

```bash
# 步骤 1：探测是否存在路径遍历
curl -s "http://localhost:5000/page?name=help"
# → 返回帮助内容（正常）

# 步骤 2：尝试跳出 pages 目录
curl -s "http://localhost:5000/page?name=../"
# → 修复前：返回目录列表或错误信息
# → 修复后：返回"非法字符"

# 步骤 3：读取核心文件
curl -s "http://localhost:5000/page?name=../app.py"
# → 修复前：返回 app.py 全部源码
# → 修复后：返回"非法字符"

# 步骤 4：读取系统文件
curl -s "http://localhost:5000/page?name=../../../../etc/passwd"
# → 修复前：返回 /etc/passwd 内容
# → 修复后：返回"非法字符"
```

### 5.2 修复验证

```bash
# 验证正常功能不受影响
curl -s "http://localhost:5000/page?name=help"
# → ✅ 正常显示帮助中心

# 验证路径遍历被拦截
curl -s "http://localhost:5000/page?name=../app.py" | grep -o "非法字符"
# → ✅ 返回"页面名称包含非法字符"

# 验证首页同样安全
curl -s "http://localhost:5000/?page=../app.py" | grep -o "非法字符"
# → ✅ 返回"页面名称包含非法字符"

# 验证超长名称安全
LONG=$(python3 -c "print('A'*200)")
curl -s "http://localhost:5000/page?name=$LONG"
# → ✅ 被截断至 50 字符，不崩溃
```

---

## 六、对其他功能的启示

路径遍历漏洞不仅存在于 `/page` 路由，还应在以下功能中保持警惕：

| 功能 | 风险点 | 防护措施 |
|------|--------|---------|
| **文件上传** | 文件名包含 `../` → 逃逸 uploads 目录 | `os.path.basename()` 截断路径 |
| **动态页面** | `name=../` → 读取任意文件 | 正则白名单校验 |
| **个人中心** | `user_id=1 OR 1=1` → SQL 注入 | 参数化查询（已修复） |

### 防御原则总结

```
1. 永远不要信任用户输入
2. 白名单比黑名单可靠
3. 最小权限原则（只能访问 pages/ 目录）
4. 深度防御（白名单 + 长度限制 + 异常捕获）
```

---

## 七、相关代码位置

| 文件 | 行号 | 说明 |
|------|------|------|
| `app.py` | 103-105 | `is_safe_page_name()` 校验函数 |
| `app.py` | 468-497 | `/page` 路由（含白名单校验） |
| `app.py` | 154-177 | 首页 `/?page=` 加载（含白名单校验） |
| `app.py` | 299-301 | 上传文件名 `os.path.basename()` 防护 |
| `pages/help.html` | — | 合法的静态页面 |

---

*安全报告生成日期: 2026-07-13*  
*对应 Git 提交: 0039bf5（首次修复）、e3b7ab8（白名单增强）*
