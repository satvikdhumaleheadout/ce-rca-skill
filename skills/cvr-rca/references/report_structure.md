# CVR-RCA Report Structure

Read `visual_kit.md` first for CSS, HTML patterns, and styling rules. This file describes the **CVR-RCA-specific** report structure on top of those primitives: the fixed three-section macro-structure (Section 1/2/3), the "What belongs in Section 3" table, and the CVR-RCA-specific HTML patterns (Mix cascade analysis block, Fixed Segment banner, Geo / Non-Geo overview, External Signals block, Shapley decomposition flex bar, URL-level breakdown, Inventory section format, Ruled-out dimensions, Hypotheses explored, Report length calibration).

**The principle:** By the time the GM finishes reading Section 2, they know exactly what happened and what to do. Section 3 is for anyone who needs to verify the conclusion. The analysis is not the report — the analysis is the evidence behind the report.

**Pre-write sanity check.** Before writing HTML, verify three items that are the most-often-dropped spec elements regardless of which CE you're analysing:

- **Header** carries the four meta spans — 📅 pre, 📅 post, 🌍 market, 🔗 landing-page URL (per Page Skeleton in `visual_kit.md`).
- **Dashboards row** carries the Omni link (CE ID always substituted; the analysis dates are substituted too when the RCA used a custom window) per "Header — CVR-RCA-specific extensions" below.
- **↗ arrows** are present after every numeric or named-finding claim cluster in the Section 1 callout, and after each Section 2 action card's cause line (per "↗ link-to-table pattern" in `visual_kit.md`).

These are universal to every CVR-RCA report. Other spec items (verdict lines, named TGIDs, source-table accuracy) are story-specific and handled in their respective sections.

---

## Header — CVR-RCA-specific extensions

The header chrome (eyebrow, h1, meta row, dashboards row container) is defined in `visual_kit.md → Page skeleton`. This section defines the CVR-RCA-specific content that fills the dashboards row.

### Dashboards row — Omni

Every CVR-RCA report header carries a `.dashboards` row beneath the meta line with a pill-button link scoped to the CE. The CSS chrome (`.dashboards`, `.dash-label`, `.dash-link`) lives in `visual_kit.md`; the URL template is defined here.

**Omni Analytics dashboard.** The URL carries two filters: a CE filter
(`f--iv8lWOuS`) and a date filter (`f--uvd3KWWJ`). Always substitute the CE ID.
The date filter depends on whether the RCA used the **default** window or a
**custom** one:

- **Default window** (the user did not pass a date range — the run defaulted to
  last 30 vs prior 30 days): use Omni's **relative** date params
  (`30 complete days ago` / `30 days`). This lets the Omni dashboard apply its own
  built-in last-30-vs-prior-30 comparison — the link tracks "now" rather than
  pinning to the RCA's computed dates.
- **Custom window** (the user passed a specific date range): pass the RCA's
  **post (analysis) window** as an absolute `BETWEEN` filter, so the Omni link
  shows exactly the period the RCA is about.

**Default-window URL** (URL-encoded — copy verbatim; only substitute `<CE_ID>`):

```
https://headout.omniapp.co/dashboards/5368ab53?f--iv8lWOuS=%7B%22values%22%3A%5B%22<CE_ID>%22%5D%7D&f--uvd3KWWJ=%7B%22left_side%22%3A%2230+complete+days+ago%22%2C%22right_side%22%3A%2230+days%22%7D
```

**Custom-window URL** (URL-encoded; substitute `<CE_ID>`, `<POST_START>`,
`<POST_END_EXCLUSIVE>`):

```
https://headout.omniapp.co/dashboards/5368ab53?f--iv8lWOuS=%7B%22values%22%3A%5B%22<CE_ID>%22%5D%7D&f--uvd3KWWJ=%7B%22kind%22%3A%22BETWEEN%22%2C%22left_side%22%3A%22<POST_START>%22%2C%22right_side%22%3A%22<POST_END_EXCLUSIVE>%22%2C%22ui_type%22%3A%22BETWEEN%22%2C%22offset_interval_string%22%3Anull%7D
```

Substitutions:
- `<CE_ID>` → the CE ID as a string (e.g., `243`, `3593`).
- `<POST_START>` → the post-window start date, `YYYY-MM-DD` (e.g., `2026-06-02`).
- `<POST_END_EXCLUSIVE>` → the post-window end date **plus one day**, `YYYY-MM-DD`.
  Omni's `BETWEEN` upper bound is **exclusive**: a window of 2–12 Jun 2026 is
  encoded as `left_side=2026-06-02`, `right_side=2026-06-13`. So compute
  `right_side = post_end + 1 day`. (The decoded date filter is
  `{"kind":"BETWEEN","left_side":"<POST_START>","right_side":"<POST_END_EXCLUSIVE>","ui_type":"BETWEEN","offset_interval_string":null}`.)

The dashboard ID (`5368ab53`) and the two filter keys (`f--iv8lWOuS`,
`f--uvd3KWWJ`) are constant. Use the post window (not the pre window, and not the
full pre→post span) — the Omni dashboard runs its own prior-period comparison off
whatever window it's given, mirroring the default last-30-vs-prior-30 behavior.

**HTML emitted in the report header** (replaces the placeholder `<div class="dashboards">` block shown in `visual_kit.md → Page skeleton`):

```html
<div class="dashboards">
  <span class="dash-label">DASHBOARDS</span>
  <a href="[Omni URL with CE_ID substituted]" target="_blank" class="dash-link">Omni ↗</a>
</div>
```

Render the Omni link on every CVR-RCA report — the row itself is unconditional. The only branch is *which* date filter goes in the URL (default relative vs custom `BETWEEN`, per the two templates above). If a future RCA targets a CE that doesn't have Omni coverage, the link still resolves (the dashboard will just show empty state), which is acceptable.

---

## Section 1 — Executive Summary

**Purpose:** The GM reads this in under 60 seconds and understands the full picture. Nothing in this section requires interpretation.

### 1a. Metric cards (always — all five)

Five cards in this order: **Site CVR · LP2S · S2C · C2O · LP Users**

(Canonical names — see ce-rca `references/metric_glossary.md`. **"Site CVR"** = the Mixpanel
funnel conversion completed/LP users; distinct from perf-audit's **"Paid CVR"** (Google-Ads
clicks→conversions). **"LP Users"** = the funnel's landing-page users; distinct from perf-audit's
**"Paid sessions"**.)

**Basis label (required):** the funnel is computed **within-session, excluding PERFORMANCE_MAX**
(matches the Omni dashboard) across **all landing page types** (no page-type whitelist). Render a
small **"within-session · excludes PMax"** pill on the funnel section heading — reuse the existing
badge styling (`delta-flat` grey), no new CSS — so the basis is explicit and never reads as a
discrepancy vs a PMax-inclusive or paid-session table.

Each card shows: pre value (grey, smaller), post value (large bold), delta badge on its own line.
Delta format: `Δ −0.33pp / −7.0%` — absolute pp change and percentage change together.
Badge color: `delta-neg` (red) for drops, `delta-pos` (green) for gains, `delta-flat` (grey) for near-zero.

These cards are orientation, not conclusion. The conclusion comes in 1b.

### 1b. 90-day CVR trend chart (always)

Place this immediately after the metric cards, before the callout. It gives the reader instant seasonal and structural context before they read the finding — whether CVR improved or declined, they can see the shape of the trend and the LY comparison at a glance.

See the 90-day chart spec in the Plotly section below.

**Section 1 hard constraint:** no other charts or tables in this section — only the metric cards, the 90-day chart, and the callout.

### 1c. Root cause callout (always)

One callout box — the most important element in the entire report. It answers three questions, each as a `.callout-item` with a `.q` label (uppercase grey, 11px) and an `.a` answer (15px, dark).

**Two answer shapes are available:**
- **Paragraph shape** — a short prose answer, used when the finding is a single mechanism.
- **Lead claim + bullet list shape** — used when the answer enumerates multiple drivers, headwinds, or mechanisms. The lead claim names the headline framing in 1–2 sentences; each bullet names a driver in `<strong>`, an em-dash, and a one-line piece of evidence with its `↗` ref-link at the end of the bullet.

Both shapes are documented in "Visual Spec → Callout HTML patterns". Pick the shape that matches the finding — there is no threshold rule, just judgment about which is more readable for the specific RCA. Styling guidelines rule 7 covers when to prefer bullets.

**When CVR declined:** Red left border (`#e53935`), heading "Root Cause". Three questions:

- **What broke?** Name the specific thing that failed — not just a metric name.
  - ❌ "LP2S declined"
  - ✅ "S2C fell from 25.6% to 24.2%, concentrated almost entirely in the HO segment — where S2C collapsed from 35.7% to 23.4% on 21% more select-page visitors"
  - When multiple funnel steps all declined meaningfully (each carrying >15% Shapley share), name all of them in one sentence rather than picking one and ignoring the others:
  - ✅ "C2O fell 3.2pp (59% of the decline), driven by Magic Kingdom checkout failures and lower checkout intent post-spring-break. S2C also fell 2.7pp (27%) for the same seasonal reason — the same mechanism explains both."
  - ✅ "S2C collapsed 12pp (83% of the decline) on the HO channel, where the date-picker showed no available slots on TGIDs 7148 and 8821. LP2S and C2O also declined modestly (17% combined) but are explained by the same supply gap reducing visible options."
- **Why did it break?** The mechanism — what it means, not what the data shows.
  - When using seasonal or event-based framing, it must be paired with a specific data signal (a traffic pattern, a daily CVR break aligned to the event date, or a controlled comparison). See Styling guidelines rule 4 above.
- **When did it break?** Exact date (sudden) or window (gradual).

**When CVR improved:** Green left border (`#2e7d32`), heading "CVR Improved — What's Driving It & What's Holding It Back". Three questions:

- **What drove the improvement?** Lead with the positive driver — which step improved, by how much, and the mechanism (seasonal uplift, paid mix growth, supply improvement, etc.). Include the structural delta vs LY: a large seasonal improvement with only +0.09pp structural delta reads very differently from +0.5pp structural gain.
- **What's holding it back?** Name any step that declined despite overall CVR being up. Quantify both the rate drop and the checkout impact. If CVR improved across all steps, write "No significant headwinds — all funnel steps improved." **Magnitude threshold:** if the headwind's net contribution to ΔCVR is less than ~10% in absolute terms (e.g., −0.04pp on a +0.51pp total CVR move), fold it into a sub-bullet within "What drove the improvement?" rather than giving it a standalone callout item. Avoids overstating noise-level dilution as a meaningful drag on an otherwise clear improvement.
- **When did the headwind emerge?** (or "When did improvement begin?" if no headwind). Timing classification as for the decline case.

**If multiple root causes confirmed:** callout names the primary driver. Secondary findings get action cards in Section 2.

**On uncertainty:** If the evidence strongly points to a mechanism but doesn't fully confirm it, say "consistent with X" — but still commit to the most actionable explanation. Do not hedge into "multiple possible factors."

**Section 1 hard constraints:**
- No tables or Shapley visualizations in this section (90-day chart is the only chart)
- No hedging language ("possibly", "may be related to", "could be")

---

## Section 2 — Actions

**Purpose:** Immediately follows Section 1. A GM who reads only Sections 1 and 2 should be able to forward the relevant action card directly to the DRI.

### Structure of each action card

One card per confirmed root cause:
- **Priority badge** — P1 / P2 / P3 pill (red/amber/green), top-left of header row
- **Cause line** — 15px bold, the finding in one sentence (same precision as callout)
- **DRI row** — `dri-badge` pill (blue-grey) + secondary team text
- **Action bullet list** — specific, named steps (not generic template text). Name the experience, date, or URL where known.

### Limits and ordering

- Maximum 3 action cards, ranked P1 first
- If more than 3 distinct causes, top 3 get full cards. Additional findings get a one-paragraph summary at the start of Section 3 under "Additional findings"
- If only one root cause, one card is correct. Do not pad with unconfirmed hypotheses
- No card saying "monitor the situation" or "investigate further"
- **Evidence threshold before creating a card:** check both the rate drop AND the raw event count. If the rate drop is large but the event count is small relative to total CE checkouts (directional signal, not a confirmed finding), fold it as a sub-bullet inside the most relevant existing P1/P2 card rather than creating a standalone card. A directional signal earns a sub-bullet: *"Also check whether [channel] A2O anomaly is a separate issue — rate crashed but n=[N] attempts; validate sample before acting."* It does not earn its own action card.

### DRI naming standard

Specific enough to forward directly:
- ❌ "Supply team — investigate availability"
- ✅ "Supply team — check availability configuration for Keukenhof Entry Tickets (TGID 10118) for dates Apr 20 – May 11; API cut-off period may be restricting inventory the SP has available"

### Improvement-direction action cards — three sub-templates

CVR-improvement RCAs produce inherently softer actions than declines (no broken thing to fix). The action card *structure* stays identical, but each card falls into one of three templates. Pick the template that matches the confirmed finding; the spec below names what each must contain to remain testable rather than drifting into "monitor the situation."

- **Protect.** Used when a confirmed mechanism is driving the lift and could regress if neglected (a ranking position, inventory window, content state, budget allocation). The card must name the specific TGID / URL / supply window / campaign that's carrying the gain and the operational lever that supports it. DRIs: Growth + BDM + Supply, depending on which lever. Example: *"Keep TGID 8869 (Pompeii Entry Tickets) in its current top-of-listing position and confirm with the SP that same-day inventory holds through July — the +0.59pp CVR gain on this segment depends on near-zero `days_to_first_available_date`."*

- **Extend.** Used when a confirmed segment grew and there is headroom to grow it further (a paid channel improved CVR, a geo surged in volume, a new TGID launched well). The card must name the segment, the headroom signal, and a specific next move. DRIs: Performance Marketing + Growth + BDM. Example: *"Italy domestic traffic grew +26.7% on Google Ads MB at higher CVR — capture more by sustaining Italian-language Google Search spend through May–August peak. Quantify the budget reallocation that would scale the segment without diluting CVR."*

- **Investigate-headwind.** Used when a small headwind is forming under the lift (HO dilution, channel mix drift, supplier softness). The card must propose the **specific next query** the DRI should run, not just the team to ask. Example: *"Audit which sources drove the +854-user HO LP increase — paid expansion, new SEO ranking, or affiliate. Run `mixpanel_user_page_funnel_progression` for HO with `previous_page_url` and `channel_name` cuts, May 1–20, to surface the new entry points; LP2S falling 46% → 39% suggests the new arrivals are browsing without intent."*

These templates are not mutually exclusive — a single improvement RCA can produce one Protect, one Extend, and one Investigate-headwind. Maximum three cards total still applies. Do not pad with a Protect card if there is no real lever to protect; if only one type fits the finding, one card is correct.


## Section 3 — Supporting Analysis

**Purpose:** Evidence that the conclusions in Sections 1–2 are correct. A reader who doubts the conclusion reads this to verify it.

### Opening rule for every analysis block

Every analysis block opens with a **verdict line** — a colored inline callout (red for a finding, neutral blue for a ruled-out result) — before showing any chart or table. The verdict states what the evidence confirms or rules out, not what the chart shows.

- ✅ Red verdict: "HO S2C collapsed −12.3pp. MB S2C held flat (−0.6pp). The drop is entirely in the headout.com segment."
- ✅ Neutral verdict: "Mix ruled out — both MB and HO show conversion-dominant effects. Traffic share held stable."
- ❌ "The following table shows S2C by distribution channel:" (describes the chart, not the finding)

### Subtext paragraphs

After a table or chart, add a grey `<p>` (13px, `#555`) that explains the **interpretive meaning** — not what the table shows, but what it implies. This is where the investigative reasoning lives.

Example after the lead-time chart:
> "From Apr 13–19, dates 15+ days out = April 28 and beyond — including the April 26 Flower Parade weekend. Dates in this range appear sold through. Users who had planned trips for those dates abandoned the funnel; those who could visit near-term still booked, causing the 0–3 day bucket to surge."

### What belongs in Section 3

Include only analyses that directly support or rule out a claim made in Sections 1–2.

**Always-present blocks appear in this fixed order:**
1. Mix cascade analysis block → Fixed Segment banner
2. Geo / Non-Geo overview
3. Shapley decomposition
4. Daily trend chart (C2O / S2C / LP2S for the primary driver)
5. Primary driver dimension cuts and experience/URL breakdowns (as applicable)
6. Secondary driver evidence (if applicable — see SKILL.md c023 for scoping)
6.5. **External signals & corroboration** (conditional — render when any external lens (Slack, perf-audit, CE Health, …) contributed a signal you used; see "External context integration & link-to-table styling" in visual_kit.md)
7. Ruled-out dimensions block
8. Hypotheses explored (always last)

Conditional blocks (inventory, price analysis, weekday composition) slot between items 5 and 6 within the relevant funnel step's evidence. The External Signals block sits *after* secondary driver evidence (item 6.5) so the data-driven story leads — external lenses are supporting evidence, not the primary lens.

The list below covers most CEs. **When the investigation surfaces a finding that doesn't match any of the standard blocks, add a custom `.analysis-block` for it** — Claude writes the report in HTML directly, so there is no rendering-pipeline constraint on what can ship. The visual guardrails come from following the `.analysis-block` HTML pattern in the Visual Spec section (rounded card, title, optional verdict line, body content); the content inside the block is freeform.

| Analysis | When to include |
|---|---|
| Shapley decomposition | Always — establishes which funnel step drove ΔCVR and by how much. Use the proportional flex bar (see visual spec), not a Plotly waterfall. |
| Mix cascade (three levels) | Always — MB/HO → paid/organic → channel breakdown. Opens with a Fixed Segment banner declaring the filters applied to all subsequent analysis. See Fixed Segment banner spec below. |
| Geo / Non-Geo overview | Always — run once after the fixed segment is declared. Shows domestic vs international CVR split across the top countries by volume. If the drop is concentrated in either Geo or Non-Geo, add the downstream-limitation note (see spec below). |
| Daily S2C/LP2S/C2O trend chart | Always — establishes sudden vs gradual onset. All trend charts filtered to the fixed segment. Pre: blue `#6c8ebf`, Post: red `#c62828`. |
| Dimension cut (device / language / page_type) | Only if it produced a concentrated signal OR is being explicitly ruled out. |
| Channel/segment breakdown table | When the drop is concentrated in HO vs MB or a specific channel. |
| Experience-level breakdown | When drop is concentrated in specific experiences. |
| URL-level breakdown | When drop is concentrated in specific page URLs. |
| Lead-time distribution | When availability scarcity is the hypothesis — compare pre/post booking bucket distribution. |
| Inventory TID summary table | When S2C drop is confirmed at a specific TGID — one row per TID, columns: TID · TID Name · Tickets 0–2d · Tickets 3–7d · Tickets 8–13d · Tickets 14–30d. Snapshot from the latest available `extracted_date`. |
| Inventory daily time-series charts | When S2C drop is confirmed at a specific TGID — always run alongside the TID snapshot. Four line charts (one per lead-time bucket), `extracted_date` on x-axis, total tickets on y-axis. Path B: pre and post as overlaid series. Path A: post series only. Path X: omit entirely — add an inline note in the S2C evidence block: *"Inventory data unavailable — post period ended more than 30 days ago. Supply mechanism cannot be confirmed or ruled out from data."* |
| Price analysis | When price changed and timing correlates with LP2S onset. |
| Weekday composition | When pre vs post differs materially in weekday/weekend mix AND the report attributes any portion of the move to that imbalance. Render only when material — otherwise the check stays in the transcript. Two-row table: pre weekdays/weekends, post weekdays/weekends; subtext explains the implied calibration on the headline metric. |
| External signals & corroboration | When **any** external lens (Slack, perf-audit, CE Health, future siblings) contributed a signal you actually used (Pattern A/B/C in the Step 2b reconciliation). Three-column table: Signal · What it tells us about this report · Source ↗. One row per *used* signal, regardless of which lens it came from. Renders whenever at least one lens contributed a used signal — even if other lenses were unavailable. This is the report's "sources cited" panel. See HTML pattern below. |
| Custom analysis block | When the investigation surfaced a finding that doesn't match any of the standard rows above but should still look visually consistent with the rest of Section 3. Write a `<div class="analysis-block">` with a `<div class="block-title">`, optional `<div class="verdict-line">`, and freeform body HTML inside. **Default home for novel findings.** |

**User-context findings get no block of their own — they ride existing surfaces, proportionally.** A user prior (from `user_context.md`, closed at Step 2b check #12) that the data **confirmed** is woven into the relevant block's verdict/subtext with a `(per user context)` parenthetical; one that was **ruled out** is a single line wherever it's most relevant (often the ruled-out-dimensions block or a one-line note), e.g. "Checked LP2S at URL level per the user's note — ruled out; the drop was CE-wide." Never give a user prior its own headline block or inflate its emphasis beyond what the data supports — the report leads with the data-driven driver. (User context is not a lens or a tab, so it carries a plain parenthetical, not a `↗` anchor.)


## CVR-RCA-specific block specs

HTML patterns and content rules for the analysis blocks that appear in Section 3 of a CVR-RCA report. Each block is keyed to a row in the "What belongs in Section 3" table above. The visual chrome (CSS, `.analysis-block` shell) lives in `visual_kit.md`; this section names the per-block content rules — verdict-line forms, table column specs, when to highlight rows, what the subtext paragraph should communicate.

---

### URL-level breakdown block

Present as a `.analysis-block` when the drop concentrates in specific page URLs or when a routing shift (traffic moved between URLs) is the story. Place within the primary driver evidence, after the dimension cut that first reveals the URL signal.

**Two verdict forms:**

- **Performance verdict** (URL rate dropped, share held): `"LP2S fell on [URL] — traffic share held flat. Something changed on that specific page."`
- **Routing verdict** (URL share shifted, rate held): `"Traffic shifted away from [URL A] toward [URL B] — per-URL rates held flat. This is a routing story, not a page quality issue."`

Apply `.highlight-row` to URLs where either the rate dropped meaningfully (performance story) OR `pct_of_lp` shifted substantially between pre and post (routing story). Use the URL breakdown query from `context.md` — it is the only query that produces `pct_of_lp`. Only show URLs that represent a meaningful share of CE LP traffic; long-tail URLs have high-variance rates and belong in subtext at most.

```html
<div class="analysis-block">
  <div class="block-title">URL Breakdown — [Funnel Step] by Landing Page</div>
  <div class="verdict-line">[State verdict: routing (volume shifted, rates held) or performance (rate dropped, share held), naming the specific URLs]</div>

  <table>
    <thead>
      <tr>
        <th>URL</th>
        <th>Period</th>
        <th class="num">Users</th>
        <th class="num">% of LP</th>
        <th class="num">LP2S</th>
        <th class="num">S2C</th>
        <th class="num">C2O</th>
        <th class="num">CVR</th>
      </tr>
    </thead>
    <tbody>
      <!-- highlight-row on URLs where rate dropped meaningfully OR pct_of_lp shifted substantially -->
      <tr class="highlight-row">
        <td>[page_url]</td>
        <td>pre</td>
        <td class="num">[n]</td>
        <td class="num">[x%]</td>
        <td class="num">[x%]</td>
        <td class="num">[x%]</td>
        <td class="num">[x%]</td>
        <td class="num">[x%]</td>
      </tr>
      <tr class="highlight-row">
        <td>[page_url]</td>
        <td>post</td>
        <td class="num">[n]</td>
        <td class="num neg">[x%]</td>
        <td class="num neg">[x%]</td>
        <td class="num">[x%]</td>
        <td class="num">[x%]</td>
        <td class="num neg">[x%]</td>
      </tr>
      <!-- repeat for other majority-contributor URLs, pre and post rows paired -->
    </tbody>
  </table>

  <p style="font-size:13px;color:#555;margin-top:12px;">
    [State which URLs are majority contributors, whether the pattern is a routing shift or a rate change,
     and what the finding implies for the DRI. For a routing story: name which channel or campaign
     drives the gaining URL. For a performance story: name the specific URL and what may have changed
     on that page (template, listed experiences, traffic composition from that entry point).]
  </p>
</div>
```

---

### Inventory section format

Present as a `.analysis-block` within the S2C evidence section, immediately after the experience-level S2C breakdown confirms the TGID locus.

**Verdict line — two patterns, two forms:**

- **Window-specific drop** (one bucket near zero, others hold):
  - ✅ "Ticket counts in the 8–13 day window for Experience 8821 fell to zero in the post period — the 0–7 day and 14–30 day buckets were unaffected. Points to a window-specific supply constraint."
  - Highlight zero or near-zero bucket rows in the TID summary table with `.highlight-row`.

- **Uniform decline** (all buckets dropped together):
  - ✅ "Ticket counts fell across all lead-time windows for Experience 8821 — no single window is uniquely affected. Consistent with a platform-wide or full-product supply reduction."
  - No `.highlight-row` — the finding is product-wide, not bucket-specific.

- ❌ "The following table shows inventory by lead time." (describes data, not finding)

**Supply gate outcome:** If the time-series confirms tickets were healthy throughout the post period for all limited-capacity TIDs, open the inventory block with the ruled-out verdict: *"Supply checked and ruled out — all limited-capacity TIDs had available tickets throughout the post period. Supply is not the mechanism for this S2C drop."* Always show the line charts when data is available (Path A or Path B) — healthy lines above zero are visual proof, not just an assertion. Do not show the TID snapshot table in this case — it adds no signal beyond the verdict. For Path X (post period outside the 30-day window), omit the charts and add the inline limitation note instead. Move directly to pricing or UX after the inventory block.

**TID summary table (all paths — current-state snapshot):** One row per TID. Columns: TID · TID Name · Tickets 0–2d · Tickets 3–7d · Tickets 8–13d · Tickets 14–30d · Capacity type. This shows today's inventory state, not the post period. Use it to scope the time-series (which TIDs have near-zero buckets now, which are unlimited-capacity) and to give orientation context. Highlight near-zero rows with `.highlight-row` as a scoping signal. Append `Capacity type` (`Limited` / `Unlimited`) from `is_fully_unlimited_capacity`. Omit unlimited-capacity TIDs from the supply finding — note in subtext: "excluded from supply analysis (unlimited capacity)." For Path A, add the orange block-level note above the table: *"Pre-period inventory data unavailable — pre period is more than 30 days ago. Current-state snapshot shown."*

**Daily time-series charts:** Four Plotly line charts, one per lead-time bucket. x-axis: `extracted_date`. y-axis: total tickets (TGID aggregate of limited-capacity TIDs — do not include unlimited-capacity TIDs in the traces). These are the primary supply RCA evidence.

- **Single TGID investigated:** one trace per chart, scoped to that TGID.
- **Multiple TGIDs investigated (2–3 significant contributors):** one colored trace per TGID on each chart. Label traces by experience name, not TGID number ("UTV Raptor Tour", not "TGID 37536"). One set of 4 charts covers all investigated TGIDs — do not produce separate chart sets per TGID.
- **Path A (pre period outside 30-day window):** post-period dates only on x-axis.
- **Path B (pre period within 30-day window):** full date range on x-axis (`pre_start` to `post_end`). Add a shaded post-period region and vertical dashed line at `post_start`, matching the 90-day chart convention. One continuous trace per TGID — do not split into separate pre/post series. The pre→post transition is visible on the same timeline.
- **Omit non-informative buckets:** If a lead-time bucket shows uniformly healthy supply across all experiences throughout the post period — no sustained near-zero values, no progressive decline — do not render a chart for that bucket. Replace it with a single inline sentence immediately before the next chart heading: *"[X–Yd bucket: all experiences maintained available tickets throughout (range: N–M tickets). Not charted.]"* Only render a chart when the time-series shows a pattern that is directly relevant to the finding.

**TID selection for charts — contribution-based**

Before building the charts, identify contributing TIDs from the median table (Path A: post-period median; Path B: pre/post median comparison):

- **One TID depleted** → chart that TID individually as a single trace
- **Multiple TIDs depleted within one TGID** → aggregate their ticket counts into one trace; label by TGID / experience name
- **Mixed (some depleted, some healthy within one TGID)** → chart depleted TIDs only; note excluded healthy TIDs in the disclosure banner
- **All TIDs healthy** → aggregate all limited-capacity TIDs (supply ruled out context)

For multiple TGIDs: apply this logic independently per TGID → one trace per TGID on the same set of 4 charts.

**Always query the time-series through the `experience_id → dim_tours` bridge. Never scope to a hardcoded `tour_id` without first confirming via the median table which TIDs are the contributing locus.**

**Yellow disclosure banner — always render immediately before the charts:**

```html
<div style="background:#fff8e1;border-left:4px solid #f9a825;border-radius:4px;padding:10px 14px;margin-bottom:16px;font-size:13px;color:#5d4037;">
  <strong>Charts cover:</strong>
  <!-- Use the applicable form: -->
  <!-- Single TID: -->
  TID [id] ([name]) — [post period only, no pre-period baseline | pre and post period shown]
  <!-- Multiple aggregated TIDs from one TGID: -->
  Combined data for TID [id1] ([name1]) + TID [id2] ([name2]) — [Path A/B note]
  <!-- Mixed — depleted only: -->
  TID [id] ([name]) — TID [id2] ([name2]) had healthy availability throughout and is excluded.
  <!-- Multiple TGIDs — one line per TGID: -->
  [TGID 1 name]: TID [id] ([name]) &nbsp;|&nbsp; [TGID 2 name]: Combined TID [id1] + TID [id2]
</div>
```

**Plotly implementation — inventory time-series:**

```javascript
// One IIFE per inventory section. One trace per contributing scope.
// Scope = single TID, or aggregated TIDs for one TGID, or one trace per TGID if multi-TGID.
// Path A: dates = post-period dates only.
// Path B: dates = pre_start→post_end; add shaded post region and vertical line (see below).
(function () {
  var dates = [/* extracted_date strings across the charted range */];

  // One data array per trace per bucket — from the daily time-series query.
  var scope1_02 = [/* tickets_0_2d for scope 1 */];
  var scope2_02 = [/* tickets_0_2d for scope 2 — omit if single trace */];
  // Repeat _37, _813, _1430 for each scope.

  var colors = { scope1: '#1a56db', scope2: '#2e7d32', scope3: '#e07b00' };

  var layout = {
    height: 220,
    margin: { t: 10, r: 10, b: 40, l: 50 },
    xaxis: { tickfont: { size: 10 }, nticks: 9 },
    yaxis: { tickfont: { size: 10 }, rangemode: 'tozero' },
    legend: { orientation: 'h', y: -0.28, font: { size: 10 } },
    plot_bgcolor: '#fafafa',
    paper_bgcolor: '#fff'
  };

  var cfg = { responsive: true, displayModeBar: false };

  function trace(name, y, color) {
    return { x: dates, y: y, name: name, type: 'scatter', mode: 'lines+markers',
             line: { color: color, width: 2 }, marker: { color: color, size: 4 } };
  }

  Plotly.newPlot('inv-chart-0-2d',
    [trace('[Scope 1 label]', scope1_02, colors.scope1)
     /* add trace('[Scope 2 label]', scope2_02, colors.scope2) if multi-scope */],
    Object.assign({}, layout), cfg);

  // Repeat newPlot calls for inv-chart-3-7d, inv-chart-8-13d, inv-chart-14-30d.
})();

// Path B additions to layout.shapes:
// { type:'rect', x0:POST_START, x1:POST_END, y0:0, y1:1, xref:'x', yref:'paper',
//   fillcolor:'rgba(198,40,40,0.06)', line:{width:0} }
// { type:'line', x0:POST_START, x1:POST_START, y0:0, y1:1, xref:'x', yref:'paper',
//   line:{color:'#c62828', dash:'dot', width:1} }
// Path B annotation: { x:midPostDate, y:0.92, xref:'x', yref:'paper',
//   text:'Post period', font:{color:'#c62828',size:10}, showarrow:false }
```

**Subtext paragraph:** State the pattern and when it started, and what the supply team should check. Do not assert the mechanism — the data shows *where* and *when*, not *why*. Never write "this was caused by [specific mechanism]" without corroborating evidence from the supply team.

**Path A — post-period median table:**

```html
<!-- Path A: pre period is outside the 30-day window — only post-period data available.
     One row per limited-capacity TID. Columns show median ticket counts across all
     extracted_dates within the post period (not today's snapshot).
     Apply highlight-row to TIDs where the post-period median is near-zero —
     this means the TID was typically constrained during the period under investigation.
     Omit rows where is_fully_unlimited_capacity = TRUE; note them in subtext. -->
<div class="analysis-block">
  <div class="block-title">Availability during post period — [Experience name]</div>
  <div class="verdict-line">[State the actual pattern using the correct verdict form from the spec above]</div>

  <p style="font-size:13px;color:#e07b00;margin-bottom:10px;">
    Pre-period availability data unavailable — pre period falls outside the 30-day window.
    Showing median daily ticket availability across the post period. No before/after comparison possible.
  </p>

  <table>
    <thead>
      <tr>
        <th>TID</th>
        <th>TID Name</th>
        <th class="num">Median 0–2d</th>
        <th class="num">Median 3–7d</th>
        <th class="num">Median 8–13d</th>
        <th class="num">Median 14–30d</th>
        <th>Capacity</th>
      </tr>
    </thead>
    <tbody>
      <!-- highlight-row on TIDs where the post-period median is near-zero -->
      <tr class="highlight-row">
        <td>[tour_id]</td>
        <td>[tour_name]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td>Limited</td>
      </tr>
      <tr>
        <td>[tour_id]</td>
        <td>[tour_name]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td class="num">[n]</td>
        <td>Limited</td>
      </tr>
    </tbody>
  </table>

  <p style="font-size:13px;color:#555;margin-top:12px;">
    [State which TIDs show near-zero median (typically constrained during the post period)
     and which are healthy. The time-series charts below confirm the daily pattern.
     If any TIDs were excluded: "TID [id] ([name]) excluded — unlimited capacity."]
  </p>
</div>
```

**Path B — TID pre/post median comparison (2×2 bucket grid):**

```html
<!-- Path B: pre period is within the 30-day window — median across all extracted_dates
     available for both periods.
     Pre Median = median of daily ticket counts across all extracted_dates in [pre_start, pre_end].
     Post Median = median of daily ticket counts across all extracted_dates in [post_start, post_end].
     Apply highlight-row to TIDs where post median dropped significantly vs pre median.
     Omit rows where is_fully_unlimited_capacity = TRUE from all tables; list them in subtext.
     No orange limitation banner — pre data is available for Path B. -->
<div class="analysis-block">
  <div class="block-title">Availability — [Experience name] (pre vs post median)</div>
  <div class="verdict-line">[State the actual pattern — which bucket(s) dropped and by how much, or ruled-out if healthy throughout]</div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px;">

    <!-- 0–2 day bucket -->
    <div>
      <p style="font-size:12px;font-weight:600;color:#444;margin:0 0 6px;">Same / next day (0–2d)</p>
      <table>
        <thead>
          <tr>
            <th>TID</th>
            <th>TID Name</th>
            <th class="num">Pre Median</th>
            <th class="num">Post Median</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>[tour_id]</td>
            <td>[tour_name]</td>
            <td class="num">[n]</td>
            <td class="num">[n]</td>
          </tr>
          <!-- add rows for remaining TIDs -->
        </tbody>
      </table>
    </div>

    <!-- 3–7 day bucket -->
    <div>
      <p style="font-size:12px;font-weight:600;color:#444;margin:0 0 6px;">3–7 days out</p>
      <table>
        <thead>
          <tr>
            <th>TID</th>
            <th>TID Name</th>
            <th class="num">Pre Median</th>
            <th class="num">Post Median</th>
          </tr>
        </thead>
        <tbody>
          <tr class="highlight-row">
            <td>[tour_id]</td>
            <td>[tour_name]</td>
            <td class="num">[n]</td>
            <td class="num neg">[n]</td>
          </tr>
          <!-- add rows for remaining TIDs -->
        </tbody>
      </table>
    </div>

    <!-- 8–13 day bucket -->
    <div>
      <p style="font-size:12px;font-weight:600;color:#444;margin:0 0 6px;">8–13 days out</p>
      <table>
        <thead>
          <tr>
            <th>TID</th>
            <th>TID Name</th>
            <th class="num">Pre Median</th>
            <th class="num">Post Median</th>
          </tr>
        </thead>
        <tbody>
          <tr class="highlight-row">
            <td>[tour_id]</td>
            <td>[tour_name]</td>
            <td class="num">[n]</td>
            <td class="num neg">[n]</td>
          </tr>
          <!-- add rows for remaining TIDs -->
        </tbody>
      </table>
    </div>

    <!-- 14–30 day bucket -->
    <div>
      <p style="font-size:12px;font-weight:600;color:#444;margin:0 0 6px;">14–30 days out</p>
      <table>
        <thead>
          <tr>
            <th>TID</th>
            <th>TID Name</th>
            <th class="num">Pre Median</th>
            <th class="num">Post Median</th>
          </tr>
        </thead>
        <tbody>
          <tr class="highlight-row">
            <td>[tour_id]</td>
            <td>[tour_name]</td>
            <td class="num">[n]</td>
            <td class="num neg">[n]</td>
          </tr>
          <!-- add rows for remaining TIDs -->
        </tbody>
      </table>
    </div>

  </div><!-- end grid -->

  <p style="font-size:13px;color:#555;margin-top:16px;">
    [State which buckets show a meaningful median drop and by how much. The time-series charts
     below confirm when the depletion started within the post period. Do not assert a supply
     verdict here — describe the pattern.
     If any TIDs were excluded: "TID [id] ([name]) excluded — unlimited capacity."]
  </p>
</div>
```

### Ruled-out dimensions section

Collect dimensions that were checked and found uninformative into a single `.analysis-block` at the end of Section 3, titled "Dimensions Checked — ruled out as independent drivers". Use a `<p>` intro sentence, then a `<ul>` with one `<li>` per dimension, each naming what moved and why it is not an independent driver.

Example:
> **Device:** Desktop S2C −2.5pp, iOS Mweb +0.7pp. Desktop drop is consistent with HO users being predominantly desktop (paid search). No evidence of a mobile UX regression.

Do not show separate tables for dimensions that produced no signal. The ruled-out block is the right home for those findings.

### What does NOT belong in Section 3

- Analyses that produced no signal — if all devices moved equally, no device cut appears anywhere
- "For completeness" tables — every element answers a question raised by something above it
- Metrics that didn't move
- Repeated information from Section 1
- Shapley visualization in a mix-dominant finding (the steps didn't break)

---

### Mix cascade analysis block

Render one `.analysis-block` for the cascade — three sub-tables inside it,
one per level. Each table shows the mix_effect vs conversion_effect arithmetic
explicitly so the reader can verify the routing-vs-conversion decision.

The verdict line states the overall cascade outcome. Each sub-table has its own
one-line finding. Highlight the fixed segment row with `.highlight-row`.

```html
<div class="analysis-block">
  <div class="block-title">Mix Cascade — Routing vs Conversion Determination</div>
  <div class="verdict-line">
    <!-- Use ONE of these: -->
    Conversion change at all levels — no routing story. Fixed segment: [MB/HO] · [Paid/Organic] · [Channel].
    <!-- OR: -->
    Routing story — mix change detected at Level [1/2/3]. [One-line reason.]
  </div>

  <!-- Level 1: MB vs HO -->
  <p style="font-size:12px;font-weight:600;margin:16px 0 6px;">Level 1 — MB vs HO</p>
  <table>
    <thead>
      <tr>
        <th>Segment</th>
        <th class="num">Pre users</th><th class="num">Post users</th>
        <th class="num">Pre share</th><th class="num">Post share</th>
        <th class="num">Pre CVR</th><th class="num">Post CVR</th>
        <th class="num">Mix effect</th><th class="num">Conv. effect</th>
        <th>Verdict</th>
      </tr>
    </thead>
    <tbody>
      <tr class="highlight-row">  <!-- highlight the fixed / dominant segment -->
        <td>[MB / HO]</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>Fixed — conversion dominates</td>
      </tr>
      <tr>
        <td>[MB / HO]</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>—</td>
      </tr>
    </tbody>
  </table>

  <!-- Level 2: Paid vs Organic -->
  <p style="font-size:12px;font-weight:600;margin:16px 0 6px;">Level 2 — Paid vs Organic (within [MB/HO])</p>
  <table>
    <thead>
      <tr>
        <th>Segment</th>
        <th class="num">Pre users</th><th class="num">Post users</th>
        <th class="num">Pre share</th><th class="num">Post share</th>
        <th class="num">Pre CVR</th><th class="num">Post CVR</th>
        <th class="num">Mix effect</th><th class="num">Conv. effect</th>
        <th>Verdict</th>
      </tr>
    </thead>
    <tbody>
      <tr class="highlight-row">
        <td>Paid</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>Fixed — conversion dominates</td>
      </tr>
      <tr>
        <td>Organic</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>—</td>
      </tr>
    </tbody>
  </table>

  <!-- Level 3: Channel breakdown within Paid -->
  <p style="font-size:12px;font-weight:600;margin:16px 0 6px;">Level 3 — Channel breakdown within Paid</p>
  <table>
    <thead>
      <tr>
        <th>Channel</th>
        <th class="num">Pre users</th><th class="num">Post users</th>
        <th class="num">Pre share</th><th class="num">Post share</th>
        <th class="num">Pre CVR</th><th class="num">Post CVR</th>
        <th class="num">Mix effect</th><th class="num">Conv. effect</th>
        <th>Verdict</th>
      </tr>
    </thead>
    <tbody>
      <!-- One row per paid channel (Google Ads, Microsoft Ads, Facebook Ads, Affiliates).
           highlight-row on the fixed channel. -->
      <tr class="highlight-row">
        <td>Google Ads</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>Fixed — conversion dominates</td>
      </tr>
      <tr>
        <td>Microsoft Ads</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td><td class="num">[±x.xxpp]</td>
        <td>—</td>
      </tr>
      <!-- add rows for Facebook Ads, Affiliates as applicable -->
    </tbody>
  </table>

  <p style="font-size:13px;color:#555;margin-top:12px;">
    [One paragraph: what the cascade found, which level fixed which segment,
     and why this is a conversion story (or routing story if applicable).
     Do not repeat the numbers — the tables carry them.]
  </p>
</div>
```

**If the cascade exited at a mix level:** render only the levels up to and
including the exit level. The exit level's verdict cell reads "Mix exit —
routing story". Do not render subsequent levels (they were not run).

---

### Fixed Segment banner

After the mix cascade concludes, declare the fixed segment once at the top of the analysis section — before the Shapley block. This banner tells the reader that all funnel data below is scoped to one coherent cohort.

```html
<div style="background:#e8f5e9;border-left:4px solid #2e7d32;border-radius:4px;padding:10px 14px;margin-bottom:20px;font-size:13px;color:#1b5e20;">
  <strong>Fixed segment for all funnel analysis:</strong>
  [MB / HO] · [Paid / Organic] · [Channel if applicable — e.g. "Google Ads"]<br>
  <span style="color:#555;font-size:12px;">
    Post-period users: [N] &nbsp;|&nbsp; Share of CE post traffic: [X]%
    &nbsp;|&nbsp; Checkout impact: [sign][N] vs pre period
  </span>
</div>
```

The banner should appear once, immediately after the mix cascade analysis block and before the Shapley decomposition block. Do not repeat it in every analysis block — subsequent blocks inherit the scope implicitly.

If the mix cascade could not fix a single segment (e.g. the signal is evenly split across MB and HO), omit the banner and note in the first analysis block's verdict line that the funnel analysis covers the full CE.

---

### Geo / Non-Geo overview block

Render immediately after the Fixed Segment banner, before the Shapley block. Always present — this is a mandatory diagnostic, not conditional on finding a geographic signal.

**Four verdict forms:**

- **Geo-concentrated** (home-market rate dropped, international held): `"Drop concentrated in domestic users — international visitors held flat."`
- **Non-Geo-concentrated** (international rate dropped, home market held): `"Drop concentrated in international visitors — home market held flat."`
- **Uniform** (both dropped similarly): `"No geographic concentration — domestic and international rates dropped similarly. Geography does not isolate the issue."`
- **Mix-dominant** (share shifted, per-group rates held): `"Geographic mix shifted — per-group rates held while composition changed. This is a traffic sourcing change, not a funnel quality issue."`

**Downstream-limitation note:** For Geo-concentrated and Non-Geo-concentrated outcomes only, add this as the subtext paragraph:
> "Note: downstream analysis — inventory availability and pricing — is not filtered by geography. Geo-specific root causes (local supply, domestic pricing, geo-targeted campaign change) should be investigated separately with the supply and BDM teams."

For Uniform and Mix-dominant outcomes, omit the note and continue to Shapley.

```html
<div class="analysis-block">
  <div class="block-title">Geographic Overview — Domestic vs International</div>
  <div class="verdict-line">
    <!-- Use ONE of the four verdict forms above -->
    [Verdict]
  </div>

  <table>
    <thead>
      <tr>
        <th>Country</th>
        <th>Segment</th>
        <th class="num">Pre Users</th>
        <th class="num">Post Users</th>
        <th class="num">Pre CVR</th>
        <th class="num">Post CVR</th>
        <th class="num">ΔCVR</th>
      </tr>
    </thead>
    <tbody>
      <!-- highlight-row on Geo row if Geo-concentrated; Non-Geo rows if Non-Geo-concentrated; no highlight-row if Uniform or Mix-dominant -->
      <tr class="highlight-row">
        <td>[Home country]</td>
        <td>Domestic</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td>
      </tr>
      <tr>
        <td>[Country 2]</td>
        <td>International</td>
        <td class="num">[n]</td><td class="num">[n]</td>
        <td class="num">[x%]</td><td class="num">[x%]</td>
        <td class="num">[±x.xxpp]</td>
      </tr>
      <!-- repeat for top countries by volume; always include home country regardless of rank -->
    </tbody>
  </table>

  <!-- For Geo-concentrated or Non-Geo-concentrated only: -->
  <p style="font-size:13px;color:#555;margin-top:12px;">
    Note: downstream analysis — inventory availability and pricing — is not filtered by geography.
    [Geo-concentrated: "Geo-specific root causes (local supply, domestic pricing, geo-targeted campaign change) should be investigated separately with the supply and BDM teams."]
    [Non-Geo-concentrated: "Language, UX friction, and international supply hypotheses should be investigated separately."]
  </p>
</div>
```

---

### External signals & corroboration block

Render this block in Section 3 between item 6 (secondary driver evidence) and item 7 (Ruled-out dimensions) **whenever any external lens contributed at least one signal you actually used** (Pattern A/B/C in the Step 2b reconciliation) — from Slack, perf-audit, CE Health, or any future sibling. This is the report's **"sources cited" panel**: every external signal that informs a callout, verdict, or narrative line gets one row here, and is also woven in at the point of use. It is the table side of the provenance contract in `SKILL.md → Step 2b → "Context reconciliation (checks #9–#11)"`. Skip the block only when no external lens contributed any used signal — silence is fine then.

The id stays `block-market-context` so existing ↗ citations continue to resolve.

Source-agnostic three-column table. The heading is generic — never bake a specific channel/section name (e.g., `#mkt-italy-switzerland-malta`, `perf-audit §4`) into the title; let the **Source** column carry per-row provenance. Each Source cell names the lens and links to it: Slack → external thread URL `[Author · date]`; perf-audit / CE Health → an in-report `↗` to the owning tab anchor (`#perfaudit-<slug>`, `#cehealth-<slug>`) so the reader jumps to the source tab.

The block is direction-agnostic (declines *and* improvements) and lens-agnostic: a row can be a Slack supplier-deploy thread, a perf-audit SIS verdict, or a CE Health Shapley/RPC fact — whatever you leaned on.

When a lens that was expected (named in `orchestration.json` `context_lenses`) did **not** reach the report — e.g. Slack timed out or hit a permission denial — add a final disclosure row noting the gap (so the reader knows a lens is missing, not that it was clean). The block still renders for the lenses that *did* contribute; a single unavailable lens never suppresses the whole table.

```html
<div class="analysis-block" id="block-market-context">
  <div class="block-title">External signals &amp; corroboration</div>
  <div class="verdict-line neutral">[One-line summary of what the external lenses add in aggregate — corroboration, reframing, or mechanism explanation across Slack / perf-audit / CE Health. Direction-agnostic.]</div>

  <table>
    <thead>
      <tr>
        <th>Signal</th>
        <th>What it tells us about this report</th>
        <th style="width:160px;">Source</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>[The signal compressed to one sentence in plain language — preserve Headout-native jargon per Styling rule 5]</td>
        <td>[The connection — which finding it corroborates, which interpretation it reframes, or which mechanism it explains. The only column requiring Claude's commitment.]</td>
        <td><!-- Slack: external thread link -->
          <a href="[slack-thread-url]" target="_blank" style="color:#3a4a8a;font-size:12px;">Slack: [Author · date]</a>
          <!-- OR perf-audit / CE Health: in-report cross-tab link -->
          <!-- <a class="ref-link" href="#perfaudit-paid-deep-dive">perf-audit §4 ↗</a> -->
          <!-- <a class="ref-link" href="#cehealth-driver-diagnosis-shapley">CE Health ↗</a> -->
        </td>
      </tr>
      <!-- one row per USED signal across all lenses (typically 3–8 rows) -->
      <!-- final row only if an expected lens was unavailable: -->
      <!-- <tr><td colspan="3" style="color:#777;font-size:12px;font-style:italic;">Slack context not retrievable this run (connector timeout) — operational lens not included.</td></tr> -->
    </tbody>
  </table>
</div>
```

Layer 1 and Layer 2 ↗ arrows that cite any external source route to this block via `href="#block-market-context"` (for the consolidated view) or directly to the owning tab anchor (for cross-tab jumps). Slack Source cells link externally to the thread; perf-audit / CE Health Source cells link in-report to their tab anchors.

---

### Shapley decomposition block

Use a proportional flex bar — not a Plotly waterfall. Each segment's `flex` value equals its percentage contribution.

**Sign-aware rule for mixed contributions:** When one funnel step contributes in the opposite direction (e.g., a CVR improvement where LP2S contributed −9% while C2O contributed +86%), `flex` proportional to *absolute value* will compress the visual scale of the dominant driver and over-represent the small counter-step. Two acceptable patterns:

1. **Absolute-value flex + sign prefix on label** (preferred for mild offsets): use `flex: 86` for C2O, `flex: 9` for the negative LP2S, and label the negative bar `−9%` or `LP2S −9%`. Add a `style="background: #6c8ebf;"` override on the negative bar so it's visually distinct from the positive bars (which use the canonical step colours).
2. **Net-positive flex only** (for large offsets > 25%): omit the counter-step from the flex bar entirely and call it out in the legend below as a separate line item with sign. Avoids the bar appearing balanced when 86% of the move is in one direction.

Pick (1) when the counter-step is small noise (< 20% absolute). Pick (2) when it materially distorts the visual.

```html
<div class="analysis-block">
  <div class="block-title">Shapley Decomposition — funnel step attribution</div>
  <div class="verdict-line">[Primary step] carries [X]% of ΔCVR. [Other steps] are noise.</div>

  <div class="shapley-bars">
    <div class="shapley-bar shapley-lp2s" style="flex: [lp2s_pct]">[lp2s_pct]%</div>
    <div class="shapley-bar shapley-s2c"  style="flex: [s2c_pct]">S2C [s2c_pct]%</div>
    <div class="shapley-bar shapley-c2o"  style="flex: [c2o_pct]">[c2o_pct]%</div>
  </div>
  <div class="shapley-legend">
    <span><span class="legend-dot" style="background:#6c8ebf"></span>LP2S [delta]pp</span>
    <span><span class="legend-dot" style="background:#c62828"></span>S2C [delta]pp</span>
    <span><span class="legend-dot" style="background:#d6a832"></span>C2O [delta]pp</span>
  </div>
  <p style="font-size:13px;color:#555;margin-top:12px;">
    Total ΔCVR = [total]pp. [Primary step] accounts for [delta]pp. [Other steps] are too small to act on independently.
  </p>
</div>
```

---

### Ruled-out dimensions block (second-to-last in Section 3)

```html
<div class="analysis-block">
  <div class="block-title">Dimensions Checked — ruled out as independent drivers</div>
  <p style="font-size:13px;color:#555;margin-bottom:12px;">
    These were checked and do not add independent signal beyond what the [primary finding] already explains.
  </p>
  <ul style="font-size:14px;color:#333;padding-left:18px;">
    <li style="margin-bottom:8px;"><strong>Device:</strong> [what moved and why it is not independent]</li>
    <li style="margin-bottom:8px;"><strong>Language:</strong> [what moved and why it is not independent]</li>
    <li style="margin-bottom:0;"><strong>Page type:</strong> [what moved or "Not a driver"]</li>
  </ul>
</div>
```

---

### Hypotheses explored (always last in Section 3)

A structured log of every hypothesis generated and tested during the
investigation. Shows the full exploration shape: what was proposed, what the
test was, what it led to, and — critically — what was attempted but couldn't
be resolved. This block earns its place by being honest about the
investigation's limits, not just its conclusions.

Render as an `.analysis-block` table at the very end of Section 3, after the
ruled-out dimensions block. Every hypothesis generated during the
investigation must appear — confirmed, ruled out, and open alike. A
hypothesis that was tested and ruled out is as valuable to show as one that
was confirmed. A `🔄` row is an honest acknowledgment that the investigation
reached a data boundary; it invites the stakeholder to pick it up.

**Outcome values:**
- ✅ **Confirmed** — test produced a specific positive finding
- ❌ **Ruled out** — test produced a specific negative result
- ⚠️ **Data gap** — couldn't test; name the data or tool that would close it
- 🔄 **Consistent with, not directly tested** — data pattern fits the
  hypothesis but no direct test was run; name what the direct test would be

```html
<div class="analysis-block">
  <div class="block-title">Hypotheses Explored</div>
  <p style="font-size:13px;color:#555;margin-bottom:14px;">
    Every hypothesis generated during this investigation — confirmed, ruled out, and open.
  </p>
  <table>
    <thead>
      <tr>
        <th>Hypothesis</th>
        <th>Test run</th>
        <th class="num" style="width:100px;">Outcome</th>
        <th>What this means</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>[Hypothesis — what was proposed and why]</td>
        <td>[What was checked — e.g. "inventory daily time-series for TID 80074"]</td>
        <td class="num">✅ Confirmed</td>
        <td>[One sentence: what the finding means for the CE]</td>
      </tr>
      <tr>
        <td>[Hypothesis — what was proposed and why]</td>
        <td>[What was checked — e.g. "price table for all TGIDs pre vs post"]</td>
        <td class="num">❌ Ruled out</td>
        <td>[One sentence: why this hypothesis was eliminated]</td>
      </tr>
      <tr>
        <td>[Hypothesis — what was proposed and why]</td>
        <td>[What you would have checked — e.g. "lead-time bucket query on select page"]</td>
        <td class="num">⚠️ Data gap</td>
        <td>[One sentence: what data or tool is missing and who could provide it]</td>
      </tr>
      <tr>
        <td>[Hypothesis — what was proposed and why]</td>
        <td>[Indirect evidence only — e.g. "supply healthy, price flat; no direct user-journey test"]</td>
        <td class="num">🔄 Untested</td>
        <td>[One sentence: what the direct test would be]</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Optional Slack source column:** If Step 2b check #9 produced at least one
Slack corroboration, add a 5th column `Source` to the table. Each cell is either
empty or a formatted thread link: `[Author · date](slack-link)`. If no
corroborations exist, omit the column entirely — do not add an empty column.

```html
<!-- With Slack source column (only when at least one row has a citation) -->
<tr>
  <th>Hypothesis</th>
  <th>Test run</th>
  <th class="num" style="width:100px;">Outcome</th>
  <th>What this means</th>
  <th style="width:120px;">Source</th>
</tr>
<!-- Cell example with citation: -->
<td><a href="https://headout.slack.com/archives/CNSHDD2H1/p1746123456789012"
    target="_blank" style="color:#3a4a8a;font-size:12px;">Rawia · Apr 8</a></td>
<!-- Cell example without citation: -->
<td></td>
```

**Inline Slack corroboration in analysis block subtext:** If a Slack thread
directly and independently confirms a finding stated in an analysis block verdict
(not just echoes it), add a parenthetical citation after the verdict sentence:

```
(corroborated: [Author · date in #channel](slack-link))
```

Use this sparingly — only when the Slack signal adds independent confirmation
beyond what the data alone shows. Never add a Slack citation just because a GM
mentioned that performance was poor; only when they named a specific mechanism,
date, or event that matches the finding.

**User-provided sources** (MMP doc / ad-hoc Sheet / user-named channel) follow the
same placement rules and use the distinct tags defined in `visual_kit.md →
"User-provided source citations"`, so a reader can tell analyst-supplied from
system-derived evidence.

---

## Report length calibration

| Scenario | Expected length |
|---|---|
| Mix-dominant story | Sections 1–2 + mix table + URL traffic comparison. ~4 subsections. No Shapley. |
| Single-step failure, single confirmed mechanism | Sections 1–2 + Shapley + trend + 1–2 cuts + experience or URL table. ~6–8 subsections. |
| Multi-step failure with recording confirmation | Full treatment. Max ~10 subsections. |

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c001 | 2026-04-24 | Initial version — three-section report structure (Executive Summary → Actions → Supporting Analysis) extracted from SKILL.md Step 3 and formalized |
| c002 | 2026-04-24 | Added Visual Spec section: shared CSS, page skeleton, component HTML patterns for all elements (metric cards, root cause callout, action cards, analysis blocks, Shapley bar, tables, Plotly conventions, ruled-out block). Derived from Keukenhof Tickets (CE 1549) reference report. render.py retired — Claude writes HTML directly using this spec. |
| c003 | 2026-04-24 | Header 🔗 link is now a clickable `<a href>` pointing to `top_page_url` from summary.json (populated by Q0 — most-visited page URL in the post period). |
| c005 | 2026-04-28 | Raw user counts mandatory in every table — any table showing rates or shares must include Pre Users and Post Users columns so stakeholders can judge volume without arithmetic. Added to table spec (with updated example), anti-patterns list, and report length calibration. |
| c004 | 2026-04-28 | Three structural changes: (1) 90-day CVR trend chart moves from Section 3 to Section 1 — always shown after metric cards, before callout, so seasonal context is visible immediately. (2) Callout has a positive-CVR variant: green border, "CVR Improved — What's Driving It & What's Holding It Back" heading, questions reframed around drivers/headwinds rather than what broke. (3) 90-day chart x-axis fix: both current-year and LY lines now use currentDates on the x-axis (aligned by calendar position, not actual date), with tickformat '%b %Y' to show month labels. |
| c006 | 2026-04-28 | Added inventory lead-time bucket table to Section 3 — new row in "What belongs in Section 3" table and a dedicated format spec with HTML pattern. Always follows the availability proxy table; verdict line names the specific window that went empty, not just "availability dropped". |
| c007 | 2026-04-28 | Generalised lead-time bucket spec: two verdict forms (window-specific spike vs uniform decline); HTML pattern replaced specific example rows with placeholders and a note to adapt buckets to the CE's booking horizon; subtext guidance changed from "state the mechanism" to "describe the pattern and what to investigate" to prevent asserting unconfirmed causes. |
| c009 | 2026-04-29 | 90-day chart LY overlay: two fixes. (1) Extraction step added — `lyCvr` must be built by filtering `trend_context.series` where `series === 'ly'` and aligning to `currentDates`; it is not a top-level key in summary.json. Complete extraction snippet added to spec. (2) Data guard strengthened to check `v > 0` in addition to non-null/undefined — zero-filled LY series (CE had no meaningful Headout history last year) now correctly triggers the warning banner instead of rendering a flat line at 0%. Also fixed hardcoded green post-window shade in code sample — shade colour now derived from `headline.delta.cvr` sign (red for decline, green for improvement). |
| c008 | 2026-04-29 | (1) Fixed Segment banner: new HTML component rendered once after the mix cascade and before the Shapley block, declaring the fixed MB/HO × Paid/Organic × Channel scope that applies to all subsequent funnel analysis. Includes fallback note if segment cannot be fixed. (2) 90-day chart x-axis changed from monthly (`dtick:'M1'`) to weekly ticks (`dtick: 7*86400000`, `tickformat:'%d %b'`) for week-level resolution across the 90-day window. (3) LY data guard added: pre-render check for non-empty lyCvr array; shows ⚠️ warning banner instead of silent missing line if LY series is absent from summary.json. (4) "What belongs in Section 3" updated: mix analysis now explicitly "Mix cascade (three levels: MB/HO → Paid/Organic → Channel)" replacing the single mix table entry. |
| c010 | 2026-04-29 | Added `POST_START`, `POST_END`, and `postDates` variable definitions to the 90-day chart spec — previously used in `shapes` and annotation midpoint but never defined in the snippet. Now explicitly derived from `summaryJson.meta.post_start/post_end`. |
| c011 | 2026-05-06 | Inventory section format spec redesigned to match new TID-level query architecture: (1) "Availability proxy table" row removed; replaced with "Inventory TID summary table" (one row per TID, pre+post bucket columns for Path B, post-only for Path A) and "Inventory daily time-series charts" (4 line charts, one per bucket). (2) Supply gate outcome added: if Step 2 shows full tickets, write a ruled-out statement and skip the table/charts. (3) TID summary table now includes `Capacity type` column from `is_fully_unlimited_capacity`; unlimited-capacity TIDs excluded from supply finding with a subtext note. (4) Chart scoping spec added: single TID if Step 2 identified one locus; TGID aggregate if all TIDs depleted equally. (5) Subtext paragraph guidance updated: state pattern + onset date + what supply team should check; never assert mechanism without corroborating evidence. |
| c012 | 2026-05-07 | Three presentation-layer fixes: (1) Supply gate wording updated — removes "Step 2" reference; supply-ruled-out verdict now states charts may still be shown as positive confirmation (lines above zero is visual proof); TID snapshot table is omitted in this case. (2) Added two anti-patterns: "Investigation-internal terminology in the report body (Step 1/2/3, Path A/B, Case A/B/C, locus, lost_checkouts_delta, candidate TGIDs)" and "Daily inventory time-series rendered as HTML table". (3) Both anti-pattern entries include the fix: translate internal labels to business language; always use Plotly line charts for daily data. |
| c013 | 2026-05-07 | Inventory section redesigned to reflect snapshot-vs-time-series architecture: (1) "What belongs in Section 3" time-series row: changed trigger from "when TID summary table shows depleted buckets" (old supply gate) to "when S2C drop is confirmed at a specific TGID — always run alongside the TID snapshot"; added Path X inline note (omit entirely; add limitation sentence to S2C evidence block). (2) TID summary table spec unified: Path B and Path A separate paragraphs merged into one "all paths — current-state snapshot" spec with single-set bucket columns (removed pre/post pair format). (3) HTML template simplified: 8 pre/post column headers (Pre 0–2d / Post 0–2d, etc.) replaced with 4 single-set headers; data rows simplified from 4 pairs to 4 individual cells; comment updated to clarify snapshot source and that highlight-row is a scoping signal, not a supply verdict. |
| c014 | 2026-05-07 | Inventory table templates split into Path A and Path B variants: (1) "Path B and Path A — same table structure" header renamed to "Path A — TID snapshot table (current-state snapshot)"; HTML comment updated — "For Path A only:" qualifier removed (template is now exclusively Path A); orange limitation note is always shown. (2) New "Path B — TID pre/post comparison (2×2 bucket grid)" template added — four small tables in a CSS grid (one per lead-time bucket), each with Pre and Post columns from the pre_end/post_end snapshots respectively. highlight-row on TIDs where the bucket dropped significantly. Unlimited-capacity TIDs excluded per subtext note. No orange banner (pre data available). (3) Supply gate always-show rule reinforced: "Always show the line charts when data is available (Path A or Path B)" — replaced earlier "may still show" wording. (4) Daily time-series chart spec expanded: explicit multi-TGID sub-case (one colored trace per TGID, labeled by experience name, not TGID number); Path A/B date range guidance added. (5) Plotly implementation snippet added for multi-TGID time-series, including Path B shading comment. |
| c015 | 2026-05-07 | Added mandatory TGID-aggregate disclosure note to the daily time-series charts spec: always render a subtext paragraph above the charts stating that the charts show total tickets aggregated across all limited-capacity TIDs per experience, that a dip reflects combined availability (not a specific TID), and that TID-level detail is in the summary table above or the investigation transcript. |
| c016 | 2026-05-07 | Added "Styling and language guidelines" section before Section 1: four rules — (1) no investigation structure labels (Path A/B, L0/L1/L2, Step 1/2/3, Case A/B) in rendered output; (2) no data-engineering terminology ("artefact", "extraction artefact", "pipeline gap"); (3) no speculative user behavior without a data signal; (4) external context (seasonality, events) only when paired with a corresponding data signal. |
| c017 | 2026-05-07 | Restored mandatory Geo / Non-Geo overview block: (1) added "Geo / Non-Geo overview" row to "What belongs in Section 3" table as always-present; (2) added "### Geo / Non-Geo overview block" section between the Fixed Segment banner and Shapley block — includes four verdict forms (Geo-concentrated / Non-Geo-concentrated / Uniform / Mix-dominant), HTML table template (top countries by volume, home country always included, highlight-row on concentrated segment), and downstream-limitation note for Geo/Non-Geo concentrated outcomes only. |
| c018 | 2026-05-07 | Three output-quality fixes from CE 6495 evaluation: (1) Inventory time-series — added "Omit non-informative buckets" rule: if a lead-time bucket is uniformly healthy across all experiences for the full post period, replace the chart with a single inline sentence rather than rendering an empty-signal chart. (2) LY data guard — changed behavior from replacing the chart div with a warning banner to always rendering the chart and inserting a visible amber ⚠️ badge after it; grey subtext is no longer an acceptable placement for the LY-absent notice. (3) Plotly conventions — added rule requiring color names in verdict lines, callouts, and subtext to be derived from the explicitly-assigned hex values in the chart's `colors` object, not inferred from Plotly default color order or trace position. |
| c019 | 2026-05-07 | Inventory section redesigned for multi-TID accuracy and period-median summary tables: (1) TID selection for charts changed from hardcoded multi-TGID traces to contribution-based: one depleted TID → individual trace; multiple depleted TIDs within one TGID → aggregate into one trace; mixed → depleted only with healthy TIDs noted in disclosure banner; all healthy → aggregate all. For multiple TGIDs: one trace per TGID applying the same logic. (2) Yellow disclosure banner added — always rendered immediately before the 4 line charts. Amber style matching LY callout. States exactly which TIDs/data the charts cover, with single-TID, aggregated, mixed-exclusion, and multi-TGID text variants. (3) Path A table replaced: "current-state snapshot" (today's MAX extracted_date) replaced with "post-period median table" — columns renamed to Median 0–2d/3–7d/8–13d/14–30d; orange banner updated; highlight-row now signals near-zero post-period median, not today's state. (4) Path B table replaced: snapshot-based Pre/Post columns replaced with Pre Median / Post Median columns from the period-median queries. Plotly implementation simplified: scope-based traces (scope1/scope2) replace hardcoded tgid1/tgid2/tgid3. |
| c020 | 2026-05-13 | Added "Hypotheses explored" block — always last in Section 3, after the ruled-out dimensions block (which is now second-to-last). Four-column table (Hypothesis · Test run · Outcome · What this means) with four outcome values: ✅ Confirmed, ❌ Ruled out, ⚠️ Data gap (name what would close it), 🔄 Consistent with — not directly tested (name what the direct test would be). Every hypothesis generated during the investigation must appear — confirmed, ruled out, and open alike. Forces honest documentation of data limits and untested inferences rather than allowing them to disappear into narrative subtext. |
| c021 | 2026-05-14 | Section 1c "What broke?" expanded: (1) Added a multi-step example showing how to name all funnel steps with meaningful Shapley share in one sentence rather than picking one and ignoring the others. Two examples provided — one for multi-step same-mechanism case, one for multi-step different-mechanism case. (2) Added cross-reference note under "Why did it break?" requiring seasonal/event-based framing to be paired with a specific data signal, pointing to Styling guidelines rule 4. |
| c022 | 2026-05-14 | Section 2 action card spec — added evidence threshold rule: before creating a standalone action card, verify both the rate drop and raw event count. Directional signals from small samples belong as a sub-bullet inside the most relevant existing card, not as a standalone card. Example sub-bullet wording provided. |
| c023 | 2026-05-14 | Section 3 "What belongs in Section 3" — added fixed ordering for always-present blocks (numbered 1–8: mix cascade + Fixed Segment banner → Geo/Non-Geo → Shapley → daily trend → primary driver cuts → secondary driver evidence → ruled-out dimensions → hypotheses explored). Conditional blocks (inventory, session recordings, price) slot within primary driver evidence. Replaces the previous unordered table header which gave no sequencing signal. |
| c024 | 2026-05-08 | Added "URL-level breakdown block" HTML pattern section, placed before the inventory section format. Fills the gap where the "What belongs in Section 3" table listed "URL-level breakdown" with no format spec. Two verdict forms: performance verdict (rate dropped, share held) and routing verdict (share shifted, rates held). Table columns: URL · Period · Users · % of LP · LP2S · S2C · C2O · CVR. `.highlight-row` on URLs where rate dropped meaningfully or `pct_of_lp` shifted substantially. Pointer to the dedicated URL breakdown query in `context.md` (not the canonical L2+ query — that query does not produce `pct_of_lp`). |
| c032 | 2026-05-29 | **Dashboards row added to the header — Omni + Sentra URL templates.** New "Header — CVR-RCA-specific extensions" section at the top of the file documents the two URL templates the dashboards row carries: Omni Analytics (`https://headout.omniapp.co/dashboards/5368ab53?f--iv8lWOuS=...&f--uvd3KWWJ=30+complete+days+ago+30+days` with only `<CE_ID>` substituted — date params constant because the Omni dashboard has built-in pre/post comparison logic) and Sentra (`https://sentra-analytics.headout.com/analysis/<CE_ID>` — Sentra defaults to its own 30-day window, no URL date params available). Pre-write sanity check at the top of the file gains a third item ensuring the dashboards row is populated. HTML pattern shown explicitly — `<div class="dashboards">` with the `DASHBOARDS` label and two pill-button links (`Omni ↗`, `Sentra ↗`). Renders on every CVR-RCA report unconditionally. Chrome (`.dashboards`, `.dash-label`, `.dash-link` CSS + the placeholder block in the Page skeleton) lives in `visual_kit.md` c002; URLs are CVR-RCA-specific and live here. |
| c031 | 2026-05-29 | **Split into `visual_kit.md` + this file.** Skill-agnostic primitives (CSS, HTML patterns for header/metric-cards/callout/action-card/analysis-block/tables, styling rules 1–7, Slack integration & ↗ link-to-table pattern, Tabbed report structure, Anti-patterns, Plotly chart conventions, Anchor ID convention) moved to `references/visual_kit.md`. This file now contains only CVR-RCA-specific content: Section 1/2/3 macro-structure, "What belongs in Section 3" table, CVR-RCA-specific block specs (URL-level breakdown, Inventory format, Session recordings, Ruled-out, Mix cascade analysis block, Fixed Segment banner, Geo/Non-Geo overview, Market context, Shapley decomposition, Hypotheses explored), Report length calibration. Companion changes in `visual_kit.md` (new file c001), perf-audit-skill's `perf_audit_structure.md` (new file c001), perf-audit-skill SKILL.md (emit `perf_audit_report.html` alongside `.md`), CVR-RCA SKILL.md Step 3 (Tab 2 embeds extracted HTML body content, falling back to markdown render if HTML missing). Driven by the v1.16 reasoning that the Claude-writes-HTML model needs a clean separation between shared primitives and per-skill structure to scale to multiple report types. |
| c030 | 2026-05-28 | **Bulleted shape added to Section 1 callout.** Section 1c spec documents two answer shapes inside each `.callout-item .a`: paragraph (single mechanism, today's default) and lead claim + bullet list (multi-driver). Pick the shape that matches the finding — no threshold rule, no word cap, just judgment. New styling rule 7 makes the preference explicit ("prefer the bullet shape when a callout enumerates drivers"). Visual Spec gains CSS for `.callout-item .a ul/li` (tight bullet spacing inside the existing 15px callout text) and a new "Shape B — multi-driver" HTML pattern alongside the existing single-mechanism pattern. Shape A and Shape B can mix within the same callout — each `.callout-item` makes the choice independently. Driven by the observation that multi-mechanism CVR-improvement and decline callouts were degrading to dense paragraphs with inline `(1)/(2)/(3)` markers, making the most-scanned section of the report the hardest to scan. |
| c029 | 2026-05-28 | **Tab framework documented as an HTML pattern, not a render-pipeline spec.** "Tabbed report structure → Spec shape" section rewritten as a copy-pasteable HTML pattern (tab bar outside `.container`, two `.tab-pane` wrappers inside). New "Perf-audit tab rendering — markdown → HTML inline" subsection documents the verbatim markdown-to-HTML conversion Claude performs when writing the report. Single-tab / flat-layout instruction clarified: omit the `.tab-bar` and `.tab-pane` wrappers entirely, do not emit vestigial tab markup. Section 3 "What belongs" table rewritten — the two escape-hatch component rows (`analysis_block`, `raw_html`) replaced with a single "Custom analysis block" row that points to the `.analysis-block` HTML pattern. Section opener text updated to reflect the Claude-writes-HTML model. Companion changes in `SKILL.md` c033 (Step 3 reverted) and the `/cvr-rca` slash-command (Step 3 reverted). Driven by CE 243 RCA where the render.py output visibly degraded vs CE 252's hand-authored quality. |
| c028 | 2026-05-28 | Two new rows in "What belongs in Section 3" table for the v1.15 escape-hatch components — `analysis_block` (wraps arbitrary HTML in the standard Section-3 chrome; the default escape hatch for novel findings, preserves visual consistency) and `raw_html` (true passthrough, no wrapper; for the rare full-bleed callout / custom Plotly container). Section opener gains one sentence pointing readers to the escape hatches when no built-in matches the finding. Codifies the freedom-of-movement guarantee: Claude has the same flexibility it had when writing HTML directly, with the determinism of the templated renderer. Companion changes in `SKILL.md` c032, `scripts/render.py` c033. Driven by CE 252 (Louvre) RCA. |
| c027 | 2026-05-28 | New "Tab bar placement — full-width, left-anchored" subsection under "Tabbed report structure → Visual differences from CVR-RCA content" documenting the v1.15 move of `.tab-bar` outside `.container`. Tab bar renders full-viewport-width and sticky at the top, with the first button left-anchored to the 40px header content edge — survives any monitor width, no more centered-island appearance on wide screens. Companion changes in `templates/report.html` c032 (.tab-bar CSS updated; new `{{TAB_BAR}}` placeholder) and `scripts/render.py` c032 (assemble() emits tab bar into the new template slot). Single-tab / flat-spec reports byte-identical to v1.14. Driven by CE 252 (Louvre) RCA. |
| c026 | 2026-05-27 | Four direction-agnostic changes driven by CE 252 (Louvre) RCA learnings. **(1) Pre-write sanity check** at top of file — two universal items every report must verify before writing: header carries the four meta spans (📅 pre, 📅 post, 🌍 market, 🔗 landing-page URL); ↗ arrows present in Section 1 callout and Section 2 action card cause-lines. Universal regardless of CVR direction or CE. **(2) Styling rule 6 — plain English for derived metrics** (e.g., `structural_delta_cvr`). When citing a derived metric in a callout, unpack it once in GM-readable language (what LY did, what we did, what the gap means) rather than analyst shorthand. Direction-agnostic — applies whether structural delta is positive or negative. **(3) "When Slack context is unavailable"** subsection in Slack integration — small disclosure card pattern rendered inside the Market Context block when slack_context.md was not available at write-time (timeout, late return after Step 3, permission denial). Replaces the silent-skip failure mode. Direction-agnostic. **(4) Anti-pattern row** added: `days_to_first_available_date` as primary supply evidence. It is a single-integer proxy from `product_rankings_features`; canonical supply evidence is `inventory_availability` ticket counts per lead-time bucket. Applies to both supply expansion (improvement) and supply depletion (decline) findings. Companion changes in `context.md` c016 (canonical-source rule on the table) and `hypothesis.md` c019 (proxy demoted in S2C decline + S2C improvement + Pattern 4). |
| c025 | 2026-05-22 | Major styling expansion driven by CE 1223 (Pompeii) RCA learnings — bidirectional support and Slack integration. **Slack integration:** new "Slack integration & link-to-table styling" section consolidates three-layer model (narrative weaving / Important Context callout-item / Market Context Section 3 block), four-pattern classification (A/B/C/D), timeframe-citation rule, one-citation-per-concept rule, Slack-corroboration-upgrades-evidence rule for declines. Section 3 ordering gains item 6.5 (Market context & operational signals, conditional). New HTML pattern for Market Context block (3-column table, generic title — never bake channel name into heading). **Link-to-table:** every Section 3 `.analysis-block` carries an `id` attribute; canonical anchor ID convention listed. New ↗ ref-link CSS (`.ref-link`, `html { scroll-behavior: smooth }`, `.analysis-block:target` highlight). Usage rules: ↗ in Section 1 callout, Section 2 action cards, Hypotheses Explored "Test run" column; never inside Section 3 verdict lines or subtexts. Citation format split: bare `↗` for internal navigation; `Source · date ↗` for Slack citations. **Bidirectional support:** Section 1c CVR-improved variant gains magnitude threshold for "What's holding it back" (<~10% of total ΔCVR → fold into sub-bullet); Section 2 gains improvement-direction action card sub-spec (Protect / Extend / Investigate-headwind templates). **Styling rule 5 (new):** preserve Headout-native jargon (WBR, SP, GBV, RR vs plan, TGID, TID, VID, CR%, FabriGPT, etc.) — paraphrasing reduces trust. Does not override rule 1 — investigation-internal labels (Path A/B, Case A/B/C) still translated. **Shapley sign-aware rule:** flex bar handles mixed-sign contributions cleanly — absolute-value flex + sign prefix for mild offsets (<20%), or net-positive flex only for large offsets (>25%). **D3 — Weekday composition Section 3 block** added to "What belongs in Section 3" table — renders only when material and the report attributes any portion of the move to weekday imbalance. |
