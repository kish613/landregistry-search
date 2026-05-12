---
title: Search methods
description: Four ways to interrogate the register — when to use each.
---

# Search methods

There are four ways to query the index. They all hit the same underlying
dataset; the difference is what you give us and how we match it.

| Mode      | You supply…                       | We return…                                   | Cost          |
| --------- | --------------------------------- | -------------------------------------------- | ------------- |
| Company   | Name (fuzzy) or CRN (exact)       | Every title held by the matched company      | £1 / 1 credit |
| Address   | Full address, partial, or postcode| Every title whose property address matches   | £1 / 1 credit |
| Director  | A person's name                   | All titles held by companies the director is/was appointed to | £3 / 3 credits |

The deep-dive pages explain matching rules and edge cases:

- [Company search](/guide/search-company)
- [Address search](/guide/search-address)
- [Director search](/guide/search-director)

## Which one should I use?

A flowchart-style decision tree:

::: tip You know the company exactly
Use **Company → CRN**. Companies House numbers are 8 characters and unique
forever, so this is the most precise lookup. Leading zeros count
(`00604574`, not `604574`).
:::

::: tip You have a company name but not the number
Use **Company → name**. Fuzzy matching handles common variations
(`PLC` / `Limited` / `Ltd.`, trailing/leading whitespace, accents). We
return both exact and near matches with a relevance score.
:::

::: tip You have a property, not an owner
Use **Address**. A postcode alone is often enough; for noisy partials,
include the street name. Address text is normalised before matching
(uppercase, punctuation stripped, common abbreviations expanded).
:::

::: tip You have a person, not a company
Use **Director**. We hit the Companies House API for live and historic
appointments under that exact name, then run a CRN search for each
match. This is the only mode that surfaces ownership through SPVs
without you needing the SPV's name.
:::

## What every mode returns

Regardless of how you matched, the result rows are **title-level**:
one row per registered title. Every row has at least:

- `title_number`
- `tenure` — `Freehold` or `Leasehold`
- `property_address`
- `postcode`
- `proprietor_name`
- `company_registration_no`
- `proprietorship_category`
- `date_proprietor_added`

For the full schema, see [Reading a result](/guide/reading-results).

## Latency

We aim for a median search time of **~180 ms** and a p95 below **420 ms**.
Director searches are slower (1–4 s) because they include a synchronous
round-trip to Companies House.

## Pagination

The web UI shows results in pages of 50. The API returns up to 1,000
matches per call — see [API · Search endpoint](/api/search).

## Empty result handling

When a search finds no exact match we return up to five **suggestions**
from a trigram-similarity scan. They appear as clickable chips below the
search bar in the UI, and as a `suggestions` array in the API response.
