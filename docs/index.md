---
layout: home

title: Docs
titleTemplate: landregistry.company — documentation

hero:
  name: "landregistry.company"
  text: "Documentation"
  tagline: A searchable index of every freehold and leasehold interest in England & Wales registered to a UK or overseas company. Indexed by company, address, or director.
  image:
    src: /logo-mark.svg
    alt: landregistry.company
  actions:
    - theme: brand
      text: Read the guide
      link: /guide/introduction
    - theme: alt
      text: API reference
      link: /api/overview
    - theme: alt
      text: Run a search ↗
      link: https://landregistry.company/search

features:
  - icon: 🏛
    title: Official CCOD data
    details: Mirrors HM Land Registry's Commercial and Corporate Ownership Data — every registered title held by a UK or overseas company, refreshed monthly.
    link: /data/ccod
    linkText: Data sources

  - icon: 🔎
    title: Three ways to search
    details: Look up by company name or registration number, by full / partial address, or by an individual director's name via Companies House.
    link: /guide/search-methods
    linkText: Search methods

  - icon: 👥
    title: Director cross-reference
    details: Pivot from a named person to every company they're appointed to — then to every title those companies hold. One workflow, current and historic.
    link: /guide/search-director
    linkText: Director search

  - icon: 📤
    title: CSV & JSON export
    details: Every result set exports to CSV for spreadsheets or JSON for tooling. Exports include title, tenure, proprietor, CRN, and address detail.
    link: /guide/exporting
    linkText: Exporting

  - icon: 💷
    title: Pay per search, no subscription
    details: £1 per title or address search, £3 per director search. Sign up for 10 free credits — no monthly fee, no minimum.
    link: /guide/pricing
    linkText: Pricing

  - icon: 🔌
    title: JSON API
    details: The same endpoints that power the site are documented here. Authenticated with session credits or per-search Stripe payment.
    link: /api/overview
    linkText: API reference
---

<div style="max-width: 880px; margin: 64px auto 0; padding: 0 24px; text-align: center;">

<span class="lr-eyebrow">What is this?</span>

## The register, indexed and searchable

`landregistry.company` mirrors HM Land Registry's Commercial and Corporate
Ownership Data (CCOD), layers a fast search index on top, and cross-references
the result with Companies House — so you can move from **a company → its
titles**, **a postcode → its proprietor**, or **a director → every property
their companies own**.

The data is public; the index is the product. The site exists because the
official CSV releases are not searchable, not cross-referenced, and not
exportable as filtered slices.

This docs site explains what the index covers, how to search it, and how to
call the API.

</div>
