---
title: Exporting data
description: Download result sets as CSV or JSON.
---

# Exporting data

Every search produces a result set you can export to **CSV** or **JSON**.
Exports are free (you've already paid for the search) and are generated
on demand against the original query — there is no separate "export
credit".

## CSV export

CSV is the right choice for Excel, Google Sheets, Numbers, or any
data-analysis tool.

### Columns

The CSV always contains the following 12 columns, in this order:

```
title_number, tenure, property_address, district, county, region,
postcode, price_paid, proprietor_name, company_registration_no,
proprietorship_category, date_proprietor_added
```

Multiple proprietors per title are flattened into multiple rows (one
per proprietor). The `title_number` repeats across those rows.

### Filename

```
properties_{search_type}_{search_value_first_20_chars}.csv
```

For example:

```
properties_name_Barratt_Developments.csv
properties_address_SW7_2AX.csv
properties_director_Jonathan_Smith.csv
```

### Encoding

UTF-8, comma-delimited, double-quoted strings. RFC 4180 compliant.

## JSON export

JSON keeps the structured data — useful for piping into another tool,
storing for audit, or rehydrating into a database.

### Shape

```json
{
  "search_type": "name",
  "search_value": "Barratt Developments PLC",
  "count": 1247,
  "properties": [
    {
      "title_number": "NGL123456",
      "tenure": "Freehold",
      "property_address": "...",
      "postcode": "SW7 2AX",
      "proprietor_name": "BARRATT DEVELOPMENTS PLC",
      "company_registration_no": "00604574",
      "proprietorship_category": "Limited Company or Public Limited Company",
      "date_proprietor_added": "2015-08-21",
      "price_paid": "42000000"
    }
    // …
  ]
}
```

For [director searches](/guide/search-director) the JSON also includes a
`directors_found` array:

```json
{
  "search_type": "director",
  "search_value": "Jonathan M. Smith",
  "count": 12,
  "directors_found": [ … ],
  "properties": [ … ]
}
```

## API export

The same exports are available over HTTP — see
[API · Export endpoints](/api/export):

```bash
# CSV
curl -X POST https://landregistry.company/api/export/csv \
  -H "Content-Type: application/json" \
  -d '{"search_type": "name", "search_value": "Tesco Stores Limited"}' \
  -o tesco-stores.csv

# JSON
curl -X POST https://landregistry.company/api/export/json \
  -H "Content-Type: application/json" \
  -d '{"search_type": "name", "search_value": "Tesco Stores Limited"}' \
  > tesco-stores.json
```

::: tip
Exports re-run the search against the latest index. If the monthly CCOD
refresh has happened since you originally paid, you'll see the new data
in the export. That's deliberate.
:::

## Privacy

Exports are generated server-side on demand. We don't store them and we
don't email them. Nothing about your downloaded file ever leaves your
device once it's on disk.

## Sharing exports

The data is under the **Open Government Licence v3.0**. You can share
exports, transform them, and use them commercially — provided you
attribute HM Land Registry. See [Licensing](/data/licensing).
