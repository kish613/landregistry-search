---
title: Tips & best practice
description: Hard-won workflow tips for journalists, lawyers, and analysts.
---

# Tips & best practice

A grab-bag of suggestions from real users of the site.

## Prefer CRN to name

A CRN is unique forever and never changes, even after rename, restructure,
or strike-off. A name search is a fuzzy match against the proprietor name
**as registered at the time** — that may be the old name.

If you have the number, use it. If you don't, the company search page on
[Companies House](https://find-and-update.company-information.service.gov.uk/)
will give you one in a click.

## Two CRN searches beat one name search for groups

There's no automatic group-resolution in CCOD. To trace a group, run a
sequence of CRN searches against each entity in the structure. Companies
House's "filing history" gives you the family tree.

Quicker still: a [director search](/guide/search-director) on the group
finance director (or a long-tenured non-exec) usually surfaces every
material entity in the group at once.

## Use the postcode partial when the full one fails

For new builds especially, the full postcode may not be in CCOD yet.
Drop down to the outward code (`SW7` instead of `SW7 2AX`) and filter
in your spreadsheet.

## Export early, dedupe later

Export the first result set even if it's noisy — it's free. You can
filter and dedupe in a spreadsheet faster than you can iterate on
the search string. The CSV is RFC-4180 compliant and opens cleanly in
Excel, Numbers, and Sheets.

## Pin the title number for follow-up

The `title_number` is the canonical reference for everything downstream
— ordering the title register, requesting the title plan, looking up
charges. Always include it when you forward an export to a lawyer or
to a registry.

## Cross-reference, don't trust

CCOD is the registered position as of the last monthly release. For
anything time-sensitive (an imminent transaction, a court filing, a
press deadline), order the official title register from HM Land Registry
**after** narrowing the field here. CCOD finds the candidate; the title
register confirms it.

## Common false negatives

A search returns no rows when:

- The company is correct but holds the land **personally through
  individuals** (CCOD doesn't cover individual proprietors).
- The property is **unregistered**. Most urban land is now registered,
  but pockets remain.
- The title is **registered outside England and Wales** —
  Scotland and Northern Ireland aren't in CCOD.
- The acquisition is **so recent** it hasn't made the monthly release
  yet. Try again next month.

## Common false positives

A search returns *too many* rows when:

- The company name is generic (e.g. `Properties Limited`). Always
  pair a generic name with a postcode or director-name filter.
- A director shares a name with someone else (`John Smith`). Sense-
  check the `directors_found` array before trusting the joined property
  list.

## Citing in writing

If you publish anything based on a search, the conventional citation is:

> Source: HM Land Registry Commercial and Corporate Ownership Data
> (CCOD), {month} {year} release, indexed via landregistry.company.
> Contains HM Land Registry data © Crown copyright and database right
> {year}. Released under the Open Government Licence v3.0.

See [Licensing](/data/licensing) for the full attribution boilerplate.

## When to escalate

If a search returns clearly wrong data — a CRN that resolves to the
wrong company, a title that's miscategorised, a missing dataset —
email **hello@inteltree.co.uk** with the search URL and the
expected result. We re-import affected slices manually inside 48 hours
when the underlying CCOD release is correct.
