# 表格操作详解

## 列出页面中的表格

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
#   }
# ]
```

## 插入列

```python
result = api.insert_column(
    page_id_or_url="238854355",
    table_index=0,           # 第几个表格（从0开始）
    column_position=2,       # 插入位置（在第2列之前插入）
    column_name="新列名",
    default_value="",        # 数据行默认值
    header_style=None        # 可选样式
)
```

## 删除列

```python
result = api.delete_column(
    page_id_or_url="238854355",
    table_index=0,
    column_position=2        # 删除第几列
)
```

## 更新单元格

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
    highlight_color=None     # 高亮颜色，如 "#e3fcef"
)

# 支持 [image:filename] 语法插入图片
api.update_table_cell("238854355", 0, 1, 2, "[image:screenshot.png]")

# 支持 Markdown 格式
api.update_table_cell("238854355", 0, 1, 2, "**加粗** 和 *斜体*")

# 设置单元格高亮颜色（浅绿背景）
api.update_table_cell("238854355", 0, 1, 2, "已完成", highlight_color="#e3fcef")

# 自定义 CSS 样式
api.update_table_cell("238854355", 0, 1, 2, "重要", style="background-color: #ffe7e7; font-weight: bold;")
```

## 插入行

在表格中指定位置插入新行。

```python
result = api.insert_table_row(
    page_id_or_url="238854355",
    table_index=0,
    row_position=2,          # 插入位置（1=在表头后，2=第二行位置...）
    cell_values=["值1", "值2", "值3"],
    is_header=False,
    cell_styles=None         # 每个单元格的样式列表
)

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

## 删除行

```python
result = api.delete_table_row(
    page_id_or_url="238854355",
    table_index=0,
    row_index=2              # 要删除的行索引（0=表头，1=第一行数据...）
)
```

## 高亮颜色速查表

| 颜色 | 色值 | 用途 |
|------|------|------|
| 浅黄 | `#ffffce` | 警告、注意 |
| 浅绿 | `#e3fcef` | 成功、通过 |
| 浅红 | `#ffe7e7` | 失败、错误 |
| 浅蓝 | `#deebff` | 信息、进行中 |
| 浅紫 | `#eae6ff` | 特殊标记 |
| 浅灰 | `#f4f5f7` | 已废弃、不适用 |

## 文字颜色

使用 `edit_page()` 设置文字颜色：

```python
api.edit_page(page_id, old_html="<p>普通文字</p>",
    new_html='<p><span style="color: rgb(255, 0, 0);">红色文字</span></p>')
```

## 表格中插入图片的简化语法

表格单元格支持 `[image:filename]` 和 `![](filename)` 两种语法：

```markdown
| 名称 | 截图 |
|------|------|
| 功能A | [image:screenshot.jpg] |
| 功能B | ![](step2.png) |
```

会自动转换为 `<ac:image><ri:attachment ri:filename="xxx"/></ac:image>`。

使用 `update_table_cell()` 或 `insert_table_row()` 时可以直接用这些语法。
