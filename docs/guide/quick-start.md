---
title: Quick start
description: Run your first search in under two minutes.
---

# Quick start

This page gets you from zero to a result set in about two minutes. No
account is required for the first search — you can pay £1 by card.

## 1. Open the search page

Go to **[landregistry.company/search](https://landregistry.company/search)**.
The default mode is **Company** search.

If you want 10 free searches first, sign up at
[`/auth`](https://landregistry.company/auth) — the credit is applied
immediately on email confirmation. See [Accounts & credits](/guide/accounts).

## 2. Pick a search type

| Mode       | Use when you know…                                  | Cost          |
| ---------- | --------------------------------------------------- | ------------- |
| Company    | A company name or its Companies House number (CRN)  | £1 / 1 credit |
| Address    | A postcode or a street address                      | £1 / 1 credit |
| Director   | A person's name (current or historic appointment)   | £3 / 3 credits|

For a deeper comparison, see [Search methods](/guide/search-methods).

## 3. Run it

Type your term and press **Search** (or **⌘ K**).

A few realistic examples:

- `Barratt Developments PLC`
- `00604574`  (Companies House number for Tesco PLC)
- `SW7 2AX`
- `12 Kensington Gore, London`
- `Jonathan M. Smith`

Fuzzy matching is on by default for company names — `Barratt Developments`
and `BARRATT DEVELOPMENT LTD` both match.

## 4. Read the results

Each row corresponds to a single registered title. Columns you'll see:

- **Title number** — the HM Land Registry identifier (e.g. `NGL123456`).
- **Tenure** — `Freehold` or `Leasehold`.
- **Address** — as held in the register, plus district / county /
  postcode where supplied.
- **Proprietor** — name, CRN, and proprietorship category.
- **Date added** — the date this proprietor was registered against the
  title.
- **Price paid** — populated where Land Registry releases the figure.

See [Reading a result](/guide/reading-results) for the full field-by-field
breakdown.

## 5. Export

The **Export CSV** and **Export JSON** buttons appear once results are
on screen. Exports are generated client-side and download instantly. See
[Exporting data](/guide/exporting).

::: tip Tip
Re-running the same search within your session is free — credits and
payments are charged once per `(search_type, search_value)` pair. Refreshing
the page does not re-charge.
:::

## Next

- [Search methods](/guide/search-methods) — how each mode is matched.
- [Pricing](/guide/pricing) — credits, top-ups, refund policy.
- [API overview](/api/overview) — run the same query from code.
