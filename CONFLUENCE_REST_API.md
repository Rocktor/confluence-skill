# Confluence REST API 参考文档

> 适用于 Confluence Server/Data Center v6.15.4+

## 认证

**重要**：使用 `os_authType=basic` 参数绕过 SSO 认证。

```
GET /rest/api/content/{id}?os_authType=basic
Authorization: Basic base64(username:password)
```

## 核心端点

### 1. 获取页面内容

```
GET /rest/api/content/{id}
```

**参数**：
| 参数 | 说明 |
|------|------|
| expand | 展开字段：`body.storage`, `version`, `space`, `ancestors` |
| os_authType | 设为 `basic` 绕过 SSO |

**响应示例**：
```json
{
  "id": "123456",
  "type": "page",
  "title": "页面标题",
  "space": {"key": "SPACE"},
  "version": {"number": 1},
  "body": {
    "storage": {
      "value": "<p>HTML内容</p>",
      "representation": "storage"
    }
  },
  "_links": {
    "webui": "/pages/viewpage.action?pageId=123456"
  }
}
```

### 2. 创建页面

```
POST /rest/api/content
Content-Type: application/json
```

**请求体**：
```json
{
  "type": "page",
  "title": "新页面标题",
  "space": {"key": "SPACE"},
  "ancestors": [{"id": "父页面ID"}],
  "body": {
    "storage": {
      "value": "<p>HTML内容</p>",
      "representation": "storage"
    }
  }
}
```

### 3. 更新页面

```
PUT /rest/api/content/{id}
Content-Type: application/json
```

**请求体**：
```json
{
  "version": {"number": 2},
  "title": "更新后的标题",
  "type": "page",
  "body": {
    "storage": {
      "value": "<p>更新后的内容</p>",
      "representation": "storage"
    }
  }
}
```

**注意**：`version.number` 必须是当前版本 +1。

### 4. 删除页面

```
DELETE /rest/api/content/{id}
```

### 5. 搜索页面

```
GET /rest/api/content/search
```

**参数**：
| 参数 | 说明 |
|------|------|
| cql | CQL 查询语句 |
| limit | 返回数量限制 |
| start | 分页起始位置 |

**CQL 示例**：
```
# 按标题搜索
cql=title~"关键词"

# 在指定空间搜索
cql=space="SPACE" AND title~"关键词"

# 搜索页面类型
cql=type=page AND text~"内容关键词"
```

### 6. 获取子页面

```
GET /rest/api/content/{id}/child/page
```

### 7. 获取空间列表

```
GET /rest/api/space
```

**参数**：
| 参数 | 说明 |
|------|------|
| type | 空间类型：`global`, `personal` |
| limit | 返回数量限制 |

## 评论 API

### 1. 添加评论

```
POST /rest/api/content
Content-Type: application/json
```

**请求体**：
```json
{
  "type": "comment",
  "container": {
    "id": "页面ID"
  },
  "body": {
    "storage": {
      "value": "<p>评论内容</p>",
      "representation": "storage"
    }
  }
}
```

**响应示例**：
```json
{
  "id": "评论ID",
  "type": "comment",
  "_links": {
    "webui": "/pages/viewpage.action?pageId=xxx&focusedCommentId=yyy"
  }
}
```

### 2. 获取评论列表

```
GET /rest/api/content/{id}/child/comment
```

**参数**：
| 参数 | 说明 |
|------|------|
| expand | 展开字段：`body.storage`, `version`, `history` |
| limit | 返回数量限制（默认25） |
| start | 分页起始位置（默认0） |

**响应示例**：
```json
{
  "results": [
    {
      "id": "评论ID",
      "type": "comment",
      "body": {
        "storage": {
          "value": "<p>评论内容</p>"
        }
      },
      "history": {
        "createdDate": "2024-01-01T00:00:00Z",
        "createdBy": {
          "displayName": "用户名"
        }
      }
    }
  ],
  "size": 总数
}
```

### 3. 删除评论

```
DELETE /rest/api/content/{commentId}
```

## 附件 API

### 1. 上传附件

```
POST /rest/api/content/{pageId}/child/attachment
X-Atlassian-Token: nocheck
```

**注意**：需要移除 `Content-Type` header，使用 multipart/form-data。

### 2. 获取附件列表

```
GET /rest/api/content/{pageId}/child/attachment
```

### 3. 更新附件

```
POST /rest/api/content/{pageId}/child/attachment/{attachmentId}/data
X-Atlassian-Token: nocheck
```



### 基础格式

| 元素 | XHTML |
|------|-------|
| 标题 | `<h1>` ~ `<h6>` |
| 粗体 | `<strong>text</strong>` |
| 斜体 | `<em>text</em>` |
| 行内代码 | `<code>text</code>` |
| 链接 | `<a href="url">text</a>` |
| 段落 | `<p>text</p>` |
| 换行 | `<br />` |

### 列表

```xml
<!-- 无序列表 -->
<ul>
  <li>项目1</li>
  <li>项目2</li>
</ul>

<!-- 有序列表 -->
<ol>
  <li>项目1</li>
  <li>项目2</li>
</ol>
```

### 表格

```xml
<table>
  <tbody>
    <tr>
      <th>表头1</th>
      <th>表头2</th>
    </tr>
    <tr>
      <td>单元格1</td>
      <td>单元格2</td>
    </tr>
  </tbody>
</table>
```

### 代码块宏

```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[
def hello():
    print("Hello World")
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

### PlantUML 宏

```xml
<ac:structured-macro ac:name="plantuml">
  <ac:plain-text-body><![CDATA[
@startuml
Alice -> Bob: Hello
Bob --> Alice: Hi
@enduml
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

### Mermaid 宏

**注意**：宏名为 `mermaid-macro`（非标准，取决于插件）

```xml
<ac:structured-macro ac:name="mermaid-macro">
  <ac:plain-text-body><![CDATA[
graph TD
    A[开始] --> B[结束]
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

### 图片

```xml
<!-- 外部图片 -->
<ac:image>
  <ri:url ri:value="https://example.com/image.png" />
</ac:image>

<!-- 附件图片 -->
<ac:image>
  <ri:attachment ri:filename="image.png" />
</ac:image>
```

### 引用块

```xml
<blockquote>
  <p>引用内容</p>
</blockquote>
```

## 常见错误

| 状态码 | 原因 | 解决方案 |
|--------|------|----------|
| 401 | 认证失败 | 添加 `os_authType=basic` 参数 |
| 400 | XHTML 解析错误 | 转义特殊字符 (`&`, `<`, `>`) |
| 404 | 页面不存在 | 检查 pageId 是否正确 |
| 409 | 版本冲突 | 使用最新版本号 +1 |

## 特殊字符转义

在 Storage Format 中必须转义：
- `&` → `&amp;`
- `<` → `&lt;`
- `>` → `&gt;`
- `"` → `&quot;` (在属性中)

**注意**：不要使用 emoji，可能导致解析失败。

## 参考链接

- [Confluence REST API Documentation](https://docs.atlassian.com/ConfluenceServer/rest/6.15.4/)
- [Confluence Storage Format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
