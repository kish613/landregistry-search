---
title: Search endpoint
description: POST /api/search — title search by company, address, or director.
---

# `POST /api/search`

The single search endpoint, polymorphic over `search_type`.

## Request

```http
POST /api/search HTTP/1.1
Host: landregistry.company
Content-Type: application/json
Cookie: session=…           # optional, if using credit balance
```

```json
{
  "search_type": "name",
  "search_value": "Barratt Developments PLC",
  "session_id": "cs_test_…", // optional, required if no credits
  "use_credits": true        // optional, defaults to true
}
```

### Fields

| Field          | Type    | Required | Notes                                                  |
| -------------- | ------- | -------- | ------------------------------------------------------ |
| `search_type`  | string  | yes      | `"name"`, `"number"`, `"address"`, `"director"`         |
| `search_value` | string  | yes      | The query. Trimmed server-side.                        |
| `session_id`   | string  | sometimes| Stripe Checkout Session ID. Required when not paying with credits. |
| `use_credits`  | boolean | no       | `false` to force Stripe-based payment.                 |

### Credit cost

| `search_type` | Credits | Price |
| ------------- | ------- | ----- |
| `name`        | 1       | £1    |
| `number`      | 1       | £1    |
| `address`     | 1       | £1    |
| `director`    | 3       | £3    |

## Successful response — name / number / address

```json
{
  "success": true,
  "search_type": "name",
  "results": [
    {
      "title_number": "NGL123456",
      "tenure": "Freehold",
      "property_address": "100 High Street, London",
      "district": "Westminster",
      "county": "Greater London",
      "region": "LONDON",
      "postcode": "SW1A 1AA",
      "multiple_address_indicator": "N",
      "price_paid": "42000000",
      "date_proprietor_added": "2015-08-21",
      "proprietor_name": "BARRATT DEVELOPMENTS PLC",
      "company_registration_no": "00604574",
      "proprietorship_category": "Limited Company or Public Limited Company",
      "country_incorporated": null,
      "data_source": "CCOD"
    }
    // …
  ],
  "count": 1247,
  "suggestions": [],
  "credits_used": true,
  "remaining_credits": 9,
  "company_name": "Barratt Developments PLC"
}
```

The response includes a search-type-specific echo key:

| `search_type` | Echo key                                              |
| ------------- | ----------------------------------------------------- |
| `name`        | `"company_name": "…"`                                 |
| `number`      | `"company_number": "…"`                               |
| `address`     | `"address": "…"`                                      |
| `director`    | `"director_name": "…"` + `"directors_found": [ … ]`   |

## Successful response — director

Same envelope, plus a `directors_found` array:

```json
{
  "success": true,
  "search_type": "director",
  "director_name": "Jonathan M. Smith",
  "directors_found": [
    {
      "name": "JONATHAN MARCUS SMITH",
      "company_name": "ACME HOLDINGS LIMITED",
      "company_number": "12345678",
      "role": "director",
      "appointed_on": "2018-04-12",
      "resigned_on": null
    }
  ],
  "results": [ … ],
  "count": 23,
  "suggestions": [],
  "credits_used": true,
  "remaining_credits": 6
}
```

## Empty results — suggestions

If the search matches nothing, the `results` array is empty and the
`suggestions` array contains up to five close matches:

```json
{
  "success": true,
  "search_type": "name",
  "results": [],
  "count": 0,
  "suggestions": [
    "BARRATT DEVELOPMENTS PLC",
    "BARRATT HOMES LIMITED",
    "BARRATT DEVELOPMENT HOLDINGS LIMITED"
  ],
  "credits_used": true,
  "remaining_credits": 8,
  "company_name": "Barat Developments"
}
```

A failed search still deducts credits — the search itself ran, the
fan-out happened, and the suggestion list is the useful result.

## Payment required

When neither credits nor a valid `session_id` are present:

```json
{
  "success": false,
  "error": "Payment required for this search.",
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

The caller should then start a Stripe Checkout session and retry —
see [Checkout & payments](/api/checkout).

## Validation errors

| HTTP | `error`                                            |
| ---- | -------------------------------------------------- |
| 200  | `"Search value is required"` *(success: false)*    |
| 200  | `"Invalid search type: …"` *(success: false)*      |
| 200  | `"Payment required …"` *(success: false, payment_required: true)* |

Note: the API doesn't currently use HTTP error status codes for
business-logic errors — they always come back as 200 with
`success: false`. Plan accordingly.

## Examples

### By CRN

```bash
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"search_type":"number","search_value":"00604574"}'
```

### By address

```bash
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"search_type":"address","search_value":"SW7 2AX"}'
```

### Anonymous + Stripe

```bash
# First, create a Checkout session (see /api/create-checkout)
# Then redirect the user to Stripe, get back the session_id, and:
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "name",
    "search_value": "Barratt Developments PLC",
    "session_id": "cs_test_abc123"
  }'
```
