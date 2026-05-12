---
title: Methodology
description: How the official CSV becomes a fast, queryable index.
---

# Methodology

This page is for the engineer-reader who wants to understand exactly
how we turn HM Land Registry's monthly CSV into a query-ready index.

## Pipeline overview

```
HM Land Registry release           ┌──────────────────────────┐
(CCOD + OCOD CSVs, monthly)  ───▶  │ scripts/load_data.py     │  ──┐
                                   └──────────────────────────┘    │
                                                                   ▼
                                                       ┌────────────────────────┐
                                                       │ Postgres (production)  │
                                                       │ or SQLite (local dev)  │
                                                       └─────────────┬──────────┘
                                                                     │
                                            ┌────────────────────────┴────────────┐
                                            │ scripts/migrate_add_indexes.py     │
                                            │ – normalised columns               │
                                            │ – trigram (pg_trgm) GIN indexes    │
                                            └────────────────────────┬────────────┘
                                                                     │
                                                                     ▼
                                                       ┌──────────────────────────┐
                                                       │ Flask API (app/main.py)  │
                                                       │ /api/search /api/export… │
                                                       └──────────────────────────┘
```

## 1 · Ingest

`scripts/load_data.py` reads the official CSV (`CCOD_FULL_YYYY_MM.csv`)
streaming row-by-row, then:

- Normalises column names from the published headers to our schema.
- Splits the row into one `properties` insert plus up to four
  `proprietors` inserts.
- Coerces `price_paid` to integer pence (preserved as text in CCOD).
- Trims and uppercases the CRN before writing to
  `company_reg_normalized`.
- Sets `data_source = 'CCOD'` or `'OCOD'` based on the input file.

OCOD is loaded by the same script with `--source ocod`. Both end up in
the same tables.

## 2 · Index

`scripts/migrate_add_indexes.py` (Postgres only) creates the indexes
that make the search fast. The relevant ones are:

| Index                              | Type      | Used for                          |
| ---------------------------------- | --------- | --------------------------------- |
| `idx_company_reg_normalized`       | B-tree    | Exact CRN match                   |
| `idx_proprietor_name_trgm`         | GIN trgm  | Fuzzy company-name search         |
| `idx_property_address_trgm`        | GIN trgm  | Fuzzy address search              |
| `idx_postcode_trgm`                | GIN trgm  | Postcode partials                 |
| `idx_property_id` (proprietors)    | B-tree    | Foreign-key join                  |
| `idx_title_number` (properties)    | B-tree    | Title-number lookup               |

Trigram indexing requires the `pg_trgm` extension:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Without it, name and address searches fall back to a sequential scan
— still correct, just slower.

## 3 · Serve

The Flask app (`app/main.py`) exposes the search endpoints. The hot
paths are:

- `search_properties_by_company(crn)` — single B-tree lookup on
  `company_reg_normalized`, then a join.
- `search_properties_by_company_name(name)` — trigram similarity
  query with a tunable threshold (currently `0.45`).
- `search_properties_by_address(addr)` — trigram on `property_address_upper`
  or `postcode_upper`, depending on whether the input looks like a
  postcode.
- `search_properties_by_director(name)` — calls the Companies House
  officer-search endpoint, fans out to the CRN lookup above.

## Performance targets

| Search type             | Median target | p95 target |
| ----------------------- | ------------- | ---------- |
| Company by CRN          | < 60 ms       | < 150 ms   |
| Company by name (fuzzy) | < 200 ms      | < 500 ms   |
| Address / postcode      | < 200 ms      | < 500 ms   |
| Director (cached name)  | < 400 ms      | < 1 s      |
| Director (uncached)     | < 2 s         | < 4 s      |

Director numbers depend on Companies House response time, which is
out of our control.

## Idempotency and re-imports

`load_data.py` is **destructive by design**: it truncates `properties`
and `proprietors` before inserting. CCOD doesn't ship a delta — every
monthly file is a full snapshot, so a full reload is the cleanest path.

This means a re-import:

- Wipes everything and re-creates the tables.
- Re-runs the index migration as the last step.
- Takes 8–15 minutes on a warm Postgres instance.

We never re-import during user traffic; the loader runs against a
shadow database, then DNS / connection-string flips when finished.

## Local development

A SQLite fallback exists for local dev. It has the same schema but
**no trigram indexes** — fuzzy queries are full table scans. Acceptable
for development, painful for production.

See the project [README](https://github.com/kish613/landregistry-search/blob/master/README.md)
for the `python scripts/load_data.py` workflow.
