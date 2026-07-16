# Ping 网络诊断功能 — 命令注入漏洞修复报告

> **功能**: `GET/POST /ping`
> **修复日期**: 2026年7月16日
> **对应提交**: `86f9d0b`（初始实现）→ `（当前）`（修复）

---

## 一、漏洞概述

| 项目 | 内容 |
|------|------|
| **漏洞类型** | 命令注入（Command Injection） |
| **严重程度** | 🔴 高危 |
| **CVSS 3.1** | 9.8 / 10（Critical） |
| **影响范围** | 服务器完全控制权 |

### 初始漏洞代码

```python
ip = request.form.get("ip", "").strip()
cmd = f"ping -c 3 {ip}"                          # f-string 直接拼接用户输入
output = subprocess.check_output(cmd, shell=True) # shell=True 执行任意命令
```

攻击者只需在 IP 后面拼接命令即可在服务器上执行任意代码：

```bash
# 注入前
ping -c 3 8.8.8.8           # 正常 Ping

# 注入后
ping -c 3 8.8.8.8; cat /etc/passwd   # 读取系统密码文件
ping -c 3 8.8.8.8; ls -la            # 列出目录
ping -c 3 8.8.8.8; rm -rf /          # 删除全部文件
```

---

## 二、攻击测试验证

### 2.1 修复前（可成功注入）

```bash
# 命令注入: 执行 ls 命令
curl -b "session=admin" -X POST http://localhost:5000/ping -d "ip=8.8.8.8; ls -la"
# 结果: 返回了 app.py、data、templates 等目录列表 ✅ 注入成功
```

### 2.2 修复后（全部拦截）

```bash
# 命令注入: ; ls
curl -b "session=admin" -X POST http://localhost:5000/ping -d "ip=8.8.8.8; ls"
# 结果: "无效的 IP 地址或域名格式" ✅ 拦截

# 命令注入: | id
curl -b "session=admin" -X POST http://localhost:5000/ping -d "ip=8.8.8.8|id"
# 结果: "无效的 IP 地址或域名格式" ✅ 拦截

# 命令注入: $(whoami)
curl -b "session=admin" -X POST http://localhost:5000/ping -d "ip=8.8.8.8$(whoami)"
# 结果: "无效的 IP 地址或域名格式" ✅ 拦截
```

---

## 三、修复方案

### 3.1 输入白名单验证

```python
def is_valid_ping_target(target):
    """校验 Ping 目标：只允许 IP 地址或合法域名"""

    # 允许 IPv4 地址
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, target):
        parts = target.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            return True

    # 允许合法域名
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    if re.match(domain_pattern, target):
        return True

    return False
```

**校验规则**：

| 类型 | 允许 | 拦截 |
|------|------|------|
| IPv4 地址 | `8.8.8.8`、`192.168.1.1` | `999.999.999.999`、`abc` |
| 域名 | `example.com`、`google.com` | `; ls`、`\| id`、`$(whoami)` |
| 特殊字符 | — | `;`、`\|`、`$`、`` ` ``、`&&`、`||` |

### 3.2 禁用 shell=True

```python
# ❌ 修复前（命令注入）
cmd = f"ping -c 3 {ip}"
output = subprocess.check_output(cmd, shell=True)

# ✅ 修复后（参数列表方式）
output = subprocess.check_output(
    ["ping", "-c", "3", target],  # 参数作为列表，不经过 shell
    timeout=30,
    stderr=subprocess.STDOUT
)
```

**为什么参数列表比 shell=True 安全？**

```
shell=True:
  ping -c 3 8.8.8.8; ls
  → shell 解释为: ping -c 3 8.8.8.8 然后执行 ls

参数列表:
  ["ping", "-c", "3", "8.8.8.8; ls"]
  → ping 接收 "-c" "3" "8.8.8.8; ls" 作为参数
  → "8.8.8.8; ls" 被当作一个普通字符串传给 ping
  → 不会执行 ls 命令
```

### 3.3 修复前后对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 命令构建 | `f"ping -c 3 {ip}"` | `["ping", "-c", "3", target]` |
| shell 执行 | `shell=True` | 默认 `shell=False` |
| 输入校验 | 无 | IPv4 白名单 + 域名白名单 |
| IP 格式 | 不检查 | 0-255 范围校验 |
| 域名格式 | 不检查 | 合法域名正则 |
| 特殊字符 | 不拦截 | `;` `|` `$` 全部拦截 |

---

## 四、修复验证

| 测试项 | 输入 | 修复前 | 修复后 | 状态 |
|--------|------|--------|--------|------|
| 正常 Ping | `8.8.8.8` | ✅ 成功 | ✅ 成功 | 通过 |
| 正常 Ping 域名 | `example.com` | ✅ 成功 | ✅ 成功 | 通过 |
| 命令注入 `; ls` | `8.8.8.8; ls` | 🔴 执行成功 | ✅ 拦截 | 修复 |
| 命令注入 `\| id` | `8.8.8.8\|id` | 🔴 执行成功 | ✅ 拦截 | 修复 |
| 命令注入 `$(whoami)` | `8.8.8.8$(whoami)` | 🔴 执行成功 | ✅ 拦截 | 修复 |
| 非法 IP | `999.999.999.999` | 🔴 执行失败 | ✅ 格式拦截 | 修复 |
| 空输入 | `` | ❌ 无提示 | ✅ 友好提示 | 修复 |

---

## 五、安全架构对比

```
修复前:
  用户输入 → f"ping -c 3 {ip}" → shell=True → 任意命令执行

修复后:
  用户输入 → is_valid_ping_target() → 参数列表 → ping 命令
                │                          │
                │ 白名单校验                │ 不经过 shell
                │ · IP 0-255               │ 参数当成字符串
                │ · 域名合法                │ 不会解析为命令
                │ · 拦截特殊字符            │
```

---

## 六、涉及文件

| 文件 | 变更 |
|------|------|
| `app.py` | 新增 `is_valid_ping_target()` 函数、修改 `ping()` 路由 |
| `templates/ping.html` | 无变更 |
| `static/css/style.css` | 无变更 |

---

## 七、经验总结

### 命令注入防御黄金法则

```
1. ✅ 永远不要使用 shell=True
   → 改用参数列表 ["ping", "-c", "3", target]

2. ✅ 永远不要 f-string 拼接命令
   → shell 参数会被解释为命令

3. ✅ 永远要校验用户输入
   → 白名单比黑名单可靠（IP 正则、域名正则）

4. ✅ 最小权限原则
   → 即使有漏洞，限制命令能造成的伤害
```

---

*安全修复报告: `SECURITY_PING_FIX.md`*
