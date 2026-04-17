"""Tests for the public REST API (app.api_v1).

Uses a temporary SQLite database so we can exercise the full auth/credit
pipeline without requiring Postgres.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test-secret-key")

# IMPORTANT: import app.main first so the api_v1 blueprint registration at
# the bottom of main.py runs cleanly. Importing app.api_v1 first would put
# main.py mid-load when api_v1.py tries `from app import main`, triggering a
# circular import error.
from app.main import app  # noqa: E402
from app import api_v1 as api_v1_module  # noqa: E402


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    credits INTEGER DEFAULT 10,
    api_credits INTEGER DEFAULT 0,
    is_unlimited INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_number TEXT NOT NULL,
    tenure TEXT,
    property_address TEXT NOT NULL,
    district TEXT, county TEXT, region TEXT, postcode TEXT,
    multiple_address_indicator TEXT,
    price_paid TEXT, date_proprietor_added TEXT,
    additional_proprietor_indicator TEXT,
    data_source TEXT DEFAULT 'CCOD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS proprietors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    proprietor_number INTEGER NOT NULL,
    proprietor_name TEXT,
    company_registration_no TEXT,
    proprietorship_category TEXT,
    country_incorporated TEXT,
    address_line_1 TEXT, address_line_2 TEXT, address_line_3 TEXT,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes TEXT NOT NULL DEFAULT 'read',
    rate_limit_per_min INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_credit_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    api_key_id INTEGER,
    amount INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    endpoint TEXT,
    stripe_session_id TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_id INTEGER,
    user_id INTEGER,
    request_id TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    credits_charged INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    ip TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class ApiV1TestCase(unittest.TestCase):
    tmp_db: Path
    api_key: str

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        cls.tmp_db = Path(cls._tmp.name)

        conn = sqlite3.connect(cls.tmp_db)
        conn.executescript(SCHEMA)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, api_credits, email_verified) VALUES (?, ?, 1)",
            ("dev@example.com", 10),
        )
        user_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO properties (title_number, tenure, property_address, postcode, data_source)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("TT000001", "Freehold", "1 TEST RD, LONDON", "SW1A 1AA", "CCOD"),
        )
        prop_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO proprietors
                (property_id, proprietor_number, proprietor_name, company_registration_no)
            VALUES (?, 1, ?, ?)
            """,
            (prop_id, "TEST OWNER LTD", "09876543"),
        )
        conn.commit()
        conn.close()

        raw_key, prefix, key_hash = api_v1_module.generate_api_key()
        conn = sqlite3.connect(cls.tmp_db)
        conn.execute(
            """
            INSERT INTO api_keys (user_id, name, key_prefix, key_hash)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, "test", prefix, key_hash),
        )
        conn.commit()
        conn.close()
        cls.api_key = raw_key
        cls.user_id = user_id

        cls.patcher = patch("app.main.LOCAL_DATABASE_PATH", cls.tmp_db)
        cls.patcher.start()
        cls.pg_patcher = patch("app.main.DATABASE_URL", None)
        cls.pg_patcher.start()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        cls.pg_patcher.stop()
        cls.tmp_db.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    def _auth(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def test_health_no_auth(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_me_rejects_missing_auth(self):
        r = self.client.get("/api/v1/me")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["error"]["code"], "unauthorized")

    def test_me_rejects_bogus_key(self):
        r = self.client.get(
            "/api/v1/me", headers={"Authorization": "Bearer lr_live_notreal"}
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["error"]["code"], "invalid_api_key")

    def test_me_returns_account_info(self):
        r = self.client.get("/api/v1/me", headers=self._auth())
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(body["email"], "dev@example.com")
        self.assertEqual(body["api_credits"], 10)
        self.assertIn("pricing", body)

    def test_by_company_number_debits_credit_and_returns_matches(self):
        before = self._credits()
        r = self.client.get(
            "/api/v1/properties/by-company-number?number=09876543",
            headers=self._auth(),
        )
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(body["pagination"]["total"], 1)
        self.assertEqual(body["data"][0]["title_number"], "TT000001")
        self.assertEqual(self._credits(), before - 1)

    def test_insufficient_credits_returns_402(self):
        self._set_credits(0)
        try:
            r = self.client.get(
                "/api/v1/properties/by-company-number?number=09876543",
                headers=self._auth(),
            )
            self.assertEqual(r.status_code, 402)
            self.assertEqual(
                r.get_json()["error"]["code"], "insufficient_credits"
            )
        finally:
            self._set_credits(10)

    def test_missing_query_param_returns_400(self):
        r = self.client.get(
            "/api/v1/properties/by-company-number", headers=self._auth()
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "invalid_request")

    def test_openapi_spec_has_expected_endpoints(self):
        r = self.client.get("/api/v1/openapi.json")
        self.assertEqual(r.status_code, 200)
        spec = r.get_json()
        self.assertEqual(spec["openapi"], "3.1.0")
        for path in (
            "/properties/by-company-number",
            "/properties/by-company-name",
            "/properties/by-address",
            "/directors/search",
            "/directors/properties",
        ):
            self.assertIn(path, spec["paths"])

    def test_developer_landing_page_renders(self):
        r = self.client.get("/developers")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"REST API", r.data)

    def test_docs_page_renders_swagger_ui(self):
        r = self.client.get("/docs/api")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"swagger-ui", r.data)

    def test_robots_allows_developers(self):
        r = self.client.get("/robots.txt")
        body = r.get_data(as_text=True)
        self.assertIn("Allow: /developers", body)
        self.assertIn("Allow: /docs/api", body)

    def test_request_logged(self):
        self.client.get("/api/v1/me", headers=self._auth())
        conn = sqlite3.connect(self.tmp_db)
        cur = conn.cursor()
        cur.execute("SELECT path, status_code FROM api_request_logs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "/api/v1/me")
        self.assertEqual(row[1], 200)

    # ------------------------------------------------------------------
    def _credits(self):
        conn = sqlite3.connect(self.tmp_db)
        cur = conn.cursor()
        cur.execute("SELECT api_credits FROM users WHERE id = ?", (self.user_id,))
        row = cur.fetchone()
        conn.close()
        return row[0]

    def _set_credits(self, value):
        conn = sqlite3.connect(self.tmp_db)
        conn.execute("UPDATE users SET api_credits = ? WHERE id = ?", (value, self.user_id))
        conn.commit()
        conn.close()


class ApiV1UnitTests(unittest.TestCase):
    def test_generate_key_prefix_and_hash(self):
        raw, prefix, key_hash = api_v1_module.generate_api_key()
        self.assertTrue(raw.startswith("lr_live_"))
        self.assertEqual(prefix, raw[:12])
        self.assertEqual(key_hash, api_v1_module._hash_key(raw))
        self.assertNotEqual(raw, key_hash)

    def test_endpoint_pricing_table(self):
        # Sanity check that the pricing table only charges for expected surfaces.
        self.assertEqual(
            api_v1_module.ENDPOINT_CREDIT_COSTS["properties.by-company-number"], 1
        )
        self.assertEqual(
            api_v1_module.ENDPOINT_CREDIT_COSTS["directors.properties"], 3
        )

    def test_credit_packs_structure(self):
        for pack in api_v1_module.API_CREDIT_PACKS.values():
            self.assertIn("credits", pack)
            self.assertIn("price_pence", pack)
            self.assertGreater(pack["credits"], 0)
            self.assertGreater(pack["price_pence"], 0)


if __name__ == "__main__":
    unittest.main()
