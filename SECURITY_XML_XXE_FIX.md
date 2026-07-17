# XML 数据导入功能 — XXE 漏洞修复报告

> **功能**: `GET/POST /xml-import`  
> **修复日期**: 2026年7月17日  
> **对应提交**: `e13ae28`（初始实现）→ `（当前）`（修复）

---

## 一、漏洞概述

| 项目 | 内容 |
|------|------|
| **漏洞类型** | XXE — XML External Entity Injection |
| **严重程度** | 🔴 高危 |
| **CVSS 3.1** | 7.5 / 10 |
| **影响范围** | 任意文件读取、SSRF 内网探测 |

### 初始漏洞代码

```python
# 提取实体定义中的文件路径
entity_pattern = re.compile(r'<!ENTITY\s+\w+\s+SYSTEM\s+["\']([^"\']+)["\']')
matches = entity_pattern.findall(xml_data)
for filepath in matches:
    with open(filepath, "r") as f:          # ⚠️ 读取任意文件
        file_content = f.read()
    xml_data = xml_data.replace("&xxe;", file_content)  # ⚠️ 文件内容注入XML
```

## 二、攻击验证

### 2.1 修复前：XXE 成功读取任意文件

```bash
# XXE 读取 /etc/passwd
curl -b "session=X" -X POST http://localhost:5000/xml-import \
  --data-urlencode 'xml_data=<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <users><user><name>&xxe;</name><email>x@x.com</email></user></users>'
# 结果: password 文件内容在 name 字段中返回 ✅ 读取成功

# XXE 读取 app.py 源码
curl -b "session=X" -X POST http://localhost:5000/xml-import \
  --data-urlencode 'xml_data=<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "/workspace/user-management/app.py">]>
    <users><user><name>&xxe;</name><email>x@x.com</email></user></users>'
# 结果: app.py 源码泄露（27392 字节）✅ 读取成功
```

### 2.2 修复后：全部拦截

```bash
# 正常 XML → 正常工作
curl -b "session=X" -X POST http://localhost:5000/xml-import \
  -d 'xml_data=<users><user><name>张三</name><email>z@t.com</email></user></users>'
# 结果: {"users": [{"name": "张三", "email": "z@t.com"}], "total": 1} ✅

# XXE 攻击 → 被拦截
curl -b "session=X" -X POST http://localhost:5000/xml-import \
  --data-urlencode 'xml_data=<?xml version="1.0"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>...'
# 结果: "XML 中包含 DTD 实体声明，已拒绝处理" ✅ 拦截
```

## 三、修复方案

### 3.1 移除文件读取逻辑

删除所有实体检测、文件读取、内容替换的代码，直接用 `ET.fromstring()` 解析原始 XML。

```python
# ❌ 修复前：检测实体 → 读取文件 → 替换内容 → 解析XML
entity_pattern = re.compile(r'<!ENTITY\s+\w+\s+SYSTEM\s+...')
matches = entity_pattern.findall(xml_data)
for filepath in matches:
    content = open(filepath).read()        # 任意文件读取
    xml_data = xml_data.replace("&xxe;", content)
root = ET.fromstring(xml_data)

# ✅ 修复后：直接解析XML，Python ET 默认不解析外部实体
if re.search(r'<!DOCTYPE\s+|<!ENTITY\s+', xml_data, re.IGNORECASE):
    error = "XML 中包含 DTD 实体声明，已拒绝处理"
else:
    root = ET.fromstring(xml_data)
```

### 3.2 修复前后对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| DTD 检测 | 无检测，主动处理实体 | 检测到 DTD 直接拒绝 |
| 文件读取 | 允许读取任意文件路径 | 无文件读取操作 |
| 内容替换 | 文件内容替换实体引用 | 无替换操作 |
| XML 解析 | 解析替换后的 XML | 直接解析原始 XML |
| 文件泄露 | 🔴 可读 /etc/passwd、app.py | ✅ 不读取任何文件 |
| Billion Laughs | 🔴 可被 DoS 攻击 | ✅ 拒绝 DTD 即防御 |

## 四、修复验证

| 测试项 | 修复前 | 修复后 | 状态 |
|--------|--------|--------|------|
| 正常 XML | ✅ 成功解析 | ✅ 成功解析 | 通过 |
| XXE file:///etc/passwd | 🔴 读取成功 | ✅ "已拒绝处理" | 修复 |
| XXE /etc/passwd（直接路径） | 🔴 读取成功 | ✅ "已拒绝处理" | 修复 |
| XXE app.py 源码 | 🔴 源码泄露 | ✅ "已拒绝处理" | 修复 |
| 格式错误 XML | ✅ 返回错误 | ✅ 返回错误 | 通过 |
| 未登录 | ✅ 302 跳转 | ✅ 302 跳转 | 通过 |

## 五、安全架构

```
修复前:
  用户 XML → 提取实体路径 → open() 读取文件 → 替换 &xxe; → 解析 XML
                │                │
                │ 任意路径       │ 任意文件内容
                ▼                ▼
          file:///etc/passwd    泄露密码
          /app.py              泄露源码

修复后:
  用户 XML → 检测 DTD 实体 → 有 DTD → ❌ 拒绝
               │
               │ 无 DTD
               ▼
           ET.fromstring() → ✅ 正常解析
               (Python ET 默认安全)
```

## 六、防御原理

```python
# Python xml.etree.ElementTree 的默认安全行为：
# 1. 不解析外部实体 → 无法读取本地文件
# 2. 不展开内部实体 → 防御 Billion Laughs
# 3. 不加载 DTD → 防御 XXE

# 额外加固：主动检测并拒绝含 DTD 的 XML
if re.search(r'<!DOCTYPE|<!ENTITY', xml_data):
    error = "拒绝含 DTD 的 XML"
```

## 七、经验总结

### XXE 防御黄金法则

```
1. ✅ 禁用 DTD 处理
   → 直接拒绝含 <!DOCTYPE 和 <!ENTITY 的 XML

2. ✅ 使用安全的 XML 解析器
   → Python ET 默认安全，不用 lxml（除非手动配置）

3. ✅ 永远不要用用户输入构造文件路径
   → open(user_input) 是最危险的操作之一

4. ✅ 最小权限原则
   → 应用不应有读取 /etc/passwd 等敏感文件的权限
```

---

*安全修复报告: `SECURITY_XML_XXE_FIX.md`*
