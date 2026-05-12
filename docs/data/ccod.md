---
title: CCOD overview
description: What the Commercial and Corporate Ownership Data dataset contains, who publishes it, and how it differs from the title register.
---

# CCOD — Commercial and Corporate Ownership Data

`landregistry.company` is built on top of **CCOD**, the Commercial and
Corporate Ownership Data release from HM Land Registry. This page
explains what CCOD is, what it isn't, and how it gets to you.

## What CCOD is

CCOD is a public dataset published by HM Land Registry that lists every
**registered freehold and leasehold title** in England and Wales held
by a **company**. It is published as a CSV under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

Each row in the source CSV represents one **proprietor on one title**.
A title with four corporate proprietors contributes four rows. We
normalise that into one `properties` row and up to four `proprietors`
rows on import — see [Schema reference](/data/schema).

## What CCOD contains

| Group     | Fields                                                       |
| --------- | ------------------------------------------------------------ |
| Title     | Title Number, Tenure                                         |
| Property  | Property Address, District, County, Region, Postcode, Multiple Address Indicator |
| Sale      | Price Paid, Date Proprietor Added                            |
| Proprietor| Name (×4), Company Reg No (×4), Proprietorship Category (×4), Country Incorporated (×4), Address (3 lines, ×4) |
| Provenance| Additional Proprietor Indicator                              |

Approximately **3.8 million title rows**, roughly **1.2 million distinct
corporate proprietors**, around **98,000 overseas entities**.

## What CCOD does not contain

- **Individual ownership.** Titles held by natural persons are excluded
  by design. They appear in a separate "Price Paid Data" release; we
  don't index those.
- **Beneficial ownership.** A nominee or trust may be the registered
  proprietor; the actual beneficial owner is not in CCOD. For UK
  companies the
  [PSC register](https://www.gov.uk/government/publications/psc-requirements-for-companies-and-limited-liability-partnerships)
  is the right primary source. For overseas owners, see the
  [Register of Overseas Entities](https://www.gov.uk/guidance/register-an-overseas-entity).
- **Charges, restrictions, or rights.** CCOD names the proprietor only.
  Lender, lease term, easements, covenants — all in the Title Register
  proper, none in CCOD.
- **Title plans.** Maps and boundaries are sold separately by Land
  Registry.
- **Scotland and Northern Ireland.** Their registry systems are
  independent.

## CCOD vs the Title Register

| Aspect              | CCOD                          | Title Register                       |
| ------------------- | ----------------------------- | ------------------------------------ |
| Coverage            | Corporate proprietors only    | All registered titles                |
| Format              | Monthly CSV release           | Per-title PDF on demand              |
| Cost                | Free (under OGL v3.0)         | £3 per title (HM Land Registry)      |
| Contents            | Proprietor + headline address | Proprietor, charges, restrictions, plan |
| Best for            | Searching across companies    | Confirming a specific title          |

A typical workflow uses **both**: search CCOD on this site to identify
candidate titles, then order the title register from HM Land Registry
for the ones you need to verify.

## Where to read more

- [Official CCOD landing page](https://use-land-property-data.service.gov.uk/datasets/ccod)
  (HM Land Registry).
- [Data User Guide (PDF)](https://use-land-property-data.service.gov.uk/datasets/ccod/tech-spec)
  — the canonical schema documentation.
- [OCOD (Overseas Ownership Data)](/data/ocod) — the sister dataset for
  non-UK companies.

## Next

- [OCOD](/data/ocod) — the overseas-companies equivalent, which we merge
  into the same index.
- [Companies House cross-reference](/data/companies-house) — how the CRN
  in CCOD links out.
- [Refresh schedule](/data/refresh-schedule) — when the monthly update
  hits the index.
