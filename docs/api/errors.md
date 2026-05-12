---
title: Errors
description: How the API signals failure, and what to do about each kind.
---

# Errors

The API tries to be predictable rather than RESTful-pure: business-logic
errors come back as HTTP 200 with `success: false` and a human-readable
`error` message. Genuine HTTP failures (5xx) are reserved for
infrastructure problems.

## Shape

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

Always check `success` before reading `results`.

## Common error messages

| `error` text                                                            | Cause                                                | Fix                                              |
| ----------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| `Search value is required`                                              | `search_value` empty or missing.                     | Send a non-empty string.                         |
| `Invalid search type`                                                   | `search_type` not one of name/number/address/director. | Use a supported value.                         |
| `Insufficient credits. Please add more credits or pay for this search.` | Signed-in user, no credits, no `session_id`.         | Top up, or pass `session_id` from `/api/create-checkout`. |
| `Payment required`                                                      | Anonymous caller, no `session_id`.                   | Start a Stripe Checkout session.                 |
| `This payment has already been used. Please complete a new search.`     | `session_id` reused.                                 | Create a new Checkout session.                   |
| `Could not reach the Companies House API. Please try again in a moment.`| Upstream timeout / 5xx during director search.       | Retry. Credits are not deducted on this failure. |
| `No results to export`                                                  | Export endpoint, search returned 0 rows.             | Run the search first, ensure it has results.     |

## HTTP status codes

| Status | Meaning                                              |
| ------ | ---------------------------------------------------- |
| 200    | Endpoint reached; check `success` for outcome.       |
| 400    | Validation error on the export endpoints.            |
| 401    | Auth endpoints only — wrong credentials or expired session. |
| 500    | Internal server error. Retryable.                    |
| 502    | Upstream (Stripe / Companies House / DB) timed out.  |
| 503    | Maintenance window during the monthly CCOD swap.     |

A 502 / 503 is a good signal to back off — retry after 30 seconds with
exponential backoff.

## Retry semantics

| Endpoint                              | Safe to retry?                                          |
| ------------------------------------- | ------------------------------------------------------- |
| `POST /api/search`                    | Yes (same `session_id` is idempotent — won't double-charge). |
| `POST /api/search/directors`          | Yes (unmetered).                                        |
| `POST /api/search/director-properties`| Yes, but the **second** identical call will re-deduct credits if the first deducted and crashed downstream. Wait 10 s before retrying. |
| `POST /api/export/csv`                | Yes.                                                    |
| `POST /api/export/json`               | Yes.                                                    |
| `POST /api/create-checkout`           | Yes — each call returns a fresh `session_id`.           |
| `POST /api/auth/login`                | Yes.                                                    |
| `POST /api/auth/magic-link`           | Avoid — every retry sends another email.                |

## Reporting a problem

If you get an error that doesn't match anything on this page, or a
search returns plainly wrong data, send the following to
**hello@inteltree.co.uk**:

1. The exact endpoint and request body.
2. The CCOD version visible in the navbar (`vYYYY.MM`).
3. The full response body.
4. The expected behaviour, one line.

We triage daily.
