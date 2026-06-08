# CVR-RCA Hypothesis Reference

## How to use this file

This is the central branch reference for the entire investigation. It operates at two levels:

**Level 1 — L0 routing map and first-pass branch sets** (sections immediately below): these tell you *which branches to open* at L1 and L2. Read this before forming any hypothesis. The L0 routing map maps each signal combination to a default branch set. The first-pass branch sets tell you which dimension cuts to run first for each primary funnel driver.

**Level 2 — Historical patterns** (Pattern 1–10 at the bottom): these provide *specific mechanism hypotheses* once a first-pass branch confirms a direction. Use them to decide *why* something may have happened in a confirmed dimension — the "why" behind a confirmed signal.

Use Level 1 to decide where to look first. Use Level 2 to decide why it might have happened there.

**These patterns are starting points, not a menu.** Form your own hypotheses from what the data actually shows. If `summary.json` points to a mechanism not listed here, follow it — the data is always the authority. A good hypothesis names a specific mechanism, a segment it would affect, and a date or pattern you would expect to see if it were true — regardless of whether it appears in this file.

---

## L0 signal → first branches to open

The three L0 signals (mix_dominance, shapley, trend_context) each open a
specific set of L1 branches. Use this table as the default starting set —
then adapt based on what the data actually shows.

The L1 cascade always runs first and determines the path. Shapley and trend
signals from L0 apply only once the cascade confirms a conversion story.

| Signal | Value / pattern | What it opens |
|--------|----------------|---------------|
| **Cascade: mix exit at Level 1** | MB/HO share shifted | Why did HO traffic fall or MB grow? Campaign paused, budget cut, routing error? (Pattern 7) |
| **Cascade: mix exit at Level 2** | Paid/organic share shifted | Why did paid spend fall or organic grow? Campaign pause, SIS cap, budget reallocation? (Patterns 1, 7) |
| **Cascade: mix exit at Level 3** | Channel share shifted within paid | Why did budget or impression share move between channels? Bid strategy, budget reallocation, Performance Max expansion? |
| **Cascade: conversion at all levels → Shapley: LP2S dominates** | LP2S is the funnel story | First-pass branches for LP2S (see below) |
| **Cascade: conversion at all levels → Shapley: S2C dominates** | S2C is the funnel story | First-pass branches for S2C (see below) |
| **Cascade: conversion at all levels → Shapley: C2O dominates** | C2O is the funnel story | First-pass branches for C2O (see below) |
| **Trend: sharp break on date X** | Event on that date | Anchor all L2 branches to that date — which dimension shows the largest change starting that day? |
| **Trend: gradual erosion** | Compounding trend | Supply trend (availability over time), pricing trend, traffic quality trend |
| **Trend: seasonal** (`structural_delta_cvr` small) | Calibrate depth | Use `structural_delta_cvr` as the magnitude to explain — not `current_delta_cvr` |

Shapley and trend signals combine. If S2C dominates AND trend shows a sharp
break, L2 branches are "experience-level S2C anchored to break date" +
"availability proxy on that date." Trend context sharpens every branch — it
does not replace the cascade.

The table is the default starting set. It does not replace reading the actual
numbers — if a signal points in an unexpected direction, follow it.

---

## First-pass branch sets by primary driver

**These are starting points, not a complete list.** They cover the most common
angles for each funnel step. After running any batch of queries, ask yourself:
*does this result suggest a hypothesis that isn't on this list?* If yes, add it.
The cuts below tell you where to look first — they don't tell you what you'll
find or what to hypothesize next. What you find determines that.

The investigation is complete when you reach a leaf (a specific mechanism at a
specific segment, experience, URL, or date). It is not complete when the list
below is exhausted. If you've run all the cuts and have no leaf, that is a
signal to look more carefully at what the data already showed — a surprising
number, an unexplained gap, a dimension that partially concentrated — and form
a new hypothesis from it.

Common reasons the list runs out before a leaf is found:
- The real locus is a cross-cut (e.g., French × iOS) not tested individually
- The mechanism is at a finer grain (specific URL, specific experience × date)
  not yet drilled into
- The cause is outside the funnel table entirely (pricing, availability, a
  campaign event) and needs a separate query against a different table

### Mix — first-pass branches (routing exit investigation)

A routing exit means traffic composition shifted at one of three levels. The
investigation after the exit is different at each level — the question is always
the same ("why did the mix change?") but the cut and the stakeholder differ.

**Level 1 exit — HO vs MB share shifted**

Tier 1 — Time the shift: query HO vs MB session volumes by week over the 90-day
window. Identify the exact week HO share started declining (or MB share growing).
That week is the anchor for everything below.

Tier 2 — Source cut: within HO sessions, break by `language` or `country_code`
pre vs post. A single language or market dropping points to a geo-specific
campaign or partnership change. A broad drop across all HO markets points to a
global organic or referral change.

Tier 3 — URL impact: query `COUNT(DISTINCT user_id)` by `page_url` for HO
sessions pre vs post. Which collection or experience pages lost HO traffic?
Those are the specific pages Marketing needs to look at.

---

**Level 2 exit — Paid vs Organic share shifted within fixed brand**

Tier 1 — Time the shift: query Paid vs Organic session volumes by week. When
did paid share drop? A sharp drop on a specific date suggests a campaign pause
or budget exhaustion. A gradual drop suggests budget reallocation or bid
strategy drift.

Tier 2 — Channel cut: within Paid sessions, break by `channel` (Google Ads,
Meta, etc.) pre vs post. Which paid channel declined? This narrows the
investigation to a specific campaign team or channel budget.

Tier 3 — URL impact: query `COUNT(DISTINCT user_id)` by `page_url` for the
declining paid channel pre vs post. Which landing pages did the campaign stop
serving traffic to?

---

**Level 3 exit — Channel share shifted within Paid**

Tier 1 — Time the shift: query session volumes by channel within Paid, by week.
Which channel gained and which lost? If Google Search lost and Performance Max
gained, that is a bid strategy shift. If Meta dropped sharply, that is a budget
or creative rotation event.

Tier 2 — URL impact: query `COUNT(DISTINCT user_id)` by `page_url` for the
losing channel pre vs post. Which specific listing or collection pages were that
channel's primary landing pages? Those are what dropped.

---

**Perf-audit background context (Level 2 and Level 3 exits).** When the cascade exits via mix at Level 2 (Paid/Organic) or Level 3 (channel within Paid), the perf-audit sub-agent runs in parallel with the tiered investigation below — spawned right after the exit level is declared (see `SKILL.md → "Perf-audit context — fire and forget"`). The tiers (timing → sub-segment cut → URL impact) still run as the primary path. At Step 2b the perf-audit summary often names the campaign-level *why* behind the mix shift: a campaign paused on a specific date, SIS lost to rank vs budget, tROAS self-suppression tightening traffic volume, or budget exhaustion. Pattern B in check #10 routes those findings into Layer 1 narrative and the Section 3 External Signals block without a second query — the campaign event explains itself once timed and named.

For all three levels: the finding is complete when you can name the shift week,
the specific sub-segment that drove it, and the affected page URLs. Do not go
further into funnel analysis — the conversion rates within the affected segment
were flat (that is why the cascade exited). Marketing owns the routing story.

### LP2S — first-pass branches

LP2S is about whether users landing on the listing page click through to the
select page.

**Run dimension cuts in parallel:**
- `page_url` × LP2S rate and volume — check both independently: (1) did traffic shift between URLs — some pages gaining volume, others losing? That is a routing story; traffic moved toward lower-converting pages. (2) did LP2S rate drop on specific URLs while others held flat? That points to something that changed on those pages (template, listed experiences, pricing). A uniform rate drop across all high-traffic URLs points to a CE-wide mechanism. Apply a majority-contributor filter — exclude long-tail URLs that represent a small share of CE LP traffic, as their rate estimates are high-variance.
- `device_type` × LP2S rate pre/post — mobile-concentrated drops point to a
  UI or performance change
- `language` × LP2S rate — a single language dropping points to geo-specific
  pricing or a localised UX issue
- `page_type` × LP2S rate — a drop in Collection but not Experience pages points
  to browse-level friction
- `experience_id` × LP2S rate — a drop in a few specific experiences points to
  listing quality, price, or availability visible on the listing
- `browsing_country` (Geo/Non-Geo) × LP2S rate — a Geo-only drop points to a
  local pricing, supply, or campaign issue; a drop concentrated in one or two
  Non-Geo countries points to an international traffic quality or UX gap. Use
  the dedicated query from `context.md → "Geo vs Non-Geo"` — it requires a
  CE country pre-step and top-5 CTE logic; do not use the canonical L2+ query
  for this cut.

**Paid fixed segment — perf-audit background context.** If the fixed segment is Paid, a perf-audit sub-agent is running in parallel (spawned at the end of the cascade — see `SKILL.md → "Perf-audit context — fire and forget"`). Do not consult it during the dimension-cut phase. Dimension findings must be reached independently so the perf-audit verdict corroborates or surprises a completed picture rather than steering branch selection. At Step 2b the verdict folds in via the four-pattern routing in check #10: traffic quality IMPROVED corroborates a page-driven leaf with high confidence; DEGRADED reframes the root cause to include a traffic-quality contributor alongside the page finding; campaign-level events (pause, tROAS suppression) explain the *why* behind the dimension findings without re-querying.

**If a dimension concentrates:** run the intersection (e.g., French × mobile), then drill to `page_url` within that segment to identify the actionable pages. If `page_url` itself concentrates at the first cut, the URL is the direct finding — identify what changed about those pages (template, listed experiences, traffic composition from that entry point). A finding is not complete until you can say "these specific URLs are where LP2S dropped, here are the user counts."

**If country concentrates:**
- Geo drop → cross-cut with `language` using the local language (e.g., Italian
  for CE in Italy). A Geo × local-language drop confirms a domestic audience
  issue. Then drill to `page_url` within that segment.
- Non-Geo country drop → cross-cut with `experience_id` for that country. If
  specific experiences show the drop, check whether those experiences have
  language-appropriate variants and available inventory for international
  booking windows.

**If no dimension concentrates (drop is CE-wide and flat across cuts):**
Run pricing analysis — `final_price_usd` from `product_rankings_features` pre vs post for top experiences. Did prices increase, and does the timing align with the LP2S drop? A CE-wide price uplift will depress LP2S broadly with no dimension cut showing concentration.

**If pricing is also flat:**
The drop is broad, no pricing explanation, no concentrated locus. Session recordings are the next tool — look for a UX pattern that affects all users equally (e.g., slow page load, broken image carousel, changed CTA placement). Note in the transcript that no quantitative locus was found; session recordings are the primary evidence. (Event-level analysis is a future addition for this tier.)

### S2C — first-pass branches

S2C is about whether users on the select/date-picker page proceed to checkout.

**If S2C is a secondary driver (primary driver is C2O or LP2S):** The question
is not "what caused the S2C drop?" but "is this an independent mechanism from
what we already found?" Run the fixed-segment aggregate for S2C first (one query
reading the S2C rate within the fixed segment). Two outcomes:
- **S2C flat or improved within the fixed segment** — the CE-level Shapley
  contribution originates outside the fixed segment. Close as RULED OUT and move
  on. No first-pass branches needed.
- **S2C declined within the fixed segment** — check whether the decline is
  directionally explained by the primary finding (same seasonal mechanism, same
  experience locus, same demand composition shift). If yes, close as CONFIRMED
  with a one-line explanation and note it shares the mechanism. Only open the
  first-pass branches below if S2C shows a meaningful decline within the fixed
  segment that is *not* directionally explained by the primary finding — that is
  the signal an independent mechanism exists.

**If S2C is the primary driver, or if it has an independent mechanism not
explained by the primary finding, run dimension cuts in parallel:**
- `language` × S2C rate pre/post — a drop in one language points to a localised
  select-page issue (broken date-picker for that locale, geo-specific pricing
  shock at variant selection)
- `device_type` × S2C rate pre/post — a mobile-concentrated drop points to a
  select-page UX or rendering issue specific to small screens
- `experience_id` × S2C rate pre/post — a drop in specific experiences points
  to a supply or pricing issue for those products. When you find this, follow
  the inventory investigation sequence below.
- `browsing_country` (Geo/Non-Geo) × S2C rate — a Geo-only S2C drop points to
  local supply scarcity or a pricing shock visible at the variant-selection step
  for domestic users; a Non-Geo country drop points to language/UX friction at
  the date-picker or international inventory gaps. Use the dedicated query from
  `context.md → "Geo vs Non-Geo"` for this cut.

**If language or device concentrates:** drill to the intersection (language × device if both signal), then to `page_url` within that segment. The URL is the actionable endpoint — give the stakeholder the specific select-page URLs and user counts.

**If country concentrates:**
- Geo drop → cross-cut with `language` (local language) and `experience_id`.
  A Geo + local-language + specific-experience triple confirms domestic supply
  or pricing as the mechanism — lead-time bucket query is the next step.
- Non-Geo country drop → cross-cut with `experience_id` for that country to
  check whether specific products lack inventory for international booking
  windows. Also check `language` — international visitors may be browsing in
  English while the experience has limited English-language variants.

**If experience concentrates — inventory investigation sequence:**

> **Transcript labels — do not carry into the HTML report.** All labels in this section (`lost_checkouts_delta`, single dominant TGID, multiple significant TGIDs, uniform drop, Path A/B/X) are investigation-internal. Translate to business language in the report: "three most-affected experiences" not "Case B candidate TGIDs"; "post-period data only — pre data unavailable" not "Path A"; "estimated checkout impact" not "lost_checkouts_delta". See report_structure.md → anti-patterns for the full list.

**1. Select which TGIDs to investigate.** From the experience × S2C results, compute `lost_checkouts_delta` for each TGID:
```
lost_checkouts_delta = users_select_post × (s2c_rate_pre − s2c_rate_post)
```
Sort descending. Investigate the TGIDs that explain the majority of the checkout loss — start with the top contributor. If two or three TGIDs are each meaningfully contributing, run the inventory queries for each. If the drop is spread uniformly with no TGID standing out, skip to the *broad-drop path* at the bottom of this section.

One TGID maps to multiple TIDs (time slots, language variants, ticket types). The queries in `context.md → inventory analysis` always operate at TID level within a TGID.

**2. Check data availability** (see `context.md → inventory availability → data availability`). If both the pre and post periods are outside the 30-day window, skip the inventory queries and state the data limitation. However, if `post_end` is within roughly 30 days of today, the post period may still be queryable — in that case, run Path A for the post period only. A near-zero post-period median on the losing experience is directional supply evidence even without pre-period data. Note clearly in the transcript that only one period was available and treat the finding as supporting context, not a confirmed cause.

**3. For a gradual S2C decline** (drift over multiple weeks): the canonical query is always `inventory_availability` (TID summary table + daily time-series) — Path B if the pre window is within the 30-day retention, Path A otherwise. See `context.md → inventory_availability` for the canonical-source rule on supply claims. `days_to_first_available_date` from `product_rankings_features` may be added as a corroborating directional signal *only* when Path A is in effect AND the diagnosis specifically needs a pre→post trend reading the canonical query cannot provide. Even then, it appears in the report as a footnote or one-line caption, never as the primary supply evidence.

**4. Run the median query** (Path A or Path B from `context.md → inventory analysis`). Always query through the `experience_id → dim_experience_management WHERE variant_status = 'Active'` bridge — never hardcode a `tour_id` directly, and never use `dim_tours` (it has no `variant_status` column and returns Disabled TIDs, which contaminates both TID selection and ticket counts). The bridge returns all Active TIDs for the TGID automatically; selecting a single `tour_id` without checking the full Active TID list risks missing the actual constrained variant. Use the results to:
- Flag unlimited-capacity TIDs (`is_fully_unlimited_capacity = TRUE`) — exclude from supply analysis
- Identify contributing TIDs: TIDs with near-zero post-period median (Path A) or a significant drop in post-median vs pre-median (Path B). These are the TIDs to include in the time-series charts.
- If one TID is the locus: scope the daily time-series to that TID. If multiple TIDs are depleted: scope to the TGID (all depleted TIDs aggregated). If mixed (some depleted, some healthy): scope to depleted TIDs only and note excluded healthy TIDs in the chart disclosure banner.

**5. Run the daily time-series query** (from `context.md → inventory analysis`), scoped to the contributing TIDs identified in step 4. This is the primary supply evidence — it shows whether inventory was depleted when the S2C drop happened, and confirms timing. Always run regardless of what the median table showed. Interpret using the timing guide in `context.md`.

**6. Confirm, partially flag, or rule out supply.** Read the trend shape and level of each bucket against its baseline (see `context.md → inventory analysis → Interpreting the time-series charts`). Three verdicts:

- **Supply is the mechanism**: a bucket shows sustained depression, an onset event that aligns with the S2C break date, or a gradual decline that tracks the S2C trend. Confirm with the `lead_time_days` distribution — users shifting toward longer lead times when that same window is depleted confirms supply is causal, not behavioural.
- **Supply partially contributed**: the time-series shows gradual depression across the post period, or episodic dips that are TGID-specific (not synchronized artifacts). Supply was not the primary root cause but suppressed S2C on specific days or weeks. Note this as a secondary finding in the report — do not dismiss it as "supply ruled out." Flag for the supply team with the affected bucket and date range.
- **Supply ruled out**: levels are flat and stable throughout the post period with no meaningful trend. State this explicitly; pivot to pricing or UX hypotheses.

**If no dimension concentrates (drop is broad):**
A CE-wide S2C drop with no language/device/experience concentration is unusual. Check two things: (1) was there a change in the checkout flow or variant selection UI? (2) did availability drop uniformly across all experiences?

To check (2) — **broad-drop inventory path**: pick the top 3 TGIDs by `users_select` volume from Q4 (by raw traffic, not by S2C drop) and run the TID snapshot and daily time-series queries for each. Two outcomes:
- **Same lead-time bucket depleted across all three TGIDs** → CE-wide supply constraint (platform-level cut-off period change, vendor pulling all inventory). Escalate to the supply team with the specific bucket and onset date.
- **Time-series shows tickets healthy throughout the post period across all three TGIDs** → supply is not the mechanism. Focus on checkout flow or variant selection UX changes that affected all experiences equally.

### C2O — first-pass branches

Check `c2o_sub` from `summary.json` first. C2O = C2A × A2O and they point to
completely different causes. Always decompose first — do not run C2O queries
before knowing which sub-metric moved.

**If C2A dropped** (users reached checkout but didn't submit payment):

Four hypotheses to run in parallel:
1. **Pax availability at checkout** — users selected a pax configuration (e.g.,
   3 adults + 2 children) but no pack style exists for that combination. They hit
   a "not available" state on the checkout page and abandon. Look at whether
   certain experience × pax combinations are unavailable in the post period. This
   is a supply/ops issue, not a UX issue — DRI is Ops/BDM.
2. **Price display friction** — total price (including booking fees, taxes,
   service charges) visible at checkout differs significantly from listing price.
   Check if any fee or pricing component changed between pre and post.
3. **Checkout UX change** — a form field change, CTA relabelling, coupon code
   breakage, or trust signal removal. Concentrate investigation on device ×
   C2A — mobile users are most sensitive to checkout form friction.
4. **Session recordings** — once any of the above narrows to a locus (device,
   language, or experience), pull recordings on the checkout page to confirm the
   pattern.

**Optional — if C2A drop is broad with no device/experience concentration:**
Run the Geo/Non-Geo cut (`context.md → "Geo vs Non-Geo"`). A checkout
abandonment rate that spikes only in specific countries can point to a
currency/pricing display issue or a payment method unavailability in that
market — distinct from a pax or UX problem.

**If A2O dropped** (users submitted payment but order failed):

Three hypotheses to run in parallel:
1. **Payment gateway failure** — elevated decline rate from a specific gateway
   or card network. Check if `payment_gateway` or `failure_reason` in
   `order_attempted_events_v2` shows a spike for a specific payment method.
2. **Fraud rule tightening** — a rule change or new fraud model version is
   blocking more legitimate transactions. `fraud_evaluation_result_origin` would
   show a change in classification rate.
3. **Live inventory failure** — the experience slot was available when the user
   reached checkout but sold out between checkout start and payment confirmation
   (another user completed a booking first). Check for a spike in
   `failure_reason` values indicating inventory unavailability at the moment of
   order attempt.

DRI for A2O: Payments team (gateway/fraud) or Engineering/Ops (live inventory
sync failures).

**If C2O improved via an experience routing shift** (one experience gained checkout dominance at the expense of another), one useful follow-up is to ask *why* the gaining experience drew more demand. Two quick checks using `product_rankings_features`:

- **Pricing signal**: Compare `final_price_usd` for the gaining and losing experiences pre vs post. If the gaining experience is materially cheaper, that's a demand signal worth noting. If pricing is comparable between the two, pricing is unlikely to be the mechanism — points toward supply, catalog presentation, or ranking position instead.
- **Availability signal**: Compare `days_to_first_available_date` for each experience post-period. If the gaining experience consistently has near-term slots and the losing experience has a long lead time (or none), that's consistent with a supply-driven shift — more bookable inventory driving more checkouts.

These checks are directional, not conclusive. If both experiences show similar pricing and availability, the shift is more likely driven by catalog or ranking changes that aren't visible in these tables — flag as a DATA GAP and note in the action card. Don't force a mechanism claim if the data doesn't support one.

---

## Improvement direction — first-pass branches

The decline-direction patterns above (LP2S / S2C / C2O sections, Mix routing exits) are the primary investigation patterns. **CVR-improvement RCAs use the same cascade and Shapley structure but with direction-sensitive branches** for the funnel-step deep-dive after the fixed segment is declared. Use this section after the cascade confirms a conversion-path story and the data-driven Shapley step is identified.

The investigation rigour is the same — find a leaf (specific mechanism × segment × timing) — but the candidate mechanisms differ. Catalogue change (Pattern 11 below) is often the most informative branch in an improvement RCA.

### LP2S improvement — first-pass branches

Run dimension cuts in parallel:
- `page_url` × LP2S rate and volume — a URL gaining traffic share with stable rates is a routing improvement (paid spend reallocated, new SEO ranking landed). A URL with rate improvement is a page-level lift (new top product, template change, image refresh).
- `experience_id` × LP2S rate — a top experience whose LP2S rose materially points to either a content/media refresh on that listing or a price reduction (cross-check with `final_price_usd` from `product_rankings_features`).
- `device_type` × LP2S rate — a uniform lift across devices is structural; a mobile-only lift points to a mobile UI improvement or page-performance gain.
- `language` × LP2S rate — a single language gaining points to a campaign creative refresh or a localisation improvement (translation completion, geo-specific content launched).
- `browsing_country` (Geo/Non-Geo) — a Geo-only LP2S lift points to domestic seasonal demand or a local campaign launch; a Non-Geo lift points to international traffic-quality improvement.

**If pricing improved:** Query `final_price_usd` pre vs post — a meaningful price reduction (≥5%) on a top-volume TGID is a direct LP2S lever. Pair with availability check.

### S2C improvement — first-pass branches

Run dimension cuts in parallel:
- `experience_id` × S2C rate — a top experience whose S2C rose materially is usually the story. Check: did availability expand for it? Did a new variant launch (Pattern 11)? Did its price drop?
- `language` × S2C rate — a localised audience newly proceeding suggests fixed translation, fixed local pricing, or completed locale-specific content.
- `device_type` × S2C rate — a mobile S2C lift is the strongest evidence of a select-page UI or performance improvement.

**If experience concentrates upward — inventory expansion check:** Query `inventory_availability` (Path A or Path B per retention) for the improving TGID — this is the canonical query whether the supply finding is direction-positive (expansion) or direction-negative (depletion). See `context.md → inventory_availability` for the canonical-source rule on supply claims. An *increase* in ticket counts across lead-time buckets, or a sustained high level on Path A, confirms supply expansion as the mechanism (SP loosened cut-off period, new release window, vendor added inventory). This is the symmetric counterpart of the supply-depletion check on declines.

### C2O improvement — first-pass branches

Check `c2o_sub` from `summary.json` first. C2O = C2A × A2O — both can lift independently and the mechanisms differ.

**If C2A improved** (more users proceeding from checkout to attempt):
1. **Pricing/fee transparency improvement** — fees moved earlier in the flow, mandatory add-ons removed, listing price aligned with checkout total. Check whether any fee structure change was deployed (cross-reference Slack at Step 2b, not L2+).
2. **Checkout UX improvement** — a form field removed, autofill restored, promo code field redesigned, trust signal added. Most sensitive on mobile.
3. **Pricing lever applied** — a last-minute discount, promo code, or fee reduction landed during the post window. Direct C2A lever on the affected TGID.
4. **Pax setup simplification** — pax type configuration cleaned up, custom fields reduced. DRI: Ops/Product.

**If A2O improved** (more attempted orders completing):
1. **Payment gateway stabilised** — gateway timeout/error rate fell after a fix; specific failure-code rate dropped.
2. **Fraud rule loosened** — a rule rollback or model update reduced false-positive blocks. Check fraud block rate by `fraud_evaluation_result_origin`.
3. **Live inventory sync improved** — fewer slot-sold-out failures at the order-attempt step.

**If C2O improved via catalogue mix shift** (one TGID gained checkout share at the expense of others, and the gaining TGID has higher native C2O):
1. **Pricing signal** — gaining TGID is cheaper than the displaced TGIDs.
2. **Availability signal** — gaining TGID has near-term inventory while displaced TGIDs don't.
3. **Catalogue change** — gaining TGID is new (Pattern 11). The mix shift may be entirely the new variant absorbing demand.

### Mix improvement — first-pass branches (routing tailwind)

If the cascade confirms a mix change (e.g., HO traffic share grew and HO is higher-CVR), the question is "why did the higher-CVR segment grow?" Direction-symmetric to the routing exit investigation above:

- Time the shift, source cut (paid channel, language, geo), URL impact. The finding is complete when you can name the gaining segment, the week the shift started, and the campaign/source that drove it.

The decline-direction Mix patterns (Pattern 7) describe why traffic shifted *toward* lower-CVR MB. For improvements, the mirror question is why traffic shifted *toward* higher-CVR HO or paid channels — typically: campaign launched/scaled up, SEO ranking landed, affiliate brought higher-intent volume, marketing budget reallocated *to* this CE.

---

## URL concentration — a cross-cutting check

URL concentration is a legitimate hypothesis regardless of which funnel step is primary — it shapes both the mechanism and the DRI. Run the URL breakdown query from `context.md` (not the canonical L2+ query — that query does not produce `pct_of_lp`). Apply a majority-contributor filter: only include URLs that account for a meaningful share of CE LP traffic on the fixed segment — long-tail URLs produce high-variance rate estimates and should be treated as directional at best.

A drop concentrated in a few high-traffic URLs points to something specific about those pages (a template change, a specific experience listed, the audience those URLs attract). A drop spread uniformly across all high-traffic URLs points to a CE-wide mechanism (availability, pricing, platform change). These two findings call for different root causes and different action owners.

For each primary driver type, the URL breakdown answers a different question:

- **Mix shift:** Did traffic volume shift between URLs — some gaining, others losing? A volume shift without a rate change is a routing story. Identify which channel or campaign drives the gaining URLs.

- **LP2S drop:** Did LP2S rate fall on specific URLs while others held? `page_url` is already a first-cut dimension in the LP2S branch — a concentrated URL rate drop points to something that changed on those pages; a uniform drop across all high-traffic URLs points to a CE-wide mechanism.

- **S2C drop:** Did S2C rate differ by landing URL? Note: `page_url` here is the session-entry URL (landing page), not the select-page URL. S2C differences by landing URL reflect user composition — users from that entry point have different purchase intent — not a select-page UX issue. A concentrated S2C drop by landing URL reinforces the experience or intent hypothesis from L2c; a uniform drop is more likely a supply or pricing signal.

- **C2O drop:** URL is a weak lens for C2O — the checkout flow is standardised and largely independent of the entry URL. If C2O is the primary driver, focus on checkout configuration and payment issues rather than URL concentration.

---

## Dimension cross-cut — when two cuts both concentrate

A cross-cut is not about adding more dimensions — it is about avoiding a double-counting error. When two independent dimension cuts for the same funnel metric both show concentration, they may be describing the same users, not two independent findings. Run the intersection before reporting both as separate root causes.

**Trigger rule:** When two dimension cuts for the same funnel metric both show concentrated movement (≥8pp absolute or ≥20% relative in the leading segment, **in either direction — a drop in a decline RCA or a rise in an improvement RCA**), run the cross-cut before closing either branch as a leaf. If the concentrations overlap substantially (one cell dominates), the cross-cut becomes the leaf — not the two individual cuts. If they are independent (multiple distinct cells show concentrated movement), both findings hold and can be reported separately.

**Threshold rationale:** 8pp absolute or 20% relative is roughly the point at which a dimension cut is large enough to explain the majority of a CE-level metric change. Below that threshold, the finding is directional — a cross-cut is useful but not required. The threshold and the cross-cut logic are identical regardless of direction; only the language around "drop" vs "rise" changes.

### Common cross-cuts by funnel step

Use the cross-cut query template in `context.md → "Cross-cut query template"` for any of these:

**A2O (order success rate):**
- `device_type × experience_id` — did one device type fail specifically on one experience, or did all devices fail on that experience equally?
- `channel_name × experience_id` — did payment failures concentrate in users from a specific channel arriving at a specific experience simultaneously?

**S2C (select-to-checkout rate):**
- `device_type × experience_id` — did mobile users specifically abandon one experience's date picker, or did all devices abandon it equally?
- `language × experience_id` — did a localised audience specifically not proceed past a particular experience's variant selection?

**LP2S (landing-to-select rate):**
- `device_type × page_url` — did mobile users specifically not engage on certain URLs, or was it all devices on those URLs?
- `language × page_url` — did a language-specific audience specifically drop on certain landing pages?

**C2A (checkout-to-attempt rate):**
- `device_type × experience_id` — did mobile users specifically not submit payment on a particular experience?

### Interpretation

- **Concentrations overlap (one cell dominates):** The two individual dimension findings describe the same users. Report the cross-cut cell as the leaf (e.g., "Android Mweb users on experience 36344"), not two separate findings. This is one root cause.
- **Concentrations are independent (multiple distinct cells show drops):** The two mechanisms are genuinely separate pools. Report both, and note they were confirmed as non-overlapping via the cross-cut.
- **One cell is too thin (< ~20 post-period users in the denominator):** Data is insufficient to confirm or deny overlap. Note the ambiguity in the report; do not assert independence.

---

## Slack signal classification — for Step 2b reconciliation

Use this table when reading `<run_dir>/slack_context.md` at Step 2b check #9 of the SKILL.md process. Every signal worth keeping classifies into one of four patterns; rejected signals get a one-line note in the transcript and never enter the report.

**Critical constraint:** Slack is consulted *only* at Step 2b — never during L0/L1/L2 investigation. Pattern classification is retrospective. The full process spec lives in `SKILL.md → Step 2b → check #9`; this section is the pattern-recognition reference.

| Pattern | What the signal looks like | Where it surfaces in the report | Action required |
|---|---|---|---|
| **A — Direct corroboration** | Slack thread names the same mechanism, TGID, date, or segment as a finding already in findings.md | Source column in Hypotheses Explored table. **On declines with a DRI-bound action:** elevate the verdict subtext citation from `(corroborated ↗)` to `(per Author · date ↗)`. | No new query. Add citation; if applicable, elevate per the decline-corroboration rule. |
| **B — Mechanism explanation** | Slack thread reveals *why* something happened (a deploy date, an assortment cap, a pricing lever, a content update, a TGID launch, an API migration) that explains a confirmed data finding | Layer 1 narrative weaving in the relevant callout question or verdict subtext, AND a row in the Section 3 External Signals block | No new query. Weave into narrative + add to External Signals table. |
| **C — Reframing context** | Slack thread introduces a metric or timeframe *outside* the report's primary comparison (YoY, vs plan, macro shift) AND would change how a stakeholder acts or prioritises | Layer 2 Important Context callout-item in Section 1 (apply the four decision-changing tests in `report_structure.md`), AND a row in the Section 3 External Signals block. **Mandatory:** name the timeframe in the same sentence when it differs from pre/post. | No new query. Add Important Context item + External Signals row + apply timeframe-citation rule. |
| **D — Testable gap** | Slack thread names a specific causal mechanism, TGID, date, or operational event the investigation did not address. Must pass three filters: (a) specific; (b) within window or causally upstream; (c) about this CE or its market | Result of the one query becomes a regular finding in Section 3, cited inline `(prompted by Author · date ↗)` | Run one query maximum. Update tree map to CONFIRMED / RULED OUT / DATA GAP. Update findings.md if the finding changes. |
| **Reject** | Vague ("things are slow"), symptom-only ("CVR is down"), or fails the gap filters | Transcript only — `"Slack signal '[summary]' — not pursued: [reason in 5 words]."` Does not enter the report. | None. |

**High-value gap categories for Pattern D** — these are the kinds of Slack signals worth pursuing as a Pattern D query, because they rarely surface in the funnel table directly but often explain residual unexplained C2A/C2O/LP2S movement:

- **MB assortment changes** — cap raised/lowered, TGIDs added/removed from MB visible set
- **Pricing levers** — last-minute discount applied, promo code introduced, fee structure change, base price adjustment for a TGID
- **Content/title updates** on top TGIDs (name change, highlights update, image refresh)
- **Product restructures** — TGID consolidation, variant split, taxonomy update
- **Supplier changes** — API migration (e.g., 1way2italy → Bokun), VID rate sheet update, vendor moved to manual FF mode, CR% intervention
- **Catalogue events** — TGID launched, TGID disabled, multi-DMC setup change

For each of these, a single query against the funnel/catalogue/inventory tables is usually sufficient to confirm or rule out the mechanism (Pattern D's one-query limit).

**Pattern selection is sequential when the signal could fit multiple:**
- If the signal corroborates an existing data finding (Pattern A applies), classify as A even if the signal also provides mechanism detail (which would be B). Saves a Layer-1 weave and keeps the data finding primary.
- If the signal both reframes and explains a mechanism, classify as C if the reframing changes priority/team; otherwise B.
- If you're tempted to classify a signal as multiple patterns, the signal probably needs to be split into two thread-references with separate handling.

---

## Historical patterns — mechanism detail by scenario

Use these once a first-pass branch confirms. They provide the specific mechanism hypotheses for each confirmed scenario — the "why" behind a confirmed dimension signal.

---

## Pattern 1: LP2S is the primary driver — sudden onset

A sharp drop in LP2S that began on a specific date means something *changed* that day. Work backwards from the date.

**Hypotheses (ranked by frequency across MMPs):**

1. **Pricing increase on listing page** — Were prices updated on or around the drop date? SP rate change, discount removed, or helipad/facility fees now included in display price. Check `price_analysis` for median price delta pre vs post. A price increase coinciding with the onset date is a strong corroborating signal.

2. **Listing page UX / MB format change** — Was a new listing page format or MB template deployed? Historical case: Vienna concerts' new Live Entertainment MB format introduced an extra decision step (venue selection before date selection), cutting LP2S roughly in half. Users reaching the select page dropped from ~40%+ to ~20% overnight. Always check if the onset date aligns with a product deploy.

3. **Campaign routing to wrong LP** — Are paid campaigns pointing to an incorrect or outdated landing page? Historical case: NY Helicopter had language-specific campaigns still routing to the old San Francisco LP. Only the affected language shows a drop; other languages hold.

4. **Product ranking change at top slot** — Did the top-ranked product change on or around the drop date? A new top product with lower inherent CVR, higher price, or worse availability depresses overall LP2S even if the rest of the CE is unchanged.

5. **Competitor pricing action** — Did GYG, Viator, or a direct competitor drop prices sharply, making HO's listed prices look expensive relative to alternatives the user sees? This typically shows up as a gradual effect but can be sudden if a competitor ran a flash promotion.

---

## Pattern 2: LP2S is the primary driver — gradual decline

A slow erosion of LP2S over weeks points to structural changes, not a single deploy event.

**Hypotheses (ranked by frequency across MMPs):**

1. **Supply thinning / availability horizon shrinking** — Is `days_to_first_available_date` increasing over the post period? Users landing on a listing page and seeing the nearest available date is weeks away are less likely to click through. Historical pattern: Blue Mountains next-day inventory progressively locked by API cut-off period settings.

2. **SIS cap reached, paid traffic quality declining** — As a CE scales, Share of Impression Share hits a ceiling. Incremental clicks are lower-intent. The CE appears to hold clicks but LP2S drifts down because the marginal user is less interested.

3. **Competitive pressure eroding click-through** — GYG/Viator strengthened their listing quality, ratings, or price positioning gradually. HO listings receive the same or more traffic but convert less.

4. **Content / media degradation** — Product images removed or replaced with lower-quality alternatives, descriptions not updated for seasonal relevance, review count stagnating relative to competitors.

5. **Assortment drift** — Products were added to the CE that are tangentially relevant but lower-CVR, diluting the listing quality for users browsing the full assortment.

---

## Pattern 3: S2C is the primary driver — sudden onset

A sharp S2C drop on a specific date almost always points to either a supply configuration change or a select page deploy.

**Hypotheses (ranked by frequency across MMPs):**

1. **Availability configuration tightened** — API cut-off period shortened, release window changed, or lead-time minimum increased by the SP. Users who reach the date picker see no bookable dates for their trip window. Historical pattern: Blue Mountains SP API cut-off periods preventing next-day and same-week bookings; USJ release settings limiting near-term inventory.

2. **Select page / date-picker UX regression** — A deploy broke or degraded the date-picker experience. Likely concentrated in mobile (iOS Mweb most sensitive). Check device breakdown for S2C — if iOS Mweb carries disproportionate drop, this is the hypothesis to pursue first.

3. **Price shock at variant level** — The select page shows a higher price than the listing page anchor (e.g., listing shows base ticket price, select page shows full price including mandatory fees). Users who clicked expecting $X now see $Y and abandon. Historical case: NY Helicopter helipad fees not included in LP display price.

4. **Specific experience availability collapse** — One key experience within the CE lost inventory entirely (vendor cancelled availability for a block of dates). Check experience-level S2C — if one experience carries most of the drop while others hold, this is a vendor-specific issue, not a CE-wide one.

5. **TGID misconfiguration** — A product variant configuration change caused the wrong experience or wrong date-picker to load. Most likely to surface as a sudden drop concentrated on one experience.

---

## Pattern 4: S2C is the primary driver — gradual decline

Slow S2C erosion points to structural supply or complexity issues that worsen over time.

**Hypotheses (ranked by frequency across MMPs):**

1. **Inventory thinning over time** — SP progressively reducing available slots or shortening the booking window. Lead times growing, last-minute availability disappearing. Historical case: NY HeliNY last-minute gaps requiring advance booking; Blue Mountains vendors limiting same-week availability.

2. **Variant complexity increasing / decision paralysis** — More SKUs or variants added without clear differentiation. Users are overwhelmed and abandon before committing. Historical case: Vienna concerts — multiple venue × composer × price × duration combinations with no clear "best" option created decision paralysis. S2C improved after assortment was simplified.

3. **Vendor throttling inventory under fulfilment strain** — A SP with rising cancellation rates often quietly reduces available slots or tightens release windows to avoid over-booking. This directly reduces 0-2D availability visible at the date picker, causing S2C to drop. The signal: ticket counts in the 0–2d bucket from the `inventory_availability` TID summary table drop for the specific experience(s) served by that vendor, while peers hold. `days_to_first_available_date` (from `product_rankings_features`) worsening over the same window is a confirmatory directional signal but is never sufficient on its own — always start with `inventory_availability`. Note: the vendor's CR% itself is a fulfilment/A2O metric — it does not directly move S2C. The connection is through availability, not fulfillment rate.

4. **Seasonal availability pattern** — Certain months have structural low-availability periods for the experience type (e.g., peak demand for a limited-capacity venue, off-season closures). Compare to prior-year data to distinguish seasonal from structural.

---

## Pattern 5: C2O is primary — C2A sub-metric is down (users abandoning before submitting payment)

Users reached checkout but did not submit payment. The problem is in the checkout experience itself.

**Hypotheses (ranked by frequency across MMPs):**

1. **Hidden fees revealed at checkout** — Total price in checkout is materially higher than what was shown during selection (helipad fees, booking fees, taxes). Users feel deceived and abandon. Historical case: NY Helicopter helipad fees not surfaced until checkout, causing C2A abandonment.

2. **Checkout UX friction — new step or broken flow** — A form field was added, autofill broke, a payment option was removed, or the checkout flow gained a step. Most sensitive on mobile mweb (iOS Safari, Android Chrome).

3. **Booking fee or mandatory add-on revealed only at checkout** — The checkout total is materially higher than the select-page price because a mandatory fee (booking fee, facility surcharge, per-person add-on) was not surfaced earlier. This is distinct from the LP price shock (Pattern 3.3) — the user cleared the select page but then sees the true cost in the checkout form and abandons. Check whether a booking fee was added or a fee structure changed around the onset date. Note: Wrong TGID in customer communications (NY Helicopter case) causes post-booking cancellations but does not directly move the C2A funnel metric — that is an operational issue handled in actions.md RC8, not a funnel hypothesis.

4. **Coupon or promo code breakage** — An active promotional code stopped working, causing users relying on it to abandon at payment.

5. **Trust signals missing** — Review score, cancellation policy, security badge, or payment method logos removed from the checkout page.

---

## Pattern 6: C2O is primary — A2O sub-metric is down (payment submitted but order failed)

Users attempted payment but it did not complete. The problem is downstream of the checkout form.

**Hypotheses:**

1. **Payment gateway degradation** — Gateway timeout, error rate increase, or outage for a specific payment method. Check engineering/gateway logs for the onset date.

2. **Fraud rule tightening** — Updated fraud filters increasing card decline rate for certain card types or geographies.

3. **Currency / FX display error** — Price shown in wrong currency or with wrong conversion rate at the payment step, causing card authorisation to fail.

4. **New payment method rollout regression** — Adding a new payment option sometimes introduces a flow breakage for existing methods on certain devices.

---

## Pattern 7: MB/HO mix shift is the dominant explanation

Before diagnosing any funnel step: if mix is dominant, the story is about traffic, not conversion.

**Hypotheses for why traffic shifted toward lower-CVR MB:**

1. **Paid campaign paused, scaled down, or budget reallocated** — HO paid traffic (high-intent) dropped, increasing MB's organic share. Historical case: NY Helicopter saw 75% drop in English campaign clicks in Jan 2026, collapsing overall CVR via mix even though per-segment rates held.

2. **LP routing error in paid campaigns** — Some language or geo campaigns now send traffic to an MB page instead of headout.com, shifting apparent MB share up. Historical case: NY Helicopter language campaigns routing to old SF landing page.

3. **Seasonal organic MB spike** — A seasonal event drove outsized organic MB traffic without a corresponding paid HO increase, diluting the mix.

4. **Budget reallocation to another CE** — Marketing shifted paid spend away from this CE, reducing HO's share of total CE sessions.

---

## Pattern 8: Drop concentrated in a specific device

**Hypotheses:**

1. **Mobile UI deploy with regression** — A front-end change broke or degraded the mobile web experience. iOS Mweb (Safari) is especially sensitive to CSS changes and font-rendering issues.

2. **Mobile page performance degradation** — Page load time increase on mobile (e.g., uncompressed images, new JS bundle) causing higher bounce rate.

3. **Mobile-specific feature breakage** — Date picker, image carousel, CTA button, or checkout form non-functional on a specific mobile browser.

---

## Pattern 9: Drop concentrated in a specific language

**Hypotheses:**

1. **Geo-specific campaign change** — That language's paid campaign was modified, paused, or re-routed. Traffic volume in that language may have held (organic SEO) but intent composition changed.

2. **Localisation issue** — Translation missing for a new product or feature, broken layout for a non-Latin character set, or locale-specific content showing incorrect dates/prices.

3. **Geo-specific availability or pricing change** — A SP adjusted pricing or availability for a specific market, affecting only the language segment that targets that geography.

4. **New lower-intent source for that language** — An affiliate partner, SEO ranking improvement, or social campaign for a specific market brought in a new audience that converts at a lower rate.

---

## Pattern 11: Catalogue change — TGID launched, disabled, or restructured (bidirectional)

A TGID launching or being removed within the analysis window can produce funnel-step movement in either direction. Catalogue change is a first-class hypothesis whenever the experience-level breakdown shows a top experience whose checkout volume changed substantially (≥20% relative or accounting for ≥10% of the net CE-level move) pre vs post. **Data-driven trigger** — no Slack input required to test this; query `dim_experience_management.experience_created_at` (or first-appearance in `product_rankings_features`) directly.

**Decline direction — TGID cannibalises or disappears:**

1. **New TGID cannibalises higher-CVR variants.** A new mid-CVR variant launches and absorbs traffic from higher-CVR siblings, depressing the CE-level rate. Signal: the new TGID's checkout share grew while one or more sibling TGIDs lost share, and the new TGID has lower native C2O or S2C than the siblings.
2. **High-CVR TGID disabled.** An experience went `variant_status != 'Active'` mid-window, removing high-converting demand from the catalogue. Signal: one TGID's checkout volume fell to zero or near-zero mid-post, others held.
3. **Variant proliferation diluting clarity.** Multiple similar TGIDs added without clear differentiation create decision paralysis at the select page. Pattern 4 covers the assortment angle in detail.

**Improvement direction — TGID launched well or restructure landed:**

1. **New TGID adds incremental volume + CVR.** A new high-CVR variant launches and grows the catalogue at favourable rates. Signal: the new TGID's checkout share grew, sibling TGIDs roughly held (not cannibalisation), and the new TGID has higher native C2O.
2. **New TGID cannibalises lower-CVR variants.** A new variant absorbs traffic from lower-CVR siblings, *lifting* the CE-level rate. Signal: gaining TGID has higher C2O than the displaced siblings. Asymmetric mirror of decline pattern 1.
3. **Catalogue restructure / MB assortment cap.** Marketing or Growth caps the visible MB assortment to a smaller, higher-CVR set (e.g., MB capped at 8 products). Concentrating traffic onto the highest-CVR TGIDs lifts CE-level rates without changing any per-TGID flow. Often layered with content/title updates on the surviving TGIDs.

**How to test (data-driven):**
- Run the catalogue-change query (`context.md → "Catalogue change query"`) to identify TGIDs whose first/last appearance is inside the window, and TGIDs whose `variant_status` flipped during the window.
- Cross-reference with the experience-level checkout breakdown — does a launching TGID line up with a major share-change?
- If a TGID launched mid-window: scope the timeline. Did the C2O/CVR inflection align with the launch date? If yes, catalogue change is confirmed as a mechanism (Pattern 11 leaf). If the inflection predates the launch, the new TGID is incidental.

**Historical reference (improvement direction):** CE 1223 Pompeii (May 2026) — new Skip-the-line Guided Tour with Archaeologist (TGID 25518) more than doubled checkout volume; MB assortment capped at 8 products on May 7; combined catalogue restructure explained part of the +0.23pp structural CVR delta.

---

## Pattern 10: Drop concentrated in specific experiences at S2C

**Hypotheses:**

1. **Experience-specific availability collapse** — This product's SP closed inventory for the post period or tightened cut-off settings. Run the `inventory_availability` TID summary table and daily time-series for that TGID (see `context.md → inventory analysis`) to confirm and identify which lead-time window was affected.

2. **Vendor-specific operational issue** — SP had cancellations, moved to manual fulfillment mode, or had an API outage affecting only their products. Historical case: NY Helicopter Charm Aviation required manual FF mode; completions dropped disproportionately on Charm-serviced TGIDs.

3. **Experience-specific pricing change** — This product's price was raised while peer products held, making it uncompetitive within the CE's own select page.

4. **TGID misconfiguration** — Wrong variants linked, duplicate TGIDs created, or experience merged/split incorrectly, confusing the date-picker for that specific product.

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c001 | 2026-04-24 | Initial version — 10 patterns drawn from 21 historical Headout MMPs |
| c002 | 2026-04-24 | Added "How to use this file" preamble clarifying these are historical priors, not a constraint; Claude generates its own hypotheses from data and is not limited to patterns listed here |
| c003 | 2026-04-24 | Added "URL concentration" preamble section before Pattern 1 — URL-level concentration is now a first-class hypothesis for all four primary driver types (mix, LP2S, S2C, C2O), with volume filter requirement and pointer to majority-contributor principle in SKILL.md |
| c004 | 2026-04-29 | Restructured as two-level reference: Level 1 (L0 routing map + first-pass branch sets by funnel step) moved from context.md; Level 2 (historical patterns) retained. "How to use this file" updated to reflect full role as the central branch reference for all investigation levels. |
| c005 | 2026-04-29 | L0 routing table rewritten: first rows now show cascade exit conditions (mix exit at Level 1/2/3) before the Shapley rows, reflecting that the cascade runs first and Shapley rows apply only after a conversion-path cascade completes. mix_dominance.is_dominant = true row removed — mix determination happens through cascade levels, not as a pre-gate. |
| c006 | 2026-05-06 | Inventory-related gaps fixed across S2C investigation branches: (1) Removed all `count_days_available_30d` references — replaced with direct `inventory_availability` TID summary table checks. (2) "If experience concentrates" branch restructured: `days_to_first_available_date` from `product_rankings_features` added as fast pre-check for gradual S2C declines; Step 2 TID summary table now serves as the supply gate (full tickets = pivot to pricing, depleted = run Step 3). (3) Tier 2 broad-drop path made concrete: pick top 3 TGIDs by volume, run Step 2 for each; same bucket depleted across all = CE-wide constraint; full across all = not supply. (4) Pattern 4 vendor throttling signal updated: `count_days_available_30d` replaced with `days_to_first_available_date` + 0–2d bucket from `inventory_availability`. (5) Pattern 10 experience availability collapse: updated to point to TID summary table + daily time-series. |
| c007 | 2026-05-07 | Inventory investigation decision logic moved here from context.md. "If experience concentrates" branch now owns the full investigation sequence: (1) TGID selection via lost_checkouts_delta + three-case classification (single dominant / multiple significant / uniform drop); (2) data availability check; (3) optional gradual-decline pre-check; (4) TID snapshot query usage; (5) daily time-series query usage; (6) supply confirm/rule-out decision. Broad-drop path (uniform drop) moved here from context.md. Removed "Step 2/3" label references throughout — queries now referenced as "TID snapshot query" and "daily time-series query". |
| c008 | 2026-05-07 | Broad-drop path verdict clarified: "Tickets healthy across all three TGIDs" changed to "Time-series shows tickets healthy throughout the post period across all three TGIDs" — making explicit that the supply rule-out is based on the historical daily time-series, not today's snapshot. |
| c009 | 2026-05-07 | Added jargon firewall note before the inventory investigation sequence: all investigation-internal labels (lost_checkouts_delta, single dominant TGID, multiple significant TGIDs, uniform drop, Path A/B/X, Case A/B/C) belong in the transcript only and must be translated to business language in the HTML report. Cross-reference to report_structure.md anti-patterns added. |
| c010 | 2026-05-07 | Reduced over-prescription in first-pass branches: (1) Removed all three "Declare:" wording templates from Mix routing exit sections — the closing paragraph already states what makes a finding complete. (2) Removed "Work through X tiers in order — don't skip ahead" instruction from LP2S and S2C; replaced "Tier 1" labels with "Run dimension cuts in parallel". (3) Removed "Tier 2/3" labels from LP2S fallback steps and "Tier 2" from S2C fallback — replaced with plain "If no dimension concentrates" headers. (4) Replaced the three-case TGID classification (≥60% / ≥10% thresholds) with a principle: investigate TGIDs that explain the majority of the checkout loss, starting with the top contributor. |
| c011 | 2026-05-07 | Step 6 (supply verdict) expanded from binary to three verdicts: (1) Supply is the mechanism — sustained depression or onset event aligned with S2C break; (2) Supply partially contributed — gradual depression or TGID-specific episodic dips; note as secondary finding, do not silence; (3) Supply ruled out — flat and stable throughout. Aligns with the trend-based interpretation guide in context.md c021. |
| c012 | 2026-05-07 | Inventory investigation steps 4 and 5 updated: (1) Step 4 renamed from "TID snapshot query" to "median query" (Path A post-period median / Path B pre/post median). Added explicit bridge enforcement: always query through `experience_id → dim_tours` — never hardcode a `tour_id`. Added contributing TID identification: near-zero post-period median (Path A) or significant post vs pre median drop (Path B). Added TID-to-chart scoping rule: one locus → single TID trace; multiple depleted → TGID aggregate; mixed → depleted only with healthy TIDs noted in chart banner. (2) Step 5 updated to reference scoping derived from step 4 rather than the snapshot. |
| c013 | 2026-05-07 | Step 4 bridge corrected and booking-horizon pre-check added: (1) Bridge changed from `experience_id → dim_tours` to `experience_id → dim_experience_management WHERE variant_status = 'Active'`. Reason: `dim_tours` has no `variant_status` column — returns Disabled TIDs, causing wrong TID selection (CE 189 post-mortem: TID 67659 Disabled was queried; Active TIDs 17000/17521 were missed). (2) Booking-horizon pre-check added as a mandatory step before running the median query: if `min_lead_time > 30` in the post period, standard bucket ceiling is mismatched to the product's horizon and all buckets return zeros that are not a supply signal. Pointer to `context.md → Booking-horizon pre-check` added. |
| c014 | 2026-05-08 | Removed booking-horizon pre-check reference from Step 4 (added in c013). The motivating example (Vatican Museums as a 60–90 day horizon product) was factually wrong; the pre-check added an unnecessary mandatory query with no analytical benefit, since zeros in both periods are already correctly handled by the "flat and stable → supply ruled out" interpretation. Bridge fix (dim_experience_management WHERE variant_status = 'Active') retained. |
| c015 | 2026-05-13 | Added URL-level analysis to LP2S investigation and fixed the broken URL concentration cross-cutting check.
| c016 | 2026-05-14 | S2C first-pass branches — added secondary-driver scoping block at the top of the section, aligned with SKILL.md c023. When S2C is a secondary driver: run the fixed-segment aggregate first; if flat or improved outside the fixed segment, close as RULED OUT; if declined within the fixed segment but directionally explained by the primary finding, close as CONFIRMED with one-line explanation; only open the full first-pass branch set if S2C shows an independent decline not explained by the primary mechanism. Prevents unnecessary dimension cuts on secondary steps while ensuring the coverage requirement from c023 is met. | (1) LP2S first-pass branches: added `page_url` × LP2S rate and volume as an explicit parallel first-cut dimension — checks both volume shift between URLs (routing story) and rate change on specific URLs (page-specific story) independently; majority-contributor filter note added. Updated "if a dimension concentrates" follow-up to reflect that when URL itself concentrates at the first cut, it is the direct finding, not a secondary drill-down. (2) URL concentration cross-cutting check: removed broken `summary.json` URL breakdown reference (that field does not exist). Replaced with: run the canonical L2+ query with `page_url` as dimension. Rewrote sub-bullets for Mix/LP2S/S2C/C2O to be operationally executable and conceptually accurate — specifically, clarified that `page_url` in S2C context is the session-entry URL (landing page), not the select-page URL, so S2C differences by URL reflect user composition (intent) rather than select-page UX. C2O sub-bullet updated to flag URL as a weak lens for checkout-stage drops. |
| c017 | 2026-05-08 | URL concentration cross-cutting check: updated the query pointer from "Run the canonical L2+ query from `context.md` with `page_url` as the dimension" to "Run the URL breakdown query from `context.md` (not the canonical L2+ query — that query does not include `pct_of_lp`)". Reason: the URL concentration section explicitly requires both volume share and rate checks to distinguish routing vs performance stories. The canonical query only answers the rate question. Without `pct_of_lp`, Claude would construct the totals CTE on the fly — the class of error flagged in the insights report. The dedicated query (added to context.md c026) is the correct reference. |
| c019 | 2026-05-27 | Demoted `days_to_first_available_date` (from `product_rankings_features`) from "fast pre-check" to "corroborating directional signal only." Three edits: (1) **S2C decline → "For a gradual S2C decline"** — replaced the pre-check framing with "canonical query is always `inventory_availability`"; proxy permitted only when Path A is in effect AND a pre→post trend reading is genuinely needed, then only as a footnote. (2) **S2C improvement → "If experience concentrates upward — inventory expansion check"** — added the same canonical-source pointer so the improvement direction inherits the rule explicitly. (3) **Pattern 4 (vendor throttling)** — reordered the signal description to lead with `inventory_availability` 0–2d bucket and demote the proxy to a confirmatory signal. Bidirectional rule, lives in `context.md` c028 (canonical-source paragraph on the table itself); `hypothesis.md` edits are short pointers, so the rule has one home and no parallel duplication. Driven by CE 252 (Louvre) RCA — substituted the proxy as evidence; the canonical query showed materially richer inventory state. Companion `report_structure.md` c026 anti-pattern row catches the substitution at the writing stage as well. |
| c018 | 2026-05-22 | Bidirectional + Slack four-pattern model added. **(1) Cross-cut trigger rule rephrased** from "concentrated drop" to "concentrated movement (in either direction)" — same threshold (8pp absolute / 20% relative), same logic, broader language so improvement RCAs trigger the cross-cut too. **(2) New "Improvement direction — first-pass branches" section** between the C2O decline branches and URL concentration — covers LP2S/S2C/C2O/Mix in the positive direction with their own dimension cuts. Catalogue change and supply expansion are direction-symmetric counterparts of the decline patterns. **(3) New "Pattern 11: Catalogue change (bidirectional)"** — TGID launch, removal, or restructure as a first-class hypothesis in both directions. Data-driven trigger via experience-level breakdown + `dim_experience_management.experience_created_at` (no Slack input required). Historical reference added for CE 1223 Pompeii (Pattern 11 improvement direction). **(4) New "Slack signal classification" section** between URL concentration and Pattern 1 — reference table mapping the four patterns (A/B/C/D) plus Reject to where each surfaces in the report and what action is required. Lists high-value gap categories for Pattern D (assortment changes, pricing levers, content updates, supplier changes, catalogue events). Reaffirms that Slack reconciliation is retrospective only — never during L0/L1/L2. Cross-references to SKILL.md Step 2b check #9 and report_structure.md Slack integration section. |
