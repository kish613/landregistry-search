"""Tests for core marketing pages and content inventory."""

from html import unescape
import os
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app.content import list_content  # noqa: E402
from app.main import app  # noqa: E402


class TestMarketingPages(unittest.TestCase):
    """Verify the new SEO-facing marketing surface."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def assert_no_cdn_dependencies(self, body):
        self.assertNotIn("cdn.tailwindcss.com", body)
        self.assertNotIn("code.iconify.design", body)
        self.assertNotIn("fonts.googleapis.com", body)
        self.assertNotIn("particles.min.js", body)

    def test_content_inventory_matches_seo_plan(self):
        self.assertGreaterEqual(len(list_content("resources")), 7)
        self.assertGreaterEqual(len(list_content("blog")), 12)

    def test_landing_page_uses_consistent_paid_monthly_positioning(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("Search official HM Land Registry CCOD data", body)
        self.assertIn("Monthly dataset refresh", body)
        self.assertNotIn("Free UK land registry search tool", body)
        self.assertNotIn("Daily", body)
        self.assertIn("/resources", body)
        self.assertIn("/blog", body)
        self.assert_no_cdn_dependencies(body)

    def test_about_page_uses_local_assets_and_due_diligence_copy(self):
        response = self.client.get("/about")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("legal and due-diligence workflows", body.lower())
        self.assertIn("/resources/data-methodology", body)
        self.assert_no_cdn_dependencies(body)

    def test_faq_page_uses_local_assets_and_links_to_guides(self):
        response = self.client.get("/faq")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("Monthly dataset refresh", body)
        self.assertIn("/resources/company-property-search-uk", body)
        self.assert_no_cdn_dependencies(body)

    def test_how_to_page_uses_local_assets_and_links_into_resources(self):
        response = self.client.get("/how-to-search-land-registry")

        self.assertEqual(response.status_code, 200)
        body = unescape(response.get_data(as_text=True))
        self.assertIn("Companies House vs Land Registry", body)
        self.assertIn("/resources/find-properties-owned-by-a-company", body)
        self.assert_no_cdn_dependencies(body)

    def test_search_page_tracks_new_seo_events(self):
        response = self.client.get("/search")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("search_started", body)
        self.assertIn("checkout_started", body)
        self.assertIn("content_cta_click", body)


if __name__ == "__main__":
    unittest.main()
