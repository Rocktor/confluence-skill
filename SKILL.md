---
name: confluence
description: >-
  Use when the user wants to read, create, edit, search, or delete Confluence
  pages; upload or download attachments and images; operate on tables (list
  tables, insert/delete rows and columns, update cells, set highlight colors);
  add or view comments; convert Markdown to/from Confluence storage format;
  move pages between parents; export Confluence content to Markdown. Use this
  skill whenever the user mentions confluence, cf, wiki, docs.matrixback.com,
  or any document management task involving the company wiki, even if they
  don't explicitly say "Confluence".
---

# Confluence 文档管理 Skill

## 触发条件

当用户提到以下内容时使用此技能：
- 读取/编辑/创建/搜索/删除 Confluence 页面
- 上传/下载/查看附件和图片
- 表格操作（增删行列、更新单元格、高亮颜色）
- 添加/查看评论
- Markdown 与 Confluence 互转
- 移动页面、导出文档

## 首次使用检测

**每次触发 Skill 时必须先执行**。详细引导流程见 `references/setup-guide.md`。

```python
from pathlib import Path
import json

creds_file = Path.home() / '.confluence_credentials'
if not creds_file.exists():
    print("SETUP_REQUIRED")  # → 阅读 references/setup-guide.md 引导用户配置
else:
    try:
        config = json.loads(creds_file.read_text())
        missing = [k for k in ['username', 'api_key'] if not config.get(k)]
        print(f"INCOMPLETE: missing {missing}" if missing else "OK")
    except Exception as e:
        print(f"INVALID: {e}")
```

## 初始化 API

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / '.claude/skills/confluence'))
from confluence_api import ConfluenceAPI
api = ConfluenceAPI()
```

## 认证配置

配置文件：`~/.confluence_credentials`（JSON，权限 600）

```json
{"base_url": "https://docs.matrixback.com", "username": "your.name", "api_key": "your_token"}
```

详细说明见 `references/setup-guide.md`。

## 快速决策矩阵

| 我想做什么 | 用什么方法 | 备注 |
|-----------|-----------|------|
| 读取页面内容 | `read_page()` | 返回 markdown + html + images |
| 创建新页面 | `create_page()` | 需要 parent_id + space_key |
| 修改某段文字 | `edit_page()` | 精确替换，保留其他内容 |
| 追加内容 | `insert_content()` | prepend=开头 / append=结尾 |
| 重写整页 | `update_page()` | 仅用户明确要求时 |
| 搜索页面 | `search()` | CQL 搜索 |
| 移动页面 | `move_page()` | 移到新父页面下 |
| 删除页面 | `delete_page()` | - |
| 列出子页面 | `list_children()` | - |
| 空间列表 | `get_spaces()` | - |
| 查看表格结构 | `list_tables()` | 获取行数、列数、表头 |
| 修改表格单元格 | `update_table_cell()` | 支持文本/图片/Markdown/高亮 |
| 在表格中加一行 | `insert_table_row()` | 支持 `[image:xxx]` 语法 |
| 在表格中删一行 | `delete_table_row()` | 指定行索引 |
| 在表格中加/删列 | `insert_column()` / `delete_column()` | 指定列位置 |
| 查看附件列表 | `list_attachments()` | 返回所有附件信息 |
| 读取附件内容 | `read_attachment()` | 按文件名或索引，自动解析 docx |
| 下载附件到本地 | `download_attachment()` | 保存到指定路径 |
| 上传图片/文件 | `upload_attachment()` → 再插入引用 | 必须两步！推荐 JPG |
| 添加评论 | `add_comment()` | 支持 Markdown |
| 获取评论 | `get_comments()` | 分页获取 |
| 获取原始 HTML | `get_page_html()` | Storage Format |
| 更新原始 HTML | `update_page_html()` | 直接操作 |

## 页面操作

### 读取页面

```python
result = api.read_page("238854355")  # 支持 pageId / URL / display URL / tiny link
# 返回: {id, title, markdown, html, url, space_key, version, images}
```

### 创建页面

```python
result = api.create_page(
    title="新页面标题",
    markdown="# 内容\n\n| A | B |\n|---|---|\n| 1 | 2 |",
    parent_id="214946975",
    space_key="cpb"
)
# 返回: {"success": True, "id": "xxx", "url": "https://..."}
```

### 精确编辑（推荐）

```python
# 1. 先读取页面获取 HTML
page = api.read_page("238854355")
# 2. 找到要修改的 HTML 片段进行替换
result = api.edit_page(
    page_id_or_url="238854355",
    old_html="<p>旧内容</p>",
    new_html="<p>新内容</p>"
)
```

### 插入内容

```python
api.insert_content("238854355", markdown="## 附录\n\n追加的内容", position="append")
```

### 更新页面（全量替换）

```python
api.update_page("238854355", markdown="# 全新内容", title="新标题")
```

### 搜索 / 移动 / 子页面

```python
pages = api.search("关键词", space="cpb", limit=10)
api.move_page("238873903", "240254369")  # 移动到新父页面
children = api.list_children("214946975")
```

## 表格操作

核心用法：先 `list_tables()` 确认索引，再操作。详细参数见 `references/table-operations.md`。

```python
# 列出表格
tables = api.list_tables("238854355")

# 更新单元格（支持文本/图片/Markdown/高亮）
api.update_table_cell("238854355", table_index=0, row_index=1, column_index=2,
    content="已完成", highlight_color="#e3fcef")

# 插入图片到单元格
api.update_table_cell("238854355", 0, 1, 2, "[image:screenshot.png]")

# 插入行（带高亮）
api.insert_table_row("238854355", 0, 2, ["值1", "值2", "值3"],
    cell_styles=[{"highlight_color": "#e3fcef"}, None, None])

# 删除行/列
api.delete_table_row("238854355", 0, row_index=2)
api.insert_column("238854355", 0, column_position=2, column_name="新列")
api.delete_column("238854355", 0, column_position=2)
```

**高亮颜色速查**：浅绿 `#e3fcef` / 浅红 `#ffe7e7` / 浅蓝 `#deebff` / 浅黄 `#ffffce` / 浅紫 `#eae6ff` / 浅灰 `#f4f5f7`

## 附件与图片

### 智能附件读取策略

- **先看正文**：先 `read_page()` 获取内容，根据正文中引用的附件（images 列表）决定下载哪些
- **按需下载**：只下载用户关心的或正文中引用的附件，不要一次性下载所有附件
- **例外情况**：如果页面本身就是附件列表页（正文很少、附件很多），或用户明确要求"列出所有附件"，才 `list_attachments()` 全量列出

### 列出与读取附件

```python
# 列出所有附件
attachments = api.list_attachments("237096712")

# 按文件名读取
result = api.read_attachment("237096712", filename="SKILL.md")

# 按索引读取
result = api.read_attachment("237096712", attachment_index=1)

# Word 文档自动解析为文本
result = api.read_attachment("237096712", filename="report.docx")
# result['parsed_from_docx'] = True

# 下载到本地
api.download_attachment("237096712", "SKILL.md", "/tmp/downloaded.md")
```

### 上传图片（两步工作流）

上传图片推荐 **JPG 格式**，PNG 可能无法正常显示。

```python
# 步骤1：上传
api.upload_attachment("238854355", "/path/to/image.jpg")

# 步骤2：插入引用（必须！否则图片不会显示）
# 方法A：插入到表格
api.update_table_cell("238854355", 0, 1, 2, "[image:image.jpg]")
# 方法B：插入到页面
api.edit_page("238854355",
    old_html="<p>原内容</p>",
    new_html='<p>原内容</p><ac:image><ri:attachment ri:filename="image.jpg"/></ac:image>')
```

## 评论操作

```python
# 添加评论
api.add_comment("238854355", content="这是一条评论")

# 获取评论列表
comments = api.get_comments("238854355", limit=25, start=0)
# 返回: {"comments": [{id, author, created, content, html}], "total": N}
```

## 编辑策略（重要规则）

### 绝对禁止
- **edit_page() 失败后，绝对不要用 update_page() 重写整个页面！**
- 应该：重新 read_page() → 更精确地复制 old_html → 重试 edit_page()

### 优先级
1. **表格内容** → `update_table_cell()`（先 list_tables 确认索引）
2. **正文段落/标题** → `edit_page()`（从 html 字段找到要改的片段）
3. **追加内容** → `insert_content()`
4. **全量替换** → `update_page()`（仅用户明确要求时）

## 常见问题速查

| 错误 | 原因 | 解决 |
|------|------|------|
| 401 | 认证失败 | 检查 `~/.confluence_credentials`，用户名不带邮箱后缀 |
| 400 | XHTML 解析错误 | 特殊字符需转义，避免 emoji |
| 404 | 页面不存在 | 检查 pageId |
| 精确编辑失败 | old_html 不匹配 | 用 `get_page_html()` 查看原始 HTML |
| 图片不显示 | 用了 `<ri:url>` | 改用 `<ri:attachment>`，见踩坑指南 |

更多排错经验见 `references/pitfalls.md`。

## 参考文档目录

| 文件 | 内容 | 何时阅读 |
|------|------|----------|
| `references/setup-guide.md` | 首次使用引导、认证配置详情 | 首次使用检测返回非 OK 时 |
| `references/table-operations.md` | 表格操作完整参数和示例 | 需要 insert_column/cell_styles 等高级用法时 |
| `references/pitfalls.md` | 11 条踩坑经验 | 遇到图片/编辑/格式问题时 |
| `references/markdown-conversion.md` | Markdown 转换对照表、直接 HTML 操作、页面标识格式 | 需要格式转换参考时 |
| `references/confluence-rest-api.md` | REST API 端点参考 | 需要底层 API 细节时 |

## 依赖

```bash
pip install requests
# 可选：pip install python-docx  # Word 文档解析
```
