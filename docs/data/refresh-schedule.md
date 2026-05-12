---
title: Refresh schedule
description: When CCOD updates, when our index updates, and what falls between.
---

# Refresh schedule

HM Land Registry publishes CCOD **monthly**. We mirror that cadence.

## Cadence

| Step                                       | Approximate timing            |
| ------------------------------------------ | ----------------------------- |
| HM Land Registry release window            | First week of the month       |
| `landregistry.company` import begins       | Within 24 h of release        |
| Re-index complete and live                 | Within 48 h of release        |
| Refresh interval (target)                  | 30 ± 3 days                   |

The exact release day from HM Land Registry varies — early-month
weekdays, usually the 1st–7th. We schedule our import to start the
morning after the official publication.

## How to know what version you're seeing

Every page on `landregistry.company` shows the active CCOD version in
the header strip:

```
SHEET EW-144 · CCOD v2026.04 · 3,814,226 titles indexed
```

The version string is `vYYYY.MM` — calendar year, calendar month of the
HM Land Registry release.

The API surfaces the same information at `/api/status` (planned) and in
the `X-CCOD-Version` response header on every successful search.

## What happens to in-flight searches during a refresh

Refreshes run against a **shadow database**. User traffic continues to
hit the previous version until the new version finishes importing and
is promoted. There is no read-only window.

If you happen to run a search precisely as the connection string flips
(a few seconds, once per month), you may see a result set from the
*previous* version even though the header has moved on. Re-running the
search clears that.

## Delta release? No — full snapshots

CCOD doesn't ship deltas. Every monthly release is a full snapshot.
We re-import the entire dataset rather than computing diffs:

- Cleaner — drift between deltas and snapshots is a recurring source
  of bugs.
- Fast enough — 8–15 minutes on a warm Postgres instance.
- Lets us pick up schema tweaks in the source without special-casing
  them.

## Historical data

We hold the **current** release and the **previous two months** in
cold storage for diff queries. They are not exposed to the public
search at present. If you need a historical slice for research, email
**hello@inteltree.co.uk** and we can usually provide a CSV under the
Open Government Licence.

## Release notes

When HM Land Registry changes the CSV schema or column names (it happens
1–2× per year) we annotate it in the [changelog](/changelog).
