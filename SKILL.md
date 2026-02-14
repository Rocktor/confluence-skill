---
name: confluence
version: 2.4.1
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

使用前需要配置 `~/.confluence_credentials`：

```json
{
  "base_url": "https://docs.matrixback.com",
  "username": "rongtao.wang",
  "api_key": "your_api_key"
}
```

API Key 在 Confluence 个人设置中生成（Profile > Personal Access Tokens）。

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
# 支持 URL 或 pageId
result = api.read_page("https://docs.matrixback.com/pages/viewpage.action?pageId=238854355")
# 或
result = api.read_page("238854355")

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
    append=False             # True=追加，False=替换
)

# 返回: {"success": True, "message": "成功更新表格 0 的第 1 行第 2 列", "url": "..."}

# 支持 [image:filename] 语法插入图片
api.update_table_cell("238854355", 0, 1, 2, "[image:screenshot.png]")

# 支持 Markdown 格式
api.update_table_cell("238854355", 0, 1, 2, "**加粗** 和 *斜体*")
```

### 插入行

在表格中指定位置插入新行。

```python
result = api.insert_table_row(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格
    row_position=2,          # 插入位置（1=在表头后，2=第二行位置...）
    cell_values=["值1", "值2", "值3"],  # 各列的值
    is_header=False          # True=创建表头行，False=创建数据行
)

# 返回: {"success": True, "message": "成功在表格 0 的第 2 行位置插入新行", "url": "..."}

# 插入包含图片的行
api.insert_table_row("238854355", 0, 2, ["功能A", "[image:demo.png]", "说明文字"])
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

## 依赖

```bash
pip install requests
```

## 参考文档

详细的 Confluence REST API 参考请查看：`CONFLUENCE_REST_API.md`
