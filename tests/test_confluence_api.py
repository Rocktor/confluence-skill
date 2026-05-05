import unittest

from confluence_api import ConfluenceAPI


class ConfluenceAPITest(unittest.TestCase):
    def test_bearer_auth_does_not_add_basic_param(self):
        api = ConfluenceAPI(base_url="https://example.com", api_key="token", auth_type="bearer")

        self.assertEqual(api.auth_type, "bearer")
        self.assertEqual(api.session.headers["Authorization"], "Bearer token")
        self.assertEqual(api._auth_params({"limit": 1}), {"limit": 1})

    def test_basic_auth_adds_os_auth_type(self):
        api = ConfluenceAPI(
            base_url="https://example.com",
            username="user",
            password="password",
            auth_type="basic",
        )

        self.assertEqual(api.auth_type, "basic")
        self.assertEqual(api._auth_params({"limit": 1}), {"limit": 1, "os_authType": "basic"})

    def test_extract_page_id_from_supported_urls(self):
        api = ConfluenceAPI(base_url="https://example.com", api_key="token", auth_type="bearer")

        self.assertEqual(api._extract_page_id("253301262"), "253301262")
        self.assertEqual(
            api._extract_page_id("https://example.com/pages/viewpage.action?pageId=253301262"),
            "253301262",
        )
        self.assertEqual(
            api._extract_page_id("https://example.com/spaces/cpb/pages/253301262/Page+Title"),
            "253301262",
        )
        self.assertEqual(
            api._extract_page_id("https://example.com/pages/253301262/Page+Title"),
            "253301262",
        )

    def test_extract_images_from_external_download_url(self):
        api = ConfluenceAPI(base_url="https://example.com", api_key="token", auth_type="bearer")
        html = (
            '<ac:image ac:thumbnail="true">'
            '<ri:url ri:value="https://example.com/download/attachments/251249601/'
            'image2026-2-26_18-11-10.png?version=1&amp;api=v2" />'
            '</ac:image>'
        )

        images = api._extract_images(html, "253301262")

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["filename"], "image2026-2-26_18-11-10.png")
        self.assertEqual(images[0]["source_page_id"], "251249601")


if __name__ == "__main__":
    unittest.main()
