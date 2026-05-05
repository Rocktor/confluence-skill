# Changelog

## [3.0.0] - 2026-05-05

### 重大升级

- **适配 Confluence Data Center 10.x**：默认支持 Personal Access Token 的 `Authorization: Bearer <token>` 认证。
- **保留旧版 Basic Auth**：通过 `auth_type: "basic"` 继续兼容旧实例，Basic 模式才追加 `os_authType=basic`。
- **新版 URL 解析**：支持 `/spaces/{space}/pages/{pageId}/{title}`、`/pages/{pageId}`、`pageId=`、`/display/{space}/{title}` 和 tiny link。
- **分页能力统一**：新增内部 `_paginate()`，`search()`、`list_children()`、`get_spaces()`、`list_attachments()` 支持跨页拉取。

### 新增功能

- `test_connection()`：诊断 base_url、认证方式、HTTP 状态、当前用户，并在有权限时读取服务端信息。
- `get_current_user()`：读取当前 token 对应用户，用于认证诊断。
- `get_server_info()`：尽力读取管理员诊断接口 `/rest/troubleshooting/1.0/pre-upgrade/info`。
- `cql()`：直接执行 CQL 查询。
- `get_labels()` / `add_labels()`：读取和添加页面标签。
- `get_restrictions()`：读取页面 read/update 权限限制。

### 改进

- 附件上传、下载、正文图片 URL 生成不再强依赖 Basic Auth 参数。
- REST 错误统一通过 `_json_error()` 提取可读摘要。
- `create_page()` 和 `add_comment()` 同时接受 200/201 成功状态。
- 文档更新为 Confluence 10.x / Data Center PAT 认证优先。

---

## [2.8.1] - 2026-03-24

### Bug 修复

- **修复附件下载 401 认证失败**：`read_attachment()` 下载时缺少 `os_authType=basic` 参数，导致所有附件读取返回 401
- **修复 `_extract_images()` URL 缺认证**：生成的图片下载链接未带 `?os_authType=basic`，同样导致 401
- **修复 sys.path 硬编码**：初始化路径从 `.kiro` 改为 `Path.home() / '.claude/skills/confluence'`

### 改进

- **SKILL.md 重构**：908 行精简到 270 行，按 Progressive Disclosure 拆分为 5 个 references/ 文件
- **description 优化**：改为 "Use when..." 格式，覆盖 attachments/tables/comments 等关键词
- **智能附件读取策略**：先看正文引用，按需下载，避免盲目拉取所有附件

---

## [2.8.0] - 2026-03-13

### 新增功能 ✨

- **附件读取功能**：新增三个方法支持读取 Confluence 页面附件
  - `list_attachments()`: 列出页面所有附件及其元数据（文件名、大小、类型、下载链接等）
  - `read_attachment()`: 读取附件内容到内存，支持按文件名或索引查找
  - `download_attachment()`: 下载附件到本地文件系统

- **Word 文档自动解析** ⭐：`read_attachment()` 自动解析 `.docx` 文件为纯文本
  - 需要安装 `python-docx` 库（可选依赖）
  - 可通过 `parse_docx=False` 参数获取原始二进制

### 改进 🔧

- 智能识别文本文件：根据 MIME 类型和文件扩展名自动判断是否为文本文件
- 支持 `.md`, `.txt`, `.py`, `.js`, `.json`, `.xml`, `.html`, `.css`, `.yaml`, `.yml`, `.sh`, `.bash`, `.conf`, `.ini`, `.log` 等常见文本格式

### 使用示例

```python
# 列出附件
attachments = api.list_attachments("237096712")

# 读取第2个附件（索引从0开始）
result = api.read_attachment("237096712", attachment_index=1)
print(result['content'])

# 读取 Word 文档（自动解析为文本）
result = api.read_attachment("237096712", filename="report.docx")
print(result['content'])  # 纯文本内容

# 按文件名读取
result = api.read_attachment("237096712", filename="SKILL.md")

# 下载到本地
api.download_attachment("237096712", filename="doc.pdf", save_path="/tmp/doc.pdf")
```

---

## [2.7.1] - 之前版本

- 表格操作、精确编辑、评论管理等功能
