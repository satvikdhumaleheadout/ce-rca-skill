# CVR-RCA Actions Reference

Use this file when writing the report (Step 3). Once a root cause has been confirmed by data, find the matching category below and use the listed actions to populate the action cards. Assign the DRI type that matches the confirmed finding.

Actions are drawn from historical Headout RCAs across 21 MMPs and the CVR Cause-to-Action Playbook. Where a historical case exists, it is cited inline.

---

## Root Cause 1: Pricing misalignment vs. competition

**Signal:** HO listed price is materially above GYG, Viator, or direct-booking price for comparable product. Users see price on LP and do not click through (LP2S drop), or see price shock at variant level (S2C drop).

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Match GYG/Viator pricing on the specific competitive SKU(s) — identify exact price gap from `price_analysis` | BDM / Growth | P1 |
| For a structured per-TGID price comparison (Headout vs GYG/Klook/Viator), trigger the **competitive intel skill** — particularly when S2C is the affected step and the drop is concentrated on specific experiences | Growth / Analytics | P1 |
| Include all mandatory fees (helipad, facility, transfer, booking) in the displayed LP price — no surprises at checkout | Ops / Product | P1 |
| Raise ILFs (Inventory Level Fees) to improve bidding competitiveness without full price reduction | BDM | P2 |
| Negotiate better net rates with SP to restore margin after price match | BDM | P2 |
| Surface promotional or discounted pricing where SP allows — if competitor has a discount badge on LP and HO does not, this directly suppresses LP2S | BDM / Growth | P2 |
| Evaluate restructuring to LP price + booking fee to lower the displayed anchor price on the listing page | Product / BDM | P3 |
| Set up weekly competitive pricing monitoring for this CE | Analytics / Growth | P3 |

**Historical reference:** Blue Mountains — GYG discount matching required to maintain LP2S; Alcatraz — competitor pricing advantage from black-market alternative at 77% impression share ($55 black-market vs $97 HO); NY Helicopter — helipad fee inclusion removed price shock at checkout; Edge NYC — price parity with GYG restored after Galaxy→Ventrata transition added $2 platform fee.

---

## Root Cause 2: Inventory / availability constraint

**Signal:** Ticket counts in one or more lead-time buckets from the `inventory_availability` TID summary table near zero in post period, or `days_to_first_available_date` (from `product_rankings_features`) increased significantly. S2C drop concentrated on specific experiences or across the CE.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Review and fix API cut-off period settings with SP — shorten minimum lead time to unlock same-day/next-day bookings | Ops / BDM | P1 |
| Review release window settings — ensure future inventory is visible sufficiently in advance | Ops | P1 |
| Negotiate next-day and same-day release windows directly with SP | BDM | P1 |
| Bucket availability by lead-time (0-2D, 2-4D, 4-7D, >7D) — if the CE has >40% last-minute bookings and 0-2D availability is thin, this is the primary S2C lever; escalate to SP immediately; trigger the **inventory skill** for a structured lead-time bucket breakdown | Ops / BDM | P1 |
| Audit assortment for missing high-demand variants that exist on GYG/SP website but not on HO — source and add them | BDM / Growth | P1 |
| Add additional SPs to reduce single-vendor dependency — multivendor setup for the key experience | BDM / Growth | P2 |
| Switch primary SP to a higher-availability alternative if current SP is structurally constrained | Growth / BDM | P2 |
| Check non-English supply gaps — do we have guided tours available for each language that paid campaigns are targeting? Missing language supply = direct S2C loss for OL traffic | BDM / Ops | P2 |
| Consider pre-purchasing inventory blocks for peak dates if same-day supply is structurally thin and SP allows it | BDM | P3 |
| Set up inventory alerts for availability drop below threshold for this CE | Ops / Analytics | P3 |

**Historical reference:** Blue Mountains — FJ Tours, Diamond Tours, Brighton Tours API cut-off periods preventing next-day bookings; NY Helicopter — HeliNY last-minute gaps; Summit One Vanderbilt — SP throttling to 3 slots on days that should have 25, confirmed by checking CTrip API independently; Colosseum — TGID 7148 (Glass Elevator) disabled but has next-day B2C inventory; USJ — multi-DMC setup for Studio Pass + Express Pass coverage.

---

## Root Cause 3: UX / listing page / MB format friction

**Signal:** LP2S or S2C drop coinciding with a deploy date. Often device-concentrated (mobile mweb). Users are landing or reaching the select page but abandoning before the natural next step, not because of price or availability.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Revert to previous MB/LP format if new format shows statistically significant CVR regression — do not wait for full A/B test if the drop is large and sudden | Product | P1 |
| Reduce decision steps in product selection flow — consolidate variants where possible, push the most popular option to default | Product | P1 |
| Improve product content with key decision-making details: dates/times, durations, what's included/excluded, venue name, seating, meeting point | Content | P2 |
| Add clear differentiation signals on listing: best-price badge, unique-to-HO label, combo value callout | Merchandising | P2 |
| Create venue/experience-specific landing pages for high-volume keyword clusters to reduce decision load on collection pages | Growth / Content | P3 |
| Audit the mobile checkout flow end-to-end on iOS Safari and Android Chrome for regressions after any deploy | Product / Engineering | P1 (if device-concentrated) |

**Historical reference:** Vienna concerts — new Live Entertainment MB format cut LP2S ~50% by adding an extra venue-selection step before date selection; revert at end of September restored CVR to prior levels.

---

## Root Cause 4: Product ranking / assortment structure

**Signal:** Experience-level CVR breakdown shows top-ranked product has materially lower LP2S or S2C than alternatives. Or CE has a structural mix issue — all traffic concentrates on one product that underperforms.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Fix ranking model at child collection level — separate product categories (e.g., HOHO vs BM Tours vs Scenic World) into independent ranking pools so each category can surface its own best product | Growth / Analytics | P1 |
| Rerank products based on revenue-per-click or orders-per-select, not just click volume | Growth | P1 |
| Promote the highest-CVR, highest-availability product to the top slot — run as a 2-week pre/post experiment if uncertain | Growth | P1 |
| Remove or demote low-CVR, low-availability products from top 3 positions | Growth | P2 |
| Remove low-performing cross-sells from the CE's LP if they dilute focus from the core product — measure Rev/Click before and after | Growth | P2 |
| Create combo/bundle TGIDs for high-value combinations (e.g., base ticket + express pass, HOHO + attraction entry) to lift AOV and CVR | Product / Ops | P2 |
| Add missing high-performing products to CE assortment | BDM / Growth | P2 |
| Merge duplicate or near-identical TGIDs that are splitting traffic and diluting select-page clarity | Product | P3 |

**Historical reference:** Blue Mountains — separate ranking models needed for BM Tours, HOHO, and Scenic World independently; Alcatraz — 99% of clicks on 1 product at 9% take rate; Chicago Cruise — separate TGID strategy per cruise type; AMNH Mini MMP — explicit re-ranking of all TGIDs by Rev/Click; OWO — removed Edge NYC cross-sell from OWO LP after it was diluting focus ("66% revenue from 1st TGID").

---

## Root Cause 5: Vendor / SP operational issue

**Signal:** Completion rate (CR%) drop for a specific SP, fulfillment failures, or TGID configuration errors. Often surfaces as C2O drop or as sharp S2C decline on specific experiences.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Investigate and fix TGID reference errors in customer communications — verify booking confirmation emails reference the correct product and experience date | Ops | P1 |
| Put underperforming vendor in manual fulfillment (FF) mode temporarily while investigating root cause | Ops | P1 |
| Verify rate sheets and pricing alignment — confirm displayed price matches what SP will honour at fulfilment | BDM | P1 |
| Escalate CR% issues directly with vendor — set a minimum acceptable CR% with a recovery timeline | BDM | P1 |
| Switch primary SP designation to the highest-CR% alternative for this CE | Growth / BDM | P2 |
| Establish weekly operational standups with SP to catch fulfillment issues before they show up in data | BDM | P2 |
| Review and standardise lead-time and release settings across all SPs for this CE | Ops | P2 |

**Historical reference:** NY Helicopter — Charm Aviation required manual FF mode; critical TGID error in customer comms (30-min booking, 15-min TGID in confirmation) drove cancellations; HeliNY rate sheet discrepancy.

---

## Root Cause 6: Campaign / traffic quality issue

**Signal:** MB/HO mix shift dominant, or channel mix shift dominant, or LP2S drop concentrated in a specific language that aligns with a campaign change. Traffic volume held but intent composition changed.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Audit LP routing: verify all campaigns — especially non-English language variants — point to the correct landing page for this CE | Performance Marketing | P1 |
| Investigate if campaign scale-down was intentional (budget reallocation) or accidental (policy issue, billing lapse) | Performance Marketing / Growth | P1 |
| Restore paused campaigns for high-ROI segments (e.g., Bing historically at 100–120% ROI for NY Helicopter) | Performance Marketing | P1 |
| Audit campaign geo restrictions — if an SP-imposed geo restriction is in place, quantify the revenue foregone before accepting it; evaluate off-hours or pincode-level workarounds | Performance Marketing / Growth | P1 |
| Run a negative keyword audit on search term reports — cut irrelevant search terms bringing low-intent traffic; restructure ad groups by intent cluster | Performance Marketing | P2 |
| Check OL campaign ad strength scores — poor ad strength (majority of ads rated "Poor") reduces CTR and brings lower-quality traffic; rewrite flagged ad copies | Performance Marketing | P2 |
| Add venue/experience-specific keywords to align ad intent with landing page content | Performance Marketing | P2 |
| Consolidate fragmented campaigns to improve quality scores and bidding efficiency | Performance Marketing | P2 |
| Scale Bing campaigns if Google SIS is capped and Bing ROI is positive | Performance Marketing | P2 |
| Review CPA targets for underperforming language/geo segments and adjust bids | Performance Marketing | P3 |
| Test new ad copy variants with sitelinks and experience-specific extensions | Performance Marketing | P3 |

**Historical reference:** NY Helicopter — 75% drop in English campaign clicks in Jan 2026 drove CVR collapse via mix; language campaigns pointing to old SF LP; Blue Mountains — SIS cap; Edge NYC — EN-NY campaign paused after SP flagged it, cost ~$50K/month; "flouted" in Apr-25 for 12 days generated $50K revenue; 9 of 16 Spanish OL ads rated poor ad strength, suppressing CTR; Alcatraz — OL campaign had US excluded, missing ~10% of keyword SVs.

---

## Root Cause 7: Take rate / margin issue

**Signal:** Revenue dropped despite stable CVR and orders. Take rate per order has declined — either vendor mix shifted to lower-TR SPs, or TR was renegotiated downward.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Negotiate TR improvement with SP — present revenue volume data to support case for higher commission | BDM | P1 |
| Shift traffic toward higher-TR products via ranking adjustments — demote low-TR products from top slots | Growth | P2 |
| Create premium or combo variants with better margin profile (e.g., combo of two products at blended higher TR) | Product / BDM | P2 |
| Explore white-label product setup for this CE to improve commission control | BDM / Product | P3 |
| Review vendor mix distribution — if lower-TR SP gained share, investigate whether this was intentional or a ranking artefact | Growth / Analytics | P2 |

**Historical reference:** Vienna concerts — Karlskirche TR improvement target from 25% to 30%; Alcatraz — GA ticket at 0% commission vs Pintours at higher TR, with Option D (20% commission negotiation) as most desirable but least likely; Harder Kulm — funicular at only 9% take rate.

---

## Root Cause 8: Checkout friction — C2A drop (users abandoning before submitting payment)

**Signal:** C2A sub-metric specifically dropped while A2O held. Users reached checkout but did not submit payment.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| For structured diagnosis of custom field count, pax type configuration, and booking fee impact on C2A, trigger the **pax setup skill** | Product / Ops | P1 |
| Audit checkout form for new friction: added required fields, removed autofill, broken promo code validation | Product | P1 |
| Verify all fees are fully transparent before checkout — no price additions appearing for the first time at the payment step | Product / Ops | P1 |
| Verify customer communication TGIDs are correct — users clicking through booking emails must land on exactly the experience they booked | Ops | P1 |
| Audit custom fields at checkout — count required fields per booking; check if DOB, age, or passport fields can be hardcoded or removed; convert free-text fields to dropdowns where possible | Product / Ops | P1 |
| Audit pax type setup — simplify confusing pax configurations; fix pricing mismatches between pax types; use primary pax where multi-pax adds no value | Ops / Product | P2 |
| Evaluate removing the booking fee if TR has improved enough to absorb it — test removal during peak season first | BDM / Product | P2 |
| Check if the promo code field is causing abandonment — users may be leaving checkout to search for discount codes; consider hiding behind a "have a code?" link instead of showing by default | Product | P2 |
| Confirm trust signals are present in checkout: review count visible, free cancellation policy highlighted, payment security badge shown | Product | P2 |
| Test full checkout flow on iOS Safari and Android Chrome mweb for regressions | Product / Engineering | P1 (if mobile-concentrated) |

**Historical reference:** NY Helicopter — helipad fees not included in LP display price created price shock at checkout; TGID reference error in customer comms caused cancellations; Colosseum — DOB field at checkout raised with IO for removal ("we have Adult 18+ as a pax descriptor, DOB redundant"); SD Zoo — C2O at 21.3% (benchmark 35.1%) driven by booking fee + fraud; booking fee removal planned when TR hits 18%.

---

## Root Cause 9: Payment failure — A2O drop (payment submitted but order failed)

**Signal:** A2O sub-metric specifically dropped. Users submitted payment but the order did not complete.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| Check payment gateway error logs for the affected period — identify specific failure codes and affected card types / geographies | Payments / Engineering | P1 |
| For a detailed A2O breakdown, investigate `order_attempted_events_v2` — key columns: `payment_gateway`, `payment_method`, `fraud_evaluation_result_origin` (Watson / Sift / Bond), `failure_reason`. Break down by each dimension to isolate whether gateway failure, live inventory failure, or fraud over-blocking is dominant. *(Automated query support in development — manual BQ query in the interim)* | Payments / Engineering | P1 |
| **When the A2O locus is confirmed but the specific mechanism is unresolved (DATA GAP — `order_attempted_events_v2` not queried during investigation):** use this action card template — *"DATA GAP — payment failure mechanism untested. Run `order_attempted_events_v2` for experience [ID] between [post_start] and [post_end]: break `failure_reason` by `payment_gateway` and `fraud_evaluation_result_origin`. If `failure_reason` shows 'inventory_unavailable' spiking → escalate to Ops/Engineering for API sync. If dominated by payment decline codes → escalate to Payments for gateway review. If fraud block rate increased → escalate to Payments for rule audit."* This template ensures the DRI receives a specific starting hypothesis, not generic "investigate further" text. | Payments / Engineering | P1 |
| Investigate live inventory failure — if the availability slot sold out between checkout start and payment completion (API sync latency), the order fails at fulfilment; check with the SP and escalate to the API provider | Ops / Engineering | P1 |
| Review fraud rule changes deployed around the onset date — assess if rules are over-blocking legitimate bookings; check CE-specific fraud block rate | Payments | P1 |
| Pre-register new TGIDs with the fraud team before launch — prevents over-blocking on products the fraud system hasn't seen before | Ops / Payments | P1 (on new TGID launch) |
| Verify currency display and FX conversion is correct at the payment step for all active currencies | Payments / Engineering | P1 |
| If a new payment method was launched around the onset date, isolate whether it introduced a regression in existing payment flows | Payments / Engineering | P2 |

**Historical reference:** SD Zoo — 6% bookings cancelled due to fraud over-blocking; fulfilment improved to 90% after escalating over-cancellation issue to Bond (API provider); OWO — Ingresso API availability going on/off caused orders to fail at fulfilment, mostly undetected until revenue monitoring flagged it.

---

## Root Cause 10: Content & media quality

**Signal:** LP2S or S2C declining gradually with no pricing or availability change. Product content audit reveals missing key information, generic descriptions, poor images, or reused photos across variants. Often gradual drift, not sudden onset.

**Actions:**

| Action | DRI | Priority |
|--------|-----|----------|
| For a structured content audit across TGIDs (descriptions, highlights, media count, FAQ, SEO metadata), trigger the **content audit sub-skill** | Content | P1 |
| Audit experience names for each top TGID — surface key differentiators in the name itself (e.g., "with Guided Bus Tour and Skyfari Aerial Tram", "Small Group, Early Morning") rather than burying them in descriptions | Content | P1 |
| Review highlights and inclusions per TGID — ensure core selling points are explicitly stated; do not rely on users reading long descriptions | Content | P1 |
| Check image count and quality for top TGIDs — minimum 3 images per product; ensure at least one image shows people experiencing the product; avoid reusing the same photo across related variants | Content / Media | P2 |
| Add video where available — video on listing page improves engagement and click-through, especially for experiential products | Content / Media | P2 |
| Create PDF pop-ups or inline callout cards for variants that include multiple exhibition types or access tiers, so users understand what they are selecting | Product / Content | P2 |
| Refresh LFC (Listing Feature Content) and shoulder pages for MB microsites — stale LFC hurts organic rank and LP quality; update metadata, revamp product content for relevant subfolder pages | Content / SEO | P2 |
| Consider a dedicated MB microsite (C1 domain) for high-competition categories where a branded domain would improve CTR against established competitors | Growth | P3 |

**Historical reference:** Colosseum — full per-TGID content and media task list with variant-level content changes, localization checks, and image sourcing from video team; AMNH — PDF pop-up added per exhibition variant; SD Zoo — experience name updated to include "with Guided Bus Tour and Skyfari Aerial Tram"; Edge NYC — photo reuse across variants flagged as a quality issue in product audit; Alcatraz — C1 domain (san-francisco-cruises.com) evaluated to compete against black-market players dominating organic results.

---

## Root Cause 11: Catalogue change (TGID launched, disabled, or restructured)

**Signal:** Experience-level breakdown shows a top experience whose checkout volume changed substantially pre vs post (≥20% relative or accounting for ≥10% of net CE-level move). `dim_experience_management` query confirms a TGID's `first_active_at` falls inside the analysis window, or a TGID flipped to/from `variant_status = 'Disabled'` mid-window. May be paired with an MB assortment cap or product restructure called out in Slack.

This pattern is bidirectional. A TGID launch can cannibalise higher-CVR variants (decline) or absorb traffic into a higher-CVR variant (improvement); a TGID disablement can remove high-converting demand (decline) or remove low-CVR variants that were diluting the catalogue (improvement). The action depends on direction and the relative CVR of the changed variant vs siblings.

**Actions (decline direction — TGID cannibalises or disappears):**

| Action | DRI | Priority |
|--------|-----|----------|
| Restore the higher-CVR sibling TGID's ranking position if a new variant has displaced it — explicit re-ranking via `dim_experience_management` ordering or merchandising override | Growth / Merchandising | P1 |
| Investigate why the high-CVR TGID was disabled — confirm with BDM/Ops whether the disable was intentional (vendor issue, content gap) or accidental (a routine update flipped status). Restore if accidental. | BDM / Ops | P1 |
| If the new launching TGID has lower native C2O, demote it from top-of-listing until either its CVR improves or it's repositioned as a niche option | Growth | P2 |
| Add the missing high-demand variant configurations (pax types, time slots, languages) that may have been lost in a TGID consolidation | Ops / BDM | P2 |

**Actions (improvement direction — TGID launched well or restructure landed):**

| Action | DRI | Priority |
|--------|-----|----------|
| **Protect** — keep the launching TGID in its current top-of-listing position; confirm with SP that inventory holds for the projected peak; quantify the incremental CVR contribution to support sustained investment | Growth / Merchandising + BDM | P2 |
| If an MB assortment cap drove the lift, document the kept-vs-cut set so future MB assortment edits don't accidentally revert it | Growth | P2 |
| Audit content/title updates that landed during the window — surface the specific changes so they can be replicated on other low-CVR TGIDs in adjacent CEs | Content / Growth | P3 |
| Pre-register the new TGID with the fraud team if not done yet — prevents A2O over-blocking once volume grows further | Ops / Payments | P2 |

**Historical reference:** CE 1223 Pompeii (May 2026) — new Skip-the-line Guided Tour with Archaeologist (TGID 25518) more than doubled checkout volume; MB assortment cap to 8 products on May 7 concentrated traffic onto higher-CVR TGIDs; combined catalogue restructure explained part of the +0.23pp structural CVR delta.

---

## Improvement direction — action templates

CVR-improvement RCAs produce inherently softer actions than declines (no broken thing to fix). The action card *structure* in the report stays identical (priority badge, cause, DRI, bullet list — see `report_structure.md → Section 2`), but each card falls into one of three templates. Use this section as the action library when populating cards for an improvement-direction confirmed root cause.

These templates are not mutually exclusive — a single improvement RCA can produce one Protect, one Extend, and one Investigate-headwind. Maximum three cards still applies. If only one type fits the finding, one card is correct — do not pad.

### Protect

**Use when:** a confirmed mechanism is driving the lift and could regress if neglected (a ranking position, an inventory window, a content state, a budget allocation).

**The card must name** the specific TGID / URL / supply window / campaign carrying the gain AND the operational lever supporting it. "Protect TGID X" alone is not actionable.

| Action | DRI | Priority |
|--------|-----|----------|
| Lock the top TGID's listing position via explicit merchandising override or ranking pin until next quarterly review | Growth / Merchandising | P2 |
| Confirm with SP that same-day inventory holds for the next 60 days at minimum — quantify and document the inventory commitment | BDM / Ops | P2 |
| Document the operational state that drove the gain (MB assortment cap configuration, current content state, current pricing/promo levers) so a future edit doesn't unintentionally revert it | Growth / Ops | P3 |
| If a specific pricing lever drove the lift (last-minute discount, promo code, fee reduction), formalise it — turn the temporary lever into a standing offer if the margin allows | BDM / Growth | P2 |

### Extend

**Use when:** a confirmed segment grew at favourable CVR and there is headroom to grow it further (a paid channel improved CVR, a geo surged in volume, a new TGID launched well).

**The card must name** the segment, the headroom signal (what the data showed), and a specific next move (budget reallocation, campaign expansion, supply commitment).

| Action | DRI | Priority |
|--------|-----|----------|
| Scale paid budget on the gaining channel proportional to its CVR uplift — quantify the incremental budget headroom against CPA targets | Performance Marketing | P2 |
| Expand the gaining geo segment — add language-specific creative variants, increase market-level bids, or add a market-specific landing page | Performance Marketing / Growth | P2 |
| Negotiate higher inventory commitment with the SP for the gaining experience — use the volume + CVR data as the case | BDM | P2 |
| Replicate the structural change (content update, fee transparency, MB assortment discipline) across adjacent CEs in the same market or category | Growth / Content | P3 |

### Investigate-headwind

**Use when:** a small headwind is forming under the lift (HO dilution, channel mix drift, supplier softness) — not material enough to be the headline but worth flagging before it compounds.

**The card must propose the specific next query** the DRI should run, not just the team to ask. The improvement-case investigate-headwind action stays testable.

| Action | DRI | Priority |
|--------|-----|----------|
| Run the funnel breakdown for the diluting segment (HO, organic, specific channel) with `previous_page_url` and `channel_name` cuts to surface the new entry points behind the volume growth — share the query as part of the card | Performance Marketing / Analytics | P2 |
| If channel mix is drifting toward lower-intent traffic, audit campaign keyword intent and landing-page match for the gaining channel before the next budget cycle | Performance Marketing | P2 |
| Tag the next 30-day review with explicit thresholds — at what CVR or LP2S level on the diluting segment would action become urgent? | Performance Marketing / Growth | P3 |

---

## Slack-corroboration upgrade on decline actions

When a decline action card is going to a DRI for execution AND a Slack thread confirms the same mechanism that the data confirmed (Pattern A in `hypothesis.md → "Slack signal classification"`), elevate the inline citation on the Section 3 verdict subtext from a bare `(corroborated ↗)` to a named source `(per [Author · date] ↗)`. This moves the finding from "we measured it" to "we measured it AND the BDM/Supply/Marketing team has independent corroboration" — directly strengthens stakeholder confidence in the P1/P2 action. Apply once per finding, not stacked across multiple subtexts.

This is a styling rule, but the action library benefits from the elevated trust signal — DRIs are more likely to act on a card whose evidence cites both internal data AND an independent corroboration from the team that would normally own the diagnosis.

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c001 | 2026-04-24 | Initial version — 10 root causes drawn from 21 historical Headout MMPs and CVR Cause-to-Action Playbook |
| c002 | 2026-04-24 | RC1: added competitive intel skill pointer (P1, S2C context). RC2: added inventory skill pointer to lead-time bucket action. RC8: added pax setup skill pointer (P1). RC9: added `order_attempted_events_v2` column detail with note that automated query support is in development. RC10: added content audit sub-skill pointer (P1) |
| c003 | 2026-05-06 | RC2 signal updated: replaced `count_days_available_30d` (unreliable proxy) with ticket counts in lead-time buckets from `inventory_availability` TID summary table as the primary signal for inventory constraint root cause. |
| c004 | 2026-05-14 | RC9 — added DATA GAP action template for when the A2O locus is confirmed but the specific mechanism is unresolved because `order_attempted_events_v2` was not queried (backlogged). Template provides a specific BQ query scope and three sub-hypotheses for the DRI to test (inventory sync failure, gateway decline, fraud over-blocking), so the action card delivers a starting hypothesis rather than generic "investigate further" text. |
| c005 | 2026-05-22 | Bidirectional support added. **(1) Root Cause 11: Catalogue change** — new bidirectional root cause covering TGID launch, disablement, and restructure events. Decline actions: restore high-CVR sibling ranking, investigate accidental disablement, demote low-CVR new launches. Improvement actions: protect the launching TGID, document the operational state that drove the gain, pre-register with fraud. Historical reference: CE 1223 Pompeii. **(2) "Improvement direction — action templates"** — three sub-templates for improvement-case action cards: **Protect** (lock the lever supporting the gain), **Extend** (scale the gaining segment), **Investigate-headwind** (propose the specific next query for small dilution signals). Each template lists 3–4 starter actions with DRIs and priorities. Templates are mutually compatible — a single RCA can produce one of each. **(3) Slack-corroboration upgrade on decline actions** — codifies the rule that Pattern A corroboration on a DRI-bound decline action card elevates the citation from `(corroborated ↗)` to `(per Author · date ↗)`. Increases stakeholder trust in P1/P2 actions. |
