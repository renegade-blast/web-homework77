# URL 抓取功能 — 功能实现报告

> **路由**: `POST /fetch-url`
> **关联文件**: `app.py`、`templates/index.html`
> **实现日期**: 2026年7月15日
> **对应提交**: `e32f723` → `c7462f1` → `4d979de` → `e87a55b`

---

## 一、功能概述

URL 抓取功能允许已登录用户输入一个 URL，系统后台使用 `urllib` 抓取该 URL 的内容，并将状态码和响应内容的前 5000 字符展示在首页上。

### 功能流程

```
用户 → 登录 → 首页 → 输入 URL → 点击抓取 → 后端请求 URL → 返回状态码+内容
```

---

## 二、前端界面

### 2.1 首页入口

URL 抓取功能的入口位于首页已登录状态下的卡片区域：

```html
<div class="card">
    <h2>URL 抓取</h2>
    <form method="post" action="/fetch-url">
        <input type="text" name="url" placeholder="输入要抓取的 URL" required>
        <button type="submit">抓 取</button>
    </form>
</div>
```

### 2.2 结果显示

抓取结果展示在输入框下方：

```html
{% if fetch_status %}
    <h3>状态码: {{ fetch_status }}</h3>
    <pre class="fetch-content">{{ fetch_content }}</pre>
{% endif %}
```

- 状态码以标题形式显示（如 `状态码: 200`）
- 响应内容在深色代码块中展示，支持滚动和自动换行
- 最大显示 5000 字符

### 2.3 样式

```css
.fetch-content {
    background: #1e1e1e;        /* 深色背景 */
    color: #f0f0f0;             /* 浅色文字 */
    padding: 14px;
    border-radius: 8px;
    font-family: "Courier New", monospace;
    max-height: 400px;          /* 最大高度限制 */
    overflow-y: auto;           /* 超出滚动 */
    white-space: pre-wrap;      /* 保留格式 + 自动换行 */
    word-break: break-all;      /* 长单词截断 */
}
```

---

## 三、后端实现

### 3.1 路由定义

```python
@app.route("/fetch-url", methods=["POST"])
def fetch_url():
```

### 3.2 登录检查

```python
username = session.get("username")
if not username:
    return redirect("/login")
```

必须登录后才能使用 URL 抓取功能，未登录跳转到登录页。

### 3.3 URL 安全检查

```python
def is_safe_url(url):
    """检查 URL 是否安全：仅允许 http/https、禁止内网地址"""
```

`is_safe_url()` 函数执行两层校验：

| 校验层 | 规则 | 拦截示例 |
|--------|------|---------|
| 协议白名单 | 仅允许 `http://` 和 `https://` | `file://`、`ftp://`、`gopher://` |
| 内网黑名单 | 禁止 7 类内网地址 | `127.0.0.1`、`192.168.x.x`、`10.x.x.x` |

### 3.4 HTTP 请求

```python
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=10)
```

- 设置 10 秒超时防止请求挂起
- 设置 User-Agent 头部避免被部分网站拦截
- 使用 `urllib` 标准库，无需额外安装依赖

### 3.5 分块读取

```python
max_size = 5120
chunks = []
total_read = 0
while total_read < max_size:
    chunk = resp.read(min(1024, max_size - total_read))
    if not chunk:
        break
    chunks.append(chunk)
    total_read += len(chunk)
raw = b"".join(chunks)
```

分块读取每次 1KB，上限 5120 字节，防止大响应耗尽服务器内存。

### 3.6 内容解码

```python
try:
    fetch_content = raw.decode("utf-8")[:5000]
except UnicodeDecodeError:
    fetch_content = f"[二进制内容，共 {total_read} 字节]"
```

- 优先尝试 UTF-8 解码
- 解码失败则提示二进制内容长度

### 3.7 日志记录

```python
log_url = url[:200] + "..." if len(url) > 200 else url
logger.info(f"URL抓取: {username} 请求 {log_url}")
```

- URL 截断至 200 字符防止日志注入
- 记录操作者用户名便于审计

---

## 四、错误处理

| 异常类型 | 捕获方式 | 用户提示 |
|---------|---------|---------|
| `HTTPError` | `urllib.error.HTTPError` | `HTTP 错误: {状态码}` |
| `URLError` | `urllib.error.URLError` | `URL 错误: {原因}` |
| URL 为空 | 表单校验 | `请输入 URL` |
| 协议/地址不安全 | `is_safe_url()` | `不支持的协议或禁止访问的地址` |
| 其他异常 | 通用 `Exception` | `请求失败: {原因}` |

---

## 五、安全架构

```
用户输入 URL
    │
    ▼
┌─────────────┐
│ 登录校验     │ ← 未登录 → 302 跳转
└──────┬──────┘
       ▼
┌─────────────┐
│ URL 非空校验 │ ← 为空 → "请输入 URL"
└──────┬──────┘
       ▼
┌─────────────┐
│ is_safe_url │ ← 不安全 → "不支持的协议或禁止访问的地址"
│ ① 协议检查  │
│ ② 内网检查  │
└──────┬──────┘
       ▼
┌─────────────┐
│ urlopen()   │ ← 异常 → 错误提示
│ timeout=10  │
│ 分块读取    │
│ 日志截断    │
└──────┬──────┘
       ▼
┌─────────────┐
│ 返回结果     │ → 状态码 + 内容(≤5000字符)
└─────────────┘
```

---

## 六、测试结果

### 6.1 功能测试

| 测试场景 | 输入 | 预期结果 | 实际结果 |
|---------|------|---------|---------|
| 正常抓取 | `https://example.com` | 状态码 200 + 内容 | ✅ |
| 空 URL | `` | 提示"请输入 URL" | ✅ |
| 未登录 | — | 302 跳转登录页 | ✅ |

### 6.2 安全测试

| 测试场景 | 输入 | 预期结果 | 实际结果 |
|---------|------|---------|---------|
| file:// 协议 | `file:///etc/passwd` | 拦截 | ✅ |
| 内网地址 | `http://127.0.0.1:5000/` | 拦截 | ✅ |
| 内网地址 | `http://192.168.1.1/` | 拦截 | ✅ |
| 超大响应 | 2MB 文件 | 分块读取 5120 字节 | ✅ |
| 超长 URL | 10000 字符 | 日志截断 200 字符 | ✅ |

---

## 七、配置文件

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 超时时间 | 10 秒 | `urlopen(timeout=10)` |
| 最大读取 | 5120 字节 | 分块读取上限 |
| 最大显示 | 5000 字符 | 返回内容截断 |
| 日志截断 | 200 字符 | URL 日志截断长度 |
| 协议白名单 | http, https | `is_safe_url()` 校验 |
| User-Agent | Mozilla/5.0 | 请求头伪装浏览器 |

---

## 八、代码统计

| 文件 | 行数 | 说明 |
|------|------|------|
| `app.py` | ~55 行 | `is_safe_url()` + `fetch_url()` |
| `templates/index.html` | ~15 行 | 前端表单 + 结果展示 |
| `static/css/style.css` | ~20 行 | `.fetch-content` 样式 |

---

*功能实现版本: `e87a55b`*
