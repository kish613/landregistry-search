---
title: Coverage & limits
description: What CCOD covers, what it doesn't, and where to go for everything else.
---

# Coverage & limits

A frank list of what you can and cannot answer from this site.

## In scope

- **Freehold and leasehold titles** registered in **England and Wales**.
- Owned by a **company** — UK or overseas.
- As of the most recent monthly CCOD release.

That's roughly **3.8 million titles** held by **1.2 million corporate
proprietors**, of which about **98,000 are overseas entities**.

## Out of scope

::: warning Individual ownership
Properties held by natural persons (you, your neighbour, most
homeowners) are **not** in CCOD. The HM Land Registry "Price Paid"
dataset captures purchase prices for residential transactions; we
don't index that.
:::

::: warning Scotland and Northern Ireland
Both have separate registries:

- **Registers of Scotland** — `ros.gov.uk`
- **Land & Property Services NI** — `nidirect.gov.uk/land-and-property-services`

Neither feeds into CCOD. A search here will not return anything for a
property in Edinburgh or Belfast.
:::

::: warning Unregistered land
Title registration was made compulsory progressively from 1925, with a
trigger-event regime that's still working through the long tail. About
**12% of England and Wales** by area is still unregistered (often rural
estates, historic family-held land). CCOD will not show these because
the register doesn't yet.
:::

::: warning Charges, restrictions, lease plans
CCOD names the proprietor; it doesn't reproduce the full register.
For charges (mortgages), restrictions (e.g. consent required to sell),
lease term, easements, and the title plan you need the **Title
Register** itself — order at £3 per title from HM Land Registry.
:::

::: warning Beneficial ownership
CCOD shows the *legal* proprietor as registered. If that proprietor is
a nominee or trustee, CCOD does not name the beneficial owner. For UK
companies, the **PSC register** (Persons with Significant Control) is
the right primary source. For overseas owners, the **Register of
Overseas Entities** (live since August 2022) names the beneficial
owners separately.
:::

::: warning Pre-publication transactions
A sale that completes today won't appear in CCOD until HM Land Registry
records the change of proprietor and includes it in the next monthly
release. Lag of 4–10 weeks is typical; longer in rare cases.
:::

::: warning Title plans, deeds, and historic register entries
None of these are in CCOD. They sit with HM Land Registry, and are
ordered per-title.
:::

## Edge-case behaviour

- **Renamed companies.** CCOD shows the proprietor name **as registered
  at the time**. If a company has renamed since acquiring the title,
  CCOD will show the old name. A CRN search picks up both.
- **Dissolved companies.** Titles registered to dissolved companies
  remain in CCOD until the register is updated (which happens slowly).
  They still appear in your results — sense-check on Companies House.
- **Joint corporate ownership.** A title can have up to four
  proprietors. We show all four in the result row.
- **Tenants in common, trusts.** Not modelled in CCOD. The proprietor
  list is what it is.

## Quality issues we know about

A handful of recurring quirks in CCOD that we surface as-is:

- **Stray whitespace in proprietor names.** Trailing spaces, double
  spaces, inconsistent capitalisation. Our search normalises
  these for matching; the result row preserves the source.
- **`Country Incorporated` formatting in OCOD.** Mixed case,
  occasional spelling drift (`BVI` vs `British Virgin Islands`).
- **Address strings.** Free-text, occasionally truncated. Don't rely
  on them being parseable into structured fields.

We don't silently clean these; the source is authoritative.

## What to do when CCOD isn't enough

| You need…                              | Go to…                                  |
| -------------------------------------- | --------------------------------------- |
| Full title register + plan             | [HM Land Registry "Find a property"](https://search-property-information.service.gov.uk/) |
| UK persons with significant control    | [Companies House search](https://find-and-update.company-information.service.gov.uk/) |
| Overseas beneficial owners             | [Register of Overseas Entities](https://www.gov.uk/guidance/register-an-overseas-entity) |
| Residential sale prices (individuals)  | [HM Land Registry Price Paid Data](https://landregistry.data.gov.uk/app/ppd) |
| Scotland                                | [Registers of Scotland](https://www.ros.gov.uk/) |
| Northern Ireland                       | [Land & Property Services NI](https://www.nidirect.gov.uk/campaigns/land-and-property-services-lps) |
