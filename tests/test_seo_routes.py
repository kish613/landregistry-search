"""SEO route and content-system tests."""

import os
from html import unescape
import unittest


os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app.main import app  # noqa: E402


class TestSeoRoutes(unittest.TestCase):
    """Verify SEO routes and content pages render correctly."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_robots_txt_is_served_and_blocks_private_routes(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Sitemap: https://landregistry.company/sitemap.xml", body)
        self.assertIn("Disallow: /auth", body)
        self.assertIn("Disallow: /api/", body)

    def test_sitemap_lists_core_and_content_urls(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("https://landregistry.company/", body)
        self.assertIn("https://landregistry.company/resources", body)
        self.assertIn("https://landregistry.company/blog", body)
        self.assertIn(
            "https://landregistry.company/resources/company-property-search-uk",
            body,
        )
        self.assertIn(
            "https://landregistry.company/blog/how-to-check-whether-a-limited-company-owns-uk-property",
            body,
        )
        self.assertNotIn("https://landregistry.company/auth", body)

    def test_rss_feed_is_served_for_blog_posts(self):
        response = self.client.get("/rss.xml")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<rss", body)
        self.assertIn("<title>LandRegistry.company Blog</title>", body)
        self.assertIn(
            "<link>https://landregistry.company/blog/how-to-check-whether-a-limited-company-owns-uk-property</link>",
            body,
        )

    def test_resources_index_lists_money_pages(self):
        response = self.client.get("/resources")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("Legal & Due Diligence Resources", body)
        self.assertIn("Company Property Search UK", body)
        self.assertIn("Commercial Property Ownership Search", body)

    def test_blog_index_lists_editorial_posts(self):
        response = self.client.get("/blog")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("Research, Guides & Data Studies", body)
        self.assertIn("CCOD vs Title Register", body)
        self.assertIn("Overseas Companies Owning Property", body)

    def test_resource_detail_has_article_metadata_and_cta(self):
        response = self.client.get("/resources/company-property-search-uk")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn(
            '<link rel="canonical" href="https://landregistry.company/resources/company-property-search-uk">',
            body,
        )
        self.assertIn("Search Official HM Land Registry CCOD Data", body)
        self.assertIn('"@type": "Article"', body)
        self.assertIn("Start a company ownership search", body)

    def test_blog_post_has_article_metadata_and_visible_update_date(self):
        response = self.client.get(
            "/blog/how-to-check-whether-a-limited-company-owns-uk-property"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn(
            '<link rel="canonical" href="https://landregistry.company/blog/how-to-check-whether-a-limited-company-owns-uk-property">',
            body,
        )
        self.assertIn('"@type": "Article"', body)
        self.assertIn("Last updated", body)
        self.assertIn("Search company ownership data", body)


if __name__ == "__main__":
    unittest.main()
