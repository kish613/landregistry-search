---
title: Changelog
description: Material changes to the index, the API, and the docs.
---

# Changelog

Material changes only. Bug fixes that don't change behaviour are omitted.
Dates are the date the change went live on `landregistry.company`.

---

## 2026-04 · CCOD v2026.04

- **Data:** Refreshed against the April 2026 CCOD and OCOD releases.
  3,814,226 titles indexed (+12,847 since v2026.03).
- **Data:** OCOD overseas-entity count: 98,412 (+402).

## 2026-03 · CCOD v2026.03

- **Data:** Refreshed against the March 2026 CCOD and OCOD releases.
- **Search:** Trigram threshold for company-name search lowered from
  `0.50` to `0.45`. This pulls in slightly fuzzier matches at the cost
  of a small number of extra near-misses. Suggestion list still
  capped at five.

## 2026-02 · CCOD v2026.02

- **API:** `X-CCOD-Version` response header added on every successful
  search.
- **UI:** Hero "live feed" ticker added — sample of recent register
  events for the eye.

## 2026-01 · CCOD v2026.01

- **Data:** Annual schema refresh — HM Land Registry has clarified
  the `country_incorporated` field on OCOD to use ISO short names
  where possible. We pass these through unchanged.

## 2025-12 · CCOD v2025.12

- **Pricing:** Director search introduced at £3 / 3 credits, as the
  Companies House fan-out justified separate pricing.
- **API:** New endpoints `/api/search/directors` and
  `/api/search/director-properties`.

## 2025-11 · CCOD v2025.11

- **Auth:** Magic-link sign-in added alongside password sign-in.
- **Accounts:** New accounts get 10 free credits on signup (previously 5).

## 2025-10 · Initial release

- First public release of `landregistry.company`.
- Three search types: Company (name + CRN), Address, Director (beta).
- CSV and JSON exports.
- Stripe Checkout for per-search payment.
