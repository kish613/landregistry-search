---
title: API overview
description: JSON endpoints that power the site, available to authenticated callers.
---

# API overview

The same endpoints that drive [landregistry.company/search](https://landregistry.company/search)
are available to authenticated callers. This page is the top-level
reference; the endpoint-specific pages dig into request and response
shapes.

## Base URL

```
https://landregistry.company
```

All endpoints are `application/json`. Responses are UTF-8 encoded.

## Endpoints at a glance

| Method | Path                                   | Purpose                                     |
| ------ | -------------------------------------- | ------------------------------------------- |
| POST   | `/api/search`                          | Title search by company / address / director |
| POST   | `/api/search/directors`                | Companies House officer search              |
| POST   | `/api/search/director-properties`      | Director search with full property fan-out  |
| POST   | `/api/export/csv`                      | Re-run + stream CSV                         |
| POST   | `/api/export/json`                     | Re-run + return JSON                        |
| POST   | `/api/create-checkout`                 | Stripe Checkout session for per-search pay  |
| POST   | `/api/auth/register`                   | Email + password sign-up                    |
| POST   | `/api/auth/login`                      | Email + password sign-in                    |
| POST   | `/api/auth/magic-link`                 | Passwordless sign-in via email              |
| POST   | `/api/auth/logout`                     | End session                                 |
| GET    | `/api/auth/me`                         | Current user + credit balance               |

The auth and Stripe endpoints are documented inline at
[Authentication & credits](/api/authentication) and
[Checkout & payments](/api/checkout).

## Authentication

There are **two** ways to authorise a paid search:

1. **Session cookie** — sign in via `/api/auth/login` or `/api/auth/magic-link`
   and reuse the session cookie. Searches will be deducted from your
   credit balance.
2. **Per-search Stripe payment** — create a checkout session with
   `/api/create-checkout`, complete payment in the browser, and pass
   the resulting `session_id` to `/api/search`.

The two methods can be mixed: pass `use_credits: false` to force a
Stripe payment even on a signed-in account.

See [Authentication & credits](/api/authentication) for details.

## Conventions

### Request body

Every endpoint accepts a JSON body. Common fields:

| Field            | Type     | Required | Notes                                         |
| ---------------- | -------- | -------- | --------------------------------------------- |
| `search_type`    | string   | yes      | `"name"`, `"number"`, `"address"`, `"director"` |
| `search_value`   | string   | yes      | The query.                                    |
| `session_id`     | string   | sometimes| Stripe Checkout Session ID. Required if not using credits. |
| `use_credits`    | boolean  | no       | Defaults to `true`. Set `false` to bypass.    |

### Response envelope

Every search/export endpoint returns:

```json
{
  "success": true,
  "results": [ … ],
  "count": 42,
  "suggestions": [],
  "search_type": "name",
  "company_name": "Barratt Developments PLC",
  "credits_used": true,
  "remaining_credits": 9
}
```

Or on error:

```json
{
  "success": false,
  "error": "Insufficient credits. Please add more credits or pay for this search.",
  "payment_required": true,
  "price_pence": 100,
  "price_display": "£1.00",
  "credit_cost": 1,
  "user_credits": 0,
  "results": [],
  "count": 0,
  "suggestions": []
}
```

`payment_required: true` indicates the caller should redirect to
Stripe Checkout (see [Checkout & payments](/api/checkout)).

### Rate limits

There is no published rate limit — but please be sensible. For volumes
> 1,000 searches/month, [get in touch](mailto:hello@inteltree.co.uk) and
we'll arrange a flat-rate account.

### CORS

The API does **not** currently allow cross-origin browser requests. Call
from a server-side context. If you need CORS for a specific integration,
email us.

## Quick example

```bash
# 1. Sign in
curl -X POST https://landregistry.company/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"…"}' \
  -c cookies.txt

# 2. Search using credit balance
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"search_type":"name","search_value":"Barratt Developments PLC"}'
```

Browse the detail pages on the left for everything else.
