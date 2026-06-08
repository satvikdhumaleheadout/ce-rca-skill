# CVR-RCA Worked Examples

Two end-to-end walkthroughs showing how the investigation tree unfolds in
practice. These are not templates — they show how L0 orientation opens specific
L1 branches, how parallel queries within a level work, and how the tree map
and detail sections work together.

---

## Example 1 — Mix-dominant story

**Starting point:** `summary.json` loaded. CVR dropped for a CE.

---

### Investigation transcript

```markdown
# Investigation Transcript — CE [id] · City Sightseeing Tours
Pre: 2026-03-01–2026-03-30 | Post: 2026-03-31–2026-04-29

## Tree map
L0: mix_dominant (58% ΔCVR) · gradual erosion · structural −2.3pp
├─ L1a: MB URL volume loss          →  CONFIRMED (2 URLs down 40%, 8,400 pre-users)
│   └─ L2a: Campaign traffic source →  CONFIRMED (Google Ads referrer −5,400)
│       └─ LEAF: Google Ads campaign stopped serving 2 MB collection pages
└─ L1b: HO channel split            →  RULED OUT (HO volume flat)

---

## L0 — Orient
**mix_dominance:** is_dominant = TRUE. MB share grew from 43% to 52% post.
  Mix effect explains 58% of total ΔCVR. No individual funnel step exceeds 2pp.
**shapley:** LP2S −0.8pp · S2C −1.1pp · C2O −0.4pp — no dominant step.
  All steps small; mix_dominance flags this as a routing story.
**trend_context:** Gradual erosion over 6 weeks. pre_period_healthy = true.
  structural_delta_cvr = −2.3pp (LY showed −0.1pp at same calendar position).

## L1 — Traffic composition shift
### MB URL volume · HO channel split — parallel

**MB URL volume**
Query: COUNT(DISTINCT user_id) by page_url WHERE is_microbrand_page = TRUE,
  pre vs post, top 20 URLs by total volume.
Result: Two collection-page URLs dropped 40% in the post period
  (tickets-amsterdam.com/tours, tickets-amsterdam.com/day-trips).
  All other MB URLs held within ±5%. Combined pre volume on those two: 8,400 users.
→ CONFIRMED — opens L2a: what drove the volume loss on those two URLs?
  Closes: device/language/page_type hypotheses (routing story, funnel steps fine).

**HO channel split**
Query: COUNT(DISTINCT user_id) by channel_name, pre vs post, HO only.
Result: HO volume flat. No channel shift within HO.
→ RULED OUT — HO is not driving the mix shift. Issue is MB-side volume loss.

## L2 — Source of MB URL volume loss
### Campaign traffic source — targeted follow-up

**Google Ads referrer on affected URLs**
Query: COUNT(DISTINCT user_id) by previous_page_url WHERE page_url IN
  (tickets-amsterdam.com/tours, /day-trips), pre vs post.
Result: Google Ads referrer: 6,200 pre → 800 post (−5,400). Organic stable.
→ CONFIRMED — LEAF reached. Campaign stopped; paid traffic removed from MB.

## Root cause confirmed
A Google Ads campaign driving 6,200 users per period to two MB collection pages
(tickets-amsterdam.com/tours, /day-trips) stopped at the start of the post
period. MB's remaining sessions shifted to predominantly organic/SEO (lower
intent), lifting MB's CE share from 43% to 52%. Neither MB nor HO per-segment
CVR changed — the entire ΔCVR is a traffic composition artefact. DRI: Marketing.
```

---

### What the report covers

CVR change card, mix table with routing finding, URL traffic comparison for the
two affected pages. No Shapley bar (misleading when steps didn't break), no
dimension cuts, no experience breakdown. One action card: Marketing to confirm
whether the campaign pause was intentional.

---

## Example 2 — S2C concentrated locus, sudden break

**Starting point:** `summary.json` loaded. CVR dropped for a CE.

---

### Investigation transcript

```markdown
# Investigation Transcript — CE [id] · Paris River Cruises
Pre: 2026-03-15–2026-04-13 | Post: 2026-04-14–2026-05-13

## Tree map
L0: S2C (83% Δ) · sharp break Apr 14 · structural −4.1pp
├─ L1a: Experience-level S2C + inventory     →  CONFIRMED (TGID 8821: −15pp; daily time-series confirms 8–30d depleted Apr 14)
│   └─ L2a: Lead time distribution for 8821  →  CONFIRMED (8+ day bookings down 75–83%)
│       └─ LEAF: Supply partner closed 8821 inventory beyond ~7 days on Apr 14
└─ L1b: MB vs HO S2C split                  →  CONFIRMED (HO carries drop; narrows locus)

---

## L0 — Orient
**mix_dominance:** is_dominant = FALSE. MB/HO 38%/62% → 36%/64% post.
  Mix effect explains 9% of ΔCVR. Not a routing story.
**shapley:** LP2S −0.4pp · S2C −3.8pp · C2O −0.3pp — S2C carries 83% of ΔCVR.
  Primary step: S2C.
**trend_context:** Sharp break. S2C stable through pre, drops on Apr 14, stays low.
  pre_period_healthy = true. structural_delta_cvr = −4.1pp
  (LY showed +0.3pp at same calendar position — fully structural).

## L1 — S2C driver identification
### Experience-level S2C + availability · MB vs HO S2C split — parallel

**Experience-level S2C breakdown**
Query: COUNT(DISTINCT user_id), S2C rate by experience_id pre vs post.
Result:
  TGID 8821 (Seine Dinner Cruise): S2C 24% → 9%.
    1,840 select users post. Rate −15pp, checkouts lost ≈276.
  TGID 8834 (Seine Sightseeing 1hr): S2C 19% → 16%. Noise level.
  All other TGIDs: <5pp rate change.
→ CONFIRMED — TGID 8821 is the locus. Run inventory_availability TID summary table.
  Closes: broad platform/UX hypothesis (would show uniform drop, not one TGID).

**Inventory TID snapshot for TGID 8821 (current-state orientation)**
Query: TID snapshot — MAX(extracted_date) = today. Path B — pre within 30d window.
Result (today's ticket counts by lead-time bucket):
  TID 30112 (Dinner Cruise 7pm): tickets_0_2d 22, tickets_3_7d 14,
    tickets_8_13d 0, tickets_14_30d 0. Limited capacity.
  TID 30113 (Dinner Cruise 9pm): tickets_0_2d 18, tickets_3_7d 9,
    tickets_8_13d 0, tickets_14_30d 0. Limited capacity.
→ SCOPING — 8–13d and 14–30d buckets zero today for both TIDs. Near-term (0–7d)
  healthy. Scopes the daily time-series to the 8–30d buckets. Supply verdict below.

**Inventory daily time-series for TGID 8821 (primary supply evidence)**
Query: tickets by extracted_date × bucket, TIDs 30112 + 30113, Path B.
  Pre (Mar 15 – Apr 13) and post (Apr 14 – May 13), all four buckets.
Result:
  tickets_8_13d: Pre stable at 380–410 tickets/day. Post Apr 14+: 0 throughout.
  tickets_14_30d: Pre stable at 600–640 tickets/day. Post Apr 14+: 0 throughout.
  tickets_0_2d and tickets_3_7d: Flat throughout pre and post (~22–25 and 14–18).
→ CONFIRMED (supply) — Both 8–30d buckets healthy throughout pre, collapsed to zero
  on Apr 14 and stayed zero through the full post period. Onset matches the S2C break
  exactly. Supply partner closed TGID 8821 inventory beyond ~7 days on Apr 14.
  Opens L2a: check lead-time distribution — do checkout bookings mirror the supply window?

**MB vs HO S2C split**
Query: S2C rate by is_microbrand_page, pre vs post.
Result: HO S2C 28% → 14%. MB S2C 18% → 16%.
→ CONFIRMED — HO carries the drop. Narrows locus: HO users on 8821 select page.
  Does not change TGID finding — reinforces it.

## L2 — Behavioral corroboration for TGID 8821
### Lead time distribution

**Lead time buckets for TGID 8821 checkouts**
Query: COUNT(DISTINCT user_id) by lead_time_days bucket (0–7, 8–14, 15–21, 22+)
  WHERE experience_id = '8821' AND has_checkout_started = TRUE, pre vs post.
Result:
  0–7 days:  210 → 198 (−6%). Near-term bookings stable.
  8–14 days: 380 →  94 (−75%).
  15+ days:  510 →  88 (−83%).
→ CONFIRMED — LEAF reached. Checkout behavior mirrors the supply window: 8+ day
  bookings down 75–83% from Apr 14, matching the bucket collapse confirmed by the
  daily time-series.

## Root cause confirmed
On Apr 14, the supply partner for TGID 8821 (Seine Dinner Cruise) closed inventory
for all dates beyond ~7 days. Daily time-series confirms: tickets_8_13d and
tickets_14_30d were stable at 380–640/day throughout pre, collapsed to zero on Apr 14,
and stayed zero through the full post period — while near-term (0–7d) buckets held
flat. HO users with planned trip dates reach the select page and find no available
dates, driving S2C from 24% to 9% on 1,840 users — a loss of ~276 checkouts and 83%
of the ΔCVR. Lead time distribution confirms the behavior side: 8+ day bookings down
75–83%. Session recordings: users consistently see an empty date picker beyond the
current week on the 8821 page.
```

---

### Session recordings

Pulled `Get-User-Replays-Data` for CE id, TGID 8821, HO, post period after the
L2 leaf was confirmed. Users consistently encountered an empty date picker beyond
7 days. Finding upgraded from "consistent with" to "directly observed."

---

### What the report covers

CVR verdict (availability closure for TGID 8821), mix ruled out in one line,
Shapley bar, S2C daily trend (break on Apr 14), experience-level S2C table
(TGID 8821 highlighted), TID snapshot table (current-state, 8–30d near-zero as
scoping signal), inventory daily time-series charts (4 line charts — pre vs post,
sharp Apr 14 break in 8–30d buckets is the primary supply verdict), lead time
distribution chart (pre vs post), session recordings table. Action cards:
Supply/Ops (reopen 8821 inventory), Growth/BDM (alert affected users).

Sections not present: LP2S deep-dive, C2O section (each <10% of ΔCVR).

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c001 | 2026-04-27 | Created — moved from SKILL.md as part of process/domain separation |
| c002 | 2026-04-27 | Rewritten to show investigation tree traversal with parallel query batches |
| c003 | 2026-04-27 | Added tree map block to both transcripts — shows full branch structure with CONFIRMED/RULED OUT/LEAF outcomes before detail sections |
| c004 | 2026-05-06 | Updated Paris river cruise example to match new inventory architecture: (1) Experience-level S2C step no longer pulls `count_days_available_30d` from `product_rankings_features`; TGID 8821 is confirmed purely from the S2C rate drop. (2) Added TID summary table result for TGID 8821 showing per-TID ticket depletion by bucket (tickets_8_13d and tickets_14_30d → 0 for all TIDs). (3) Root cause summary updated: replaced `count_days_available_30d: 38 → 11` with TID summary table finding. |
| c005 | 2026-05-07 | Inventory investigation sequence corrected to snapshot-vs-time-series architecture: (1) Tree map L1a label updated — "avail 38→11d" replaced with "daily time-series confirms 8–30d depleted Apr 14". (2) TID snapshot block rewritten: removed "post snapshot vs pre snapshot" arrow notation (e.g., 180→0); now shows today's single-state ticket counts; verdict changed from CONFIRMED to SCOPING SIGNAL. (3) Daily time-series block added as separate step — shows pre-period stability, Apr 14 collapse to zero in both 8–30d buckets, and flat near-term throughout; this block is now the supply verdict source. (4) L2 header changed from "Availability mechanism" to "Behavioral corroboration"; outcome updated to state that checkout lead-time behavior mirrors the supply window. (5) Root cause paragraph updated: supply confirmation attributed to daily time-series (pre healthy → collapsed Apr 14) not TID snapshot. (6) "What the report covers" updated to include both TID snapshot (scoping) and inventory daily time-series charts (primary supply verdict). |
