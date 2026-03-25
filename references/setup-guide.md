# Confluence 首次使用引导

## 首次使用检测（每次触发 Skill 时必须执行）

**在执行任何操作之前**，先运行以下检测：

```python
from pathlib import Path
import json

creds_file = Path.home() / '.confluence_credentials'
if not creds_file.exists():
    print("SETUP_REQUIRED")
else:
    try:
        config = json.loads(creds_file.read_text())
        missing = [k for k in ['username', 'api_key'] if not config.get(k)]
        if missing:
            print(f"INCOMPLETE: missing {missing}")
        else:
            print("OK")
    except Exception as e:
        print(f"INVALID: {e}")
```

**根据结果决定下一步：**

| 结果 | 说明 | 处理方式 |
|------|------|----------|
| `OK` | 配置完整 | 直接执行用户请求 |
| `SETUP_REQUIRED` | 文件不存在 | 进入**新手引导流程** |
| `INCOMPLETE` | 配置缺字段 | 提示缺少哪些字段，进入**配置修复流程** |
| `INVALID` | 文件格式错误 | 显示错误，进入**配置修复流程** |

## 新手引导流程

检测到未配置时，**主动引导用户完成设置**，不要直接报错退出：

### 第一步：了解用户信息

向用户说明只需要两项信息（网址已预设好，不需要用户提供）：

```
我需要先帮您配置 Confluence 连接，只需要两项信息：

1. 用户名（登录 docs.matrixback.com 的用户名，不含邮箱后缀）
2. Personal Access Token（API 密钥，下面教您怎么获取）

请先告诉我您的用户名？
```

### 第二步：引导获取 Personal Access Token

用户提供用户名后，给出获取步骤：

```
获取 Personal Access Token 的步骤：
1. 登录 https://docs.matrixback.com
2. 点击右上角头像 → 「Profile」（个人资料）
3. 左侧菜单找「Personal Access Tokens」
4. 点击「Create token」
5. 填写 Token 名称（如「Claude Code」），选择过期时间
6. 点击「Create」，复制生成的 Token（只显示一次！）

如果没有「Personal Access Tokens」菜单，请提供您的登录密码，
配置文件中用 "password" 字段代替 "api_key"。
```

### 第三步：创建配置文件

收到两项信息后，帮用户创建配置文件（base_url 自动填入默认值）：

```python
import json
from pathlib import Path

config = {
    "base_url": "https://docs.matrixback.com",  # 默认值，无需用户提供
    "username": "用户提供的用户名",               # 替换为实际值
    "api_key": "用户提供的Token"                  # 替换为实际值
}

creds_file = Path.home() / '.confluence_credentials'
creds_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))
creds_file.chmod(0o600)  # 仅本人可读，保护 Token 安全
print(f"配置已保存到 {creds_file}")
```

### 第四步：验证连接

配置保存后，立即验证是否可以连接：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / '.claude/skills/confluence'))
from confluence_api import ConfluenceAPI

try:
    api = ConfluenceAPI()
    spaces = api.get_spaces()
    print(f"连接成功！找到 {len(spaces)} 个 Space：{[s['key'] for s in spaces[:3]]}")
except Exception as e:
    print(f"连接失败：{e}")
```

连接成功后告诉用户，并继续执行他最初的请求。

连接失败时，根据错误类型给出提示：
- `401 Unauthorized` → Token 或用户名有误，请重新检查
- `ConnectionError` / `timeout` → 网址可能有误，或网络不通
- `403 Forbidden` → Token 权限不足，需要重新生成

## 认证配置详情

配置文件路径：`~/.confluence_credentials`（JSON 格式，权限建议设为 600）

```json
{
  "base_url": "https://docs.matrixback.com",
  "username": "your.name",
  "api_key": "your_personal_access_token"
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `base_url` | Confluence 站点根地址，不带末尾斜杠 | `https://docs.matrixback.com`（已内置） |
| `username` | 登录用户名，不含邮箱后缀 | 必填 |
| `api_key` | Personal Access Token（推荐）或登录密码 | 必填 |

> 使用密码代替 Token：如果 Confluence 版本不支持 PAT，可用 `"password"` 字段代替 `"api_key"`。
