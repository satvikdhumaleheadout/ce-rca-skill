# Changelog

## 6.2.0 (2026-06-15)

Sync from `~/analytics` — Phase 3 coverage gate, diagnosis-layer additions, PMax fixes, and an output/language overhaul.

### Features
- **Coverage gate (Phase 3)** — new `engine/signals.py`: enumerates material movers (channels/cohorts >10% of |rev Δ|, headline metrics past threshold, Shapley drivers >15%, TGID |Δ share|>5pp), tags L12M trajectory, and is closed in a backend §9 comment (visible §9 = ranked Red Flags). EVAL hard-gates that every signal is disposed.
- **Paid Value Shapley** — `shapley_multiplicative` (exact Clicks × CVR × Avg CM1 decomposition) consolidated into one §4 table (per-window inputs + MoM/YoY contribution + share).
- **Campaign × Product** join (`fetch_campaign_product_mix`) — which campaign sells which product at what margin (TR / CM1/Ord); narrative in report, full matrix in Sheet Tab 7.
- **Ad Group Audit** (`fetch_ad_group_audit`) — per-ad-group performance + bid-headroom opportunity (Scale / Leak vs tROAS target), with MoM Δ inlined into Spend/ROI; full set + MoM columns in Sheet Tab 8.
- **Plain-language narrative rule** — concrete cause→effect prose across every section (modeled on the cvr-rca exec summary).
- **Driver-ordering caveat** — Shapley is arithmetic, not causal: trace clicks back through the §7b TR chain when TR/CR moved >5%.

### Bug Fixes
- **PMax CM1 from `fct_orders`** (headline paths + A2 monthly appendix) — `sum_conversion_value × revenue_percentage` understated PMax CM1 ~4.3× post-Sep-2025; sourcing value from fct_orders corrects paid ROI (Eiffel ~123% → ~142%, near target).
- Campaign × product Channel made deterministic (GROUP BY channel, was non-deterministic ANY_VALUE).

## 6.1.0 (2026-05-21)

Initial standalone release. Extracted from `~/analytics` monorepo.

### Features
- 10-section report structure with conditional depth (SHORT/STANDARD/FULL)
- 20 BigQuery fetch functions covering CE health, channel attribution, campaign cohorts, budget/bidding, geo coverage, landing pages, ad group coverage, market benchmarks
- PMax merged into Table 2 (ads_campaign_stats + google_ads_pmax_asset_stats)
- Sep 2025 boundary handling for CM1/CVR (offline vs calculated)
- Portfolio campaign awareness (Individual vs Portfolio type detection)
- 12 diagnostic hypothesis trees (DIAGNOSTICS.md)
- 7-theme quality evaluator with pre-ship gates (EVAL.md)
- Dual-mode operation: full engine or SQL-only reference
- Standalone SQL reference for running without Python engine

### Architecture
- Zero Google Ads MCP dependency (all data from BQ)
- Search terms via CSV upload
- Ahrefs + Slack MCP optional for enrichment
- Python 3.9 compatible, single dependency (google-cloud-bigquery)

### Bug Fixes (from monorepo development)
- PMax ROI waterfall: 158→154→151 (was non-monotonic without PMax merge)
- Sep 2025 LY CM1 fix in both Table 2 (Python-level) and Table 3 (SQL-level)
- AOV: uses order_value/orders (was revenue/orders)
- Landing page CPC: divided by 1M (campaign_page_stats cost is in micros)
- Ad group table: uses google_ads_ad_group_stats (keyword_device_stats stale post-consolidation)
