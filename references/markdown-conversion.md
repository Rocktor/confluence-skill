# Markdown 转换参考

## Markdown → Confluence 格式对照

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

反向转换（Confluence → Markdown）同样支持所有上述格式。

## 直接 HTML 操作

当需要绕过 Markdown 转换，直接操作 Confluence Storage Format 时：

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

## 页面标识格式

所有接受 `page_id_or_url` 参数的方法均支持以下四种格式：

| 格式 | 示例 |
|------|------|
| 纯 pageId | `238854355` |
| pageId URL | `https://docs.matrixback.com/pages/viewpage.action?pageId=238854355` |
| display URL | `https://docs.matrixback.com/display/cpb/Page+Title` |
| tiny link | `https://docs.matrixback.com/x/TndqDg` |

display URL 通过 API 查询 spaceKey + title 解析；tiny link 通过跟随重定向解析为最终 URL。
