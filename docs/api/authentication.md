---
title: Authentication & credits
description: How session auth and Stripe per-search pay work together.
---

# Authentication & credits

Two mutually-compatible ways to pay for a search:

- **Account session** — sign in once, debit credits per search.
- **Per-search payment** — create a Stripe Checkout session, complete
  it in the browser, send the `session_id` along with your search.

## Endpoint: `POST /api/auth/register`

Create an account and receive 10 free credits.

```json
{
  "email": "you@example.com",
  "password": "your-password"   // optional; magic-link if omitted
}
```

Response:

```json
{
  "success": true,
  "user": {
    "id": 42,
    "email": "you@example.com",
    "credits": 10,
    "is_unlimited": false,
    "email_verified": false
  }
}
```

On success, a session cookie is set. Save it for subsequent requests.

## Endpoint: `POST /api/auth/login`

```json
{
  "email": "you@example.com",
  "password": "your-password"
}
```

Response is identical to `register`. Session cookie is set on success.

## Endpoint: `POST /api/auth/magic-link`

Request a one-time link to your inbox. No password required.

```json
{ "email": "you@example.com" }
```

Response:

```json
{ "success": true, "message": "Magic link sent to your email." }
```

The user clicks the link in their inbox; that route (`/auth/verify`)
sets the session cookie and redirects to `/search`.

## Endpoint: `GET /api/auth/me`

Returns the current user and credit balance. Useful before triggering
a search to decide whether to fall through to Stripe.

```json
{
  "logged_in": true,
  "user": {
    "id": 42,
    "email": "you@example.com",
    "credits": 9,
    "is_unlimited": false
  }
}
```

If not signed in:

```json
{ "logged_in": false }
```

## Endpoint: `POST /api/auth/logout`

Clears the session cookie. Idempotent.

```json
{ "success": true }
```

## How credits are deducted

On every successful search the server, in order:

1. Loads the current user from the session cookie (if any).
2. If `user.is_unlimited == true`, the search is free; no deduction.
3. Otherwise, looks up the search type's credit cost
   (1 for name/number/address; 3 for director).
4. If `user.credits >= cost` and `use_credits` is `true` (the default),
   the search runs and a `credit_transactions` row is appended.
5. If the user is anonymous or out of credits, the server checks for
   a paid `session_id` (see [Checkout & payments](/api/checkout)).
6. If neither check passes, returns `payment_required: true`.

## Forcing Stripe even when signed in

Pass `use_credits: false` in the search body to bypass credits and
require a paid `session_id`.

```json
{
  "search_type": "name",
  "search_value": "Barratt Developments PLC",
  "use_credits": false,
  "session_id": "cs_test_..."
}
```

Useful for testing the payment path or for accounts that need an
auditable Stripe-receipt-per-search trail (some compliance contexts).

## Audit trail

Every credit movement is recorded in `credit_transactions`:

| Column            | Notes                                            |
| ----------------- | ------------------------------------------------ |
| `user_id`         | FK to `users`.                                   |
| `amount`          | Negative for deduction, positive for top-up.     |
| `transaction_type`| `signup_bonus`, `search_used`, `purchase`.       |
| `search_type`     | `name` / `number` / `address` / `director` (search_used only). |
| `description`     | Free-text; usually the truncated search value.   |
| `created_at`      | Timestamp.                                       |

The current site doesn't expose this log to end users; email us if you
need an export for accounting.
