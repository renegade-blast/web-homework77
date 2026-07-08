# SQL Injection Payload 字典

## 目录结构

| 文件名 | 内容 | 适用阶段 |
|---|---|---|
| `01-basic-detection.txt` | 基础探测类 — 判断是否存在注入 | Step 1 |
| `02-column-detection.txt` | 列数探测类 — 用 ORDER BY / UNION SELECT 找列数 | Step 2 |
| `03-db-info-probe.txt` | 数据库信息探测类 — 获取版本、用户、路径 | Step 4 |
| `04-table-column-extract.txt` | 表名与列名提取类 — 拉取数据库结构 | Step 5~6 |
| `05-error-based-injection.txt` | 报错注入类 — 用报错函数提取数据 | 报错有回显时 |
| `06-boolean-blind.txt` | 布尔盲注类 — 页面有真/假差异时逐字符猜解 | 无回显时 |
| `07-time-based-blind.txt` | 时间盲注类 — 靠延时判断条件真假 | 完全无差异时 |
| `08-auth-bypass.txt` | 登录绕过类 — 绕过登录表单验证 | 登录框 |
| `09-waf-bypass.txt` | WAF 绕过类 — 绕 Web 应用防火墙 | 有 WAF 时 |
| `10-file-operations.txt` | 文件操作类（高危）— 读文件/写 webshell | root 权限时 |
| `11-database-specific.txt` | 数据库专用 Payload — SQL Server/Oracle/PostgreSQL/SQLite | 确定数据库后 |

## 攻击流程参考

```
Step 1:  01-basic-detection.txt     → 是否存在注入
Step 2:  02-column-detection.txt    → 有几列？
Step 3:  确认 UNION 可用
Step 4:  03-db-info-probe.txt       → 是什么数据库？什么版本？
Step 5~6:04-table-column-extract.txt → 有哪些表？哪些列？
Step 7:  04-table-column-extract.txt（底部） → 提取数据

特殊场景:
  有报错 → 05-error-based-injection.txt
  无回显 → 06-boolean-blind.txt
  无差异 → 07-time-based-blind.txt
  登录框 → 08-auth-bypass.txt
  有 WAF → 09-waf-bypass.txt
  root权限 → 10-file-operations.txt
  确定数据库 → 11-database-specific.txt（精细化）
```

## 使用方式

### Burp Suite Intruder
1. 截获请求，定位参数位置，添加 `§`
2. Intruder → Payloads → Load → 选择 `.txt` 文件
3. 开始攻击
4. 按响应长度/状态码/时间排序分析结果

### 手动测试
```
原始 URL:  http://target.com/page.php?id=1
测试 URL:  http://target.com/page.php?id=1 UNION SELECT 1,database(),3--
```

## 注意事项

- `N` 需要替换为实际的列数（Step 2 确定后）
- `database_name`、`table_name` 需要替换为目标名称
- `--` 注释符在发送时可能需要 URL 编码为 `%23`（#）或去掉
- 如果网站有 WAF，参考 `09-waf-bypass.txt` 进行绕过
- 所有 payload 仅用于授权测试！

## 来源说明

基于 SQL 注入常规手法整理，涵盖 PortSwigger Academy、sqli-labs、OSCP 等主流靶场和认证的常见考点。
