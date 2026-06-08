# Perf Audit v6 — Quality Evaluator

## Your role

You just completed a paid performance audit. Now step back and grade your own work honestly.

This is not a formality. The purpose is to surface where the analysis fell short of what a sharp analyst would have done — not to ratify the choices made. Be harder on yourself than the perf team would be. If you claimed "no Bing campaigns" without checking fct_orders, say so. If you ran 600 lines for a HEALTHY CE that needed 200, name it. If a section rehashed dashboard data without adding insight, flag it.

---

## What to review

Before scoring, read five things in this order:

1. **The skill reference files** — read all before anything else, so you know what instructions existed:
   - `SKILL.md` — report structure, section specs, execution steps, anti-patterns, quality checklist
   - `DIAGNOSTICS.md` — the cascading hypothesis tree, escalation map, cause-detection-action patterns
2. **The report you wrote** — read it as if you've never seen this CE before. Does it hold together? Would you trust the conclusions?
3. **Your investigation transcript** — recall what data you queried, what you skipped, what you decided at each fork. The reasoning matters as much as the conclusion.
4. **The BQ script output and MCP results** — check that claims in the report are grounded in actual data, not inferences from partial data.
5. **The fct_orders channel breakdown** — this is the ground truth for "which channels exist." Cross-check Table 3 (Channel Breakdown) against it. This single check would have caught the Antelope Canyon Bing/PMax error.

Reading the skill files first is what makes the failure mode classification (Section 4) possible. You cannot say "the instruction was missing" unless you have actually looked.

---

## Scoring

For each of the 7 themes below, give:

- **Score:** 1-5
- **Justification:** 2-3 sentences citing specific content from the report or investigation. Vague justifications ("the report was clear") are not acceptable.
- **Gap** (required if score <= 4): describe specifically what was missing or wrong.
- **Why** (required for every gap): classify the root cause using one of four tags, backed by a citation. See failure mode classification below.

**Scale:**

| Score | Meaning |
|---|---|
| 5 | Exemplary — hard to do better given the data available |
| 4 | Good — clear execution, one or two minor gaps |
| 3 | Adequate — meets the minimum bar but nothing exceptional |
| 2 | Weak — some effort but significant gaps or errors |
| 1 | Poor — fundamental failure of this dimension |

---

## Failure Mode Classification

Every gap gets a **Why** line. Use exactly one of these four tags:

| Tag | Meaning |
|---|---|
| `[MISSING_INSTRUCTION]` | The skill files contain no instruction for this behavior. Claude had no way to know it was expected. |
| `[AMBIGUOUS_INSTRUCTION]` | An instruction exists but is vague, incomplete, or conflicting enough that Claude reasonably interpreted it differently. |
| `[EXEC_ERROR]` | The instruction was clear and present. Claude attempted to follow it but reasoned incorrectly (wrong data source, faulty inference, incomplete check). |
| `[DATA_LIMIT]` | The data needed to do this correctly was unavailable (MCP gap, BQ schema limit, context exhausted). Skipping or noting the absence was the right call. |

### Grounding requirement

Never assign a tag without citing the source. The citation format depends on the tag:

**`[MISSING_INSTRUCTION]`** — state which files you checked and confirm the instruction was absent:
> "Searched SKILL.md, DIAGNOSTICS.md — no instruction found for [behavior]."

**`[AMBIGUOUS_INSTRUCTION]`** — quote the instruction that exists, then state what it was missing:
> "SKILL.md Section 1 Table 3 says 'show ALL paid channels at macro level using BQ attribution data.' Instruction says to use BQ but doesn't explicitly say 'query fct_orders for all channels before concluding which channels exist' — Claude used GAds MCP campaign list instead."

**`[EXEC_ERROR]`** — name the file + section, show the instruction was clear, then state what went wrong:
> "SKILL.md Section 1 Table 3 Channel Taxonomy lists 'Bing' as a required channel. BQ fct_orders returned $20.4K Bing revenue. Report stated 'No Bing campaigns identified.' The data was available; the report ignored it."

**`[DATA_LIMIT]`** — name the instruction that required the data, and explain why it was unavailable:
> "SKILL.md 6b requires LY search terms (Q3). Q3 was not run for this CE due to context limits. Report correctly noted 'LY search term data not available at term level.'"

If you cannot write a specific citation, you have not done enough checking.

---

## Theme 1: Diagnostic Accuracy & Hypothesis Quality

**Did the audit reach the right conclusions, and did it get there through rigorous hypothesis testing?**

This theme has two sub-dimensions: the conclusion (1a) and the process that produced it (1b).

### 1a. Diagnostic conclusion

Score high if:
- The status (CRITICAL/WARNING/HEALTHY) is correct and defensible
- The primary driver is named correctly — the #1 thing the perf team should focus on
- Structural dynamics are distinguished from cyclical/seasonal (e.g., MoM softening is seasonal not structural)
- The diagnosis accounts for perf infra context (geo consolidation, tROAS transition, PMax migration, SIS denominator change)
- If the CE is HEALTHY, the report says so quickly and focuses on optimization upside, not phantom problems

Score low if:
- The status is wrong (e.g., called WARNING when the CE is growing +118% with 163% ROI)
- The primary driver is misattributed (e.g., blaming paid search when the decline is organic)
- Structural changes are flagged as problems (e.g., "campaigns dropped from 20 to 9" when it's consolidation)
- Perf infra context is ignored (e.g., flagging YoY SIS drops as CRITICAL)
- A HEALTHY CE gets a 600-line report treating minor optimization gaps as serious issues

### 1b. Hypothesis process (DIAGNOSTICS.md tree walking)

The audit's conclusions should emerge from walking the DIAGNOSTICS.md trees — not from describing what metrics moved. For each metric signal (CPC up, SIS down, clicks down, etc.), did the audit:
1. **Enter the right tree?** — Map the signal to the correct DIAGNOSTICS.md section (e.g., CPC↑ → Section 4, 3-lens tree)
2. **Test branches in order?** — Walk top-down, not cherry-pick. The CPC tree says quality→structural→competition in that order.
3. **Confirm or rule out each branch with data?** — "Checked CVR rose alongside CPC (Lens 1 confirmed)" not "CPC might be competition"
4. **Name the primary cause and rank alternatives?** — "Quality traffic is primary (CVR +2.1pp). Competition is real but secondary (Viator +7.2pp IS)."
5. **Stop when evidence was conclusive?** — Don't keep testing branches after the answer is clear

Score high if:
- Hypotheses are falsifiable and specific: "Spanish campaign death spiral under MAXIMIZE_CONVERSION_VALUE — fewer conversions → less signal → algorithm contracts spend" is falsifiable. "Spanish campaign is underperforming" is just an observation.
- The report names the most likely explanation AND distinguishes it from alternatives considered
- DIAGNOSTICS.md trees were walked in order — the 3-lens CPC tree, the SIS rank-vs-budget fork, the CVR funnel cascade
- At each fork, the data that confirmed or ruled out the branch is cited
- The root cause names something specific: a campaign, a bidding strategy, a landing page, a date, a competitor — not a generic metric

Score low if:
- The report presents observations as hypotheses ("LP2S dropped, possibly due to UX or pricing or availability")
- Multiple root causes are listed without ranking them
- The DIAGNOSTICS.md trees were not consulted — analysis followed a fixed template order instead of the highest-signal path
- No attempt was made to distinguish what actually happened from what could have happened
- The verdict could apply to any CE on any day ("CPC is high and competition is strong")

**Combined T1 score:** Average of 1a and 1b. Getting the right answer through sloppy process is fragile — it'll be wrong next time. Getting the wrong answer through rigorous process is fixable — the process just needs a better data source.

## Theme 2: Factual Correctness (The Embarrassment Test)

**Would the perf team find errors that destroy the report's credibility?**

This is the hardest theme to score honestly. Factual errors aren't "minor gaps" — they make the entire report untrustworthy. A single wrong channel identification ("No Bing campaigns" when Bing is generating $20K/month) is worse than a verbose exec summary.

Score high if:
- All channels are correctly identified — every channel with >$500 L4W revenue in fct_orders appears in Table 3 (Channel Breakdown)
- Campaign names, statuses, and bid strategies match what GAds MCP returned
- Numbers are internally consistent (CE Snapshot matches Channel Overview matches Appendix)
- Source attributions are correct (BQ vs GAds, revenue vs conv_value)
- ROI math checks out (CM1 / Spend = stated %)
- No recommendations for things already in place (e.g., "launch Bing" when Bing is live)

Score low if:
- A channel generating >$1K/month is missing from Table 3 (Channel Breakdown)
- Numbers contradict across sections (different revenue totals in snapshot vs channel overview)
- Actions recommend something that already exists or was already tried
- Campaign statuses are wrong (called "dormant" when spending $37K/month)
- The wrong revenue column was used (GMV instead of net revenue)

**Post-audit cross-check (run this before scoring Theme 2):**
1. Query `fct_orders` for this CE's L4W revenue by channel — does Table 3 (Channel Breakdown) match?
2. Sum all campaign spend in Section 4a — does it match the CE Snapshot spend total?
3. For each action: does the thing you're recommending NOT already exist?

## Theme 3: Insight Novelty (The "So What" Test)

**Does the audit surface things the perf team can't see in their Omni dashboard?**

The perf team sees campaign metrics, SIS, CPC, CVR in Omni every day. If the audit just restates those numbers with YoY deltas, it's a formatted dashboard export. The audit earns its existence by connecting dots the dashboard can't.

Score high if:
- Search term clustering reveals hidden patterns (e.g., sub-attraction LP converts 2.2x better than main page)
- 3-window temporal analysis reveals dynamics invisible in YoY (e.g., Spanish campaign death spiral only visible in MoM)
- Coverage gaps are sized with $ impact (not just "SIS is 24%")
- The CPC explanation goes beyond "CPC up" to explain the mechanism (quality premium vs competition vs structural)
- At least one finding would make the perf team say "I didn't know that"

Score low if:
- Every finding could be derived from the Omni dashboard in 5 minutes
- Search term section just lists top terms by impressions without clustering or IS
- CPC is described ("CPC increased 80%") without explaining why (3-lens tree)
- LP analysis is absent despite multiple landing pages existing
- Match-type coverage not analyzed despite keyword_view data being available

## Theme 4: Narrative & Causal Chain Quality

**Does the report read as analyst prose with a coherent story, or as a template filled with data?**

Two things matter here — the logical chain (are findings connected causally?) and the prose quality (does it read like an analyst wrote it for a human audience?). Both must work. A report with perfect causal chains but clunky template prose fails the "would the GM read past page 1" test. A beautifully written report with disconnected sections fails the "so what do I do" test.

### 4a. Causal chain (logical structure)

Score high if:
- Section 2 (Exec Summary) threads findings from Section 1 Tables->4->5->6 into one coherent story with an explicit connecting sentence
- Metric movements are connected causally: "CPC +$0.80 -> but CVR +2.1pp -> so RPC/CPC ratio healthy -> premium is justified"
- Alternative explanations are explicitly ruled out: "MoM softening tracks Ahrefs seasonal demand (Mar 20.1K -> May 16.6K), not structural decline"
- Actions trace back through the chain: "Route Ken's Tours queries to Ken's LP (10.1% CVR vs 4.6% main) -> est. +275 conv/month ($13.8K)"

Score low if:
- Sections are independent — each could be read in isolation without losing meaning
- The exec summary is a bullet list of findings with no connecting thread
- Metric movements are listed without connecting them: "SIS 24.8%. CPC $2.10. CVR 6.0%."
- No alternatives are ruled out — the first explanation is presented as the only one

### 4b. Narrative quality (prose and flow)

Score high if:
- Each section follows the frame->test->conclude arc from SKILL.md (natural reasoning, not labeled template sections)
- Each section opens by connecting to the prior section's finding — the reader never wonders "why is this section here?"
- No structural markers in the output: no `**Hypothesis:**`, `**Verdict:**`, `**Check:**` — just analyst prose
- The report is appropriately concise: sentences that add no information are absent. Can you delete a sentence without losing meaning? If yes, it should have been deleted.
- The GBTB report's Section 4c CPC prose is the benchmark: "CPC $0.83 is 80% above market median — but that doesn't automatically mean we're overpaying. CVR rose alongside CPC to 6.9%..."

Score low if:
- Sections read like filled-in templates (same structure regardless of what the data shows)
- Opening framings are generic ("This section examines...") instead of specific ("Table 3 showed organic drove the decline. The question shifts to whether paid has internal gaps...")
- Boilerplate appears: sentences defining ROI, explaining what SIS means, disclaimers that add no analytical value
- The report reads like a list of section summaries stitched together, not a progressive argument

**Combined T4 score:** Average of 4a and 4b. A report can score 5 on chains but 3 on prose (correct but clunky), or 4 on prose but 2 on chains (reads well but disconnected). Both matter.

## Theme 5: Investigation Adaptivity

**Did the audit go deep where signal was strong and skip where it wasn't?**

The skill defines three report depths: SHORT (0-1 flags), STANDARD (2-4 flags), FULL (5+ flags). A 600-line FULL report for a HEALTHY CE is as much a failure as a 200-line report for a CE in freefall.

Score high if:
- Report depth matches the CE status (healthy CE = focused report highlighting 2-3 optimization levers)
- Sections with no findings are compressed to 1-2 sentences, not padded with boilerplate
- Escalation queries (DIAGNOSTICS.md Section 12) were fired only when standard data was insufficient
- The CPC 3-lens tree was walked only as far as needed (stopped at Lens 1 if quality traffic confirmed)
- The DIAGNOSTICS.md tree was followed — branches were tested in order, and the first confirmed branch was named as primary

Score low if:
- Every section is fully expanded regardless of whether it has findings
- The report runs all possible analyses "just in case" instead of following the diagnostic tree
- Boilerplate sections appear (device split in narrative, budget utilization commentary, campaign count YoY)
- Escalation queries were skipped when the standard data left a key question unanswered
- The DIAGNOSTICS.md tree was not consulted — branches were chosen based on "what's standard" not "what's the highest-signal next question"

## Theme 6: Action Specificity & Sizing (Monday Morning Test)

**Could the perf team lead forward the action card to a team member without adding context?**

Score high if:
- Every action says WHO does WHAT by WHEN for HOW MUCH, linked to evidence section
- Ordering is lowest-hanging-fruit first (not random or by section number)
- Actions are falsifiable: "Route 'kens tours' queries to kens-tours LP via ad group URL override" not "Improve landing page"
- $ sizing uses concrete methodology: SIS gap x RPC, tourist % x CVR x AOV, LP CVR gap x traffic
- At least 7 actions, and a manual audit wouldn't find 10 more
- Competitive response included if competitor IS > ours
- Bid/tROAS actions match the actual bid strategy (don't say "set tROAS" if already using it)

Score low if:
- Actions say "investigate further" or "monitor the situation" without specifying what to check
- Generic actions: "Improve CVR," "Scale spend," "Optimize bids"
- Actions don't cite evidence sections
- $ sizing is absent or uses theoretical ceilings instead of recovery-discounted estimates
- The same action card could have been written for any CE on any day
- Actions recommend things already in place (the Bing error: "Launch Bing" when Bing is generating $20K)

## Theme 7: Skill Compliance (Anti-Pattern Avoidance)

**Did the audit follow its own rules?**

The skill has 16 anti-patterns ("NEVER DO THESE") and a 30-item quality checklist. This theme checks compliance with the playbook — not analytical quality (that's Themes 1-6), but whether the structural rules were followed.

Score high if:
- All 16 anti-patterns in SKILL.md avoided
- Source labeling present (BQ vs GAds) on every metric
- ROI in % format, not x format
- No blended funnel (or labeled with caveat)
- SIS MoM as primary signal, YoY as directional only
- Geography table present with customer-vs-ad coverage comparison
- Monthly Campaign Totals in appendix with YoY deltas
- Google Sheet created with 5 tabs (or noted as pending with explanation)
- Inline deltas on every metric in campaign cohort tables
- Every section leads with narrative, not a table

Score low if:
- Anti-patterns violated (budget utilization flags, Shapley at aggregate level, "competition" without evidence, campaign count YoY, YoY SIS flagged as CRITICAL)
- Source labels missing — reader can't tell if a number is from BQ or GAds
- Blended funnel presented without caveat
- Geography table absent
- Monthly Campaign Totals missing from appendix
- Tables lead sections instead of narrative

---

## Output format

Do not dump a score table. Write the evaluation as a structured assessment:

### 1. Overall verdict (3-4 sentences)

State the overall quality of this audit in plain language. What did it get right? What was the main failure mode? Would you send this to the perf team as-is?

### 2. Theme scores

Present each theme with its score, justification, and gap + Why for each gap. Format each gap block as:

```
**Gap:** [what was missing or wrong — specific, not vague]
**Why:** [TAG] — [citation proving you checked the skill files] — [one sentence on what the fix would be]
```

Example of a correctly-written gap block:

```
**Gap:** Section 1 Table 3 stated "No Bing campaigns identified" when fct_orders showed $20.4K Bing revenue (EN $9.0K + OL $10.2K + Spanish $0.5K).
**Why:** [EXEC_ERROR] — SKILL.md Section 1 Table 3 Channel Taxonomy lists "Bing" as a required channel row. Step 1 runs the BQ script which outputs channel breakdown including Bing. The data existed in fct_orders but was not queried before writing Section 1 Table 3 — the channel list was inferred from GAds MCP (which only returns Google campaigns). Fix: add explicit instruction in Step 1 to "query fct_orders for ALL channels before writing Section 1 Table 3."
```

### 3. Top 2-3 improvements for the next run

Concrete and actionable — not generic advice. Each should name a specific file to edit and what to change.

### 4. Failure Mode Summary

After the top-3 section, add this table aggregating every gap from Section 2:

| Gap (short label) | Theme | Tag | Fix target |
|---|---|---|---|
| [gap name] | T[N] | [TAG] | [file name + what to change] |

The fix target column should name the specific skill file and a one-phrase description of the edit needed. This is what gets turned into a skill improvement in the next iteration.

---

## Scoring summary

| Theme | Weight | Score (1-5) | Weighted |
|---|---|---|---|
| T1. Diagnostic Accuracy | 20% | | |
| T2. Factual Correctness | 20% | | |
| T3. Insight Novelty | 15% | | |
| T4. Causal Chain Quality | 15% | | |
| T5. Investigation Adaptivity | 10% | | |
| T6. Action Specificity | 10% | | |
| T7. Skill Compliance | 10% | | |
| **TOTAL** | **100%** | | |

**Thresholds:**
- >= 4.5: Ship as-is
- 4.0-4.4: Ship with minor edits
- 3.5-3.9: Rewrite weak sections before sharing
- < 3.5: Major rewrite — do not share

**Weight rationale:** T1 and T2 together are 40% because getting the right answer with correct facts is the floor. An insightful, well-structured report built on a wrong conclusion or wrong facts is worse than a boring report that's right. T3 and T4 (30% combined) are what make the audit worth doing vs just reading the Omni dashboard. T5-T7 (30% combined) are execution quality — important but not the main event.

---

## Self-honesty check

Before submitting the evaluation, ask yourself:

1. **Did I give scores that reflect what I would give a colleague's work, or did I inflate them because this is my own?**
2. **Did I cite specific things from the report, or did I write vague justifications?**
3. **Did I identify at least one real weakness, even if the overall quality was high?**
4. **For every `[MISSING_INSTRUCTION]` tag: did I actually check SKILL.md and DIAGNOSTICS.md, or did I assume?**
5. **For every `[EXEC_ERROR]` tag: was the data actually available, or am I retroactively blaming myself for something I couldn't have known?**
6. **Did I run the Theme 2 cross-check** (fct_orders channel query, spend reconciliation, action existence check)?
7. **Does every row in the Section 4 table map to a concrete edit in a named file?**

An evaluation where every theme scores 4 or 5 with no improvements identified is almost certainly not honest. An evaluation where failure mode tags appear without citations is not grounded — recheck those before submitting.

---

## Quick pre-ship check (run before finalizing any report)

These are pass/fail gates. If any fails, fix before scoring.

1. Read the exec summary aloud. Can you explain the CE's paid health in 3 sentences? If not, rewrite.
2. Query `fct_orders` for this CE — does every channel with >$500 L4W revenue appear in Table 3 (Channel Breakdown)?
3. Point to any cell in the campaign cohort table — does it have an inline delta? If not, fix.
4. For each action — does it say WHO does WHAT by WHEN for HOW MUCH? If any element is missing, fix.
5. For each action — does the thing you're recommending NOT already exist? Check fct_orders and GAds campaign list.
6. Delete every sentence that starts with "Note:" or "ROI is defined as" or "Source:". Does the report still make sense? If yes, those sentences were unnecessary.
7. Is the report length proportional? HEALTHY with 0-1 flags: <200 lines. WARNING with 2-4 flags: 200-400 lines. FULL with 5+ flags: 400-700 lines. Over 700 lines for any CE status = too verbose.

---

## Applying this evaluator to past reports

### Antelope Canyon (2026-05-14) — retroactive eval

The Antelope Canyon report scored 4.72 on the old checklist EVAL but would have scored lower on this evaluator:

- **T2 (Factual Correctness): 2** — Section 1 Table 3 initially stated "No Bing campaigns" and "No PMax" when Bing was generating $20.4K and PMax $26.1K. This is a credibility-destroying error. `[EXEC_ERROR]`: SKILL.md Section 1 Table 3 requires BQ attribution data; fct_orders had the data; report used GAds MCP campaign list instead.
- **T5 (Investigation Adaptivity): 3** — 600+ lines for a HEALTHY CE with 2 optimization levers (LP routing + Spanish scaling). SKILL.md Step 8 says "0-1 flags = SHORT (~1 page)" — this CE arguably warranted STANDARD, not FULL.
- **T6 (Action Specificity): 3** — Action #5 recommended "Launch Bing" when Bing was already live and growing +1,594% YoY. Recommending something that already exists is worse than a vague action — it shows the analyst didn't check.

This retroactive example demonstrates why the old eval was insufficient: it checked structure (inline deltas present? geography table present?) but not substance (are the claims actually true?).
