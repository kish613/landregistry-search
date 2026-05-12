---
title: Pricing
description: Pay-per-search and credit costs, with no subscription.
---

# Pricing

The data is public; we charge only for the index, the cross-reference, and
the export. No subscription, no tiered plans, no minimum monthly spend.

## Per-search prices

| Search type           | Price  | Credits |
| --------------------- | ------ | ------- |
| Company name          | £1.00  | 1       |
| Company number (CRN)  | £1.00  | 1       |
| Address / postcode    | £1.00  | 1       |
| Director              | £3.00  | 3       |

Director searches cost more because they fan out: we query the Companies
House API for every appointment under the supplied name, then search the
register for every company returned. See
[Director search](/guide/search-director) for the mechanics.

## Free credits

New accounts receive **10 free credits** at sign-up. That's 10 standard
searches, 3 director searches, or any mix in between.

## Payment

Cards are processed by **Stripe Checkout**. We never see your card
details. We support Visa, Mastercard, American Express, and Apple Pay /
Google Pay where the device supports them.

## Idempotency

A successful Stripe payment is tied to a specific
`(search_type, search_value)` pair. Refreshing the result page does not
re-charge; running the same search again within the same browser session
does not re-charge. Running it tomorrow, in a new session, with a new
Stripe session id, **does** count as a new search.

For account-credit deductions the same rule applies: the search is
deducted once per query in the `credit_transactions` audit log.

## Refunds

We refund honest mistakes. Email **hello@inteltree.co.uk** with the
Stripe receipt or your account email and a one-line reason; we aim to
process refunds within two working days. Standard reasons:

- Charged twice for the same query (shouldn't happen — see idempotency).
- The result set is empty due to a data issue on our side.
- The result set turned out to be obviously wrong (e.g. wrong
  proprietor for an exact CRN match).

We do **not** refund searches that returned valid results just because
the result wasn't the one you hoped for.

## Bulk and API

For high-volume use (≥ 1,000 searches/month) get in touch — we'll set you
up with a flat-rate account or programmatic access at a discount.
[hello@inteltree.co.uk](mailto:hello@inteltree.co.uk)

## VAT

Prices include UK VAT where applicable. A VAT receipt is emailed by
Stripe with each transaction.
