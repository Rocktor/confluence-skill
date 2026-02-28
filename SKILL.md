---
name: confluence
version: 2.7.1
description: Confluence文档管理Skill。支持Markdown上传到Confluence、从Confluence导出为Markdown，支持PlantUML和Mermaid图表转换、表格操作、精确编辑等全功能。
---

# Confluence 文档管理 Skill（全功能版）

## 触发条件

当用户提到以下内容时使用此技能：
- 上传markdown到confluence / 把md发到cf
- 读取/导出confluence页面 / 从cf导出markdown
- 同步文档到confluence
- 搜索confluence页面
- 编辑/修改confluence页面
- 表格操作（列出表格、插入列、删除列、更新单元格、插入行、删除行）

## ⚡ 首次使用检测（每次触发 Skill 时必须执行）

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
        missing = [k for k in ['base_url', 'username', 'api_key'] if not config.get(k)]
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

### 新手引导流程

检测到未配置时，**主动引导用户完成设置**，不要直接报错退出：

**第一步：了解用户的 Confluence 信息**

向用户说明需要三项信息，并询问：

```
我需要先帮您配置 Confluence 连接信息，需要以下三项：

1. Confluence 网址（如 https://your-company.atlassian.net 或内网地址）
2. 用户名（登录 Confluence 的邮箱或用户名）
3. Personal Access Token（API 密钥，下面会教您怎么获取）

请先告诉我您的 Confluence 网址和用户名？
```

**第二步：引导获取 Personal Access Token**

用户提供网址和用户名后，根据 Confluence 类型提供对应引导：

*如果是 Confluence Cloud（网址含 `.atlassian.net`）：*
```
获取 API Token 的步骤：
1. 访问：https://id.atlassian.com/manage-profile/security/api-tokens
2. 点击「Create API token」
3. 输入 Token 名称（如「Claude Code」），点击创建
4. 复制生成的 Token（只显示一次！）
```

*如果是 Confluence Server/Data Center（自建或内网）：*
```
获取 Personal Access Token 的步骤：
1. 登录您的 Confluence
2. 点击右上角头像 → 「Profile」（个人资料）
3. 左侧菜单找「Personal Access Tokens」
4. 点击「Create token」
5. 填写 Token 名称（如「Claude Code」），选择过期时间
6. 点击「Create」，复制生成的 Token（只显示一次！）

💡 如果没有「Personal Access Tokens」菜单，说明您的 Confluence 版本较旧，
   请提供您的登录密码代替 Token（在配置文件中用 "password" 字段代替 "api_key"）。
```

**第三步：创建配置文件**

收到三项信息后，帮用户创建配置文件：

```python
import json
from pathlib import Path

config = {
    "base_url": "用户提供的网址",   # 替换为实际值
    "username": "用户提供的用户名",  # 替换为实际值
    "api_key": "用户提供的Token"     # 替换为实际值
}

creds_file = Path.home() / '.confluence_credentials'
creds_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))
creds_file.chmod(0o600)  # 仅本人可读，保护 Token 安全
print(f"配置已保存到 {creds_file}")
```

**第四步：验证连接**

配置保存后，立即验证是否可以连接：

```python
import sys
sys.path.insert(0, str(Path.home() / '.claude/skills/confluence'))
from confluence_api import ConfluenceAPI

try:
    api = ConfluenceAPI()
    spaces = api.get_spaces()
    print(f"✅ 连接成功！找到 {len(spaces)} 个 Space：{[s['key'] for s in spaces[:3]]}")
except Exception as e:
    print(f"❌ 连接失败：{e}")
```

*连接成功后告诉用户，并继续执行他最初的请求。*
*连接失败时，根据错误类型给出提示：*
- `401 Unauthorized` → Token 或用户名有误，请重新检查
- `ConnectionError` / `timeout` → 网址可能有误，或网络不通
- `403 Forbidden` → Token 权限不足，需要重新生成

## 快速决策矩阵

| 我想做什么 | 用什么方法 | 备注 |
|-----------|-----------|------|
| 读取页面内容 | `read_page()` | 返回 Markdown + HTML |
| 修改某段文字/标题 | `edit_page()` | 精确替换，保留其他内容 ⭐ |
| 修改表格单元格 | `update_table_cell()` | 支持文本/图片/Markdown ⭐ |
| 在表格中加一行 | `insert_table_row()` | 支持 `[image:xxx]` 语法 |
| 在表格中删一行 | `delete_table_row()` | 指定行索引 |
| 在表格中加/删列 | `insert_column()` / `delete_column()` | 指定列位置 |
| 查看表格结构 | `list_tables()` | 获取行数、列数、表头 |
| 在页面追加内容 | `insert_content(position="append")` | 不影响原有内容 |
| 重写整个页面 | `update_page()` | ⚠️ 仅用户明确要求时 |
| 创建新页面 | `create_page()` | 需要 parent_id + space_key |
| 上传图片到页面 | `upload_attachment()` → 再插入引用 | 必须两步！ |
| 搜索页面 | `search()` | CQL 搜索 |
| 移动页面 | `move_page()` | 移到新父页面下 |
| 添加/查看评论 | `add_comment()` / `get_comments()` | - |

## 认证配置

配置文件路径：`~/.confluence_credentials`（JSON 格式，权限建议设为 600）

```json
{
  "base_url": "https://your-confluence.example.com",
  "username": "your.name",
  "api_key": "your_personal_access_token"
}
```

**字段说明：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `base_url` | Confluence 站点根地址，不带末尾斜杠 | `https://docs.example.com` |
| `username` | 登录用户名（Cloud 版用邮箱） | `zhang.san` 或 `zhang.san@example.com` |
| `api_key` | Personal Access Token（推荐）或登录密码 | 生成后为长字符串 |

> **使用密码代替 Token**：如果 Confluence 版本不支持 Personal Access Tokens，可用 `"password"` 字段代替 `"api_key"`。

**一键创建配置文件：**

```bash
cat > ~/.confluence_credentials << 'EOF'
{
  "base_url": "https://your-confluence.example.com",
  "username": "your.name",
  "api_key": "your_token_here"
}
EOF
chmod 600 ~/.confluence_credentials
```

## 页面标识（v2.5.0+）

所有接受 `page_id_or_url` 参数的方法均支持以下三种格式：

| 格式 | 示例 |
|------|------|
| 纯 pageId | `238854355` |
| pageId URL | `https://docs.matrixback.com/pages/viewpage.action?pageId=238854355` |
| display URL | `https://docs.matrixback.com/display/cpb/Page+Title` |
| tiny link | `https://docs.matrixback.com/x/TndqDg` |

display URL 通过 API 查询 spaceKey + title 解析；tiny link 通过跟随重定向解析为最终 URL。

## Claude 使用指南

### 初始化 API

```python
import sys
sys.path.insert(0, '/home/ubuntu/.claude/skills/confluence')
from confluence_api import ConfluenceAPI

api = ConfluenceAPI()
```

### 读取页面

```python
# 支持四种格式：pageId、pageId URL、display URL、tiny link
result = api.read_page("238854355")
result = api.read_page("https://docs.matrixback.com/pages/viewpage.action?pageId=238854355")
result = api.read_page("https://docs.matrixback.com/display/cpb/Page+Title")
result = api.read_page("https://docs.matrixback.com/x/TndqDg")

# 返回:
# {
#   "id": "238854355",
#   "title": "页面标题",
#   "markdown": "# 标题\n内容...",
#   "html": "<p>原始HTML...</p>",  # 用于精确编辑
#   "url": "https://...",
#   "space_key": "cpb",
#   "version": 1,
#   "images": [...]  # 页面中的图片列表
# }

# 不提取图片信息
result = api.read_page("238854355", include_images=False)
```

### 创建页面

```python
result = api.create_page(
    title="新页面标题",
    markdown="# 内容\n\n支持 **粗体**、*斜体*、`代码`\n\n## 表格\n\n| A | B |\n|---|---|\n| 1 | 2 |",
    parent_id="214946975",  # 父页面ID
    space_key="cpb"         # 空间Key
)

# 返回: {"success": True, "id": "xxx", "url": "https://..."}
```

### 更新页面（全量替换）

```python
result = api.update_page(
    page_id="238854355",
    markdown="# 更新后的内容",
    title="新标题"  # 可选
)
```

### 精确编辑（推荐）⭐

在原始 HTML 中查找并替换指定内容，保留其他所有格式和图片。

```python
# 1. 先读取页面，获取 HTML
page = api.read_page("238854355")
print(page['html'])  # 查看原始 HTML

# 2. 找到要修改的 HTML 片段，进行精确替换
result = api.edit_page(
    page_id_or_url="238854355",
    old_html="<p>旧内容</p>",
    new_html="<p>新内容</p>"  # 可以是 HTML 或 Markdown
)

# 返回: {"success": True, "url": "...", "message": "内容已精确替换"}
```

### 插入内容（保留原有内容）

在页面开头或结尾插入新内容，完全保留原有内容。

```python
# 在开头插入
result = api.insert_content(
    page_id_or_url="238854355",
    markdown="# 新增的标题\n\n这是新增的内容",
    position="prepend"  # prepend=开头，append=结尾
)

# 在结尾插入
result = api.insert_content(
    page_id_or_url="238854355",
    markdown="## 附录\n\n这是追加的内容",
    position="append"
)
```

### 搜索页面

```python
pages = api.search("关键词", space="cpb", limit=10)
# 返回: [{"id": "...", "title": "...", "space_key": "...", "url": "..."}]
```

### 移动页面

```python
# 将页面移动到新的父页面下
result = api.move_page("238873903", "240254369")
# 也支持 URL
result = api.move_page(
    "https://docs.xxx.com/pages/viewpage.action?pageId=238873903",
    "https://docs.xxx.com/pages/viewpage.action?pageId=240254369"
)
# 返回: {"success": True, "page_id": "238873903", "new_parent_id": "240254369", "title": "...", "url": "..."}
```

### 列出子页面

```python
children = api.list_children("214946975")
# 返回: [{"id": "...", "title": "...", "url": "..."}]
```

### 获取空间列表

```python
spaces = api.get_spaces()
# 返回: [{"key": "cpb", "name": "空间名称", "type": "global"}]
```

## 表格操作 ⭐

### 列出页面中的表格

```python
tables = api.list_tables("238854355")
# 返回:
# [
#   {
#     "index": 0,
#     "header_row": ["项目", "需求", "类", ...],
#     "row_count": 10,
#     "col_count": 8,
#     "preview": "项目 | 需求 | 类 | ..."
#   },
#   ...
# ]
```

### 插入列

```python
result = api.insert_column(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格（从0开始）
    column_position=2,       # 插入位置（在第2列之前插入）
    column_name="新列名",
    default_value="",        # 数据行默认值
    header_style=None        # 可选样式
)

# 返回: {"success": True, "message": "成功在表格 0 的第 2 列位置插入列 '新列名'", "url": "..."}
```

### 删除列

```python
result = api.delete_column(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格
    column_position=2        # 删除第几列
)

# 返回: {"success": True, "message": "成功删除表格 0 的第 2 列", "url": "..."}
```

### 更新单元格 ⭐

修改表格中指定位置的单元格内容。

```python
result = api.update_table_cell(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格（从0开始）
    row_index=1,             # 行索引（0=表头，1=第一行数据）
    column_index=2,          # 列索引（从0开始）
    content="新内容",         # 支持文本、HTML、Markdown
    append=False,            # True=追加，False=替换
    style=None,              # CSS 样式，如 "background-color: #e3fcef;"
    highlight_color=None     # 高亮颜色，如 "#e3fcef"（自动设置 data-highlight-colour）
)

# 返回: {"success": True, "message": "成功更新表格 0 的第 1 行第 2 列", "url": "..."}

# 支持 [image:filename] 语法插入图片
api.update_table_cell("238854355", 0, 1, 2, "[image:screenshot.png]")

# 支持 Markdown 格式
api.update_table_cell("238854355", 0, 1, 2, "**加粗** 和 *斜体*")

# 设置单元格高亮颜色（浅绿背景）
api.update_table_cell("238854355", 0, 1, 2, "已完成", highlight_color="#e3fcef")

# 自定义 CSS 样式
api.update_table_cell("238854355", 0, 1, 2, "重要", style="background-color: #ffe7e7; font-weight: bold;")
```

### 插入行

在表格中指定位置插入新行。

```python
result = api.insert_table_row(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格
    row_position=2,          # 插入位置（1=在表头后，2=第二行位置...）
    cell_values=["值1", "值2", "值3"],  # 各列的值
    is_header=False,         # True=创建表头行，False=创建数据行
    cell_styles=None         # 每个单元格的样式列表，支持 style 和 highlight_color
)

# 返回: {"success": True, "message": "成功在表格 0 的第 2 行位置插入新行", "url": "..."}

# 插入包含图片的行
api.insert_table_row("238854355", 0, 2, ["功能A", "[image:demo.png]", "说明文字"])

# 插入带高亮颜色的行
api.insert_table_row(
    "238854355", 0, 2,
    ["已完成", "功能开发完毕", "2024-01-15"],
    cell_styles=[
        {"highlight_color": "#e3fcef"},  # 第1列浅绿
        None,                             # 第2列无样式
        None                              # 第3列无样式
    ]
)
```

### 删除行

删除表格中的指定行。

```python
result = api.delete_table_row(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格
    row_index=2              # 要删除的行索引（0=表头，1=第一行数据...）
)

# 返回: {"success": True, "message": "成功删除表格 0 的第 2 行", "url": "..."}
```

## 评论操作

### 添加评论

```python
result = api.add_comment(
    page_id_or_url="238854355",
    content="这是一条评论"  # 支持 Markdown 或 HTML
)

# 返回: {"success": True, "id": "评论ID", "url": "https://..."}
```

### 获取评论

```python
comments = api.get_comments(
    page_id_or_url="238854355",
    limit=25,   # 每次获取数量
    start=0     # 分页起始位置
)

# 返回:
# {
#   "comments": [
#     {
#       "id": "评论ID",
#       "author": "作者名字",
#       "created": "2024-01-01T00:00:00Z",
#       "content": "评论内容（Markdown）",
#       "html": "原始HTML"
#     },
#     ...
#   ],
#   "total": 总数
# }
```

## 附件操作

### 上传图片/文件

⚠️ **重要**：上传图片推荐使用 **JPG 格式**，PNG 格式可能无法正常显示。

```python
result = api.upload_attachment("238854355", "/path/to/image.jpg")
# 返回: {"success": True, "filename": "image.jpg"}
```

### 在页面中引用已上传的图片

Markdown 的 `![](filename.jpg)` 会被转换为 `<ri:url>`，无法正确显示附件。需要使用精确编辑修改为 `<ri:attachment>` 格式：

```python
# 方法1: 使用精确编辑修改图片引用
api.edit_page(
    page_id="238854355",
    old_html='<ac:image><ri:url ri:value="chart.jpg" /></ac:image>',
    new_html='<ac:image><ri:attachment ri:filename="chart.jpg" /></ac:image>'
)
```

## 直接 HTML 操作

### 获取原始 HTML

```python
page_info = api.get_page_html("238854355")
# 返回: {"id": "...", "title": "...", "html": "<p>...</p>", "version": 1, "url": "..."}
```

### 直接更新 HTML

```python
result = api.update_page_html(
    page_id="238854355",
    html_content="<p>直接的HTML内容</p>",
    title=None  # 可选，不填保持原标题
)
```

## Markdown 转换支持

### Markdown → Confluence

| 格式 | Markdown | Confluence |
|------|----------|------------|
| 标题 | # ~ ###### | h1 ~ h6 |
| 粗体 | **text** | strong |
| 斜体 | *text* | em |
| 行内代码 | \`code\` | code |
| 链接 | [text](url) | a href |
| 图片 | ![alt](url) | ac:image |
| 无序列表 | - item | ul > li |
| 有序列表 | 1. item | ol > li |
| 引用 | > quote | blockquote |
| 表格 | \| A \| B \| | table |
| 代码块 | \`\`\`lang | code宏 |
| Mermaid | \`\`\`mermaid | mermaid-macro宏 |
| PlantUML | \`\`\`plantuml | plantuml宏 |

### Confluence → Markdown

反向转换同样支持所有上述格式。

## 功能速查表

| 功能 | 方法 | 说明 |
|------|------|------|
| 读取页面 | `read_page()` | 返回 Markdown + HTML |
| 创建页面 | `create_page()` | 使用 Markdown |
| 更新页面 | `update_page()` | 全量替换 |
| 精确编辑 | `edit_page()` | HTML 查找替换 ⭐推荐 |
| 插入内容 | `insert_content()` | 开头/结尾追加 |
| 移动页面 | `move_page()` | 移动到新父页面下 ⭐新增 |
| 删除页面 | `delete_page()` | - |
| 搜索页面 | `search()` | CQL 搜索 |
| 子页面 | `list_children()` | - |
| 空间列表 | `get_spaces()` | - |
| 列出表格 | `list_tables()` | 获取表格信息 |
| 插入列 | `insert_column()` | 表格操作 |
| 删除列 | `delete_column()` | 表格操作 |
| 更新单元格 | `update_table_cell()` | 修改指定单元格 ⭐ |
| 插入行 | `insert_table_row()` | 在表格中插入新行 |
| 删除行 | `delete_table_row()` | 删除表格中的行 |
| 上传附件 | `upload_attachment()` | 图片/文件 |
| 添加评论 | `add_comment()` | 向页面添加评论 |
| 获取评论 | `get_comments()` | 获取页面评论列表 |
| 获取 HTML | `get_page_html()` | 原始存储格式 |
| 更新 HTML | `update_page_html()` | 直接更新 |

## 编辑策略建议

### ⛔ 绝对禁止的行为
- **edit_page() 失败后，绝对不要使用 update_page() 重写整个页面！**
- 如果 edit_page() 返回"未找到要替换的内容"，应该：
  1. 重新调用 read_page() 获取最新 HTML
  2. 从 html 字段中更精确地复制要替换的 HTML 片段
  3. 如果是表格内容，改用 update_table_cell()
  4. 绝不能因为精确编辑失败就改用 update_page() 全量替换

### 表格内容修改（最常见场景）
- **修改表格单元格内容时，必须优先使用 update_table_cell()**
- 操作步骤：先 list_tables() → 确认索引 → update_table_cell()
- 只有当 update_table_cell() 因 colspan/rowspan 失败时，才用 edit_page() 直接编辑 HTML

### 优先使用 edit_page()（精确编辑）
- 修改正文段落、标题等非表格内容
- 需要保留原有格式和图片
- 从 read_page() 返回的 html 字段中找到要修改的 HTML 片段

### 使用 insert_content()
- 在开头添加总结、在结尾添加内容
- 不影响原有内容

### 仅在必要时使用 update_page()
- 仅当用户明确要求"重写整个页面"或"替换全部内容"时
- **绝不能作为 edit_page() 失败的后备方案！**

## 常见问题

### 401 认证失败
- 检查 `~/.confluence_credentials` 配置
- 用户名不带邮箱后缀

### 400 XHTML 解析错误
- 特殊字符需要转义 (API 已自动处理)
- 避免使用 emoji

### 页面创建失败
- 检查 space_key 是否正确
- 检查 parent_id 是否有效
- 标题在空间内必须唯一

### 精确编辑失败
- 确保 old_html 与页面中的 HTML 完全匹配
- 使用 `get_page_html()` 查看原始 HTML

---

## 踩坑指南（开发经验总结）

### 1. 图片附件格式（极其重要！）

**问题**：图片上传成功但在页面中显示为破图

**原因**：Confluence 有两种图片引用方式：

```html
<!-- ❌ 错误格式 - Markdown 转换默认生成这个，无法显示附件 -->
<ac:image><ri:url ri:value="chart.jpg" /></ac:image>

<!-- ✅ 正确格式 - 引用已上传的附件 -->
<ac:image><ri:attachment ri:filename="chart.jpg" /></ac:image>
```

**解决方案**：
- 上传附件后必须使用 `<ri:attachment>` 格式引用
- 用 `edit_page()` 将 `<ri:url>` 修改为 `<ri:attachment>`

### 2. 表格中插入图片的简化语法

表格单元格支持简化语法：

```markdown
| 名称 | 截图 |
|------|------|
| 功能A | [image:screenshot.jpg] |
```

会自动转换为：
```html
<td><ac:image><ri:attachment ri:filename="screenshot.jpg"/></ac:image></td>
```

使用 `update_table_cell()` 或 `insert_table_row()` 时可以直接用这个语法。

### 3. 表格中的 Markdown 格式

表格单元格中的 Markdown 会自动转换：

```markdown
| 状态 | 说明 |
|------|------|
| **已完成** | 任务 *已* 完成 |
```

转换为：
```html
<td><strong>已完成</strong></td>
<td>任务 <em>已</em> 完成</td>
```

### 4. 图片插入两步工作流

用户上传图片后要插入到 Confluence 页面，必须执行两步：

**步骤1：上传附件**
```python
result = api.upload_attachment(page_id, "/path/to/image.jpg")
# 返回 {"success": True, "filename": "image.jpg"}
```

**步骤2：插入到页面（必须！）**
```python
# 方法A：插入到表格单元格（推荐）
api.update_table_cell(
    page_id_or_url="238854355",
    table_index=0,
    row_index=1,
    column_index=2,
    content="[image:image.jpg]"
)

# 方法B：插入到页面内容
api.edit_page(
    page_id="238854355",
    old_html="<p>原内容</p>",
    new_html='<p>原内容</p><ac:image><ri:attachment ri:filename="image.jpg"/></ac:image>'
)
```

⚠️ **只执行步骤1不会在页面中显示图片！必须执行步骤2！**

### 5. 推荐使用 JPG 格式

上传图片推荐使用 **JPG 格式**，PNG 格式在某些 Confluence 配置下可能无法正常显示。

### 6. 编辑策略总结

| 场景 | 推荐方法 | 原因 |
|------|----------|------|
| 修改某段文字 | `edit_page()` | 精确替换，保留其他内容 |
| 修改表格单元格 | `update_table_cell()` | 直接定位，支持图片语法 ⭐ |
| 在表格插入图片 | `update_table_cell()` + `[image:xxx]` 语法 | 简单直观 |
| 插入表格行 | `insert_table_row()` | 支持批量插入 |
| 删除表格行 | `delete_table_row()` | 直接操作 |
| 追加内容 | `insert_content()` | 不影响原有内容 |
| 重写整页 | `update_page()` | 仅在明确要求时使用 |

### 7. Markdown 图片语法 `![](filename)` 支持

除了 `[image:filename]` 语法，标准 Markdown 图片语法也支持：

```markdown
| 截图 | 说明 |
|------|------|
| ![](step1.png) | 第一步 |
| ![截图](step2.png) | 第二步 |
```

会自动转换为 Confluence 附件格式。

### 8. 正则处理顺序（开发注意）

在 `_markdown_to_html` 中，**图片正则必须在链接正则之前**：

```python
# ✅ 正确顺序
text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, text)  # 先图片
text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)    # 后链接

# ❌ 错误顺序会导致 ![alt](url) 被当作链接处理
```

### 9. edit_page 的 HTML 内容处理

当使用 `edit_page()` 替换 HTML 内容时，即使 `new_html` 以 `<` 开头，其中的 `[image:xxx]` 和 `![](xxx)` 语法也会被自动转换：

```python
# 这样写会正确转换图片
api.edit_page(
    page_id="xxx",
    old_html="<td>旧内容</td>",
    new_html="<td>[image:new.png]</td>"  # 会转换为 <ac:image>
)
```

### 10. edit_page 双重转义 HTML 实体（v2.7.0 修复）

**问题**：使用 `edit_page()` 或 `create_page()` 上传包含 HTML 实体（如 `&mdash;`、`&nbsp;`、`&#8226;`）的 Markdown 时，`html.escape()` 会把 `&` 转义为 `&amp;`，导致页面上显示 `&amp;mdash;` 而非破折号 `—`。

**原因**：`markdown_to_confluence()` 内部调用 `html.escape()` 处理表格单元格和普通行，但 HTML 实体本身的 `&` 也被二次转义。

**解决方案**（v2.7.0 已修复）：
- 新增 `_unescape_double_encoded()` 方法，在 `html.escape()` 之后调用
- 通过正则 `&amp;(#?\w+;)` → `&\1` 还原被双重转义的实体

**如果你还在用 v2.6.0**，可以手动在 `new_html` 中直接使用 HTML 标签代替实体：
```python
# 绕过方案：用 Unicode 字符而非 HTML 实体
api.edit_page(page_id, old_html="...", new_html="<p>文字 — 更多</p>")  # 直接用 Unicode 破折号
```

### 11. 给文字/单元格加颜色标注（v2.7.0 新增）

**场景**：需要在表格中用颜色区分状态（如绿色=通过、红色=失败）。

**方法1：使用 `update_table_cell()` 设置单元格高亮颜色**
```python
# 设置浅绿背景
api.update_table_cell("page_id", 0, 1, 0, "已通过", highlight_color="#e3fcef")

# 设置浅红背景
api.update_table_cell("page_id", 0, 2, 0, "失败", highlight_color="#ffe7e7")
```

**方法2：使用 `insert_table_row()` 批量设置颜色**
```python
api.insert_table_row("page_id", 0, 2, ["通过", "说明"],
    cell_styles=[{"highlight_color": "#e3fcef"}, None])
```

**方法3：使用 `edit_page()` 设置文字颜色**
```python
api.edit_page(page_id, old_html="<p>普通文字</p>",
    new_html='<p><span style="color: rgb(255, 0, 0);">红色文字</span></p>')
```

**常用高亮颜色表**：

| 颜色 | 色值 | 用途 |
|------|------|------|
| 浅黄 | `#ffffce` | 警告、注意 |
| 浅绿 | `#e3fcef` | 成功、通过 |
| 浅红 | `#ffe7e7` | 失败、错误 |
| 浅蓝 | `#deebff` | 信息、进行中 |
| 浅紫 | `#eae6ff` | 特殊标记 |
| 浅灰 | `#f4f5f7` | 已废弃、不适用 |

## 依赖

```bash
pip install requests
```

## 参考文档

详细的 Confluence REST API 参考请查看：`CONFLUENCE_REST_API.md`
