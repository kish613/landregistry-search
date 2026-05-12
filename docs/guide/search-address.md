---
title: Address search
description: Reverse lookup — find the corporate proprietor for a property.
---

# Address search

Address mode is a **reverse lookup**: you give us a property, we give you
the registered corporate proprietor (if there is one).

## What you can type

| Input                                | Behaviour                                              |
| ------------------------------------ | ------------------------------------------------------ |
| `SW7 2AX`                            | Full postcode — usually a single building or block.    |
| `SW7`                                | Outward code — matches everything in that postal area. |
| `12 Kensington Gore, London`         | Full address — matched as a substring.                 |
| `Kensington Gore`                    | Street name — matches every title on the street.       |
| `Royal Albert Hall`                  | Property name — matched as a substring.                |

## Matching rules

1. Your term is uppercased and trimmed.
2. Postcodes are detected and matched against
   `properties.postcode_upper` (trigram index).
3. Non-postcode strings are matched against
   `properties.property_address_upper` (trigram index).
4. Results are ordered by exact match first, then by similarity.

The address text stored in CCOD is exactly as registered. We don't
re-geocode or rewrite it — so abbreviations match abbreviations
(`Rd` ≠ `Road` for substring matching). If a partial doesn't return
what you expect, try a shorter substring.

## Result scope

You get **every title** whose registered address matches. That can
include:

- The freehold and one or more leaseholds at the same address.
- Multiple flats / units at a single street number.
- Adjoining titles where the registered address strings overlap.

The `multiple_address_indicator` flag tells you when a single title
covers multiple addresses (e.g. a development with several units on
one title). The full address list isn't included in CCOD — only the
"primary" address registered with the title.

::: warning Unregistered land
Only **registered** titles appear in CCOD. If a building is held under
an unregistered title (rare in urban areas, more common for rural
estates), an address search returns no rows. That isn't a bug — it's
a gap in the underlying register.
:::

## Edge cases

- **Postcode reuse.** Royal Mail occasionally retires and reissues
  postcodes. CCOD reflects the postcode that was current at the time
  of the proprietor's registration; we don't back-date.
- **New-build addresses.** Newly assigned postcodes can take 6–12
  months to flow through HM Land Registry's monthly release. Try the
  street name or developer plot reference if the postcode isn't yet
  in the index.
- **Title vs property.** The address on a title is the *registered*
  address. A leasehold flat may have a separate postal address used
  in the lease — we hold the registered one.

## When you should still order an official title register

For the **definitive** owner, chain of charges, restrictions, and lease
plan, you still want the **Title Register** from HM Land Registry
(£3 per title). CCOD only gives you the corporate proprietor as last
registered — not the full deeds bundle. See
[`/data/ccod`](/data/ccod#ccod-vs-the-title-register) for the comparison.

## API

```bash
curl -X POST https://landregistry.company/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "address",
    "search_value": "SW7 2AX",
    "session_id": "cs_test_..."
  }'
```
