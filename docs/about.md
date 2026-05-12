---
title: About
description: Who runs landregistry.company and why.
---

# About

`landregistry.company` is a property-ownership search service for
England and Wales. It is built and operated by **IntelTree Ltd**, a
UK private company.

## What we do

We take HM Land Registry's monthly Commercial and Corporate Ownership
Data (CCOD) and Overseas Companies Ownership Data (OCOD) releases,
load them into a Postgres index, and serve them through a fast search.
We cross-reference with the Companies House API for director-based
search.

The data is public; the index is the product.

## Why we built it

The official CCOD release is a 1 GB monthly CSV. It isn't searchable,
isn't indexed against Companies House, and isn't exportable as a
filtered slice. You can't ask "which titles does Tesco hold?"
without writing an SQL pipeline of your own.

Plenty of professional users — solicitors, journalists, dealers —
need exactly that kind of query, repeatedly. So we built the index
once and serve it for £1 per query.

## What this site is not

- We are **not** HM Land Registry. We mirror their public data; we
  don't issue title plans or official copies. For that, go directly
  to [HM Land Registry](https://www.gov.uk/government/organisations/land-registry).
- We are **not** a Companies House clone. We query their officer API
  for director search, but we don't replicate the broader company
  filings.
- We are **not** a beneficial-ownership service. CCOD names the
  *legal* proprietor, which is often a nominee or an SPV. For
  beneficial ownership, the PSC register and the Register of
  Overseas Entities are the right primary sources.

## Operating principles

- **The data is authoritative; we display it as-is.** We don't
  silently rewrite proprietor names, addresses, or CRNs. If CCOD has
  a quirk, we surface the quirk.
- **Pay per search, not per month.** There's no tier you can outgrow
  and no clock running. £1 buys one search; if you only need one
  search a year, that's fine.
- **Open licence in; open licence out.** Anything you export from the
  site is yours to use commercially under the Open Government
  Licence v3.0. See [Licensing](/data/licensing).
- **Minimum data.** Search queries are not stored. The
  `credit_transactions` audit log retains the search type and a
  truncated value for accounting. Stripe handles payment data; we
  never see the card.

## Audience

The site is built for people who do real work with the register:

- Investigative journalists tracing ownership chains.
- Solicitors and paralegals doing due diligence.
- Property dealers and auctioneers verifying proprietors before
  bidding.
- Insolvency practitioners tracking titles held by distressed
  companies.
- Academic researchers studying land concentration.

If your use case is something else and the site nearly fits, email us
— we usually can adjust.

## The team

`landregistry.company` is operated by **IntelTree Ltd**, registered in
England and Wales. The site is owned, designed, and engineered by a
small team — no investors, no third-party reseller. Contact:

- **Email:** hello@inteltree.co.uk
- **Web:** [inteltree.co.uk](https://inteltree.co.uk)

## Status

All systems online. The active CCOD version is visible in the navbar
on every page (`vYYYY.MM`). For a structured status page, watch this
docs site — we'll add `/changelog` posts when something material
changes.
