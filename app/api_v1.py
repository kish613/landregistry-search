"""
Public REST API v1 for landregistry.company.

Independent from the web-UI session auth and credit pool. Developers sign up,
mint an API key on the developer dashboard, and call these endpoints with an
`Authorization: Bearer <key>` header. Billing uses the separate `api_credits`
column on `users`, topped up via dedicated Stripe checkout sessions.

All endpoints are registered under /api/v1 via the `api_v1` Flask Blueprint.
"""

from __future__ import annotations

import hashlib
import os
import random
import secrets
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Optional

import stripe
from flask import Blueprint, Response, g, jsonify, request

# Re-use everything from the main app so there's a single source of truth for
# data access and search behaviour.
from app import main as app_main

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------
# Pricing (API credits, not web credits)
# ---------------------------------------------------------------------------
ENDPOINT_CREDIT_COSTS = {
    "properties.by-company-number": 1,
    "properties.by-company-name": 1,
    "properties.by-address": 1,
    "directors.search": 1,
    "directors.properties": 3,
}

API_KEY_PREFIX = "lr_live_"
FREE_SIGNUP_API_CREDITS = 50  # given to any user who creates their first key

# Top-up packs sold via Stripe checkout. Keys are stable product codes used in
# `/developers/api-billing/checkout`, values map to (pence, credits).
API_CREDIT_PACKS = {
    "starter": {"credits": 100, "price_pence": 500, "label": "100 API credits"},
    "growth": {"credits": 500, "price_pence": 2000, "label": "500 API credits"},
    "scale": {"credits": 2500, "price_pence": 7500, "label": "2,500 API credits"},
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _db():
    return app_main.get_db_connection()


def _cursor(conn):
    return app_main.dict_cursor(conn)


def _is_pg() -> bool:
    return bool(app_main.DATABASE_URL)


def _sql(pg: str, sqlite: str) -> str:
    """Pick the flavoured SQL statement."""
    return pg if _is_pg() else sqlite


# ---------------------------------------------------------------------------
# Key hashing
# ---------------------------------------------------------------------------
def _hash_key(raw_key: str) -> str:
    """Deterministic SHA-256 of the raw key so we can look it up without
    storing the plaintext."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash). Prefix is the first 12
    characters of the raw key for display in the dashboard."""
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, raw[:12], _hash_key(raw)


def _lookup_key(raw_key: str) -> Optional[dict]:
    if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
        return None
    key_hash = _hash_key(raw_key)
    conn = _db()
    cur = _cursor(conn)
    cur.execute(
        _sql(
            """
            SELECT k.id, k.user_id, k.name, k.scopes, k.rate_limit_per_min,
                   k.revoked_at, u.email, u.api_credits, u.is_unlimited
            FROM api_keys k
            JOIN users u ON u.id = k.user_id
            WHERE k.key_hash = %s
            """,
            """
            SELECT k.id, k.user_id, k.name, k.scopes, k.rate_limit_per_min,
                   k.revoked_at, u.email, u.api_credits, u.is_unlimited
            FROM api_keys k
            JOIN users u ON u.id = k.user_id
            WHERE k.key_hash = ?
            """,
        ),
        (key_hash,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    row = dict(row) if hasattr(row, "keys") else row
    if row["revoked_at"]:
        return None
    return row


# ---------------------------------------------------------------------------
# Rate limiting (per-minute window, PostgreSQL-only enforcement)
# ---------------------------------------------------------------------------
def _check_and_bump_rate_limit(api_key_id: int, limit_per_min: int) -> bool:
    if not _is_pg():
        # SQLite is only used for local dev; skip rate limiting there.
        return True
    minute_bucket = datetime.utcnow().replace(second=0, microsecond=0)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO api_rate_counters (api_key_id, window_start, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (api_key_id, window_start)
            DO UPDATE SET count = api_rate_counters.count + 1
            RETURNING count
            """,
            (api_key_id, minute_bucket),
        )
        count = cur.fetchone()[0]
        # Probabilistic cleanup of old windows so we don't scan on every hit.
        if random.random() < 0.01:
            cur.execute(
                "DELETE FROM api_rate_counters WHERE window_start < (CURRENT_TIMESTAMP - INTERVAL '1 hour')"
            )
        conn.commit()
        return count <= limit_per_min
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Credits
# ---------------------------------------------------------------------------
def _debit_api_credits(
    user_id: int,
    api_key_id: int,
    amount: int,
    endpoint: str,
    description: str,
) -> bool:
    """Atomically deduct API credits. Returns True on success."""
    if amount <= 0:
        return True
    conn = _db()
    try:
        cur = conn.cursor()
        if _is_pg():
            cur.execute(
                """
                UPDATE users
                SET api_credits = api_credits - %s
                WHERE id = %s AND api_credits >= %s
                RETURNING api_credits
                """,
                (amount, user_id, amount),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False
            cur.execute(
                """
                INSERT INTO api_credit_transactions
                    (user_id, api_key_id, amount, transaction_type, endpoint, description)
                VALUES (%s, %s, %s, 'debit', %s, %s)
                """,
                (user_id, api_key_id, -amount, endpoint, description),
            )
        else:
            cur.execute(
                "SELECT api_credits FROM users WHERE id = ?", (user_id,)
            )
            row = cur.fetchone()
            current = row[0] if row else 0
            if current < amount:
                return False
            cur.execute(
                "UPDATE users SET api_credits = api_credits - ? WHERE id = ?",
                (amount, user_id),
            )
            cur.execute(
                """
                INSERT INTO api_credit_transactions
                    (user_id, api_key_id, amount, transaction_type, endpoint, description)
                VALUES (?, ?, ?, 'debit', ?, ?)
                """,
                (user_id, api_key_id, -amount, endpoint, description),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def credit_api_account(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str,
    stripe_session_id: Optional[str] = None,
) -> None:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(
                "UPDATE users SET api_credits = api_credits + %s WHERE id = %s",
                "UPDATE users SET api_credits = api_credits + ? WHERE id = ?",
            ),
            (amount, user_id),
        )
        cur.execute(
            _sql(
                """
                INSERT INTO api_credit_transactions
                    (user_id, amount, transaction_type, stripe_session_id, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                """
                INSERT INTO api_credit_transactions
                    (user_id, amount, transaction_type, stripe_session_id, description)
                VALUES (?, ?, ?, ?, ?)
                """,
            ),
            (user_id, amount, transaction_type, stripe_session_id, description),
        )
        conn.commit()
    finally:
        conn.close()


def _get_api_credits(user_id: int) -> int:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(
                "SELECT api_credits FROM users WHERE id = %s",
                "SELECT api_credits FROM users WHERE id = ?",
            ),
            (user_id,),
        )
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Request context, logging, error envelope
# ---------------------------------------------------------------------------
def _api_error(code: str, message: str, http_status: int, **extra) -> Response:
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(g, "request_id", None),
            **extra,
        }
    }
    resp = jsonify(body)
    resp.status_code = http_status
    return resp


def _log_request(status_code: int, credits_charged: int) -> None:
    key = getattr(g, "api_key", None)
    if not key:
        # Unauthenticated requests still logged for abuse detection but w/o
        # user context.
        return
    duration_ms = int((time.monotonic() - g.api_started_at) * 1000)
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(
                """
                INSERT INTO api_request_logs
                    (api_key_id, user_id, request_id, method, path,
                     status_code, credits_charged, duration_ms, ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                """
                INSERT INTO api_request_logs
                    (api_key_id, user_id, request_id, method, path,
                     status_code, credits_charged, duration_ms, ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            ),
            (
                key["id"],
                key["user_id"],
                g.request_id,
                request.method,
                request.path[:255],
                status_code,
                credits_charged,
                duration_ms,
                (request.headers.get("X-Forwarded-For", request.remote_addr) or "")[
                    :64
                ],
            ),
        )
        cur.execute(
            _sql(
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s",
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            ),
            (key["id"],),
        )
        conn.commit()
    finally:
        conn.close()


@api_v1.before_request
def _before_request() -> None:
    g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    g.api_started_at = time.monotonic()
    g.api_key = None
    g.credits_charged = 0


@api_v1.after_request
def _after_request(resp: Response) -> Response:
    resp.headers["X-Request-Id"] = getattr(g, "request_id", "") or ""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    try:
        _log_request(resp.status_code, getattr(g, "credits_charged", 0))
    except Exception as exc:  # noqa: BLE001 - never fail a response on logging
        print(f"[api_v1] request log failed: {exc}")
    return resp


@api_v1.errorhandler(Exception)
def _handle_exc(exc: Exception):
    print(f"[api_v1] unhandled: {exc!r}")
    return _api_error(
        "internal_error",
        "An unexpected error occurred. The request has been logged.",
        500,
    )


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------
def require_api_key(cost_key: Optional[str] = None, charge: bool = True):
    """Wrap a view so it:

    1. Parses `Authorization: Bearer <key>`.
    2. Loads + validates the key.
    3. Enforces rate limits.
    4. Optionally debits credits (unless the user is is_unlimited, or cost=0).
    5. On success, `g.api_key` is populated and `g.credits_charged` is set.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return _api_error(
                    "unauthorized",
                    "Missing Authorization: Bearer <api_key> header.",
                    401,
                )
            raw_key = auth[len("Bearer ") :].strip()
            key = _lookup_key(raw_key)
            if not key:
                return _api_error("invalid_api_key", "API key is invalid or revoked.", 401)
            g.api_key = key

            if not _check_and_bump_rate_limit(
                key["id"], key["rate_limit_per_min"]
            ):
                resp = _api_error(
                    "rate_limited",
                    f"Rate limit of {key['rate_limit_per_min']} req/min exceeded.",
                    429,
                    retry_after_seconds=60,
                )
                resp.headers["Retry-After"] = "60"
                return resp

            cost = ENDPOINT_CREDIT_COSTS.get(cost_key, 0) if cost_key else 0
            if charge and cost > 0 and not key["is_unlimited"]:
                if not _debit_api_credits(
                    key["user_id"],
                    key["id"],
                    cost,
                    cost_key or "",
                    f"{request.method} {request.path}",
                ):
                    return _api_error(
                        "insufficient_credits",
                        "Your API credit balance is too low for this request. Top up at /developers/api-billing.",
                        402,
                        required_credits=cost,
                        current_balance=_get_api_credits(key["user_id"]),
                    )
                g.credits_charged = cost

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------
_PUBLIC_PROPERTY_FIELDS = (
    "title_number",
    "tenure",
    "property_address",
    "district",
    "county",
    "region",
    "postcode",
    "price_paid",
    "date_proprietor_added",
    "proprietor_name",
    "company_registration_no",
    "proprietorship_category",
    "country_incorporated",
    "address_line_1",
    "address_line_2",
    "address_line_3",
    "data_source",
)


def _serialize_property(row: dict) -> dict:
    return {k: row.get(k) for k in _PUBLIC_PROPERTY_FIELDS}


def _paginate(items: list, limit: int, offset: int) -> dict:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    sliced = items[offset : offset + limit]
    return {
        "data": sliced,
        "pagination": {
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "returned": len(sliced),
            "has_more": offset + len(sliced) < len(items),
        },
    }


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@api_v1.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1", "time": datetime.utcnow().isoformat() + "Z"})


@api_v1.route("/me", methods=["GET"])
@require_api_key()
def me():
    key = g.api_key
    return jsonify(
        {
            "email": key["email"],
            "api_credits": _get_api_credits(key["user_id"]),
            "is_unlimited": bool(key["is_unlimited"]),
            "key": {
                "id": key["id"],
                "name": key["name"],
                "scopes": key["scopes"],
                "rate_limit_per_min": key["rate_limit_per_min"],
            },
            "pricing": ENDPOINT_CREDIT_COSTS,
        }
    )


@api_v1.route("/usage", methods=["GET"])
@require_api_key()
def usage():
    key = g.api_key
    limit = _parse_int(request.args.get("limit"), 50)
    limit = max(1, min(limit, 500))
    conn = _db()
    try:
        cur = _cursor(conn)
        cur.execute(
            _sql(
                """
                SELECT request_id, method, path, status_code,
                       credits_charged, duration_ms, created_at
                FROM api_request_logs
                WHERE api_key_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                """
                SELECT request_id, method, path, status_code,
                       credits_charged, duration_ms, created_at
                FROM api_request_logs
                WHERE api_key_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
            ),
            (key["id"], limit),
        )
        rows = [dict(r) if hasattr(r, "keys") else r for r in cur.fetchall()]
    finally:
        conn.close()
    return jsonify({"requests": rows, "api_credits": _get_api_credits(key["user_id"])})


@api_v1.route("/properties/by-company-number", methods=["GET"])
@require_api_key(cost_key="properties.by-company-number")
def properties_by_company_number():
    number = (request.args.get("number") or "").strip()
    if not number:
        return _api_error(
            "invalid_request", "Query parameter `number` is required.", 400
        )
    results = app_main.search_properties_by_company(number)
    page = _paginate(
        [_serialize_property(r) for r in results],
        _parse_int(request.args.get("limit"), 50),
        _parse_int(request.args.get("offset"), 0),
    )
    return jsonify({"query": {"company_number": number}, **page})


@api_v1.route("/properties/by-company-name", methods=["GET"])
@require_api_key(cost_key="properties.by-company-name")
def properties_by_company_name():
    name = (request.args.get("name") or "").strip()
    if not name:
        return _api_error("invalid_request", "Query parameter `name` is required.", 400)
    fuzzy = request.args.get("fuzzy", "true").lower() != "false"
    threshold = _parse_int(request.args.get("fuzzy_threshold"), 70)
    results, suggestions = app_main.search_properties_by_company_name(
        name, fuzzy_threshold=threshold
    )
    page = _paginate(
        [_serialize_property(r) for r in results],
        _parse_int(request.args.get("limit"), 50),
        _parse_int(request.args.get("offset"), 0),
    )
    return jsonify(
        {
            "query": {"company_name": name, "fuzzy": fuzzy},
            "suggestions": suggestions if fuzzy else [],
            **page,
        }
    )


@api_v1.route("/properties/by-address", methods=["GET"])
@require_api_key(cost_key="properties.by-address")
def properties_by_address():
    q = (request.args.get("q") or "").strip()
    if not q:
        return _api_error("invalid_request", "Query parameter `q` is required.", 400)
    results = app_main.search_properties_by_address(q)
    page = _paginate(
        [_serialize_property(r) for r in results],
        _parse_int(request.args.get("limit"), 50),
        _parse_int(request.args.get("offset"), 0),
    )
    return jsonify({"query": {"address": q}, **page})


@api_v1.route("/directors/search", methods=["GET"])
@require_api_key(cost_key="directors.search")
def directors_search():
    name = (request.args.get("name") or "").strip()
    if not name:
        return _api_error("invalid_request", "Query parameter `name` is required.", 400)
    officers, err = app_main.search_directors_from_companies_house(name)
    if err:
        return _api_error("upstream_error", err, 502)
    return jsonify(
        {
            "query": {"name": name},
            "directors": [
                {
                    "name": o.get("name"),
                    "date_of_birth": o.get("date_of_birth") or {},
                    "address": o.get("address") or {},
                    "appointment_count": o.get("appointment_count", 0),
                    "officer_id": (o.get("links") or {}).get("self"),
                    "description": o.get("description"),
                }
                for o in officers
            ],
        }
    )


@api_v1.route("/directors/properties", methods=["GET"])
@require_api_key(cost_key="directors.properties")
def directors_properties():
    """Given an officer_id from /directors/search, resolve their company
    appointments and return any properties owned by those companies."""
    officer_id = (request.args.get("officer_id") or "").strip()
    if not officer_id:
        return _api_error(
            "invalid_request", "Query parameter `officer_id` is required.", 400
        )
    appointments = app_main.get_officer_appointments(officer_id)
    if not appointments:
        return jsonify(
            {
                "query": {"officer_id": officer_id},
                "appointments": [],
                "data": [],
                "pagination": {
                    "total": 0,
                    "limit": 0,
                    "offset": 0,
                    "returned": 0,
                    "has_more": False,
                },
            }
        )
    company_numbers = {
        a.get("company_number", "").strip()
        for a in appointments
        if a.get("company_number")
    }
    properties: list = []
    seen_titles: set = set()
    for number in company_numbers:
        for row in app_main.search_properties_by_company(number):
            key = row.get("title_number"), row.get("proprietor_name")
            if key in seen_titles:
                continue
            seen_titles.add(key)
            properties.append(_serialize_property(row))
    page = _paginate(
        properties,
        _parse_int(request.args.get("limit"), 50),
        _parse_int(request.args.get("offset"), 0),
    )
    return jsonify(
        {
            "query": {"officer_id": officer_id},
            "appointments": appointments,
            **page,
        }
    )


# ---------------------------------------------------------------------------
# OpenAPI spec
# ---------------------------------------------------------------------------
@api_v1.route("/openapi.json", methods=["GET"])
def openapi():
    from app.api_docs import build_openapi_spec

    return jsonify(build_openapi_spec())


# ---------------------------------------------------------------------------
# Stripe webhook for API credit top-ups
# ---------------------------------------------------------------------------
@api_v1.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Stripe webhook that credits the purchased API-credit pack on
    checkout.session.completed."""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_API_WEBHOOK_SECRET")
    if not webhook_secret:
        return _api_error(
            "not_configured", "Webhook secret not configured.", 500
        )
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return _api_error("invalid_signature", "Bad webhook signature.", 400)

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        if session_obj.get("metadata", {}).get("purpose") != "api_credits":
            return jsonify({"ignored": True})
        user_id = int(session_obj["metadata"]["user_id"])
        credits = int(session_obj["metadata"]["credits"])
        # Idempotency: skip if we've already credited this session.
        conn = _db()
        cur = conn.cursor()
        cur.execute(
            _sql(
                "SELECT 1 FROM api_credit_transactions WHERE stripe_session_id = %s",
                "SELECT 1 FROM api_credit_transactions WHERE stripe_session_id = ?",
            ),
            (session_obj["id"],),
        )
        already = cur.fetchone()
        conn.close()
        if already:
            return jsonify({"idempotent": True})
        credit_api_account(
            user_id=user_id,
            amount=credits,
            transaction_type="stripe_purchase",
            description=f"API credit pack {session_obj.get('metadata', {}).get('pack', '')}",
            stripe_session_id=session_obj["id"],
        )
    return jsonify({"received": True})
