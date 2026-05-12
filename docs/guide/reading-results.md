---
title: Reading a result
description: Field-by-field guide to a CCOD result row.
---

# Reading a result

Every row in a search result represents **one registered title**. This page
walks through each column and explains what it means, what it doesn't mean,
and where the data comes from.

## Field reference

### Title identity

| Field             | Description                                                   |
| ----------------- | ------------------------------------------------------------- |
| `title_number`    | HM Land Registry's unique identifier for the title. Format varies by district: `NGL123456`, `EGL12345`, `K123456`, etc. |
| `tenure`          | `Freehold` or `Leasehold`. The lease term itself is not in CCOD — order the title register for that. |

The title number is the canonical reference. If you need to **order the
full title register** from HM Land Registry, this is the field to give them.

### Address

| Field                       | Description                                       |
| --------------------------- | ------------------------------------------------- |
| `property_address`          | Full address as registered.                       |
| `district`                  | Local authority district (e.g. "City of Westminster"). |
| `county`                    | Historic county (e.g. "Greater London").          |
| `region`                    | Statistical region (e.g. "LONDON").               |
| `postcode`                  | UK postcode. Empty if the title pre-dates postcoding. |
| `multiple_address_indicator`| `Y` if the title covers more than one address; `N` otherwise. |

::: tip
When `multiple_address_indicator = Y`, the `property_address` field
is the **primary** address only. The full list isn't in CCOD — order
the title register if you need every address.
:::

### Proprietor

A title can have up to four proprietors. The fields below appear once
per proprietor (1–4):

| Field                       | Description                                       |
| --------------------------- | ------------------------------------------------- |
| `proprietor_name`           | Legal name as registered.                         |
| `company_registration_no`   | Companies House number (CRN). Empty for some overseas entities. |
| `proprietorship_category`   | Legal form — see [Company search](/guide/search-company#proprietorship-categories). |
| `country_incorporated`      | Country of incorporation (overseas/OCOD only).    |
| `address_line_1` … `_3`     | Registered address of the proprietor.             |

If a title has multiple proprietors, they are joint owners. Severance,
charges, and beneficial trusts are **not** visible in CCOD — you need
the title register.

### Provenance

| Field                       | Description                                       |
| --------------------------- | ------------------------------------------------- |
| `date_proprietor_added`     | When this proprietor was registered against the title. Not the purchase date — see below. |
| `price_paid`                | Sale price, where Land Registry publishes it. Often blank for older titles, leases, or transfers without a sale. |
| `additional_proprietor_indicator` | `Y` if this is an additional proprietor on the title; `N` otherwise. |
| `data_source`               | `CCOD` for UK companies, `OCOD` for overseas.     |

::: warning Date proprietor added ≠ purchase date
`date_proprietor_added` is when HM Land Registry recorded the change,
not when contracts were exchanged. The two are usually within a few
weeks, but the registry can lag by months in extreme cases.
:::

## A worked example

A CSV row for a single Tesco title might look like:

```csv
title_number, tenure,    property_address,                       district,             postcode, price_paid, proprietor_name,            company_registration_no, proprietorship_category,                  date_proprietor_added
NGL123456,    Freehold,  Tesco Extra, 100 High Street, London,   Westminster,          SW1A 1AA, 42000000,   TESCO STORES LIMITED,       00519500,                Limited Company or Public Limited Company, 2015-08-21
```

What that tells you:

- It's a **freehold** title held by Tesco Stores Limited (CRN `00519500`).
- The current registered address is on High Street, Westminster, SW1A 1AA.
- Tesco Stores Limited became the registered proprietor on
  **21 August 2015**.
- A **£42m** consideration was published with the transfer.

What it does **not** tell you:

- Whether there are charges, restrictions, or covenants.
- Whether Tesco actually paid £42m, or whether that's an intra-group
  transfer at book value.
- The lease plan, ancillary rights, or boundary detail.

For any of that, order the title register from HM Land Registry directly.

## Joined data: directors

For a [director search](/guide/search-director), the result also
includes a `directors_found` array — see that page for the schema.

## Schema reference

The full underlying SQL schema is on
[Data → Schema reference](/data/schema).
