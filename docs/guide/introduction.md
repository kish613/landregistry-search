---
title: Introduction
description: What landregistry.company is, what data it covers, and who it's for.
---

# Introduction

`landregistry.company` is a searchable index of every freehold and leasehold
interest in **England and Wales** that is registered to a **company**
(UK or overseas).

It exists because HM Land Registry publishes the underlying dataset —
the **Commercial and Corporate Ownership Data** (CCOD) — only as a monthly
CSV. The official file isn't searchable, isn't indexed against Companies
House, and isn't exportable as a filtered slice. This site does those three
things.

## What's in the index

| Field group        | Examples                                                         |
| ------------------ | ---------------------------------------------------------------- |
| Property           | Title number, tenure, full address, district, county, postcode   |
| Proprietor         | Name, Companies House registration number (CRN), category        |
| Overseas proprietor| Country of incorporation, registered address (OCOD)              |
| Provenance         | Date proprietor added, price paid (where published)              |

Up to four proprietors are tracked per title, in the same order as HM Land
Registry publishes them.

## What it does **not** include

- Properties owned by **individuals** (CCOD covers corporate ownership only).
- **Unregistered land** — only registered titles appear in CCOD.
- **Scotland and Northern Ireland** — they run separate registry systems
  (Registers of Scotland, Land & Property Services NI).
- A live link to the **Title Register** itself — for a specific title's full
  history, deeds, or charges you still need to order the official register
  from HM Land Registry.

See [Coverage & limits](/data/coverage) for the full list.

## Who it's for

- **Investigative journalists** — trace ownership chains through SPVs,
  overseas entities, and director appointments.
- **Solicitors and paralegals** — verify the registered proprietor against
  CCOD during conveyancing or due diligence.
- **Property dealers and auctioneers** — confirm proprietor identity before
  bidding or putting in an offer.
- **Insolvency practitioners** — identify titles held by distressed
  companies.
- **Researchers and analysts** — quantify corporate land holding across a
  region, sector, or post-code area.

## How the site is organised

- **[Guide](/guide/quick-start)** — how to use the search end-to-end.
- **[Data](/data/ccod)** — what the source datasets are, how often they
  refresh, and what's in the schema.
- **[API](/api/overview)** — JSON endpoints for programmatic access.
- **[FAQ](/faq)** — short answers to recurring questions.

## Next step

Head to the [quick start](/quick-start.html) for a five-minute walkthrough,
or skip straight to [search methods](/guide/search-methods).
