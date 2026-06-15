# Cascading Hypothesis Tree — Paid Audit v6

For each metric signal, walk the tree top-down. Test each hypothesis with its data cut. The first confirmed hypothesis is primary; continue checking remaining branches for secondary/compounding causes. In the report output, show the reasoning naturally (hypothesis → check → result) WITHOUT referencing this file or hypothesis IDs.

---

## 0. Coverage Gate — close every enumerated signal

The engine enumerates the **material movers** into the "Signals to Close" tables inside a **backend HTML comment** at Section 9 (channels/cohorts >10% of |rev Δ|, headline metrics past threshold, Shapley drivers >15% of |paid CM1 Δ|, TGID |Δ share|>5pp). That list is the gate: **every row must be closed** in the comment — none may be silently dropped. The comment is *not* rendered in the report; the visible §9 is only the ranked **Red Flags** table (the CONFIRMED subset). This is the perf-audit analogue of CVR-RCA's "close every quantified signal ≥10% of Shapley."

**Disposition vocabulary** — every row gets exactly one:
- **CONFIRMED** — a real driver/problem. Flows into the Red Flags table (severity-ranked).
- **RULED OUT** — not a driver. Requires a one-line reason: *noise* (within ±5% / a few pp), *below materiality*, or *explained by another signal* (e.g. "CVR −0.7pp is assortment-mix, not funnel — see TGID 39257"). 
- **DATA GAP** — can't be closed with available data; name what's missing (CSV, Ahrefs, a query not run).

**A one-line closure satisfies the gate.** You don't owe every signal a paragraph — a sub-threshold or already-explained mover can be closed in a single clause. The rule is *always closed*, not *always deep*. The engine renders two tiers: the **HIGH-severity** movers get reasoned dispositions (these are the 3–4 conclusions the report leads with); the **"Also enumerated"** rows get **one line each** (most RULED OUT). Narrating a paragraph for every minor signal is itself a failure — it buries the verdict.

**Account for the L12M trajectory** (the table's L12M column) when disposing — it changes the verdict:
- `cliff` → a single-month break; look for a point event (pause, tracking outage, SP action) at that month.
- `gradual` → structural erosion; not a recent shock.
- `recovering` → the YoY drop is already reversing (MoM up); temper the severity, credit the recovery — don't alarm on a metric that's climbing back.
- `volatile` → noisy; be cautious sizing a single-window move.
- `new` → a recently-appeared SKU/cohort; expected to be small/ramping, not a "loss."
This maps onto §11 (Temporal Diagnostics) — use it to separate structural from cyclical.

**Which tree closes which signal** (the gate says *which* to close; these trees say *how*):
- Clicks / Impressions driver → §1 / §2 ; CPC → §4 (3-lens) ; SIS / rank-lost → §6
- CVR driver → §5 (route to /cvr-rca) ; Take Rate → §7b ; ROI → §7
- Channel mover → §9 ; Spend → §8 ; Coverage/dormancy → §10 ; Temporal shape → §11
- TGID / assortment shift → §5 "Assortment change" (read the Product Mix table's Δ Share)

After closing all rows, build **Red Flags** = the CONFIRMED rows, severity-ranked, plus any qualitative flag not in the enumeration (data caveats, competitor surges). Every CONFIRMED signal must appear in Red Flags.

---

## 1. Clicks ↓

Decompose first: Clicks = Impressions × CTR. Which component drove the drop?

### If Impressions dropped (volume problem):

**Search volume declined (external demand)**
- Check: Ahrefs volume history for CE core keywords. Seasonal calendar.
- Confirmed if: volume trending down across the market, not just our campaigns
- Action: If seasonal → ride it out. If structural → expand into low-IS clusters.

**SIS dropped (we're showing less)**
→ Fork to SIS tree (Section 6 below)

**Campaigns paused or dormant**
- Check: campaign status flags, spend trend, consolidation context (geo merge Oct 2025)
- Confirmed if: campaigns with LY revenue now PAUSED or spend <$10/month
- Action: Verify if paused campaigns have active replacements. Only flag if targeting genuinely missing.

**Campaign structure changed (fewer campaigns than LY)**
- Check: campaign count L4W vs LY. If LY had geo-split campaigns now consolidated.
- Confirmed if: total campaigns reduced but total clicks stable = consolidation, not loss
- Action: Use channel-level BQ revenue for YoY comparison, not campaign-level clicks.

### If CTR dropped (same impressions, fewer clicks):
→ Fork to CTR tree (Section 3 below)

### If both dropped:
Investigate both branches. Compounding = more severe. Likely a structural issue (competition + demand decline) or a campaign pause that removed volume AND changed the remaining traffic mix.

---

## 2. Impressions ↓

**SIS declined**
→ Fork to SIS tree (Section 6)

**Search volume declined (external)**
- Check: Ahrefs `keywords-explorer-volume-history`. Compare 3-month trend to LY same period.
- Confirmed if: Ahrefs volume down >15% vs same period LY
- Action: Seasonal → optimize for efficiency. Structural → check keyword IS for expansion clusters.

**Campaign paused/dormant**
- Check: campaign status, spend/budget ratio, dormancy detection (ENABLED but <20 clicks/week)
- Check: Slack for SP/supplier/yellow card mentions
- Confirmed if: PAUSED campaigns with significant LY contribution, OR ENABLED with spend/budget <0.3
- Action: For paused → quantify foregone revenue. For dormant → fork to Coverage tree (Section 10).

**Budget cut**
- Check: Q7 budget amount L4W vs change_event log. Flag if cut >20% in last 30d.
- Confirmed if: budget_amount_micros decreased AND budget_lost_IS > 0
- Action: If intentional → understand rationale. If drift → restore.

---

## 3. CTR ↓

**Ad position worsened**
- Check: top-of-page % L4W vs LY (Q1 vs Q1b). Abs-top % shift.
- Confirmed if: top-of-page dropped >5pp
- Chain: Competitor bids up → our position drops → CTR falls → fewer clicks
- Action: Increase bids to recover position. Verify via auction insights position-above-rate.

**Ad copy quality degraded**
- Check: ad strength scores (GAQL ad_group_ad.ad_strength). Flag if >50% POOR on high-spend campaigns.
- Confirmed if: majority POOR/AVERAGE on top-spend campaigns
- Action: Rewrite ads. Cheapest CTR fix (1-2 day timeline).

**Search partner traffic mix increased**
- Check: Q4 network type. % of clicks from SEARCH_PARTNERS vs SEARCH.
- Confirmed if: search partner share grew >5pp, partner CTR much lower than Search
- Action: Consider excluding search partners if partner CVR is also 0.

**Competition for top positions**
- Check: auction insights overlap rate increasing. New entrants with high top-of-page %.
- Confirmed if: new competitor appeared OR existing competitor IS jumped >5pp
- Action: Differentiate via extensions, sitelinks, offer-based copy.

---

## 4. CPC Analysis

### Step 0: Decompose by language BEFORE applying 3-lens tree

NEVER conclude on blended CPC alone. Blended CPC hides mix shifts — if expensive cohorts shrink while cheap cohorts grow, blended CPC looks flat despite competition.

For each language cohort with >$1K spend, classify:
- **CPC ↑ + Scale ↓** = competition (competitor bidding up, we're losing auctions)
- **CPC ↑ + Scale ↑** = healthy scaling (paying more but winning more)
- **CPC flat + Scale ↓** = SIS compression / competition (not bidding enough to enter auctions — same root cause as competition, just expressed differently. Competitors bid higher → we lose rank → SIS drops → clicks drop)
- **CPC ↓ + Scale ↓** = algorithm retreat OR demand decline (see Step 1b to distinguish)
- **CPC ↓ + Scale ↑** = efficiency gain (rare — usually means competitor exited)

A flat blended CPC with large click loss almost always means competition or SIS compression at the cohort level. The mix shift masks it.

### Step 1a: If dominant pattern is CPC ↑ — apply 3-lens tree

Walk in order. Stop at the first confirmed lens for primary cause, but check remaining for secondary.

**Lens 1: Quality traffic (good CPC)**
- Check: CVR rose alongside CPC. RPC/CPC ratio healthy (>1.5x).
- Confirmed if: CVR above market median AND RPC > CPC
- Meaning: Google is optimizing for converting clicks at higher cost. This is GOOD.
- Action: Accept the premium. Monitor RPC/CPC ratio.

**Lens 2: Average CM1 structural (replaces AOV)**
- Check: Average CM1 (= CM1 / conversions) L4W vs LY. This captures AOV × take rate × completion rate in one metric.
- Confirmed if: avg CM1 up >10% and CPC up proportionally — the algorithm bids more because each conversion is worth more
- If avg CM1 DOWN despite AOV up → take rate or completion rate dropped, limiting bidding ability. This is the Eiffel pattern: AOV rose but TR fell, so avg CM1 fell, so the algorithm couldn't bid high enough.
- Meaning: avg CM1 is what the algorithm optimizes for. CPC follows avg CM1, not AOV.
- Action: If avg CM1 up → CPC rise is justified (structural). If avg CM1 down → investigate TR/CR as the root constraint (see §7b TR tree).

**Lens 3: Competition**
- Check: (a) per-cohort CPC rose while scale dropped for the largest cohort, OR (b) auction insights show competitor SIS expansion, OR (c) SIS Δ of Δ shows Headout decelerating while competitors accelerate
- Confirmed if: at least 1 of the 3 evidence types present. Per-cohort CPC × scale is sufficient evidence — don't require auction insights CSV.
- Action: If RPC still > CPC → accept but flag SIS gap. If RPC < CPC → find lower-competition segments (Bing, OL, long-tail).

**Lens 4: Internal bid change**
- Check: tROAS or bid strategy changed in last 14d (change_event log, Q7)
- Confirmed if: strategy changed AND CPC moved within 14d of change
- Action: If in learning period (<14d) → defer judgment. If post-learning → evaluate if new bids are profitable.

### Step 1b: If dominant pattern is CPC ↓ + Scale ↓ — algorithm retreat vs demand decline

CPC declining is NOT always good. If clicks also dropped, distinguish:

**Algorithm retreat (campaign entering dormancy) — the dangerous pattern:**
- Check: (a) demand is growing (Ahrefs volume up or stable), AND (b) SIS is low (<30%) with high rank-lost (>60%), AND (c) RPC dropped (often from TR decline)
- Confirmed if: demand growing + SIS low + RPC dropped. The algorithm can't hit tROAS with low RPC, so it retreats to cheaper (lower-competition) auctions and enters fewer total auctions.
- Causal chain: TR decline → RPC drop → tROAS gap widens → algorithm bids less aggressively → wins only cheap auctions (CPC↓) → enters fewer auctions (clicks↓, SIS↓)
- Action: Fix the upstream constraint (TR/RPC), THEN loosen tROAS. Loosening tROAS alone won't help if RPC can't support it.

**Demand decline (external):**
- Check: Ahrefs volume trending down for CE core keywords
- Confirmed if: volume down >15% vs same period LY
- Meaning: Fewer people searching. CPC drops because fewer bidders per auction.
- Action: Seasonal → ride it out. Structural → diversify keywords or expand to adjacent products.

**Key distinction:** Both show CPC↓ + Scale↓. The difference is demand direction. If demand is UP but CPC and clicks are DOWN → algorithm retreat. If demand is DOWN → external contraction.

---

## 5. CVR ↓ (paid audit scope — funnel level)

The paid audit detects and sizes funnel leaks, rules out traffic quality as the cause, and routes to Product. Don't diagnose LP content, pricing, or availability — that's Product's scope.

**Run `/cvr-rca` for the deep investigation.** The perf audit's role is to:
1. Call CVR-RCA with the CE and date windows
2. Validate direction against cohort table CVR
3. Incorporate findings into Section 7 narrative
4. Surface P1/P2 funnel actions in Executive Summary

CVR-RCA provides the full diagnostic: Shapley decomposition (which step), mix cascade (routing vs conversion), device/experience/language cuts (where), C2O sub-stages (C2A checkout submission vs A2O payment success), and LY structural gap.

**How to interpret CVR-RCA output in the perf audit context:**

**LP2S dropped (landing page → selection)**
- CVR-RCA Shapley shows LP2S as significant step (>10% contribution)
- Before routing to Product, rule out paid-side cause using perf audit data:
  - Check informational term share from Section 8 clusters — if informational grew, LP2S drop may be traffic mix
  - Check cohort CVR trend from Section 5 — if CVR up but LP2S down, traffic quality improved but LP degraded
- Action: Route to Product WITH the traffic-quality argument. Size: LP sessions × LP2S gap × downstream rates × AOV.

**S2C dropped (selection → cart)**
- CVR-RCA Shapley shows S2C significant
- Check experience-level S2C from CVR-RCA — if specific experiences drag, it's supply/availability
- Check LY gap — if S2C persists below LY all year, it's structural (not a point event)
- Action: Route to Product/Supply. Check `/availability-diagnostics` for inventory gaps.

**C2O dropped (cart → order)**
- CVR-RCA splits C2O into C2A (checkout submission) and A2O (payment success)
- C2A drop → checkout UX regression. Check device concentration — mobile-only means mobile UX issue.
- A2O drop → payment failures. Check experience-level — if one experience has A2O drop while volume surged, it's capacity/gateway issue.
- Action: Route to Tech/Product with specific device + experience locus.

**Blended CVR down but largest cohort CVR stable**
- Check: filter funnel to Google Search English only. Compare blended vs filtered.
- CVR-RCA's mix cascade (L1: MB/HO, L2: Paid/Organic, L3: Channel) resolves this automatically
- If mix exit at any level → routing story, not conversion problem
- Action: Don't fix CVR. Fix coverage (dormant cohorts).

**Assortment change (product/experience contribution shift)**
- Check: the **Product Mix — Top Experiences (TGID) table in Section 4** (rendered by the engine from `fct_orders.experience_id`). Read the **Δ Share** column directly — no ad-hoc query needed.
- Confirmed if: any TGID with |Δ Share| > 5pp — a product that was a meaningful share of revenue LY is now near-zero (⚠️ / decayed), OR a new TGID (🆕) accounts for >5pp of revenue that didn't exist LY.
- Meaning: product mix shifted — CVR/RPC change is a side effect of different products converting and pricing differently, not a change in traffic quality or funnel performance. The table's AOV / CR / TR / Net Rev/Order / CM1/Order columns show *how* the economics differ between the gaining and losing products (Net Rev/Order = AOV × CR × TR; CM1/Order subtracts direct costs).
- **Tie to the Paid Value Shapley:** a mix shift toward a lower-AOV or lower-TR product mechanically drags blended Avg CM1 → this shows up as the Avg CM1 driver in the Section 4 Shapley. If the Shapley's Avg CM1 contribution is material and the TGID table shows a mix shift, they are the same story — state it once, with the product named.
- Action: Surface in the narrative — "revenue/CVR moved because the product mix changed (TGID X 50%→18%, TGID Y 0%→13%), not because the funnel improved/degraded." If a high-value product grew, positive (catalogue expansion / pricing). If a high-value product disappeared, route to Supply.

---

## 6. SIS ↓ (sub-tree — referenced by Clicks and Impressions)

**Rank-lost dominant (>60% of total lost IS)**
- Check: `rank_lost / (rank_lost + budget_lost)` from Q7 or cohort table
- Confirmed if: ratio > 0.6
- Sub-causes:
  - Competition scaled → Check: auction insights for competitor IS increase, new entrants
  - Quality score declined → Check: QS data if available
  - tROAS too aggressive → Check: our tROAS vs actual CPC capability
- Chain: Competition up → rank-lost → fewer impressions → CPC inflates on remaining auctions
- Action: Review bids on high-ROI campaigns first. Pull auction insights to identify who scaled.

**Budget-lost dominant (>40%)**
- Check: budget_lost_IS from Q7
- Confirmed if: budget_lost > 0.4 of total lost IS
- Note: budget level itself is not meaningful — budgets are managed as profitability controls, not spend caps. Check if actual SPEND dropped instead.
- Sub-causes:
  - Spend dropped → Check: L4W spend vs P4W spend. If spend dropped with constant budget → algorithm is self-suppressing (tROAS too high for current avg CM1)
  - CPC inflation consumed budget → Check: CPC trending up + spend constant but clicks down
- Action: If spend dropped → investigate avg CM1 trend (see Lens 2). If CPC consumed budget → raise budget on high-ROI campaigns only.

**SP-imposed cap**
- Check: Slack for "yellow card", "descale", "pause", "SP", "supplier" mentions
- Confirmed if: campaign previously scaled then abruptly paused + Slack evidence
- Action: Quantify foregone revenue. Include Slack thread links as evidence.

**Bidding self-suppression (dormancy)**
- Check: campaign ENABLED but spend/budget < 0.3. tROAS too high for current CVR.
- Confirmed if: ROI improving while clicks declining
- Chain: tROAS too tight → bids too low → impressions collapse → dormant
- Action: Lower tROAS. Calculate acceptable ROI given RPC and CPC.
- Key pattern: "ROI improving + clicks declining = tROAS too tight."

**SIS high (>60%) + ROI above target**
- This is the GOOD problem. Profitable headroom sitting idle.
- Action: Lower tROAS to unlock volume. Scale into it.

---

## 7. ROI ↓ (below 145% target)

**CPC too high, Rev/Click didn't keep pace**
- Check: CPC trend vs RPC trend. Is CPC growing faster than RPC?
- Confirmed if: CPC ↑ but RPC flat or ↓
- Action: Find lower-CPC segments (Bing, OL, long-tail). Do NOT cut bids — that kills volume.
- Key insight: Fix the numerator (Rev/Click), not the denominator (spend).

**CVR too low for the CPC level**
- Check: CVR vs subcategory benchmark. Calculate `Required CVR = (CPC × target_ROI) / (TR × AOV × CR)`
- Confirmed if: required CVR > 2× subcategory p50 → UNIT_ECONOMICS_CHALLENGING
- Action: Fix CVR first (route to funnel tree). ROI will follow.

**GAds ROI ≠ BQ ROI (metric confusion)**
- Check: GAds conv_value is CM1-based (since Oct 2025 migration). GAds ROI = CM1/spend. BQ ROI uses full revenue.
- Confirmed if: GAds ROI looks bad but BQ revenue is growing
- Action: Always show both. Explain: "GAds ROI 0.50x reflects CM1/spend. BQ revenue +22% YoY — the CE is growing. GAds metric is profitability per ad dollar, not total revenue health."

**ROI above target but not scaling**
- Check: ROI well above 145%, clicks plateaued, SIS < 40%
- Meaning: Over-optimization. Leaving money on the table.
- Action: Lower tROAS to unlock volume.

---

## 7b. Take Rate (TR) ↓ — Algorithm Constraint

TR decline is often the hidden root cause of SIS and ROI problems. When TR drops, RPC drops proportionally, making tROAS targets harder to achieve. The algorithm then self-suppresses to maintain profitability.

**Causal chain:** TR ↓ → RPC ↓ → tROAS gap widens → algorithm bids lower → SIS ↓ → clicks ↓ → revenue ↓

This chain can produce a confusing pattern: CPC declining, ROI stable or slightly improving, but massive volume loss. The algorithm is "winning" on efficiency by retreating from auctions it can't profitably compete in.

**SP contract / commission change**
- Check: L12M TR trend from appendix A1. Did TR drop abruptly (point event) or gradually (structural)?
- Check Slack for SP renegotiation, commission changes, new vendor terms
- Confirmed if: TR dropped >3pp in a specific month + Slack evidence of contract change
- Action: This is not a Perf issue. Route to Biz/SP team. Size the impact: every 1pp TR ≈ proportional % drop in RPC.

**Product mix shift**
- Check: Are lower-TR TGIDs growing in share? (e.g., combo tickets with lower commission vs standard tickets)
- Confirmed if: share of low-TR products increased while blended TR dropped
- Action: Accept structural TR shift. Adjust tROAS targets to reflect new blended RPC reality. If tROAS was set when TR was higher, it's now unachievable.

**Completion rate (CR) decline contributing**
- Check: CR from Table 1 or cohort table. TR = Rev / (OV × CR) approximately. If CR dropped, TR drops even if commission didn't change.
- Confirmed if: CR dropped >2pp YoY
- Action: Route to Supply (fulfillment issues, cancellations). CR recovery restores TR.

**Impact on tROAS recommendations:**
When TR is the root cause, loosening tROAS alone won't fully solve the problem — it buys temporary volume but at unsustainable efficiency. The report should:
1. Size the TR impact: "TR dropped Xpp → RPC dropped $Y → each click is worth $Y less → tROAS of Z% requires CVR of W% which exceeds market median"
2. Recommend tROAS adjustment as a short-term bridge
3. Flag TR fix as the structural solution (SP team, product mix, CR recovery)

---

## 8. Spend ↓ (without intentional cut)

**Bid strategy self-suppressing**
- Check: tROAS too high + clicks declining + ROI improving
- Confirmed if: spend/budget ratio dropping over time
- Action: Lower tROAS. Same pattern as dormancy.

**Spend dropped (replaces "budget was cut")**
- Check: L4W spend vs P4W spend. Did actual spend decline?
- Confirmed if: spend dropped >15% MoM without a budget reduction
- Meaning: algorithm is self-suppressing — avg CM1 can't support the tROAS target, so it bids less, spends less
- Action: Check avg CM1 trend. If avg CM1 dropped → TR/CR is the root cause (see §7b). Budget level itself is irrelevant — don't flag budget as a problem.

**Campaigns paused**
- Check: campaign status timeline. Any campaigns paused in last 30d?
- Confirmed if: paused campaign had significant spend before pause
- Action: Check if replacement exists. Only flag if gap genuine.

**Bidding in learning period**
- Check: bid strategy change within last 14d
- Confirmed if: strategy changed <14d ago AND spend volatile
- Action: Wait. Note "in learning period, defer judgment." Revisit in 2 weeks.

**Seasonality adjustment suppressing spend**
- Check: Q14 — active or recently-expired seasonality adjustments on this campaign
- Confirmed if: negative seasonality multiplier active during L4W, or expired within last 14d
- Chain: Negative seasonality → algorithm bids lower → impressions/spend collapse → campaign appears dormant
- Key distinction: This is intentional suppression by the perf team, not a market or bidding problem. Don't diagnose further if negative seasonality explains the spend drop.
- Action: If seasonality expired → spend should recover naturally within 7-14d. If still active → note in 4a narrative with dates and multiplier. If campaign remains dormant after seasonality expires, escalate to tROAS tree (Section 6).

---

## 9. Channel-Level Diagnostics (Section 1 Table 3)

**Paid search drove the decline**
- Check: Google Search + PMax revenue L4W vs LY
- Refuted if: Google Search/PMax grew while total CE declined = decline is from other channels
- Action: Identify which non-paid channels declined. Before routing, do the attribution drift check:
  - Sum Organic + Others (non-paid) L4W vs LY. If combined is stable but individual channels shifted, it's attribution reclassification, not real decline.
  - If combined also declined → actual demand/traffic loss, route to SEO/Product.

**A specific channel disappeared (>90% drop)**
- Check: any channel in LY but missing/near-zero in L4W
- Confirmed if: channel revenue dropped >90%
- Sub-check: PMax → verify child account migration. Bing → check campaign status.
- Action: Only flag if volume genuinely lost (not migrated to another account).

**MoM diverges from YoY**
- Check: channel deltas L4W vs LY vs Prior 4W. Do they tell different stories?
- Confirmed if: YoY says "up" but MoM says "down" (or vice versa)
- Meaning: YoY masks a recent trend change. MoM is the early warning.
- Action: Flag the divergence explicitly. Monitor next period.

---

## 10. Coverage Diagnostics (Section 4a)

**Dormant cohorts from over-bidding**
- Check: tROAS of dormant cohorts vs active cohorts
- Confirmed if: dormant tROAS > active tROAS (bidding too conservatively)
- Action: Lower dormant cohort tROAS to match active levels.

**No tROAS configured**
- Check: Q7 — MAXIMIZE_CONVERSION_VALUE without target_roas set
- Confirmed if: tROAS shows "—" or 0%
- Meaning: Algorithm has no profitability signal. May suppress or overspend unpredictably.
- Action: Set initial tROAS at 130% for campaigns with <50 conversions/month (learning mode — gives the algorithm a target while allowing room to explore). Raise to 145% (Pro+ standard) once the campaign sustains >50 conversions/month for 2+ consecutive months. For campaigns already at >50 conversions/month, set directly at 145%.
  - **130% vs 145%:** 130% is the on-ramp — it allows the algorithm more bid headroom while it learns conversion patterns. 145% is the steady-state target. Don't start at 145% on a cold-start campaign — the algorithm will self-suppress before it learns.
- If recommending merge into OL: **note the dilution risk**. OL may be the best-performing campaign — adding zero-converting dormant traffic could degrade its learning signal. Always include a revert trigger: "monitor OL ROI for 2 weeks post-merge; revert if ROI drops >20pp."

**Active seasonality adjustment**
- Check: Q14 — any seasonality multiplier on campaigns for this CE
- Confirmed if: multiplier ≠ 1.0 (positive or negative)
- Meaning: Perf team manually adjusted bidding intensity. Positive = scaling push. Negative = intentional suppression.
- Action: Note in 4a narrative with dates and multiplier value. If negative and campaign is dormant, this is likely the cause — don't diagnose further (it's intentional). If positive and campaign is still under-performing, the seasonality push isn't working — investigate other branches.

**Intentional consolidation (not a gap)**
- Check: geo-specific campaigns paused (EN-RoW, EN-RoA) + All-countries campaign active
- Confirmed if: consolidated campaign exists and captures equivalent volume
- Action: Do NOT recommend reactivation. Verify via geographic_view that user countries are covered.

**"Other" / catch-all cohort collapse (≥90% YoY drop)**
- Check: "Other" or "Other Languages" cohort had significant LY spend/clicks but near-zero now.
- Confirmed if: language-specific cohorts (EN, DE, FR, IT, etc.) grew or were created in the same period, absorbing the "Other" traffic. Sum of language-specific L4W spend ≈ "Other" LY spend.
- Meaning: Campaign restructuring moved traffic from a catch-all "Other" into dedicated language campaigns. This is expected — better targeting, not lost volume.
- Action: Verify that total clicks/spend across all cohorts hasn't dropped disproportionately. If total is stable but "Other" collapsed → consolidation artifact, note it but don't flag as a problem. If total also dropped significantly → there's a real volume loss on top of the restructuring, investigate other branches (SIS, demand).

**PMax missing from this account**
- Check: no PMax campaigns found with spend for this CE
- Before confirming: check if PMax was migrated to new child account (common since Nov 2025)
- Action: Only flag if genuinely missing after child account check.

**Language/geo coverage gap (inactive cohort)**
- Check: language/geo combinations with NO campaign at all
- Size: estimate potential using tourist demographic proxy or Keyword Planner volume
- Action: Flag as "money on the table" with estimated opportunity.

---

## 11. Temporal Diagnostics (MoM — Section 1 Table 3 + all tables)

**Drop is new (started in current window)**
- Check: L4W down vs LY, but Prior 4W was healthy vs LY
- Meaning: Something changed in the last 4 weeks.
- Action: Investigate recent changes: bid strategy (last 14d), campaign pauses, SP issues, seasonal event.

**Drop is ongoing (persistent 2+ months)**
- Check: both L4W AND Prior 4W are down vs LY
- Meaning: Structural issue, not a blip.
- Action: Look for fundamental causes: competition entrenched, demand shifted, pricing changed.

**Recovery in progress**
- Check: L4W still down vs LY, but improving vs Prior 4W
- Meaning: Trajectory positive. A recent change may be working.
- Action: Credit the recovery. Don't over-alarm on YoY if MoM shows improvement.

---

## 12. Data Escalation Map

After standard data collection (Steps 1–3b), walk the active trees above. Each "Check:" line maps to a data source. Most are satisfied by the standard queries (Q1–Q9, Ahrefs, Slack, auction CSV). When a branch is active but its required data is missing or insufficient, fire the escalation query below.

**How to use:** After Step 3b completes, scan results for these conditions. If the condition is true AND the standard data doesn't answer the branch's question, fire the escalation query. This is NOT a fixed checklist — only fire what the tree demands.

### Escalation queries by tree branch

| Tree | Branch active when... | Standard data covers? | Escalation query if not |
|---|---|---|---|
| **6. SIS ↓** | Any cohort SIS drop >10pp YoY | Q7 has L4W snapshot only — no trend | **E1: Monthly SIS trend** (L12M) — determines cliff vs gradual vs recent. Without this, you can't tell the perf team whether the problem started last month or last year. |
| **4. CPC ↑** | CPC rose >20% AND Lens 1 (quality) confirmed | Standard data has L4W/LY/Prior4W — 3 points | **E2: Monthly CPC + RPC trend** (L12M) — if CPC is rising alongside competition (Tree 6), the monthly trend shows whether it's accelerating. Three points hide the shape of the curve. |
| **7. ROI ↓** | ROI within ±15pp of 145% target | Standard data has ratio only | **E3: Absolute CM1 dollars** — derive from standard data: `CM1 = ROI × Spend`. Show L4W vs LY. A ratio near threshold is ambiguous; absolute dollars are not. No additional query needed — just the math. |
| **1/2. Clicks/Impr ↓** | Clicks and revenue diverge >20pp (e.g., clicks -50%, rev +20%) | Standard data has L4W/LY totals | **First: check if Oct 2025 consolidation explains the gap** — fewer campaigns = less double-counting = fewer GAds conversions but same BQ orders. Compare BQ orders YoY (stable baseline) vs GAds conversions YoY (inflated LY). If BQ orders are stable/up, the "click decline" is a measurement artifact. **Only fire E4** if BQ orders also declined. |
| **5. CVR ↓** | Funnel stage drops >5pp YoY AND >2pp MoM | Standard data has L4W, Prior4W, LY funnel | No additional query — the 3 windows are enough. Flag as **URGENT/accelerating** in the report if MoM decline >2pp. The temporal signal is in the data; the escalation is in urgency, not data. |
| **10. Coverage** | Campaign/geo data disagree >30pp | Q5 geo + campaign cohort table | No additional query — flag and **explain the data source difference**. Campaign counts clicks regardless of user location; geographic_view counts by user country. The gap itself IS the finding. |
| **9. Channel** | Non-paid channel dropped >50% | BQ channel breakdown | No additional query — but **test the attribution hypothesis**: check if organic + non-paid combined is stable vs LY. If sum is stable, it's attribution shift, not actual decline. The math is in the channel table. |
| **11. Temporal** | L4W and Prior4W both down vs LY (ongoing) | Standard 3 windows | **E5: Monthly metric trend** (L12M, same as E1/E2 pattern) — for whichever metric is declining. An ongoing decline needs the full trajectory to diagnose structural vs competitive vs seasonal. |

### Escalation query templates

**E1/E2/E5: Monthly trend (L12M) — generic pattern, adapt columns per tree:**
```sql
SELECT campaign.name, segments.month,
  metrics.search_impression_share,       -- E1: SIS
  metrics.search_rank_lost_impression_share,
  metrics.clicks, metrics.impressions,
  metrics.cost_micros,                   -- E2: CPC = cost/clicks
  metrics.conversions, metrics.conversions_value  -- E4/E5: conv + AOV
FROM campaign
WHERE campaign.name LIKE '%CE_NAME%LANGUAGE%'
  AND campaign.status = 'ENABLED'
  AND segments.date BETWEEN 'L12M_START' AND 'L4W_END'
ORDER BY segments.month ASC
```
Select only the columns needed for the specific escalation. Don't pull everything — large result sets slow the analysis.

**E3: Absolute CM1 (no query — derived):**
```
L4W CM1 = L4W_ROI × L4W_Spend
LY CM1 = LY_ROI × LY_Spend
Δ CM1 = L4W CM1 - LY CM1
```
Show in report: "EN ROI 147% on $12.5K spend = $6.1K CM1. LY: ~139% on $6.9K = $2.7K CM1. CM1 doubled (+$3.4K) — the ratio is marginal but the absolute gain is real."

### When NOT to escalate

- CE is HEALTHY (0-1 red flags) → skip all escalations, write SHORT report
- Metric movement is <10pp / <20% → standard 3 windows are sufficient
- Data is already in the standard pull → derive, don't re-query
- Escalation would add >2 additional GAQL calls → cap at 2 escalations per audit to avoid context bloat. Prioritize by $ impact of the tree branch.
