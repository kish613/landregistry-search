---
title: FAQ
description: Recurring questions about pricing, data, exports, and accounts.
---

# FAQ

Short answers. For longer treatments, follow the links.

## Is the search free?

You can sign up for **10 free credits** — enough for 10 standard
searches, or three director searches with one credit left over. After
that, searches are **£1 per company / address search** or
**£3 per director search**. No subscription. See [Pricing](/guide/pricing).

## What is CCOD?

**Commercial and Corporate Ownership Data** — an official dataset
published by HM Land Registry, listing every freehold or leasehold title
in England and Wales that's owned by a company (UK or overseas). It's
about 3.8 million rows, refreshed monthly. See [CCOD overview](/data/ccod).

## How do I find what a company owns?

Pick the **Company** search type and enter either the company name (fuzzy
matched) or its **Companies House registration number** (exact match). The
CRN is the most precise option if you have it. See
[Company search](/guide/search-company).

## Can I find out who owns a specific address?

Yes. Use the **Address** search type. A full postcode works best, but
street names and partial addresses also match. See
[Address search](/guide/search-address).

## Can I search by a person's name?

Yes — that's the **Director** search type. We query the Companies House
officer index for everyone matching the name (current and historic
appointments), then return every CCOD title held by any of those
companies. £3 per search, because we may fan out to hundreds of company
lookups. See [Director search](/guide/search-director).

## Can I export results?

Yes — every result set can be exported as **CSV** (for spreadsheets) or
**JSON** (for tooling). Exports are free once the search has been paid
for. See [Exporting](/guide/exporting).

## How often is the data updated?

Monthly. HM Land Registry releases CCOD in the first week of every
month; we mirror within 48 hours. The active CCOD version is visible
in the navbar (`v2026.04` for the April 2026 release). See
[Refresh schedule](/data/refresh-schedule).

## What areas does this cover?

**England and Wales only.** Scotland and Northern Ireland have separate
registries (Registers of Scotland, Land & Property Services NI) and are
not part of CCOD. See [Coverage & limits](/data/coverage).

## Does the data include individuals?

No — CCOD covers corporate ownership only. Properties held by natural
persons are not in scope. The HM Land Registry "Price Paid Data" covers
residential transactions; we don't index that.

## Do I need to create an account?

No. You can pay £1 (or £3) per search via Stripe without an account.
An account gives you a credit balance (10 free credits on signup),
which is just a convenience. See [Accounts & credits](/guide/accounts).

## How do I sign in?

Either with a password, or via a **magic link** sent to your email.
Both options are on the [`/auth`](https://landregistry.company/auth)
page.

## Is my search history stored?

Search **queries** themselves are not stored. We do keep an audit row
in `credit_transactions` recording the search type and a truncated
search-value description when a credit deduction occurs — that's an
accounting requirement.

## Can I use the data commercially?

Yes. The underlying CCOD and Companies House data are released under
the **Open Government Licence v3.0** — commercial reuse is explicitly
permitted, provided you attribute the source. See [Licensing](/data/licensing).

## Is there an API?

Yes. Every endpoint that powers the site is documented under
[API](/api/overview). Authentication is by session cookie (credit
balance) or by Stripe Checkout session id (per-search pay).

## What if a search returns the wrong company / no results?

For a wrong-data report, email **hello@inteltree.co.uk** with the
search URL and the expected result — see
[Tips → When to escalate](/guide/tips#when-to-escalate).

If a search returns zero results, the response will usually include up
to five **suggestions** from a close-match scan. Check the suggestions
first — typos are the most common cause.

## How do I contact you?

Email **hello@inteltree.co.uk** for support, refunds, press, or
bulk-data enquiries. Aim for one working day response.
