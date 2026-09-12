# PriceWise Phase 1 — Planning

**Status:** complete  
**Date:** 9 September 2026  
**Working name:** PriceWise  
**Launch city:** Karachi

This document is the Phase 1 contract. It does not implement connectors, scrapers, or UI.

The product promise is **verified, timestamped, normalized prices** — not second-by-second live scraping.

---

## 1. What we are building

A grocery price comparison platform for Pakistan.

User flow:

1. Search (`Surf Excel 1kg`, `Coke 1.5L`)
2. System resolves a canonical product + variant
3. Show side-by-side prices from Pakistani retailers
4. Highlight the cheapest in-stock option
5. Send the user to the retailer to buy

PriceWise never sells the product. PriceWise never scrapes from the browser. The frontend only talks to PriceWise’s API.

---

## 2. Business model

### MVP (no revenue required)

Free consumer tool. No accounts. No ads on comparison results.

### Near-term revenue (after accuracy is trusted)

1. **Affiliate / referral** — Naheed already has a public affiliate program (10% of cart on referred orders, subject to approval). Apply during Phase 2 outreach. Other retailers: ask for tracked outbound links.
2. **Retailer partnerships** — official product feeds in exchange for traffic.
3. **Later:** price alerts, shopping-list optimization, B2B price intelligence.

### What we will not do in MVP

- Sponsored “cheapest” badges
- Ranking that is not explained by price, stock, or user sort
- Mixing grocery with electronics marketplaces (Daraz, etc.) — different matching problem, crowded category

### Competitive gap

Pakistan already has electronics/gadget comparators (Qeemat, PriceWalay, WhatPrice). There is no widely used **grocery** comparator covering Naheed, Metro, Imtiaz, Springs, SPAR, and Carrefour. That is the wedge.

---

## 3. Target users

### Primary (MVP)

Karachi household shoppers who buy branded packaged goods online or check prices before a store run.

Why Karachi first: it is the only city where all six MVP retailers overlap.

| Retailer | Karachi | Other notes |
| --- | --- | --- |
| Springs | Yes (HQ + stores) | Ships nationwide |
| Metro | Yes | Also LHR, ISB, FSD, MUL |
| Naheed | Yes (HQ) | Some SKUs Karachi-only |
| Imtiaz | Yes | 33 stores / 14 cities |
| SPAR | Yes only | 4 Karachi stores |
| Carrefour | Yes | Also LHR, ISB, FSD |

### Secondary (later)

Lahore and Islamabad Metro/Carrefour/Imtiaz shoppers. Shopping-list users. Price-alert users.

### Explicit non-goals for v1

- Kiryana / informal market prices
- Fresh produce by the kilo (high variance, weak barcodes)
- In-store shelf prices that are not on the retailer’s website

---

## 4. MVP (Version 1)

### User-facing

1. Search
2. Autocomplete
3. Exact variant matching (size + pack count)
4. Side-by-side comparison
5. Sort: cheapest, most expensive, store, availability
6. Product image (retailer URL, not copied files)
7. Size / weight
8. Price in PKR
9. Last-updated timestamp + freshness colour
10. Buy / view on store
11. Filter by store
12. Cheapest in-stock highlight
13. Price per canonical unit (Rs/kg or Rs/L)
14. Filter in-stock / out-of-stock

### Not in MVP

- User accounts, alerts, shopping lists
- Delivery-fee totals
- Voice search
- AI-only matching without a confidence gate
- Admin UI beyond a thin retailer/job status page
- Elasticsearch / OpenSearch
- All of Pakistan’s retailers

### Success test for launch

A Karachi user can search a packaged grocery item, see at least two retailers with **the same variant**, and trust the cheapest badge because every row has a timestamp, source, and match confidence.

---

## 5. Categories (MVP)

Start with packaged, barcode-friendly goods:

1. Laundry and household cleaning
2. Beverages
3. Personal care
4. Snacks and confectionery
5. Baby care
6. Dairy (UHT / packaged only)
7. Cooking oil and ghee
8. Staples (atta, rice, sugar, tea) — branded packs only

Defer: loose fruit/veg, butcher counter meat, pharmacy ethics, electronics.

Seed catalog size: **200–500 canonical variants**, not 50,000. Coverage grows after matching is proven.

---

## 6. Retailer research (this is the hard Phase 1 output)

No retailer publishes a documented public Pakistan grocery API except Springs’ Shopify catalog JSON / UCP.

### 6.1 Springs — **pilot**

| Field | Finding |
| --- | --- |
| Platform | Shopify |
| Data | `GET /products.json`, `/{handle}.json`, collection JSON |
| Barcodes | SKU is often EAN/UPC (example: `8801619048481`) |
| robots.txt | Product HTML allowed; cart/admin disallowed |
| Agent docs | https://springs.com.pk/agents.md explicitly documents read-only catalog access |
| Risk | **Low technical, medium legal** — ToS say commercial reproduction of site content needs written permission |

**Collector rule:** HTTP JSON only. No Playwright. Store name, price, availability, URL, barcode, image URL. Do not republish long descriptions.

### 6.2 Metro

| Field | Finding |
| --- | --- |
| Platform | Next.js (`metro-online.pk`) |
| robots.txt | `Allow: /`, disallow `/loyalty` |
| Cities | Karachi, Lahore, Islamabad, Faisalabad, Multan |
| Price semantics | **Guide prices.** Billed price is in-store pick time |
| Risk | Medium |

**Product implication:** Metro rows must say prices are last-checked website prices, not a checkout guarantee.

**Collector rule:** Use the public storefront only. Do **not** call reported admin hosts (`admin.metro-online.pk` appears in third-party writeups). That is an unauthorized-access risk under PECA.

### 6.3 Naheed

| Field | Finding |
| --- | --- |
| Platform | Magento |
| robots.txt | Disallows `/catalogsearch/`, `/catalog/product/view/`, `/ajax/` |
| Sitemap | `https://www.naheed.pk/pub/media/sitemap.xml` |
| Product pages | Server-rendered SEO URLs work (price + stock visible) |
| Affiliate | Public program at `/affiliate/account/welcome` |
| Risk | Medium |

**Collector rule:** Follow sitemap product URLs. Do not hit disallowed search/ajax paths. Apply for affiliate + ask for a feed.

### 6.4 Imtiaz

| Field | Finding |
| --- | --- |
| Storefront | `shop.imtiaz.com.pk` SPA (“Loading…”) |
| robots.txt | 404 at research time |
| Scale | 52,000+ products, 33 stores, 14 cities |
| Delivery | Selective areas |
| Risk | High — JS, location, no public API |

Partnership or careful browser collection later. Not first.

### 6.5 SPAR

| Field | Finding |
| --- | --- |
| Platform | Blink (`store.spar.pk`) |
| robots.txt | **`Disallow: /api/*`** |
| Geography | Karachi only (4 stores) |
| Risk | High if we touch `/api`; medium if HTML-only after ToS review |

**Collector rule:** Never use `/api/*`. Prefer a Blink/SPAR partnership.

### 6.6 Carrefour

| Field | Finding |
| --- | --- |
| Platform | Majid Al Futtaim (`carrefour.pk/mafpak`) |
| robots.txt | HTTP 500 at research time |
| Pricing | Store-location specific |
| Risk | High (JS, likely WAF, no public PK API) |

Playwright only after legal review. Last of the six.

### Integration order

```text
Springs  →  Metro (public storefront)  →  Naheed (sitemap HTML)
        →  SPAR HTML or partnership
        →  Imtiaz
        →  Carrefour
```

---

## 7. Legal and technical constraints

This is not legal advice. Pakistani counsel should review before public launch.

### Allowed posture

- Read publicly visible product name, price, availability, URL
- Respect `robots.txt`
- Rate-limit; identify PriceWise with a contact User-Agent
- Prefer official JSON / feeds / affiliates
- Store **facts** (price, barcode, size) with a timestamp
- Link out; do not clone storefronts

### Forbidden posture

- Bypass WAF, CAPTCHA, logins, or signed APIs
- Hit SPAR `/api/*` or any admin host
- Harvest customer PII
- Copy copyrighted descriptions/images into our CDN without permission
- Show a price with no `collected_at`

### Pakistan

- **PECA 2016:** unauthorized access to information systems is the red line. Public pages ≠ logged-in or protected APIs.
- **Copyright:** prices and barcodes are facts; product photography and copy are not free to republish.
- **Springs ToS:** commercial use of site material needs written permission — outreach is a Phase 2 task.
- **Metro ToS:** website grocery prices are guides.

### Product copy we will use

> Prices are last checked at the time shown. Retailer sites can change. Metro website prices are guide prices.

---

## 8. Architecture (locked)

Six systems, as specified:

```text
User → Next.js  → FastAPI  → PostgreSQL
                      ├── Search (Postgres FTS)
                      ├── Product matching
                      └── Collectors (one module per retailer)
```

Redis and job queues come **after** Springs writes prices successfully.

### Collector contract

Every connector emits the same object:

```json
{
  "retailer": "springs",
  "name": "Surf Excel Matic",
  "brand": "Surf Excel",
  "pack_count": 1,
  "size_value": 1000,
  "size_unit": "g",
  "price": 510,
  "compare_at_price": null,
  "currency": "PKR",
  "availability": true,
  "url": "https://...",
  "image_url": "https://...",
  "barcode": "8901030...",
  "sku": "...",
  "city": "Karachi",
  "collected_at": "2026-09-09T14:00:00+05:00",
  "source": "shopify_products_json"
}
```

### Matching (not silent)

| Confidence | Action |
| --- | --- |
| Barcode exact | Auto-match (100%) |
| Brand + normalized name + size + pack | Auto if ≥ 95 |
| Fuzzy name only | Review 80–94; never auto |
| Below 80 | Unmatched — no comparison row |

AI may **suggest** a review item. It may not write a price join by itself.

### Unit rules

- Mass → grams internally (`1 kg` = `1000 g`, `2 × 500 g` = pack 2 × 500 g, not 1 kg)
- Volume → millilitres
- Multipacks never collapse into singles

### Freshness

| Age | UI |
| --- | --- |
| < 30 min | Recently checked |
| Same calendar day | Checked today |
| Older | May be outdated |

Scheduler tiers (after more than one retailer): popular 15 min, normal 1–3 h, rare 6–24 h.

### Validation

Flag for review if:

- New price < 40% of 14-day median for that retailer product
- Currency missing
- Size parse failed
- Duplicate URL/SKU
- Collector error rate spike

---

## 9. Open questions (do not block Phase 2)

1. Public brand name (PriceWise vs alternatives)
2. Counsel review of Springs commercial-use clause
3. Naheed affiliate approval
4. Whether Metro exposes a **public** JSON search we can use without admin hosts
5. City model: Karachi-only until retailer 3, or city column from day one (**decision: city column from day one, default Karachi**)

---

## 10. Phase order change

The original plan put UI before data. Phase 1 decision: **invert that.**

| Original | PriceWise sequence |
| --- | --- |
| Phase 2 UI/UX | **Phase 2: PostgreSQL + Springs collector + matching + API** |
| Phase 3 database | Folded into Phase 2 |
| Phase 4 backend | Folded into Phase 2 |
| Phase 5 first retailer | Springs is that retailer |
| Then | Next.js search + comparison UI |
| Then | Metro, Naheed, remaining stores, Redis, admin, launch |

---

## 11. Phase 2 entry criteria

Phase 1 is done. Phase 2 starts when we implement, in order:

1. Apply this schema to PostgreSQL
2. Seed the six-retailer registry
3. Springs collector → normalizer → matcher → `prices` table
4. `GET /api/search` and `GET /api/products/{id}/prices`
5. Only then: Next.js comparison UI against that API
