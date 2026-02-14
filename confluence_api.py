#!/usr/bin/env python3
"""
Confluence API 客户端 - 全功能版

用法:
    from confluence_api import ConfluenceAPI

    api = ConfluenceAPI()  # 从 ~/.confluence_credentials 读取认证

    # 读取页面
    result = api.read_page("https://docs.matrixback.com/pages/viewpage.action?pageId=xxx")

    # 创建页面
    api.create_page(title="标题", markdown="内容", parent_id="xxx", space_key="cpb")

    # 搜索页面
    pages = api.search("关键词")

    # 表格操作
    tables = api.list_tables(page_id)
    api.insert_column(page_id, table_index=0, column_position=2, column_name="新列")
    api.delete_column(page_id, table_index=0, column_position=2)

    # 精确编辑
    api.edit_page(page_id, old_html="<p>旧内容</p>", new_html="<p>新内容</p>")
    api.insert_content(page_id, markdown="# 新章节", position="append")
"""

import os
import re
import json
import html
import requests
from pathlib import Path
from html import unescape
from typing import Optional, List, Dict, Any


class ConfluenceAPI:
    """Confluence API 客户端 - 全功能版"""

    DEFAULT_BASE_URL = "https://docs.matrixback.com"

    def __init__(self, base_url: str = None, api_key: str = None, username: str = None, password: str = None):
        """
        初始化 Confluence API 客户端

        优先使用传入参数，否则从 ~/.confluence_credentials 读取
        支持两种认证方式：
        1. API Key: username + api_key (优先)
        2. 用户名密码: username + password
        """
        config = self._load_credentials()

        self.base_url = (base_url or config.get('base_url') or self.DEFAULT_BASE_URL).rstrip('/')
        self.username = username or config.get('username')
        self.api_key = api_key or config.get('api_key')
        self.password = password or config.get('password')

        if not self.username:
            raise ValueError("缺少用户名，请配置 ~/.confluence_credentials")

        # 优先使用 API Key，否则使用密码
        if self.api_key:
            auth_credential = self.api_key
        elif self.password:
            auth_credential = self.password
        else:
            raise ValueError("缺少认证信息（api_key 或 password），请配置 ~/.confluence_credentials")

        self.session = requests.Session()
        self.session.auth = (self.username, auth_credential)
        self.session.headers.update({'Content-Type': 'application/json'})

    def _load_credentials(self) -> Dict[str, str]:
        """从配置文件加载认证信息"""
        config_file = Path.home() / '.confluence_credentials'

        if not config_file.exists():
            return {}

        try:
            content = config_file.read_text().strip()

            # 尝试 JSON 格式
            if content.startswith('{'):
                return json.loads(content)

            # 简单格式: username:password 或 username:password@base_url
            if ':' in content:
                parts = content.split(':')
                if len(parts) == 2:
                    return {'username': parts[0], 'password': parts[1]}
                elif len(parts) >= 3:
                    # username:password 格式，可能密码包含冒号
                    return {'username': parts[0], 'password': ':'.join(parts[1:])}

            return {}
        except Exception:
            return {}

    def _request(self, method: str, endpoint: str, params: Dict = None,
                 data: Dict = None, timeout: int = 30) -> requests.Response:
        """发送 API 请求"""
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}
        params["os_authType"] = "basic"

        return self.session.request(
            method, url, params=params,
            data=json.dumps(data) if data else None,
            timeout=timeout
        )

    def _extract_page_id(self, page_id_or_url: str) -> str:
        """从 URL 或直接 ID 提取页面 ID"""
        s = str(page_id_or_url)
        # pageId=xxx 格式
        if "pageId=" in s:
            match = re.search(r'pageId=(\d+)', s)
            return match.group(1) if match else s
        # /display/SPACE/Title 格式
        match = re.match(r'https?://.+/display/([^/]+)/(.+?)(?:\?.*)?$', s)
        if match:
            space_key = match.group(1)
            title = requests.utils.unquote(match.group(2)).replace('+', ' ')
            resp = self._request("GET", "/rest/api/content", params={
                "spaceKey": space_key,
                "title": title,
                "limit": 1
            })
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"]
            raise ValueError(f"未找到页面: space={space_key}, title={title}")
        return s

    def _extract_images(self, html_content: str, page_id: str) -> List[Dict[str, str]]:
        """从 HTML 内容中提取图片信息"""
        images = []

        # 查找所有附件图片: <ri:attachment ri:filename="xxx.png" />
        attachment_pattern = r'<ri:attachment ri:filename="([^"]+)"'
        for match in re.finditer(attachment_pattern, html_content):
            filename = match.group(1)
            download_url = f"{self.base_url}/download/attachments/{page_id}/{filename}"
            images.append({
                'filename': filename,
                'url': download_url,
                'type': 'attachment'
            })

        # 查找外部图片: <ri:url ri:value="https://..." />
        url_pattern = r'<ri:url ri:value="([^"]+)"'
        for match in re.finditer(url_pattern, html_content):
            url = match.group(1)
            if any(url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
                images.append({
                    'filename': url.split('/')[-1],
                    'url': url,
                    'type': 'external'
                })

        return images

    # ============ 核心 API 方法 ============

    def read_page(self, page_id_or_url: str, include_images: bool = True) -> Optional[Dict[str, Any]]:
        """
        读取页面内容并转换为 Markdown

        Args:
            page_id_or_url: 页面 ID 或完整 URL
            include_images: 是否提取图片信息（默认 True）

        Returns:
            {id, title, markdown, html, url, space_key, version, images} 或 None
        """
        page_id = self._extract_page_id(page_id_or_url)

        response = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "body.storage,space,version"}
        )

        if response.status_code != 200:
            return None

        data = response.json()
        html_content = data['body']['storage']['value']

        result = {
            "id": data['id'],
            "title": data['title'],
            "markdown": self.confluence_to_markdown(html_content),
            "html": html_content,  # 原始 HTML，用于精确编辑
            "url": f"{self.base_url}{data['_links']['webui']}",
            "space_key": data['space']['key'],
            "version": data['version']['number']
        }

        # 提取图片信息
        if include_images:
            images = self._extract_images(html_content, page_id)
            if images:
                result['images'] = images

        return result

    def get_page_html(self, page_id_or_url: str) -> Optional[Dict[str, Any]]:
        """
        获取页面原始 HTML（不转换为 Markdown）

        Returns:
            {id, title, html, version, url} 或 None
        """
        page_id = self._extract_page_id(page_id_or_url)

        response = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "body.storage,space,version"}
        )

        if response.status_code != 200:
            return None

        data = response.json()
        return {
            "id": data['id'],
            "title": data['title'],
            "html": data['body']['storage']['value'],
            "version": data['version']['number'],
            "url": f"{self.base_url}{data['_links']['webui']}"
        }

    def create_page(self, title: str, markdown: str, parent_id: str,
                    space_key: str) -> Dict[str, Any]:
        """
        创建新页面

        Args:
            title: 页面标题
            markdown: Markdown 内容
            parent_id: 父页面 ID
            space_key: 空间 Key

        Returns:
            {success, id, url} 或 {success, error}
        """
        html_content = self.markdown_to_confluence(markdown)

        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "ancestors": [{"id": str(parent_id)}],
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }

        response = self._request("POST", "/rest/api/content", data=data)

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "id": result['id'],
                "url": f"{self.base_url}{result['_links']['webui']}"
            }
        return {"success": False, "error": response.text, "status": response.status_code}

    def update_page(self, page_id: str, markdown: str, title: str = None) -> Dict[str, Any]:
        """
        更新页面内容（使用 Markdown）

        Args:
            page_id: 页面 ID
            markdown: 新的 Markdown 内容
            title: 新标题 (可选，默认保持原标题)

        Returns:
            {success, url} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id)

        # 先获取当前页面信息
        current = self.read_page(page_id)
        if not current:
            return {"success": False, "error": "页面不存在"}

        html_content = self.markdown_to_confluence(markdown)

        data = {
            "type": "page",
            "title": title or current['title'],
            "version": {"number": current['version'] + 1},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }

        response = self._request("PUT", f"/rest/api/content/{page_id}", data=data)

        if response.status_code == 200:
            return {"success": True, "url": current['url']}
        return {"success": False, "error": response.text}

    def update_page_html(self, page_id: str, html_content: str, title: str = None) -> Dict[str, Any]:
        """
        直接更新页面 HTML（不经过 Markdown 转换）

        Args:
            page_id: 页面 ID
            html_content: 新的 HTML 内容
            title: 新标题 (可选)

        Returns:
            {success, url} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id)

        # 获取当前页面信息
        page_info = self.get_page_html(page_id)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        data = {
            "type": "page",
            "title": title or page_info['title'],
            "version": {"number": page_info['version'] + 1},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }

        response = self._request("PUT", f"/rest/api/content/{page_id}", data=data)

        if response.status_code == 200:
            return {"success": True, "url": page_info['url']}
        return {"success": False, "error": response.text}

    def edit_page(self, page_id_or_url: str, old_html: str, new_html: str) -> Dict[str, Any]:
        """
        精确编辑：在原始 HTML 中查找并替换指定内容

        Args:
            page_id_or_url: 页面 ID 或 URL
            old_html: 要替换的原始 HTML 片段
            new_html: 替换后的新内容（HTML 或 Markdown）

        Returns:
            {success, url, message} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id_or_url)

        # 获取当前页面
        page_info = self.get_page_html(page_id)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        current_html = page_info['html']

        # 检查 old_html 是否存在
        if old_html not in current_html:
            return {
                "success": False,
                "error": "未找到要替换的内容。请确保 old_html 与页面中的 HTML 完全匹配。"
                         "建议：1) 重新 read_page() 获取最新 HTML；"
                         "2) 如果是修改表格内容，请改用 update_table_cell()；"
                         "3) 请勿使用 update_page() 重写整个页面！"
            }

        # 如果 new_html 看起来像 Markdown，转换为 HTML
        if new_html.strip() and not new_html.strip().startswith('<'):
            new_html = self.markdown_to_confluence(new_html)

        # 精确替换（只替换第一个匹配）
        updated_html = current_html.replace(old_html, new_html, 1)

        # 更新页面
        result = self.update_page_html(page_id, updated_html)

        if result['success']:
            result['message'] = "内容已精确替换"
        return result

    def insert_content(self, page_id_or_url: str, markdown: str, position: str = "append") -> Dict[str, Any]:
        """
        在页面开头或结尾插入新内容，保留原有内容

        Args:
            page_id_or_url: 页面 ID 或 URL
            markdown: 要插入的 Markdown 内容
            position: "prepend"（开头）或 "append"（结尾）

        Returns:
            {success, url, position} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id_or_url)

        # 获取当前页面
        page_info = self.get_page_html(page_id)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        current_html = page_info['html']
        new_html = self.markdown_to_confluence(markdown)

        # 插入到指定位置
        if position == "prepend":
            combined_html = new_html + current_html
        else:
            combined_html = current_html + new_html

        # 更新页面
        result = self.update_page_html(page_id, combined_html)

        if result['success']:
            result['position'] = position
        return result

    def delete_page(self, page_id: str) -> bool:
        """删除页面"""
        page_id = self._extract_page_id(page_id)
        response = self._request("DELETE", f"/rest/api/content/{page_id}")
        return response.status_code == 204

    def move_page(self, page_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        移动页面到新的父页面下

        Args:
            page_id: 要移动的页面 ID 或 URL
            new_parent_id: 新的父页面 ID 或 URL

        Returns:
            {"success": True/False, "page_id": str, "new_parent_id": str, "title": str, "url": str}
        """
        page_id = self._extract_page_id(page_id)
        new_parent_id = self._extract_page_id(new_parent_id)

        # Get current page info
        response = self._request(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "version,space"}
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to get page info: {response.status_code}"
            }

        page_data = response.json()
        current_version = page_data['version']['number']
        space_key = page_data['space']['key']
        title = page_data['title']

        # Update page with new parent
        update_data = {
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "ancestors": [{"id": new_parent_id}]
        }

        response = self._request(
            "PUT",
            f"/rest/api/content/{page_id}",
            data=update_data
        )

        if response.status_code == 200:
            return {
                "success": True,
                "page_id": page_id,
                "new_parent_id": new_parent_id,
                "title": title,
                "url": f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            }
        else:
            error_msg = response.text
            try:
                error_msg = response.json().get('message', response.text)
            except:
                pass
            return {
                "success": False,
                "error": f"Failed to move page: {error_msg}"
            }

    def search(self, keyword: str, space: str = None, limit: int = 10) -> List[Dict]:
        """
        搜索页面

        Args:
            keyword: 搜索关键词
            space: 空间 Key (可选)
            limit: 返回数量限制

        Returns:
            [{id, title, space_key, url}]
        """
        cql = f'type=page AND title~"{keyword}"'
        if space:
            cql += f' AND space="{space}"'

        response = self._request(
            "GET",
            "/rest/api/content/search",
            params={"cql": cql, "limit": limit}
        )

        if response.status_code != 200:
            return []

        results = []
        for item in response.json().get('results', []):
            results.append({
                "id": item['id'],
                "title": item['title'],
                "space_key": item.get('space', {}).get('key', ''),
                "url": f"{self.base_url}{item['_links']['webui']}"
            })
        return results

    def list_children(self, page_id: str) -> List[Dict]:
        """
        列出子页面

        Args:
            page_id: 父页面 ID

        Returns:
            [{id, title, url}]
        """
        page_id = self._extract_page_id(page_id)

        response = self._request(
            "GET",
            f"/rest/api/content/{page_id}/child/page",
            params={"limit": 100}
        )

        if response.status_code != 200:
            return []

        results = []
        for item in response.json().get('results', []):
            results.append({
                "id": item['id'],
                "title": item['title'],
                "url": f"{self.base_url}{item['_links']['webui']}"
            })
        return results

    def get_spaces(self, limit: int = 50) -> List[Dict]:
        """获取空间列表"""
        response = self._request("GET", "/rest/api/space", params={"limit": limit})

        if response.status_code != 200:
            return []

        results = []
        for item in response.json().get('results', []):
            results.append({
                "key": item['key'],
                "name": item['name'],
                "type": item.get('type', '')
            })
        return results

    # ============ 附件操作 ============

    def upload_attachment(self, page_id: str, file_path: str) -> Dict[str, Any]:
        """
        上传附件到 Confluence 页面

        Args:
            page_id: 目标页面 ID
            file_path: 文件路径

        Returns:
            {success, filename} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id)
        url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
        params = {"os_authType": "basic"}

        filename = Path(file_path).name

        # 先检查是否已存在
        resp = self.session.get(url, params=params)
        existing = {a['title']: a['id'] for a in resp.json().get('results', [])}

        with open(file_path, 'rb') as f:
            # 根据文件扩展名确定 MIME 类型
            ext = Path(file_path).suffix.lower()
            mime_types = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.svg': 'image/svg+xml', '.pdf': 'application/pdf',
            }
            content_type = mime_types.get(ext, 'application/octet-stream')

            files = {'file': (filename, f, content_type)}

            # 移除 Content-Type header，添加 X-Atlassian-Token
            old_ct = self.session.headers.pop('Content-Type', None)
            self.session.headers['X-Atlassian-Token'] = 'nocheck'

            try:
                if filename in existing:
                    # 更新已存在的附件
                    att_id = existing[filename]
                    update_url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment/{att_id}/data"
                    resp = self.session.post(update_url, files=files, params=params)
                else:
                    # 创建新附件
                    resp = self.session.post(url, files=files, params=params)

                if resp.status_code in [200, 201]:
                    return {"success": True, "filename": filename}
                return {"success": False, "error": resp.text}
            finally:
                # 恢复 header
                if old_ct:
                    self.session.headers['Content-Type'] = old_ct
                self.session.headers.pop('X-Atlassian-Token', None)

    # ============ 评论操作 ============

    def add_comment(self, page_id_or_url: str, content: str) -> Dict[str, Any]:
        """
        向页面添加评论

        Args:
            page_id_or_url: 页面 ID 或 URL
            content: 评论内容（支持 Markdown 或 HTML）

        Returns:
            {success, id, url} 或 {success, error}
        """
        page_id = self._extract_page_id(page_id_or_url)

        # 判断 content 是否为 HTML（以 < 开头），否则转换 Markdown
        if content.strip() and not content.strip().startswith('<'):
            # 是 Markdown，转换为 HTML
            html_content = self.markdown_to_confluence(content)
        else:
            # 已是 HTML，直接使用
            html_content = content

        data = {
            "type": "comment",
            "container": {
                "id": page_id,
                "type": "page"
            },
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }

        response = self._request("POST", "/rest/api/content", data=data)

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "id": result['id'],
                "url": f"{self.base_url}{result['_links']['webui']}"
            }
        return {"success": False, "error": response.text, "status": response.status_code}

    def get_comments(self, page_id_or_url: str, limit: int = 25, start: int = 0) -> Dict[str, Any]:
        """
        获取页面的所有评论

        Args:
            page_id_or_url: 页面 ID 或 URL
            limit: 每次获取数量（默认 25）
            start: 分页起始位置（默认 0）

        Returns:
            {comments: [{id, author, created, content, html}], total}
        """
        page_id = self._extract_page_id(page_id_or_url)

        response = self._request(
            "GET",
            f"/rest/api/content/{page_id}/child/comment",
            params={
                "expand": "body.storage,version,history",
                "limit": limit,
                "start": start
            }
        )

        if response.status_code != 200:
            return {"comments": [], "total": 0}

        data = response.json()
        comments = []

        for item in data.get('results', []):
            html_content = item.get('body', {}).get('storage', {}).get('value', '')
            markdown_content = self.confluence_to_markdown(html_content)

            # 提取作者信息（从 history 中获取创建者）
            author = "Unknown"
            if 'history' in item and 'createdBy' in item['history']:
                author = item['history']['createdBy'].get('displayName', 'Unknown')

            comments.append({
                "id": item['id'],
                "author": author,
                "created": item.get('history', {}).get('createdDate', ''),
                "content": markdown_content,
                "html": html_content
            })

        return {
            "comments": comments,
            "total": data.get('size', 0)
        }

    # ============ 表格操作 ============

    def list_tables(self, page_id_or_url: str) -> List[Dict[str, Any]]:
        """
        列出页面中的所有表格信息

        Returns:
            [
                {
                    "index": 0,
                    "header_row": ["项目", "需求", "类", ...],
                    "row_count": 10,
                    "col_count": 8,
                    "preview": "项目 | 需求 | 类 | ..."
                },
                ...
            ]
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return []

        html_content = page_info['html']
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html_content, re.DOTALL)

        result = []
        for idx, table in enumerate(tables):
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)

            # 找表头行（第一个包含 <th> 的行，或第一行）
            header_row = []
            col_count = 0

            for row in rows:
                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
                if cells:
                    # 提取文本内容
                    header_row = [re.sub(r'<[^>]+>', '', c).strip()[:30] for c in cells]
                    col_count = len(cells)
                    break

            result.append({
                "index": idx,
                "header_row": header_row,
                "row_count": len(rows),
                "col_count": col_count,
                "preview": " | ".join(header_row[:5]) + ("..." if len(header_row) > 5 else "")
            })

        return result

    def insert_column(self, page_id_or_url: str, table_index: int,
                      column_position: int, column_name: str,
                      default_value: str = "",
                      header_style: str = None) -> Dict[str, Any]:
        """
        在表格中插入新列

        Args:
            page_id_or_url: 页面 ID 或 URL
            table_index: 表格索引（从 0 开始）
            column_position: 插入位置（从 0 开始，在该位置之前插入）
            column_name: 新列的表头名称
            default_value: 数据行的默认值（默认为空）
            header_style: 表头样式，如 "text-align: left;width: 100.0px;"

        Returns:
            {success, message, url} 或 {success, error}
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        html_content = page_info['html']

        # 找到所有表格
        table_pattern = r'(<table[^>]*>)(.*?)(</table>)'
        tables = list(re.finditer(table_pattern, html_content, re.DOTALL))

        if table_index >= len(tables):
            return {"success": False, "error": f"表格索引 {table_index} 超出范围，页面只有 {len(tables)} 个表格"}

        target_table = tables[table_index]
        table_start = target_table.group(1)
        table_content = target_table.group(2)
        table_end = target_table.group(3)

        # 处理表格中的每一行
        def process_row(row_match):
            row_tag = row_match.group(1)  # <tr...>
            row_content = row_match.group(2)
            row_end = row_match.group(3)  # </tr>

            # 找到所有单元格（th 或 td）
            cell_pattern = r'(<t[hd][^>]*>)(.*?)(</t[hd]>)'
            cells = list(re.finditer(cell_pattern, row_content, re.DOTALL))

            if not cells:
                return row_match.group(0)

            # 检查这一行是否是跨列的标题行（colspan > 1 的单一单元格）
            first_cell_tag = cells[0].group(1)
            colspan_match = re.search(r'colspan="(\d+)"', first_cell_tag)
            if colspan_match and len(cells) <= 2:
                # 这是跨列标题行，增加 colspan
                old_colspan = int(colspan_match.group(1))
                new_colspan = old_colspan + 1
                new_first_cell_tag = first_cell_tag.replace(
                    f'colspan="{old_colspan}"',
                    f'colspan="{new_colspan}"'
                )
                new_row_content = row_content.replace(first_cell_tag, new_first_cell_tag, 1)
                return row_tag + new_row_content + row_end

            # 确定插入位置
            insert_pos = min(column_position, len(cells))

            # 判断是表头行还是数据行
            is_header_row = '<th' in cells[0].group(1)

            # 构造新单元格
            if is_header_row:
                # 复制相邻单元格的样式
                if insert_pos > 0:
                    ref_cell_tag = cells[insert_pos - 1].group(1)
                else:
                    ref_cell_tag = cells[0].group(1)

                # 提取样式
                style_match = re.search(r'style="([^"]*)"', ref_cell_tag)
                style = style_match.group(1) if style_match else ""
                if header_style:
                    style = header_style

                new_cell = f'<th style="{style}">{column_name}</th>'
            else:
                # 数据行 - 复制相邻单元格的样式
                if insert_pos > 0:
                    ref_cell_tag = cells[insert_pos - 1].group(1)
                else:
                    ref_cell_tag = cells[0].group(1)

                # 提取样式（包括 highlight 等）
                style_match = re.search(r'style="([^"]*)"', ref_cell_tag)
                class_match = re.search(r'class="([^"]*)"', ref_cell_tag)
                highlight_match = re.search(r'data-highlight-colour="([^"]*)"', ref_cell_tag)

                style = style_match.group(1) if style_match else ""
                cell_class = class_match.group(1) if class_match else ""
                highlight = highlight_match.group(1) if highlight_match else ""

                new_cell = '<td'
                if cell_class:
                    new_cell += f' class="{cell_class}"'
                if style:
                    new_cell += f' style="{style}"'
                if highlight:
                    new_cell += f' data-highlight-colour="{highlight}"'
                new_cell += f'>{default_value}</td>'

            # 在指定位置插入新单元格
            if insert_pos == 0:
                new_row_content = new_cell + row_content
            elif insert_pos >= len(cells):
                new_row_content = row_content + new_cell
            else:
                # 在 insert_pos 位置的单元格之前插入
                insert_point = cells[insert_pos].start()
                new_row_content = row_content[:insert_point] + new_cell + row_content[insert_point:]

            return row_tag + new_row_content + row_end

        # 处理所有行
        row_pattern = r'(<tr[^>]*>)(.*?)(</tr>)'
        new_table_content = re.sub(row_pattern, process_row, table_content, flags=re.DOTALL)

        # 重建表格
        new_table = table_start + new_table_content + table_end

        # 替换原表格
        new_html = html_content[:target_table.start()] + new_table + html_content[target_table.end():]

        # 更新页面
        result = self.update_page_html(page_info['id'], new_html)

        if result['success']:
            return {
                "success": True,
                "message": f"成功在表格 {table_index} 的第 {column_position} 列位置插入列 '{column_name}'",
                "url": result['url']
            }
        return result

    def delete_column(self, page_id_or_url: str, table_index: int,
                      column_position: int) -> Dict[str, Any]:
        """
        删除表格中的指定列

        Args:
            page_id_or_url: 页面 ID 或 URL
            table_index: 表格索引（从 0 开始）
            column_position: 要删除的列位置（从 0 开始）

        Returns:
            {success, message, url} 或 {success, error}
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        html_content = page_info['html']

        # 找到所有表格
        table_pattern = r'(<table[^>]*>)(.*?)(</table>)'
        tables = list(re.finditer(table_pattern, html_content, re.DOTALL))

        if table_index >= len(tables):
            return {"success": False, "error": f"表格索引 {table_index} 超出范围"}

        target_table = tables[table_index]
        table_start = target_table.group(1)
        table_content = target_table.group(2)
        table_end = target_table.group(3)

        # 处理表格中的每一行
        def process_row(row_match):
            row_tag = row_match.group(1)
            row_content = row_match.group(2)
            row_end = row_match.group(3)

            # 找到所有单元格
            cell_pattern = r'<t[hd][^>]*>.*?</t[hd]>'
            cells = list(re.finditer(cell_pattern, row_content, re.DOTALL))

            if not cells or column_position >= len(cells):
                return row_match.group(0)

            # 检查是否是跨列标题行
            first_cell = cells[0].group(0)
            colspan_match = re.search(r'colspan="(\d+)"', first_cell)
            if colspan_match and len(cells) <= 2:
                # 跨列标题行，减少 colspan
                old_colspan = int(colspan_match.group(1))
                if old_colspan > 1:
                    new_first_cell = first_cell.replace(
                        f'colspan="{old_colspan}"',
                        f'colspan="{old_colspan - 1}"'
                    )
                    new_row_content = row_content.replace(first_cell, new_first_cell, 1)
                    return row_tag + new_row_content + row_end
                return row_match.group(0)

            # 删除指定位置的单元格
            target_cell = cells[column_position]
            new_row_content = row_content[:target_cell.start()] + row_content[target_cell.end():]

            return row_tag + new_row_content + row_end

        # 处理所有行
        row_pattern = r'(<tr[^>]*>)(.*?)(</tr>)'
        new_table_content = re.sub(row_pattern, process_row, table_content, flags=re.DOTALL)

        # 重建表格
        new_table = table_start + new_table_content + table_end

        # 替换原表格
        new_html = html_content[:target_table.start()] + new_table + html_content[target_table.end():]

        # 更新页面
        result = self.update_page_html(page_info['id'], new_html)

        if result['success']:
            return {
                "success": True,
                "message": f"成功删除表格 {table_index} 的第 {column_position} 列",
                "url": result['url']
            }
        return result

    def update_table_cell(self, page_id_or_url: str, table_index: int, row_index: int,
                          column_index: int, content: str, append: bool = False) -> Dict[str, Any]:
        """
        更新表格中指定单元格的内容

        Args:
            page_id_or_url: 页面 ID 或 URL
            table_index: 表格索引（从 0 开始）
            row_index: 行索引（0=表头行，1=第一行数据）
            column_index: 列索引（从 0 开始）
            content: 新内容（支持文本、HTML、Markdown 或 [image:filename.png] 语法）
            append: 如果为 True，追加到现有内容；否则替换

        Returns:
            {success, message, url} 或 {success, error}
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        html_content = page_info['html']

        # 找到所有表格
        tables = list(re.finditer(r'<table[^>]*>.*?</table>', html_content, re.DOTALL))

        if table_index >= len(tables):
            return {"success": False, "error": f"表格索引 {table_index} 超出范围（共 {len(tables)} 个表格）"}

        table_match = tables[table_index]
        table_html = table_match.group(0)

        # 找到所有行
        rows = list(re.finditer(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL))

        if row_index >= len(rows):
            return {"success": False, "error": f"行索引 {row_index} 超出范围（共 {len(rows)} 行）"}

        row_match = rows[row_index]
        row_html = row_match.group(0)

        # 检查是否有合并单元格
        if 'colspan' in row_html.lower() or 'rowspan' in row_html.lower():
            return {"success": False, "error": "该行包含合并单元格（colspan/rowspan），请使用 edit_page 直接编辑 HTML"}

        # 找到该行的所有单元格
        cells = list(re.finditer(r'<(t[hd])([^>]*)>(.*?)</\1>', row_html, re.DOTALL))

        if column_index >= len(cells):
            return {"success": False, "error": f"列索引 {column_index} 超出范围（该行共 {len(cells)} 列）"}

        cell_match = cells[column_index]
        tag = cell_match.group(1)  # 'th' or 'td'
        attrs = cell_match.group(2)  # 保留样式等属性
        old_content = cell_match.group(3)

        # 处理内容：支持 [image:filename] 语法
        new_content = self._process_cell_content(content)

        # 追加或替换
        if append:
            final_content = old_content + new_content
        else:
            final_content = new_content

        # 构建新单元格
        new_cell = f'<{tag}{attrs}>{final_content}</{tag}>'

        # 替换单元格
        new_row_html = row_html[:cell_match.start()] + new_cell + row_html[cell_match.end():]

        # 替换行
        new_table_html = table_html[:row_match.start()] + new_row_html + table_html[row_match.end():]

        # 替换表格
        new_html = html_content[:table_match.start()] + new_table_html + html_content[table_match.end():]

        # 更新页面
        result = self.update_page_html(page_info['id'], new_html)

        if result['success']:
            return {
                "success": True,
                "message": f"成功更新表格 {table_index} 的第 {row_index} 行第 {column_index} 列",
                "url": result['url']
            }
        return result

    def insert_table_row(self, page_id_or_url: str, table_index: int, row_position: int,
                         cell_values: List[str], is_header: bool = False) -> Dict[str, Any]:
        """
        在表格中插入新行

        Args:
            page_id_or_url: 页面 ID 或 URL
            table_index: 表格索引（从 0 开始）
            row_position: 插入位置（0=在表头之前，1=在表头之后，...）
            cell_values: 单元格值列表
            is_header: 如果为 True，创建 <th> 单元格；否则创建 <td>

        Returns:
            {success, message, url} 或 {success, error}
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        html_content = page_info['html']

        # 找到所有表格
        tables = list(re.finditer(r'<table[^>]*>.*?</table>', html_content, re.DOTALL))

        if table_index >= len(tables):
            return {"success": False, "error": f"表格索引 {table_index} 超出范围（共 {len(tables)} 个表格）"}

        table_match = tables[table_index]
        table_html = table_match.group(0)

        # 找到所有行
        rows = list(re.finditer(r'<tr[^>]*>.*?</tr>', table_html, re.DOTALL))

        if row_position > len(rows):
            return {"success": False, "error": f"行位置 {row_position} 超出范围（可插入位置 0-{len(rows)}）"}

        # 构建新行
        tag = 'th' if is_header else 'td'
        cells_html = ''.join(f'<{tag}>{self._process_cell_content(str(v))}</{tag}>' for v in cell_values)
        new_row = f'<tr>{cells_html}</tr>'

        # 确定插入位置
        if row_position == 0:
            # 在第一行之前插入
            if rows:
                insert_pos = rows[0].start()
            else:
                # 空表格 - 在 <tbody> 或 <table> 之后插入
                tbody_match = re.search(r'<tbody[^>]*>', table_html)
                if tbody_match:
                    insert_pos = tbody_match.end()
                else:
                    table_tag_match = re.match(r'<table[^>]*>', table_html)
                    insert_pos = table_tag_match.end() if table_tag_match else 0
        elif row_position >= len(rows):
            # 在最后一行之后插入
            insert_pos = rows[-1].end()
        else:
            # 在 row_position-1 行之后插入
            insert_pos = rows[row_position - 1].end()

        new_table_html = table_html[:insert_pos] + new_row + table_html[insert_pos:]

        # 替换表格
        new_html = html_content[:table_match.start()] + new_table_html + html_content[table_match.end():]

        # 更新页面
        result = self.update_page_html(page_info['id'], new_html)

        if result['success']:
            return {
                "success": True,
                "message": f"成功在表格 {table_index} 的第 {row_position} 行位置插入新行",
                "url": result['url']
            }
        return result

    def delete_table_row(self, page_id_or_url: str, table_index: int, row_index: int) -> Dict[str, Any]:
        """
        删除表格中的指定行

        Args:
            page_id_or_url: 页面 ID 或 URL
            table_index: 表格索引（从 0 开始）
            row_index: 要删除的行索引（0=表头行，1=第一行数据）

        Returns:
            {success, message, url} 或 {success, error}
        """
        page_info = self.get_page_html(page_id_or_url)
        if not page_info:
            return {"success": False, "error": "页面不存在"}

        html_content = page_info['html']

        # 找到所有表格
        tables = list(re.finditer(r'<table[^>]*>.*?</table>', html_content, re.DOTALL))

        if table_index >= len(tables):
            return {"success": False, "error": f"表格索引 {table_index} 超出范围（共 {len(tables)} 个表格）"}

        table_match = tables[table_index]
        table_html = table_match.group(0)

        # 找到所有行
        rows = list(re.finditer(r'<tr[^>]*>.*?</tr>', table_html, re.DOTALL))

        if row_index >= len(rows):
            return {"success": False, "error": f"行索引 {row_index} 超出范围（共 {len(rows)} 行）"}

        # 检查是否有跨行单元格
        row_html = rows[row_index].group(0)
        if 'rowspan' in row_html.lower():
            return {"success": False, "error": "该行包含跨行单元格（rowspan），删除可能破坏表格结构，请使用 edit_page 直接编辑"}

        # 删除该行
        row_match = rows[row_index]
        new_table_html = table_html[:row_match.start()] + table_html[row_match.end():]

        # 替换表格
        new_html = html_content[:table_match.start()] + new_table_html + html_content[table_match.end():]

        # 更新页面
        result = self.update_page_html(page_info['id'], new_html)

        if result['success']:
            return {
                "success": True,
                "message": f"成功删除表格 {table_index} 的第 {row_index} 行",
                "url": result['url']
            }
        return result

    def _process_cell_content(self, content: str) -> str:
        """
        处理单元格内容，支持 [image:filename] 语法和基本 Markdown

        Args:
            content: 原始内容

        Returns:
            处理后的 HTML 内容
        """
        # 处理 [image:filename.png] 语法
        image_pattern = r'\[image:([^\]]+)\]'

        def replace_image(match):
            filename = match.group(1)
            return f'<ac:image><ri:attachment ri:filename="{html.escape(filename)}"/></ac:image>'

        processed = re.sub(image_pattern, replace_image, content)

        # 处理 Markdown 图片语法 ![alt](filename)
        def replace_md_image(match):
            filename = match.group(2)
            # 如果是文件名（不是 URL），作为附件处理
            if not filename.startswith('http'):
                return f'<ac:image><ri:attachment ri:filename="{html.escape(filename)}"/></ac:image>'
            return f'<img src="{html.escape(filename)}"/>'

        processed = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_md_image, processed)

        # 处理 Markdown 格式（粗体、斜体）
        processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
        processed = re.sub(r'__(.+?)__', r'<strong>\1</strong>', processed)
        processed = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', processed)

        # 如果内容已经是 HTML（以 < 开头），返回
        if processed.strip().startswith('<'):
            return processed

        # 对于非 HTML 内容，处理更多 Markdown 语法
        # 行内代码
        processed = re.sub(r'`([^`]+)`', r'<code>\1</code>', processed)
        # 链接（在图片之后处理）
        processed = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', processed)

        return processed

    # ============ Markdown 转换 ============

    def markdown_to_confluence(self, markdown_content: str) -> str:
        """Markdown 转 Confluence Storage Format (XHTML)"""
        lines = markdown_content.split('\n')
        html_lines = []
        in_code_block = False
        in_table = False
        in_list = False
        list_type = None  # 'ul' or 'ol'
        code_lang = ''
        code_content = []

        for line in lines:
            # 代码块处理
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_lang = line.strip()[3:].lower()
                    code_content = []
                else:
                    in_code_block = False
                    content = '\n'.join(code_content)

                    if code_lang == 'mermaid':
                        html_lines.append(f'<ac:structured-macro ac:name="mermaid-macro"><ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body></ac:structured-macro>')
                    elif code_lang in ['plantuml', 'uml', 'puml']:
                        html_lines.append(f'<ac:structured-macro ac:name="plantuml"><ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body></ac:structured-macro>')
                    else:
                        lang_param = f'<ac:parameter ac:name="language">{code_lang}</ac:parameter>' if code_lang else ''
                        html_lines.append(f'<ac:structured-macro ac:name="code">{lang_param}<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body></ac:structured-macro>')
                    code_lang = ''
                continue

            if in_code_block:
                code_content.append(line)
                continue

            # 关闭列表（如果当前行不是列表项）
            stripped = line.strip()
            is_ul_item = stripped.startswith('- ') or stripped.startswith('* ')
            is_ol_item = re.match(r'^\d+\.\s', stripped)

            if in_list and not is_ul_item and not is_ol_item:
                html_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None

            # 表格处理
            if stripped.startswith('|') and stripped.endswith('|'):
                cells = [c.strip() for c in stripped[1:-1].split('|')]
                if all(set(c) <= set('-: ') for c in cells):
                    continue

                if not in_table:
                    in_table = True
                    html_lines.append('<table><tbody>')
                    # 表头单元格也需要处理行内格式
                    row = '<tr>' + ''.join(f'<th>{self._process_inline_formats(html.escape(c))}</th>' for c in cells) + '</tr>'
                else:
                    # 表格单元格需要处理行内格式（加粗、斜体等）
                    row = '<tr>' + ''.join(f'<td>{self._process_inline_formats(html.escape(c))}</td>' for c in cells) + '</tr>'
                html_lines.append(row)
                continue
            elif in_table:
                in_table = False
                html_lines.append('</tbody></table>')

            # 转义并处理行内格式
            escaped_line = html.escape(line)
            escaped_line = self._process_inline_formats(escaped_line)

            # 块级元素
            if not escaped_line.strip():
                continue  # 空行是 Markdown 段落分隔符，不生成 HTML
            elif escaped_line.startswith('# '):
                html_lines.append(f'<h1>{escaped_line[2:]}</h1>')
            elif escaped_line.startswith('## '):
                html_lines.append(f'<h2>{escaped_line[3:]}</h2>')
            elif escaped_line.startswith('### '):
                html_lines.append(f'<h3>{escaped_line[4:]}</h3>')
            elif escaped_line.startswith('#### '):
                html_lines.append(f'<h4>{escaped_line[5:]}</h4>')
            elif escaped_line.startswith('##### '):
                html_lines.append(f'<h5>{escaped_line[6:]}</h5>')
            elif escaped_line.startswith('###### '):
                html_lines.append(f'<h6>{escaped_line[7:]}</h6>')
            elif escaped_line.startswith('&gt; '):  # 引用块
                html_lines.append(f'<blockquote><p>{escaped_line[5:]}</p></blockquote>')
            elif is_ul_item:  # 无序列表
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                content = escaped_line[2:] if escaped_line.startswith('- ') else escaped_line[2:]
                html_lines.append(f'<li>{content}</li>')
            elif is_ol_item:  # 有序列表
                if not in_list or list_type != 'ol':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                content = re.sub(r'^\d+\.\s', '', escaped_line)
                html_lines.append(f'<li>{content}</li>')
            else:
                html_lines.append(f'<p>{escaped_line}</p>')

        # 关闭未闭合的标签
        if in_table:
            html_lines.append('</tbody></table>')
        if in_list:
            html_lines.append(f'</{list_type}>')

        return '\n'.join(html_lines)

    def _process_inline_formats(self, line: str) -> str:
        """处理行内格式（粗体、斜体、代码、链接、图片）"""
        # 图片 ![alt](url)
        line = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            r'<ac:image><ri:url ri:value="\2"/></ac:image>',
            line
        )
        # 链接 [text](url)
        line = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2">\1</a>',
            line
        )
        # 粗体 **text**
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        # 斜体 *text* (但不是 ** 的一部分)
        line = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', line)
        # 行内代码 `code`
        line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)

        return line

    def confluence_to_markdown(self, html_content: str) -> str:
        """Confluence Storage Format 转 Markdown"""
        content = html_content

        # 标题
        for i in range(6, 0, -1):
            content = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'{"#" * i} \1\n', content, flags=re.DOTALL)

        # 粗体和斜体
        content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
        content = re.sub(r'<b>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)
        content = re.sub(r'<em>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
        content = re.sub(r'<i>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)

        # 行内代码
        content = re.sub(r'<code>(.*?)</code>', r'`\1`', content, flags=re.DOTALL)

        # 链接
        content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL)

        # 图片
        content = re.sub(
            r'<ac:image[^>]*>.*?<ri:url ri:value="([^"]+)"[^>]*/?>.*?</ac:image>',
            r'![](\1)',
            content, flags=re.DOTALL
        )

        # 列表
        content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content, flags=re.DOTALL)
        content = re.sub(r'</?[uo]l[^>]*>', '', content)

        # 引用
        content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n', content, flags=re.DOTALL)

        # 表格
        def convert_table(match):
            table_html = match.group(0)
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, flags=re.DOTALL)
            md_rows = []
            for i, row in enumerate(rows):
                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, flags=re.DOTALL)
                cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                md_rows.append('| ' + ' | '.join(cells) + ' |')
                if i == 0:
                    md_rows.append('|' + '|'.join(['---'] * len(cells)) + '|')
            return '\n'.join(md_rows) + '\n'

        content = re.sub(r'<table[^>]*>.*?</table>', convert_table, content, flags=re.DOTALL)

        # Mermaid 宏
        def convert_mermaid(match):
            return f'```mermaid\n{match.group(1)}\n```\n'
        content = re.sub(
            r'<ac:structured-macro[^>]*ac:name="mermaid-macro"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body></ac:structured-macro>',
            convert_mermaid, content, flags=re.DOTALL
        )

        # PlantUML 宏
        def convert_plantuml(match):
            return f'```plantuml\n{match.group(1)}\n```\n'
        content = re.sub(
            r'<ac:structured-macro[^>]*ac:name="plantuml"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body></ac:structured-macro>',
            convert_plantuml, content, flags=re.DOTALL
        )

        # 代码块宏
        def convert_code(match):
            lang = ''
            lang_match = re.search(r'ac:parameter[^>]*ac:name="language"[^>]*>([^<]+)<', match.group(0))
            if lang_match:
                lang = lang_match.group(1)
            code = match.group(1)
            return f'```{lang}\n{code}\n```\n'
        content = re.sub(
            r'<ac:structured-macro[^>]*ac:name="code"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body></ac:structured-macro>',
            convert_code, content, flags=re.DOTALL
        )

        # 段落
        content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', content, flags=re.DOTALL)

        # 清理剩余 HTML 标签
        content = re.sub(r'<[^>]+>', '', content)

        # HTML 实体
        content = unescape(content)

        # 多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()


# 便捷方法
def get_api() -> ConfluenceAPI:
    """获取 API 实例（使用默认配置）"""
    return ConfluenceAPI()
