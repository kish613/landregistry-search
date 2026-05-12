---
title: Schema reference
description: The SQL schema behind the search.
---

# Schema reference

The index is stored in two main tables, plus auxiliary tables for
auth and payments. This page documents the schema relevant to the
search and API. The full DDL is in
[`schema.sql`](https://github.com/kish613/landregistry-search/blob/master/schema.sql)
in the repo.

## `properties`

One row per registered title.

| Column                            | Type      | Notes                                         |
| --------------------------------- | --------- | --------------------------------------------- |
| `id`                              | int (PK)  | Surrogate primary key.                        |
| `title_number`                    | text      | HM Land Registry title number.                |
| `tenure`                          | text      | `Freehold` or `Leasehold`.                    |
| `property_address`                | text      | Full address as registered.                   |
| `district`                        | text      | Local authority district.                     |
| `county`                          | text      | Historic county.                              |
| `region`                          | text      | Statistical region.                           |
| `postcode`                        | text      | UK postcode. Often empty for older titles.    |
| `multiple_address_indicator`      | text      | `Y` / `N`.                                    |
| `price_paid`                      | text      | Sale price in pounds, as published. May be empty. |
| `date_proprietor_added`           | text      | ISO 8601 date.                                |
| `additional_proprietor_indicator` | text      | `Y` / `N`.                                    |
| `data_source`                     | text      | `CCOD` or `OCOD`.                             |
| `created_at`                      | timestamp | Row import time.                              |

Normalised columns added by `migrate_add_indexes.py`:

| Column                       | Notes                                                |
| ---------------------------- | ---------------------------------------------------- |
| `property_address_upper`     | Uppercased, trimmed. Trigram-indexed.                |
| `postcode_upper`             | Uppercased, trimmed. Trigram-indexed.                |

## `proprietors`

One row per (title, proprietor) — up to 4 per title.

| Column                       | Type     | Notes                                         |
| ---------------------------- | -------- | --------------------------------------------- |
| `id`                         | int (PK) | Surrogate primary key.                        |
| `property_id`                | int (FK) | → `properties.id`. `ON DELETE CASCADE`.       |
| `proprietor_number`          | int      | 1–4. Order from the CCOD source.              |
| `proprietor_name`            | text     | As registered.                                |
| `company_registration_no`    | text     | Companies House CRN. Possibly empty for OCOD. |
| `proprietorship_category`    | text     | Legal form of proprietor.                     |
| `country_incorporated`       | text     | OCOD only; `NULL` for CCOD.                   |
| `address_line_1`             | text     | Proprietor's registered address.              |
| `address_line_2`             | text     | "                                             |
| `address_line_3`             | text     | "                                             |

Normalised columns:

| Column                       | Notes                                                |
| ---------------------------- | ---------------------------------------------------- |
| `company_reg_normalized`     | CRN uppercased, with spaces / hyphens / parens stripped. B-tree indexed. |
| `proprietor_name_upper`      | Uppercased, trimmed. Trigram-indexed.                |

## Indexes

| Index                          | Type      | Column                                        |
| ------------------------------ | --------- | --------------------------------------------- |
| `idx_company_registration_no`  | B-tree    | `proprietors.company_registration_no`         |
| `idx_company_reg_normalized`   | B-tree    | `proprietors.company_reg_normalized`          |
| `idx_property_id`              | B-tree    | `proprietors.property_id`                     |
| `idx_title_number`             | B-tree    | `properties.title_number`                     |
| `idx_postcode`                 | B-tree    | `properties.postcode`                         |
| `idx_proprietor_name_trgm`     | GIN trgm  | `proprietors.proprietor_name_upper`           |
| `idx_property_address_trgm`    | GIN trgm  | `properties.property_address_upper`           |
| `idx_postcode_trgm`            | GIN trgm  | `properties.postcode_upper`                   |

The GIN trigram indexes require the `pg_trgm` Postgres extension. They
turn `LIKE '%term%'` queries into single-millisecond lookups on the
3.8M-row table.

## Auxiliary tables (auth & payments)

The auth tables (`users`, `magic_links`, `credit_transactions`,
`password_reset_tokens`) and the `payments` table support the account
system. They are not relevant to the search workflow itself — see
[`schema.sql`](https://github.com/kish613/landregistry-search/blob/master/schema.sql)
for definitions.

## Storage footprint

Approximate sizes on Postgres 15 with the production index set:

| Table         | Rows     | Data    | Indexes |
| ------------- | --------:|--------:|--------:|
| `properties`  |  3.8 M   | ~1.8 GB | ~0.6 GB |
| `proprietors` |  6.5 M   | ~2.4 GB | ~1.2 GB |

Total disk: roughly 6 GB. Memory budget for the production instance is
8 GB — enough to keep the hot indexes in shared buffers.
