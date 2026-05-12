---
title: Director search
description: Pivot from a person to every company they're appointed to, then to every title those companies hold.
---

# Director search

The director mode is the only search that takes a **person** as input.
It is the most powerful workflow on the site — and the most expensive,
because it fans out across two external systems.

::: warning £3 per search
Director searches cost 3 credits or £3. See [Pricing](/guide/pricing).
:::

## How it works

```
┌──────────────────┐    1   ┌────────────────────────┐
│ Director name in │ ─────▶ │ Companies House API    │
└──────────────────┘        │ (officer search)       │
                            └────────────┬───────────┘
                                         │ list of appointments
                                         ▼
                            ┌────────────────────────┐
                       2    │ For each company:      │
                            │ search our CRN index   │
                            └────────────┬───────────┘
                                         │ title rows
                                         ▼
                            ┌────────────────────────┐
                       3    │ Aggregate & dedupe     │
                            │ → results + directors  │
                            └────────────────────────┘
```

1. We hit `GET /search/officers?q={name}` on the Companies House API.
2. For every appointment returned (current **and** resigned), we look up
   the company's CRN in the CCOD index.
3. We aggregate, dedupe by title, and return two arrays in the response:
   - `directors_found` — the appointments matched on Companies House.
   - `results` — every title held by any of those companies.

## What we send to Companies House

Only the **director name** you typed. Nothing about your account, your IP,
or your other searches.

## Match quality

Companies House matches officer names as a substring. Specific
names ("Jonathan Marcus Smith") return a tight list. Common names
("John Smith") return hundreds of officers — all of whom will be
queried, which is why this mode is slower than a CRN lookup.

Best practice:

- Use the **full registered name** including middle names if you have
  them.
- Add a **date of birth** to disambiguate from the Companies House
  website first if there are many results — then come back here with a
  more specific spelling.
- For very common names, run a [company search](/guide/search-company)
  first on the company you suspect, and look at the proprietor list
  for verification.

## Resigned and historic appointments

We include resigned officers in the fan-out — past directorships count.
A property held by a company where the director resigned three years
ago will still appear in the result set, because the title was
acquired during their tenure (and the register hasn't been updated
since).

The `directors_found` array tells you which appointments matched:

```json
{
  "directors_found": [
    {
      "name": "JONATHAN MARCUS SMITH",
      "company_name": "ACME HOLDINGS LIMITED",
      "company_number": "12345678",
      "role": "director",
      "appointed_on": "2018-04-12",
      "resigned_on": null
    }
  ]
}
```

## Rate limits

The Companies House API enforces 600 requests per 5 minutes per
authenticated key. A single director search consumes one officer-list
call plus one company-lookup per appointment. We cache officer lists
for one hour to stay well inside the budget.

## Cost rationale

A name like `John Smith` can produce 200+ company lookups, each of which
is an independent network call. The £3 / 3-credit price is set to cover
that fan-out across typical names, including caching.

## API

```bash
# Step A: search officers (cheap, no charge)
curl -X POST https://landregistry.company/api/search/directors \
  -H "Content-Type: application/json" \
  -d '{"director_name": "Jonathan M. Smith"}'

# Step B: fetch their properties (charged: 3 credits / £3)
curl -X POST https://landregistry.company/api/search/director-properties \
  -H "Content-Type: application/json" \
  -d '{"director_name": "Jonathan M. Smith", "session_id": "cs_test_..."}'
```

See [API · Director endpoints](/api/directors) for the full schema.
