---
title: Export endpoints
description: CSV and JSON exports — same search, different envelope.
---

# Export endpoints

Re-run a search and stream the result set as **CSV** or **JSON**. No
extra charge — exports re-use the original payment / credit deduction
audit row from the search itself.

::: warning Note
The current implementation re-runs the search at the time of export.
That means a re-export tomorrow may include rows from the new monthly
CCOD release. If you want a frozen snapshot, persist the JSON locally
when you first download it.
:::

## `POST /api/export/csv`

### Request

```json
{
  "search_type": "name",
  "search_value": "Tesco Stores Limited"
}
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: text/csv
Content-Disposition: attachment; filename=properties_name_Tesco_Stores_Limited.csv

title_number,tenure,property_address,district,county,region,postcode,price_paid,proprietor_name,company_registration_no,proprietorship_category,date_proprietor_added
NGL123456,Freehold,"100 High Street, London",Westminster,"Greater London",LONDON,SW1A 1AA,42000000,TESCO STORES LIMITED,00519500,Limited Company or Public Limited Company,2015-08-21
...
```

The 12 columns are fixed in this order:

```
title_number, tenure, property_address, district, county, region,
postcode, price_paid, proprietor_name, company_registration_no,
proprietorship_category, date_proprietor_added
```

For titles with multiple proprietors, the title_number repeats across
rows — one row per (title, proprietor).

Encoding: UTF-8, RFC 4180.

## `POST /api/export/json`

### Request

```json
{
  "search_type": "director",
  "search_value": "Jonathan M. Smith"
}
```

### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "search_type": "director",
  "search_value": "Jonathan M. Smith",
  "count": 23,
  "properties": [
    {
      "title_number": "NGL123456",
      "tenure": "Freehold",
      "property_address": "100 High Street, London",
      "district": "Westminster",
      "county": "Greater London",
      "region": "LONDON",
      "postcode": "SW1A 1AA",
      "multiple_address_indicator": "N",
      "price_paid": "42000000",
      "date_proprietor_added": "2015-08-21",
      "proprietor_name": "ACME HOLDINGS LIMITED",
      "company_registration_no": "12345678",
      "proprietorship_category": "Limited Company or Public Limited Company",
      "country_incorporated": null,
      "data_source": "CCOD"
    }
  ],
  "directors_found": [
    {
      "name": "JONATHAN MARCUS SMITH",
      "company_name": "ACME HOLDINGS LIMITED",
      "company_number": "12345678",
      "role": "director",
      "appointed_on": "2018-04-12",
      "resigned_on": null
    }
  ]
}
```

`directors_found` is only present for `search_type: "director"`.

## Error cases

| HTTP | Body                                                | When                                  |
| ---- | --------------------------------------------------- | ------------------------------------- |
| 400  | `{ "success": false, "error": "Search value is required" }` | Empty `search_value`.        |
| 400  | `{ "success": false, "error": "No results to export" }`     | The search returned 0 rows. |
| 400  | `{ "success": false, "error": "<Companies House error>" }`  | Director search upstream error. |

## Examples

```bash
# CSV → file
curl -X POST https://landregistry.company/api/export/csv \
  -H "Content-Type: application/json" \
  -d '{"search_type":"name","search_value":"Tesco Stores Limited"}' \
  -o tesco.csv

# JSON → stdout, piped to jq
curl -X POST https://landregistry.company/api/export/json \
  -H "Content-Type: application/json" \
  -d '{"search_type":"address","search_value":"SW7 2AX"}' \
  | jq '.properties[].proprietor_name' | sort -u
```
