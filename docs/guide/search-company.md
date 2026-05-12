---
title: Company search
description: Lookup by company name (fuzzy) or Companies House registration number (exact).
---

# Company search

The company mode resolves a name or registration number to every CCOD title
held by that proprietor.

## By Companies House number (CRN)

The CRN is the most precise match. It's a fixed 8-character identifier
issued by Companies House. Two examples:

| CRN          | Company                       |
| ------------ | ----------------------------- |
| `00445790`   | TESCO PLC                     |
| `00604574`   | TESCO STORES LIMITED          |
| `OC305129`   | LINKLATERS LLP                |
| `OE029114`   | Kirkwood Holdings S.à r.l. (overseas) |

The matcher:

1. Uppercases your input.
2. Strips spaces, hyphens, and parentheses.
3. Matches against the normalised `company_reg_normalized` column —
   a single B-tree index lookup.

This is why a CRN search is consistently the fastest mode.

::: tip
Leading zeros count. `604574` will not match `00604574`. The UI preserves
zeros if you paste them.
:::

## By company name

When you don't have the number, type the name. Behind the scenes:

1. Your term is uppercased and trimmed.
2. We run a **trigram-similarity** query against
   `proprietors.proprietor_name_upper`.
3. Matches above the similarity threshold (default `0.45`) are returned,
   sorted by similarity descending, then by date proprietor added.

Trigram matching means these will all find the same company:

- `BARRATT DEVELOPMENTS PLC`
- `Barratt Developments`
- `Barratt Development Ltd`  (note typo)
- `barratt developments p.l.c.`

What it does **not** do:

- Find subsidiaries by parent name (`Barratt` won't return
  `BDW Trading Ltd`).
- Match nicknames (`Barratt` is fine, but `Barratts Homes` will rank
  lower than the legal name).

To follow group structure you'll typically combine company-search
results with a [director search](/guide/search-director) on the
shared directors, or run several CRN searches in turn.

## Result ordering

Rows come back ordered by:

1. Exact CRN match first (if you searched by number).
2. Trigram similarity to your input.
3. `date_proprietor_added` descending (most recent appointment first).

## Proprietorship categories

A title can have up to four proprietors. The `proprietorship_category`
field tells you the legal form. Common values:

| Category                        | Notes                                     |
| ------------------------------- | ----------------------------------------- |
| `Limited Company or Public Limited Company` | UK Ltd / PLC          |
| `Limited Liability Partnership` | UK LLP                                    |
| `Corporate Body`                | Statutory bodies, councils, NHS trusts    |
| `Limited Partnership`           | UK LP                                     |
| `Unlimited Company`             | Rare; private unlimited co.               |
| `Overseas Company`              | Registered outside UK — see [OCOD](/data/ocod) |

## Common pitfalls

- **The company has been renamed.** CCOD records the proprietor name as
  registered at the title — that may be the old name. Search by CRN to
  catch both old and new entries.
- **The company has been struck off.** Titles registered to dissolved
  companies remain in CCOD until the register is updated. They still
  appear in your results.
- **The proprietor is a nominee.** CCOD shows the registered proprietor,
  which is sometimes a nominee or trustee. The beneficial owner is **not**
  in CCOD — you need the
  [Persons with Significant Control register](https://www.gov.uk/government/publications/psc-requirements-for-companies-and-limited-liability-partnerships)
  for that.

## API

Same search via JSON: see [API · Search endpoint](/api/search).

```bash
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "name",
    "search_value": "Barratt Developments PLC",
    "session_id": "cs_test_..."
  }'
```
