# Cascading Hypothesis Tree — Paid Audit v6

For each metric signal, walk the tree top-down. Test each hypothesis with its data cut. The first confirmed hypothesis is primary; continue checking remaining branches for secondary/compounding causes. In the report output, show the reasoning naturally (hypothesis → check → result) WITHOUT referencing this file or hypothesis IDs.

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

## 4. CPC ↑ (3-lens tree + internal check)

Walk in order. Stop at the first confirmed lens for primary cause, but check remaining for secondary.

**Lens 1: Quality traffic (good CPC)**
- Check: CVR rose alongside CPC. RPC/CPC ratio healthy (>1.5x).
- Confirmed if: CVR above market median AND RPC > CPC
- Meaning: Google is optimizing for converting clicks at higher cost. This is GOOD.
- Action: Accept the premium. Monitor RPC/CPC ratio.

**Lens 2: AOV structural**
- Check: AOV / ticket price L4W vs LY. Did product pricing increase?
- Confirmed if: AOV up >10% and CPC up proportionally
- Meaning: Everyone bids more when the prize is bigger. Structural, not fixable.
- Action: Note as context. Adjust ROI expectations.

**Lens 3: Competition**
- Check: top-of-page % dropped AND/OR auction insights show competitor IS up AND/OR search partner mix changed
- Confirmed if: at least 2 of 3 evidence types present. NEVER say "competition" with only CPC data.
- Evidence sources: position data (Q1), auction insights (CSV), search partner mix (Q4)
- Action: If RPC still > CPC → accept. If RPC < CPC → find lower-competition segments (Bing, OL, long-tail).

**Lens 4: Internal bid change**
- Check: tROAS or bid strategy changed in last 14d (change_event log, Q7)
- Confirmed if: strategy changed AND CPC moved within 14d of change
- Action: If in learning period (<14d) → defer judgment. If post-learning → evaluate if new bids are profitable.

---

## 5. CVR ↓ (paid audit scope — funnel level)

The paid audit detects and sizes funnel leaks, rules out traffic quality as the cause, and routes to Product. Don't diagnose LP content, pricing, or availability — that's Product's scope.

**LP2S dropped (landing page → selection)**
- Check: Mixpanel funnel, filtered to paid channel
- Possible causes: LP content/UX change, availability display, pricing visibility, traffic quality shift
- **Before routing to Product, rule out the paid-side cause:**
  - Check traffic quality indicators: top-of-page % (Q1), informational term share (6a), CVR trend
  - If traffic quality improved (higher top-of-page %, fewer informational clicks, CVR up) BUT LP2S worsened → LP is confirmed. The argument: "better traffic should convert better at every funnel stage; if it doesn't, the stage itself degraded."
  - If traffic quality degraded (more search partner clicks, informational share grew) → funnel drop may be traffic mix, not LP. Investigate search term shift before routing.
- Action: Route to Product WITH the traffic-quality argument. Size the leak: sessions lost × historical CVR × AOV.

**S2C dropped (selection → cart)**
- Check: Mixpanel funnel
- Possible causes: pricing change, variant availability gaps, merchandising changes
- Action: Route to Product/Supply. Check `/availability-diagnostics` for inventory gaps.

**C2O dropped (cart → order)**
- Check: Mixpanel funnel
- Possible causes: checkout UX, payment failures, booking fee changes
- Action: Route to Tech/Product.

**Blended CVR down but largest cohort CVR stable**
- Check: filter funnel to Google Search English only. Compare blended vs filtered.
- Confirmed if: blended down but largest cohort stable = dormant/low-CVR cohorts diluting
- Meaning: Not a conversion problem — it's a traffic mix problem (coverage issue).
- Action: Don't fix CVR. Fix coverage (dormant cohorts).

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
- Sub-causes:
  - Budget was cut → Check: change_event log for budget reduction
  - CPC inflation consumed budget → Check: CPC trending up + budget constant
- Action: Raise budget on high-ROI campaigns. Redistribute from low-ROI groups.

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

## 8. Spend ↓ (without intentional cut)

**Bid strategy self-suppressing**
- Check: tROAS too high + clicks declining + ROI improving
- Confirmed if: spend/budget ratio dropping over time
- Action: Lower tROAS. Same pattern as dormancy.

**Budget was cut**
- Check: Q7 budget amount, change_event log
- Confirmed if: budget_amount decreased >20% in last 30d
- Action: Verify if intentional. Restore if drift.

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
