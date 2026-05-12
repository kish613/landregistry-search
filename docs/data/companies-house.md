---
title: Companies House cross-reference
description: How we link CCOD proprietors to Companies House data, and what that buys you.
---

# Companies House cross-reference

The **Companies House** integration is what makes director search
possible, and what lets you pivot from a CCOD row to live filings and
appointment history.

## What's joined

Two integrations, used in different places:

1. **Officer search** — the `/api/search/directors` endpoint queries
   Companies House for live and historic officers under a supplied
   name. Used by [director search](/guide/search-director).
2. **Company lookup** — for each appointment, we look up the company's
   CRN against the CCOD/OCOD index to find titles. We do not enrich
   the CCOD row with extra Companies House metadata at search time;
   the link is the CRN.

There is **no batch re-import of Companies House data**. Companies
House is queried on demand, per search.

## The link key: CRN

Every UK-registered company has a unique 8-character Companies House
registration number (CRN). Format examples:

| Prefix     | Meaning                          |
| ---------- | -------------------------------- |
| `00000001`–`14000000+` | England & Wales companies     |
| `SC……`     | Scottish companies              |
| `NI……`     | Northern Irish companies        |
| `OC……`     | LLPs                            |
| `FC……`     | Overseas companies registered to operate in the UK |
| `OE……`     | Register of Overseas Entities IDs |

CCOD stores the CRN as supplied — some leading zeros are present, some
have been historically truncated. Our normalisation column
`company_reg_normalized` strips spaces/hyphens/parentheses and
uppercases, which is what's actually indexed for lookups.

## What you don't get from CCOD alone

CCOD gives you the proprietor's **registered name** and **CRN**. To
get any of the following you have to follow the CRN out to
Companies House:

- Current officers, PSCs, accounts, charges register.
- Group structure (parent/subsidiary relationships are filed there).
- Active vs dissolved status, last accounts filed.
- Trading addresses (which can differ from CCOD's "address of
  proprietor as registered").

For UK officers and persons with significant control, Companies House
publishes its own bulk data and API — start at
[developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk/).

## Rate budget

The Companies House API enforces 600 requests per 5 minutes per
authenticated key. The director-search workflow can fan out to many
calls per query (one per appointment). We cache the officer-list
response for 60 minutes per name to keep latency and quota under
control.

## Beneficial ownership

CCOD + Companies House together cover the **legal** proprietor and
the **directors / PSCs** of UK entities. They do **not** cover:

- Trustees, nominees, or beneficiary trusts (where the registered
  proprietor is a nominee).
- Overseas beneficial owners — those are now (post-Aug 2022) on the
  separate **[Register of Overseas Entities](https://www.gov.uk/guidance/register-an-overseas-entity)**.
- Pre-PSC-register ownership history of UK companies (PSC data only
  goes back to April 2016).

For maximum-transparency due diligence you typically pair this site
with Companies House and (for overseas) the Register of Overseas
Entities.
