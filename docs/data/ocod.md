---
title: OCOD (overseas)
description: The Overseas Companies Ownership Data dataset, merged into the same index as CCOD.
---

# OCOD — Overseas Companies Ownership Data

OCOD is the sister dataset to [CCOD](/data/ccod) — same shape, but for
**non-UK companies** that own freehold or leasehold titles in England
and Wales.

We import OCOD into the same `properties` and `proprietors` tables as
CCOD, with `data_source = 'OCOD'` set on the row. Searches don't ask
you to choose between them: results are merged by default.

## What's different about OCOD

Compared to a CCOD row, an OCOD row adds one field that's always
populated:

- `country_incorporated` — country of incorporation (e.g. `JERSEY`,
  `BRITISH VIRGIN ISLANDS`, `LUXEMBOURG`).

And subtracts one field that's often **empty**:

- `company_registration_no` — overseas companies don't always have a
  Companies House number. Some carry a foreign registration ID in
  this field; many leave it blank.

The address fields can be longer and noisier than CCOD's, because
foreign address formats don't map cleanly to UK conventions.

## Coverage

Approximately **98,000 overseas-owned titles** in the current release.
The major jurisdictions, in order of frequency:

| Country of incorporation       | Approx. titles |
| ------------------------------ | --------------:|
| Jersey                         |          25,400|
| British Virgin Islands         |          17,200|
| Guernsey                       |          11,900|
| Isle of Man                    |           9,400|
| Luxembourg                     |           6,800|
| Hong Kong                      |           3,200|
| Panama                         |           2,500|
| Singapore                      |           2,100|
| Other                          |          19,500|

Numbers move month-to-month; the table above is illustrative of typical
proportions.

## Why OCOD matters

Overseas ownership has been a focal point for UK transparency reform:

- The **Register of Overseas Entities** (2022) now requires overseas
  companies that own UK property to register their beneficial owners
  separately.
- Sanctions regimes (Russia, others) intersect heavily with overseas
  property ownership.

OCOD on its own gives you the **registered proprietor and country of
incorporation**. To get from there to the **beneficial owner**, you
need the Register of Overseas Entities (separate gov.uk service).

## Search behaviour

OCOD rows appear in every search type:

- **Company name / CRN** — overseas companies often have stylised
  names ("Holdings S.à.r.l.", "Limited Partnership", "Pte. Ltd."); use
  fuzzy matching.
- **Address** — identical to CCOD.
- **Director** — the Companies House officer endpoint covers UK and
  overseas companies registered in the UK. Some overseas entities are
  not Companies House-registered at all (they hold property directly)
  — those will not surface via a director search.

## Identifying OCOD rows in results

The `data_source` field is `OCOD` for overseas, `CCOD` for UK. You can
filter your CSV export on this column.

## Reference

- [Official OCOD page](https://use-land-property-data.service.gov.uk/datasets/ocod)
- [Register of Overseas Entities (Companies House)](https://www.gov.uk/guidance/register-an-overseas-entity)
