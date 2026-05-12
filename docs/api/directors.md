---
title: Director endpoints
description: Two-step director search via Companies House + CCOD.
---

# Director endpoints

Director search is split into two endpoints so that you can preview the
list of officers (cheap) before committing to a paid fan-out (3 credits
or £3).

## `POST /api/search/directors`

Look up officers on Companies House by name. **Not charged** — this is
a preview to help you disambiguate before running the paid search.

### Request

```json
{ "director_name": "Jonathan M. Smith" }
```

### Response

```json
{
  "success": true,
  "directors": [
    {
      "name": "JONATHAN MARCUS SMITH",
      "company_name": "ACME HOLDINGS LIMITED",
      "company_number": "12345678",
      "role": "director",
      "appointed_on": "2018-04-12",
      "resigned_on": null,
      "address": "10 Acme Court, London W1A 0AX"
    }
    // … up to ~100 per page
  ],
  "count": 47
}
```

If Companies House returns nothing, you get an empty `directors` array
and `count: 0`.

### Use case

Show this list to the user, let them pick a specific person (by name +
date of birth), and only then run the paid full search.

## `POST /api/search/director-properties`

Run the full director search — Companies House officer fan-out plus
CCOD lookup for every matched company. **Charged: 3 credits or £3.**

### Request

```json
{
  "director_name": "Jonathan M. Smith",
  "session_id": "cs_test_…",      // if not using credits
  "use_credits": true              // optional, defaults to true
}
```

### Response

Identical envelope to the [main search endpoint](/api/search) with
`search_type: "director"`:

```json
{
  "success": true,
  "search_type": "director",
  "director_name": "Jonathan M. Smith",
  "directors_found": [ /* full appointment list, like `/api/search/directors` */ ],
  "results": [ /* CCOD title rows */ ],
  "count": 23,
  "suggestions": [],
  "credits_used": true,
  "remaining_credits": 6
}
```

### Errors

If Companies House is unreachable, returns:

```json
{
  "success": false,
  "error": "Could not reach the Companies House API. Please try again in a moment.",
  "results": [],
  "count": 0,
  "suggestions": [],
  "directors_found": [],
  "credits_used": false,
  "remaining_credits": 9
}
```

When this happens, credits are **not** deducted.

## Why two endpoints

The site's UI calls `/api/search/directors` on every keystroke (debounced)
to populate the suggestion dropdown — that's a cheap, unmetered call. The
paid `/api/search/director-properties` only fires when the user confirms a
specific name. The split keeps everything fast and avoids accidentally
charging for an exploration round.

When calling the API directly from a script, you can skip straight to
`/api/search/director-properties` — there's no requirement to call the
preview endpoint first.

## Caching

Officer lookups (the unmetered endpoint) are cached for 60 minutes per
exact name. The full search re-queries every time so it always reflects
the latest CCOD + appointment state.
