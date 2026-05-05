# 踩坑指南（开发经验总结）

## 0. Confluence 10.x 认证方式变化

**问题**：换了新的 Personal Access Token 后仍然 401。

**原因**：Confluence Data Center 10.x 推荐 PAT Bearer 认证，不能把 PAT 当成 `username + api_key` 的 Basic Auth 来用。Confluence 10.0 起 Basic Auth 默认禁用。

**正确配置**：

```json
{
  "base_url": "https://docs.matrixback.com",
  "auth_type": "bearer",
  "api_key": "your_personal_access_token"
}
```

**正确请求形态**：

```http
Authorization: Bearer <personal_access_token>
```

只有旧实例或管理员明确开启 Basic Auth 时，才配置 `auth_type: "basic"`。

## 1. 图片附件格式（极其重要！）

**问题**：图片上传成功但在页面中显示为破图

**原因**：Confluence 有两种图片引用方式：

```html
<!-- 错误格式 - Markdown 转换默认生成这个，无法显示附件 -->
<ac:image><ri:url ri:value="chart.jpg" /></ac:image>

<!-- 正确格式 - 引用已上传的附件 -->
<ac:image><ri:attachment ri:filename="chart.jpg" /></ac:image>
```

**解决方案**：
- 上传附件后必须使用 `<ri:attachment>` 格式引用
- 用 `edit_page()` 将 `<ri:url>` 修改为 `<ri:attachment>`

## 2. 表格中插入图片的简化语法

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

## 3. 表格中的 Markdown 格式

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

## 4. 图片插入两步工作流

用户上传图片后要插入到 Confluence 页面，必须执行两步：

**步骤1：上传附件**
```python
result = api.upload_attachment(page_id, "/path/to/image.jpg")
# 返回 {"success": True, "filename": "image.jpg"}
```

**步骤2：插入到页面（必须！）**
```python
# 方法A：插入到表格单元格（推荐）
api.update_table_cell(page_id, 0, 1, 2, "[image:image.jpg]")

# 方法B：插入到页面内容
api.edit_page(page_id,
    old_html="<p>原内容</p>",
    new_html='<p>原内容</p><ac:image><ri:attachment ri:filename="image.jpg"/></ac:image>'
)
```

**只执行步骤1不会在页面中显示图片！必须执行步骤2！**

## 5. 推荐使用 JPG 格式

上传图片推荐使用 **JPG 格式**，PNG 格式在某些 Confluence 配置下可能无法正常显示。

## 6. 编辑策略总结

| 场景 | 推荐方法 | 原因 |
|------|----------|------|
| 修改某段文字 | `edit_page()` | 精确替换，保留其他内容 |
| 修改表格单元格 | `update_table_cell()` | 直接定位，支持图片语法 |
| 在表格插入图片 | `update_table_cell()` + `[image:xxx]` | 简单直观 |
| 插入表格行 | `insert_table_row()` | 支持批量插入 |
| 删除表格行 | `delete_table_row()` | 直接操作 |
| 追加内容 | `insert_content()` | 不影响原有内容 |
| 重写整页 | `update_page()` | 仅在明确要求时使用 |

## 7. Markdown 图片语法 `![](filename)` 支持

除了 `[image:filename]` 语法，标准 Markdown 图片语法也支持：

```markdown
| 截图 | 说明 |
|------|------|
| ![](step1.png) | 第一步 |
| ![截图](step2.png) | 第二步 |
```

会自动转换为 Confluence 附件格式。

## 8. 正则处理顺序（开发注意）

在 `_markdown_to_html` 中，**图片正则必须在链接正则之前**：

```python
# 正确顺序
text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, text)  # 先图片
text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)    # 后链接

# 错误顺序会导致 ![alt](url) 被当作链接处理
```

## 9. edit_page 的 HTML 内容处理

当使用 `edit_page()` 替换 HTML 内容时，即使 `new_html` 以 `<` 开头，其中的 `[image:xxx]` 和 `![](xxx)` 语法也会被自动转换：

```python
# 这样写会正确转换图片
api.edit_page(page_id,
    old_html="<td>旧内容</td>",
    new_html="<td>[image:new.png]</td>"  # 会转换为 <ac:image>
)
```

## 10. edit_page 双重转义 HTML 实体（v2.7.0 修复）

**问题**：使用 `edit_page()` 或 `create_page()` 上传包含 HTML 实体（如 `&mdash;`、`&nbsp;`、`&#8226;`）的 Markdown 时，`html.escape()` 会把 `&` 转义为 `&amp;`，导致页面上显示 `&amp;mdash;` 而非破折号。

**原因**：`markdown_to_confluence()` 内部调用 `html.escape()` 处理表格单元格和普通行，但 HTML 实体本身的 `&` 也被二次转义。

**解决方案**（v2.7.0 已修复）：
- 新增 `_unescape_double_encoded()` 方法，在 `html.escape()` 之后调用
- 通过正则 `&amp;(#?\w+;)` → `&\1` 还原被双重转义的实体

如果你还在用旧版本，可以手动在 `new_html` 中直接使用 Unicode 字符而非 HTML 实体：
```python
api.edit_page(page_id, old_html="...", new_html="<p>文字 — 更多</p>")  # 直接用 Unicode 破折号
```

## 11. 给文字/单元格加颜色标注

**方法1：使用 `update_table_cell()` 设置单元格高亮颜色**
```python
api.update_table_cell("page_id", 0, 1, 0, "已通过", highlight_color="#e3fcef")
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
