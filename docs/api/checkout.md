---
title: Checkout & payments
description: Per-search Stripe Checkout sessions.
---

# Checkout & payments

When the caller doesn't have credits — either because they aren't signed
in, or because their balance is empty — a search runs against a paid
**Stripe Checkout session** instead. This page documents the create-then-
redirect flow.

## `POST /api/create-checkout`

Create a Stripe Checkout session for a specific (search_type, search_value)
pair.

### Request

```json
{
  "search_type": "name",
  "search_value": "Barratt Developments PLC"
}
```

Both fields are required. `search_type` must be one of
`"name"`, `"number"`, `"address"`, `"director"`.

### Response

```json
{
  "success": true,
  "session_id": "cs_test_a1b2c3…",
  "url": "https://checkout.stripe.com/c/pay/cs_test_a1b2c3…",
  "publishable_key": "pk_live_…"
}
```

Open `url` in the user's browser. Stripe collects the payment and
redirects back to:

```
https://landregistry.company/search?session_id={SESSION_ID}&search_type={TYPE}&search_value={VALUE}
```

The frontend reads `session_id` from the URL and includes it in the next
`/api/search` call to authorise the search.

### Pricing

Pricing is enforced server-side:

| `search_type` | Amount (pence) | Display |
| ------------- | --------------:| ------- |
| `name`        |            100 | £1.00   |
| `number`      |            100 | £1.00   |
| `address`     |            100 | £1.00   |
| `director`    |            300 | £3.00   |

Mismatched / unrecognised search types return an error:

```json
{ "success": false, "error": "Invalid search type" }
```

## End-to-end flow

```
┌────────────────────┐  1. /api/create-checkout
│ Your code / UI     │ ───────────────────────────▶  Flask
└─────────┬──────────┘
          │ 2. open url
          ▼
┌────────────────────┐
│ Stripe Checkout    │   user pays
└─────────┬──────────┘
          │ 3. redirect with session_id
          ▼
┌────────────────────┐  4. /api/search { …, session_id }
│ Your code / UI     │ ───────────────────────────▶  Flask
└────────────────────┘                              │
                                                     5. verify session
                                                        with Stripe
                                                     6. run search
                                                     7. mark session used
```

## Session reuse

A Stripe `session_id` is **single-use**. Once `/api/search` has marked it
consumed, a second search with the same `session_id` will return:

```json
{
  "success": false,
  "error": "This payment has already been used. Please complete a new search.",
  "payment_required": true,
  "price_pence": 100
}
```

Refreshing the result page within the same browser session does **not**
re-charge — the result is cached in client memory by the frontend. To
re-run, click "Search" again with the same query: the request is
served from the same session_id while the page is alive.

## Payment record

Every successful payment writes a row to the `payments` table:

| Column                 | Notes                                          |
| ---------------------- | ---------------------------------------------- |
| `stripe_session_id`    | Unique. Doubles as the idempotency key.        |
| `search_type`          | One of name / number / address / director.     |
| `search_value`         | The original query (truncated to 500 chars).   |
| `amount_pence`         | 100 or 300.                                    |
| `currency`             | `gbp`.                                         |
| `status`               | `pending` → `completed` → `used`.              |
| `customer_email`       | If Stripe returned one.                        |
| `created_at`           | Insert time.                                   |
| `completed_at`         | Stripe webhook confirmation time.              |
| `used_at`              | When the search consumed the session.          |

## Webhook

We don't currently expose a public webhook endpoint for downstream
listeners. If you need search-completed notifications for integration
purposes, email **hello@inteltree.co.uk**.

## Stripe environments

The publishable key returned by `/api/create-checkout` is whichever the
server is currently configured with — test (`pk_test_…`) or live
(`pk_live_…`). On `landregistry.company` it is live. There is no
sandbox environment exposed publicly; use a sub-£1 charge against your
own test account if you need to exercise the full flow.
