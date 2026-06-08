# Changelog

## 6.3.0 (2026-06-08)

### Changed
- **Decision transcript is now a decision *tree*.** Step 6's `transcript_perf_audit.md` was a flat
  list of per-section verdicts; it now mirrors CVR-RCA's two-layer transcript — a **fenced
  ` ```text ` tree-map** (root verdict → one branch per audit lens: traffic quality, campaigns +
  portfolio, coverage + matchmaking, funnel, search intelligence — each CONFIRMED / RULED OUT + the
  call, `LEAF` = headline finding) plus short **detail sections** below. The tree is fenced so its
  alignment survives markdown rendering in the CE-RCA umbrella's Transcript tab (which now renders
  transcripts as markdown). No engine change — still authored by the analyst step. Companion: ce-rca
  v1.9.0.

## 6.2.0 (2026-06-08)

### Added
- **Decision transcript (Step 6).** The audit now writes a lightweight, structured decision log to
  `transcript_perf_audit.md` in the run directory — CE + windows resolved, mode + data pulled,
  one-line verdict per section (traffic quality, campaign/portfolio status, coverage + matchmaking,
  funnel, search intelligence), the headline finding, and what was skipped/ruled out. Conclusions
  and decisions only, not a re-run of the report's tables — it exposes the *reasoning* behind the
  audit. Under the CE-RCA umbrella orchestrator the file is collected verbatim into the composite
  report's **Transcript** tab (the orchestrator globs `transcript_<skill>.md`); standalone runs drop
  it next to the report. No engine change — the transcript is authored by the analyst step, model-side.

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
