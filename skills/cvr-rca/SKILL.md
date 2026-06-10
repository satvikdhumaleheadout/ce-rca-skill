---
name: cvr-rca
description: >
  CVR Root Cause Analysis for a Headout Combined Experience (CE). Use this skill
  whenever someone mentions a CVR drop, conversion decline, funnel performance
  issue, or asks for an RCA on bookings/orders for a specific CE — even if they
  don't use the phrase "CVR-RCA". Also triggers when someone says "why did CVR
  fall for CE X", "diagnose this funnel", "conversion is down on experience Y",
  or any similar phrasing. Run /cvr-rca or invoke whenever a funnel investigation
  is needed.
---

# CVR Root Cause Analysis

## Before you begin

Derive the skill directory from the path of this SKILL.md file you just read.
For example, if you read it from `~/.cvr-rca/SKILL.md`, then:

```bash
SKILL_DIR=~/.cvr-rca
```

If the user has a custom install location, use that path instead. The variable
must point to the directory that contains this file.

**Reference files are loaded per phase, not upfront.** When a phase reads a
reference, it reads the **whole file** — splitting into per-section reads
would constrain cross-pattern reasoning that produces non-obvious findings.

Per-phase reads:
- **Step 1** (run pipeline) — `SKILL.md` only (this file).
- **Step 2** (investigation: L0 / cascade / L2+ branches / sub-agent
  reconciliation) — read `references/context.md` and `references/hypothesis.md`,
  both fully.
- **Step 3** (write the report) — read `references/actions.md` and
  `references/report_structure.md`, both fully.
- **Quality evaluation** (on-demand, not part of the run) — read `evals/evaluator.md`.

### Version check

Run this before proceeding:

```bash
INSTALLED=$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo "0.0.0")
LATEST=$(curl -s --max-time 3 \
  https://raw.githubusercontent.com/satvikdhumaleheadout/cvr-rca-skill/main/VERSION \
  2>/dev/null || echo "unknown")
MIN=$(curl -s --max-time 3 \
  https://raw.githubusercontent.com/satvikdhumaleheadout/cvr-rca-skill/main/MIN_VERSION \
  2>/dev/null || echo "unknown")
```

- If `LATEST` or `MIN` is `unknown` (no internet): continue silently.
- If `INSTALLED` < `MIN`: **stop**. Tell the user:
  > "Your CVR-RCA skill (v`INSTALLED`) is below the minimum required version
  > (v`MIN`). Please update before running: see `~/.cvr-rca/INSTALL.md`."
- If `INSTALLED` < `LATEST` (but ≥ `MIN`): continue, then append a soft note at
  the end of Step 1 output:
  > "A newer version of CVR-RCA (v`LATEST`) is available. Run the update steps
  > in `~/.cvr-rca/INSTALL.md` when convenient."
- If `INSTALLED` = `LATEST`: continue silently.

Each file owns a distinct concern:

**`context.md`** — data vocabulary, table schemas, query rules, dimension meanings,
and funnel step definitions. Read this before writing any query.

**`hypothesis.md`** — the central branch reference for the investigation. Two levels:
(1) L0 routing map and first-pass branch sets by funnel step — which branches to open
at each level; (2) historical patterns from 21 Headout RCAs — specific mechanism
hypotheses for each confirmed scenario. Read this at Step 2 before forming any branch.

**`actions.md`** — cause-to-action mapping. Once a root cause is confirmed, find
the matching category here and use the listed actions for the report's action cards.

**`report_structure.md`** — CVR-RCA-specific report structure. Section 1/2/3
macro-layout, "What belongs in Section 3" table, CVR-RCA-specific block specs
(Mix cascade, Fixed Segment banner, Geo overview, Shapley flex bar, Hypotheses
Explored, etc.). Read at Step 3, alongside `visual_kit.md`.

**`visual_kit.md`** — shared visual primitives. CSS, HTML patterns for header /
metric cards / callout / action cards / analysis blocks / tables / tab framework /
↗ link-to-table pattern / Slack integration. Skill-agnostic — any HTML-report-
producing skill reads this. Read at Step 3, alongside `report_structure.md`.

---

## On reading references — a note on freedom

You have complete freedom to form hypotheses, design queries, and follow the
data wherever it leads. The reference files are not a checklist — they are
the shared context that lets you exercise that freedom precisely.

- `context.md` gives you the data vocabulary: table schemas, column meanings,
  query rules, dimension definitions. It is the language. Use it so the
  queries you write are technically correct against the actual tables.
- `hypothesis.md` gives you historical patterns: what other investigations
  found, where to look first when a particular signal appears. These are
  starting points, not a menu. When the data points to a mechanism the
  patterns don't cover, follow the data — invent the cross-cut, write the
  custom query, propose the novel finding.
- `actions.md` (Step 3 only, after the root cause is confirmed) gives you
  the cause-to-action library. Novel root causes can produce novel actions,
  not just remixes from the library.

Reference files are loaded whole when loaded — never in slices. The freedom
is what matters; the references are what make the freedom precise rather
than vague.

---

## Your role

A GM has noticed CVR dropped for a specific CE. Your job is to figure out what
actually happened and what to do — not to run every analysis available, but to
run the right ones.

The output is an HTML report that reads like a story: here is what we found, here
is why it matters, here is what to do. Every chart and table earns its place by
being necessary to the finding.

---

## Invocation

```
/cvr-rca <ce_id> [<pre_start> <pre_end> <post_start> <post_end>]
```

Dates are optional. When omitted, the script defaults to **last 30 days vs the
30 days before that** (yesterday back 30 days = post; the prior 30 days = pre).

---

## Step 1 — Run the baseline queries

```bash
bash "$SKILL_DIR/scripts/run_analysis.sh" \
  <ce_id> <pre_start> <pre_end> <post_start> <post_end>
```

This produces `summary.json` inside a run folder under
`~/Documents/CVR RCA Runs/` (or `$CVR_RCA_OUTPUT_DIR` if set). The folder is named
`ce<ce_id>_<pre_start>_<post_end>/`. If that folder already exists (a previous
run on the same CE and dates), the script auto-increments: `_run2/`, `_run3/`,
etc. The script prints the chosen folder name — call it `<run_dir>` for the
rest of this document.

`summary.json` contains: CE metadata, headline funnel rates, Shapley, MB/HO +
paid/non-paid mix, mix dominance, daily pre/post trend (`trend`), and the
90-day rolling trend + LY context (`trend_context`).

Everything beyond the baseline — dimensions, experience breakdowns, price,
URL-level funnels — is your responsibility to query from scratch. `context.md`
has every table schema and column definition you need. Write the query that
tests your specific hypothesis.

If the script fails: check `gcloud auth application-default login` and that `bq`
is on `$PATH`.

---

## Data pull errors — log and continue

At any point a query may fail or return empty. When this happens:

**Do not stop. Do not retry in a loop.**

1. **Log the failure** in the investigation transcript:
   ```
   ### [Data pull failure — <query name>]
   Error: <exact error message or "empty result">
   Impact: <which part of the analysis this affects>
   Workaround: <what you will use instead, or "none available">
   ```

2. **Add a data-gap note in the report** wherever the missing data would have
   appeared:
   > ⚠️ **Data unavailable — [query name]:** [one sentence on what failed and
   > what it means for this finding]. Analysis continues with available data.

3. **Continue the investigation** using everything else that did return.

4. **Adjust confidence language** in the root cause callout if the missing data
   was material. Use "consistent with" rather than "confirmed by" for that claim.

**Scope:** applies to all data pulls — BQ queries and the baseline pipeline.

---

## Step 2 — Investigate

**Now read the investigation references:**

```bash
cat "$SKILL_DIR/references/context.md"
cat "$SKILL_DIR/references/hypothesis.md"
```

Both are loaded for the entire investigation phase. Cross-pattern reasoning
across them is expected — a pattern in `hypothesis.md` often combines with a
query template in `context.md` and a creative cross-cut to produce the leaf.

Read `summary.json`. Then run the investigation as a tree: orient at L0 using
everything that is already computed, open branches at L1, descend to a leaf.

### Slack context — fire and forget

Before reading any data, spawn the Slack context sub-agent. Pass it the values
below (all available from `summary.json`), then continue immediately — do not
wait for it to return. You will read its output at Step 2b check #9, not before.

```
Sub-agent instruction file: "$SKILL_DIR/references/slack_context_guide.md"

Pass:
  ce_id       → meta.ce_id
  ce_name     → meta.combined_entity_name
  market      → meta.market
  country     → meta.country
  pre_start   → pre-period start date
  post_start  → post-period start date
  post_end    → post-period end date
  run_dir     → <run_dir>
  output_path → <run_dir>/slack_context.md
  user_channels → orchestration.json `user_slack_channels` (if present; else omit)
```

The sub-agent runs entirely in the background. It has no access to the
investigation and forms no hypotheses. Its only job is to collect and categorise
Slack signals into `<run_dir>/slack_context.md`.

---

### Start the investigation transcript

Before reading the data, open the transcript file. The run directory was
already created by the baseline script — write the transcript there:

```
<run_dir>/transcript.md
```

The transcript has two layers: a **tree map** at the top that shows the full
branch structure at a glance, and **detail sections** below with query results.
Write both as you go.

````markdown
# Investigation Transcript — CE [id] · [name]
Pre: [dates] | Post: [dates]

## Tree map
<!-- Update this block each time a branch resolves. Keep the tree inside the ```text
     fence below so its alignment survives markdown rendering in the umbrella report. -->
```text
L0: [primary signal summary — e.g. "S2C (83% Δ) · gradual · structural"]
├─ L1a: [hypothesis name]  →  [CONFIRMED / RULED OUT / OPEN] ([one-line evidence])
├─ L1b: [hypothesis name]  →  [CONFIRMED / RULED OUT / OPEN] ([one-line evidence])
│   └─ L2a: [sub-hypothesis]  →  [CONFIRMED / RULED OUT] ([one-line evidence])
│       └─ LEAF: [mechanism in one line]
└─ L1c: [hypothesis name]  →  [RULED OUT] ([why])
```

---

## L0 — Orient
**mix_dominance:** [is_dominant value + what it means for this CE]
**shapley:** [LP2S Xpp · S2C Xpp · C2O Xpp — primary step and share of ΔCVR]
**trend_context:** [shape: sharp/gradual/recovery + pre_period_healthy + structural_delta_cvr]

## L1 — [descriptive label for this level's focus]
### [Hypothesis A name] · [Hypothesis B name] — parallel

**[Hypothesis A]**
Query: [what you tested and why]
Result: [key numbers — rates, counts, deltas]
→ CONFIRMED — opens L2: [sub-hypotheses] | Closes: [what this rules out]

**[Hypothesis B]**
Query: [...]
Result: [...]
→ RULED OUT — [reason in one line]

## L2 — [descriptive label]
### [Hypothesis C name]

**[Hypothesis C]**
Query: [...]
Result: [...]
→ CONFIRMED — LEAF reached

## Root cause confirmed
[One paragraph: the mechanism, the segment, the timing — fully stated.
Every number here must trace to a named query result in the detail sections above.]
````

**Tree map = fenced.** Write the tree map inside a ` ```text ` … ` ``` ` code fence (as shown);
the detail sections stay plain markdown. The umbrella report renders the transcript as markdown, so
the fence is what keeps the `├─ │ └─` alignment intact.

**How to use the tree map:** Start it after L0 with all L1 branches marked
`OPEN`. Update each entry to `CONFIRMED` or `RULED OUT` as results come in.
Add child branches (`└─ L2a`) only when a parent confirms. When the primary
leaf is reached, mark it `LEAF` — then check whether any other signal you
explicitly quantified during the investigation remains open. Each open signal
becomes a new branch in the map. Anyone reading the transcript sees the full
investigation shape in the map before reading a single detail section.

If a branch produces nothing actionable, mark it `RULED OUT` in the map and
write one line in the detail section explaining why. Do not descend further.

Any signal you explicitly quantified (computed a specific rate delta or
checkout impact for) must appear as a named branch in the map. A branch may
only be closed as CONFIRMED, RULED OUT, or DATA GAP — not left as a
narrative observation or inline inference in a detail section.

Note on depth vs completeness: the "every quantified signal needs a branch"
rule is about map completeness — making sure the reader can see what was
checked. It does not require deep investigation of every branch. If a
quantified finding is below the 10% Shapley threshold or already explained by
the same mechanism as a higher-priority branch, a one-line closure (e.g.,
"same mechanism as C2O — CONFIRMED" or "A2O within-experience improvement:
mechanism untested — DATA GAP") satisfies the completeness rule without
requiring a full investigation branch. When in doubt: add the branch, write
one line, close it with a status label.

---

### L0 — Orient from summary.json

Read `summary.json` and extract all three orientation signals at once. These
three signals are read simultaneously — they are not a sequential gate.

**Signal 1 — mix_dominance (preliminary orientation)**

Check `mix_dominance.is_dominant` as a first read. If true, the L1 cascade
is likely to find a mix exit early — be prepared for a routing story. If
false, the cascade is likely to confirm conversion changes at all levels.

This is orientation only — not a gate. The L1 cascade is what actually
determines whether the story is routing or conversion, and at which level.
Do not skip the cascade based on this signal alone.

See `context.md` → "MB vs HO" and "Channels" for what mix signals mean.

**Signal 2 — shapley (which step is the story)**

Check `shapley`. Note which step(s) carry the majority of ΔCVR — this will
direct L2+ branches after the cascade determines the fixed segment. Do not
open funnel queries yet; that comes after L1. Do not deep-dive steps that carry
less than ~10% of the delta — even if a rate change is visible there, it is not
the driver.

The Shapley delta for each step is a quantified signal. Any step whose absolute
contribution you read and recorded counts toward the "close every quantified
signal" requirement at the end of L2+, regardless of whether it is the primary
driver. Record the contribution for every step now so the closing check can act
on it.

See `hypothesis.md` → "L0 signal → first branches to open" for how each
shapley outcome maps to L2+ branch sets (used after the cascade, not before).

**Signal 3 — trend_context (timing and seasonal calibration)**

Read the 90-day trend shape, `pre_period_healthy`, `structural_delta_cvr`, and
the weekday composition:

- **Sharp break** → something changed on a specific date. That date is the
  most important clue. L1 branches should include a date-of-change cut.
- **Gradual erosion** → something has been compounding. Look for trends in
  supply, pricing, or traffic quality rather than a single event.
- **Recovery in progress** → the pre window may already be below normal; the
  pre/post delta understates the real change.
- **seasonal component** → compare `current_delta_cvr` to `ly_delta_cvr`. If
  `structural_delta_cvr` is small, calibrate investigation depth accordingly.
  A small structural delta raises the bar for concluding "new problem".
- **Weekday composition** → count weekday vs weekend days in pre and post. A
  post period heavy in weekends can produce apparent drop with no real change.

See `context.md` → "Q3 Trend Interpretation" for full interpretation guide.

**Signal 0 — user context (if present): priors that steer, not narrow**

Check for `<run_dir>/user_context.md` — the manifest at
`<run_dir>/orchestration.json` names it under `user_context` when the CE-RCA
umbrella captured it; on a standalone run, detect it by file presence. If it
isn't there, skip this signal entirely (most runs).

When it *is* there, it carries the analyst's **Focus**, **Hypothesis priors**,
and **Known events**. Treat it differently from every other external input:

- **It is the one input allowed to steer branch selection.** Slack, perf-audit,
  and CE Health are *lenses* — secondhand evidence held to Step 2b so they can't
  bias the investigation. User context is the analyst's **intent**, which
  legitimately directs where to look. So you read it here, at L0 — the deliberate
  exception to the "lenses consulted only at Step 2b" rule.
- **Priority, not tunnel-vision.** Each Hypothesis prior and Known event becomes
  a **prioritised, falsifiable** first-pass branch — opened early in L2+,
  *tested*, and able to be **RULED OUT**. Focus indicates which funnel step
  leads. But these branches are **appended to** the data-driven default set, never
  a replacement for it: Signals 1–3 (mix_dominance, shapley, trend) still run in
  full and still determine the primary driver. **The data decides the leaf**, even
  if it lands somewhere the user didn't point.
- **Known events → chart markers.** A Known event with an in-window date also
  gets a dated marker on the relevant daily/90-day trend chart (see `visual_kit.md
  → "Known-event markers"`), so the reader sees when it landed. It **never moves
  the analysis window** — the window is fixed at Step 0; the event annotates, it
  doesn't re-scope.
- **Always closed.** Every user prior must be resolved as CONFIRMED / RULED OUT /
  DATA GAP in the tree map — same discipline as the "close every quantified
  signal" rule at the end of L2+. A prior is never silently dropped.
- **Lean + proportional.** `user_context.md` is short by construction; don't let
  it expand the investigation's scope or the report's emphasis beyond what the
  data supports (proportional output is enforced at Step 2b / Step 3).

Example: a prior "LP2S looks broken at the landing-page level" → open an
LP2S × `page_url` branch early and test it; if shapley says S2C is the real
driver, S2C still leads the report and the LP2S prior is closed (CONFIRMED as a
secondary factor, or RULED OUT in one line).

---

### L1 — Mix cascade (routing vs conversion determination)

Run the cascade now — before opening any LP2S, S2C, or C2O branches. The
cascade has three levels. At each level, determine whether the change is a
**mix change** (traffic composition shifted → routing story, exit here) or a
**conversion change** (rates declined within the segment → fix it, descend to
the next level). The fixed segment produced by completing all three levels is
the filter that every subsequent funnel query carries.

**Level 1 — MB vs HO** (from `summary.json`, no query needed)
Compare mix_effect vs conversion_effect for MB and HO.
- Mix exit → investigate why HO traffic fell or MB grew (routing story)
- Conversion → fix dominant brand, run Level 2

**Level 2 — Paid vs Organic within fixed brand** (BQ query)
Compare mix_effect vs conversion_effect for Paid vs Organic.
- Mix exit → investigate why paid/organic share shifted (campaign paused, budget cut)
- Conversion → fix dominant type (almost always Paid), run Level 3

**Level 3 — Channel breakdown within Paid** (BQ query)
Compare mix_effect vs conversion_effect per paid channel.
- Mix exit → investigate why budget or impression share shifted between channels
- Conversion → fix dominant channel (e.g., Google Search) — this is the fixed segment

Full query templates, the mix vs conversion test, and the decision rule are in
`context.md` → "Mix Cascade — Routing vs Conversion Determination".

Declare the outcome in the transcript before opening any funnel branches:
- Conversion path: `Fixed segment: [MB/HO] · [Paid/Organic] · [channel]` + filters
- Routing exit: `Mix change at Level [X] — [reason]`. Then follow the routing
  exit investigation path in `hypothesis.md` → "Mix — first-pass branches" for
  that exit level (timing → sub-segment cut → URL impact → declare).

Log the cascade as its own L1 section in the tree map.

### Perf-audit context — fire and forget (Paid-side only)

If the cascade fixed on Paid — either via a conversion path that included Paid
at Level 2 or Level 3, or via a mix exit at Level 2 (Paid/Organic shift) or
Level 3 (channel shift within Paid) — spawn the perf-audit sub-agent now and
continue immediately. The sub-agent runs in the background. You will read its
output at Step 2b check #10, not before. **Do not consult it during the L2+
investigation** — the data-driven branches must reach their own leaves before
the perf-audit verdict is read, so it corroborates or surprises a completed
picture rather than steering branch selection. Mirrors the Slack pattern.

Skip the spawn when the fixed segment is Organic, or when the perf-audit skill
is not installed (path resolution fails — see below).

**Delegation check (master-orchestrated runs).** Before deciding to spawn, check
if `<run_dir>/orchestration.json` exists. If it does, parse it; if
`perf-audit-skill` appears in its `fired_by_master` array, a parent orchestrator
(e.g. the CE-RCA master skill) is already running perf-audit against this same
run directory. Log one line in the transcript —
`Perf-audit spawn delegated to <orchestrator> (orchestration.json) — will consume existing output at Step 2b check #10` —
and **do not spawn**. Proceed with the cascade and L2+ investigation exactly as
normal. The Step 2b check #10 polling logic below ("if the file does not exist
yet, wait briefly... if still missing after a short wait, log 'Perf-audit
unavailable — skipped'") already handles any timing race between this skipped
spawn and the master's parallel perf-audit run — whoever writes
`perf_audit_report.md` first, you read it at Step 2b.

As a secondary safety net, if `<run_dir>/perf_audit_report.md` already exists at
this point (e.g. pre-staged without an orchestration file), likewise skip the
spawn and consume the existing file. The `orchestration.json` check is the
primary mechanism; this is belt-and-braces.

If neither file is present, fall through to the normal spawn logic below —
standalone `/cvr-rca` runs are unchanged.

**Path resolution.** The perf-audit skill is distributed separately at
`https://github.com/aaradhyaraiHO/perf-audit-skill`. Look for its `SKILL.md`
in this order, taking the first match that exists:

1. `$PERF_AUDIT_SKILL_PATH` (env var, if set)
2. `$HOME/.perf-audit-skill/SKILL.md` (companion install — see `INSTALL.md`)
3. `$SKILL_DIR/../perf-audit-skill/SKILL.md` (sibling directory)
4. `$HOME/Documents/perf-audit-skill/SKILL.md` (legacy local default)

If none resolve, log one line in the transcript — `Perf-audit skill not
installed — skipped (install at https://github.com/aaradhyaraiHO/perf-audit-skill)` —
and proceed to L2+. CVR-RCA runs fully without it.

**Spawn block** (use the resolved path as `<perf_audit_skill_md>`):

```
Sub-agent role: paid-performance auditor

Skill: read "<perf_audit_skill_md>" and follow its instructions. The skill is
self-contained — its bundled references and scripts sit beside that file.

Pass:
  ce_name      → meta.combined_entity_name
  ce_id        → meta.ce_id
  pre_start    → pre-period start date
  pre_end      → pre-period end date
  post_start   → post-period start date
  post_end     → post-period end date
  run_dir      → <run_dir>
  trigger      → "conversion-path" or "routing-exit-L2" or "routing-exit-L3"

Run the full perf-audit using the pre/post windows above as the comparison
windows. When complete, write TWO files:

1. Full report → <run_dir>/perf_audit_report.md (verbatim perf-audit output)

2. Structured summary → <run_dir>/perf_audit_summary.md in EXACTLY this shape
   (use literal "n/a" if a field can't be determined):

   ## Perf-Audit Insight Summary

   **Overall verdict:** HEALTHY | WARNING | CRITICAL | DATA GAP

   **Traffic quality:**
   - SIS trend: stable | up X pp | down X pp (rank-lost X%, budget-lost X%)
   - CPC trend: stable | up X% | down X%
   - Paid CVR trend: stable | up X pp | down X pp
   - Assessment: IMPROVED | DEGRADED | STABLE | DATA GAP

   **Campaign status:**
   - Paused/dormant campaigns in post-period: none | <list with dates>
   - tROAS self-suppression (ROI up + clicks down): yes | no
   - Budget exhaustion (spend/budget ≥ 0.95): yes | no

   **Key finding (one sentence):** [the single most important insight for the
   CVR-RCA — e.g., "Traffic quality improved (SIS +3pp, CPC quality lens
   positive) — funnel drop is page-driven, not traffic-driven."]

   **Surprise / new hypothesis (optional):** [if perf-audit surfaced
   something CVR-RCA's dimension cuts wouldn't catch — a creative rotation,
   an auction-insights competitor surge, a Performance Max audience
   expansion, a campaign paused on a specific date — name it here as a
   one-sentence hypothesis with a date if available. Leave blank if nothing
   surprising.]

Return only the contents of perf_audit_summary.md as your final message; the
full report is already on disk.
```

The sub-agent receives no CVR-RCA files (SKILL.md, hypothesis.md, context.md).
It only gets the perf-audit skill path, the CE, and the date windows. It runs
in its own context — context isolation is required so it diagnoses the paid
side independently rather than reasoning about the CVR-RCA investigation.

If the sub-agent returns `DATA GAP: no campaigns` (the CE has no active Google
Ads campaigns in the windows), that is a legitimate outcome — not a failure.
Step 2b will note it in findings and move on.

### L2+ — Branch and descend (all queries filtered to fixed segment)

The cascade is complete and the fixed segment is declared. Now use the Shapley
step identified at L0 to direct the first set of branches. Start with the
primary funnel step — LP2S if LP2S dominated, S2C if S2C dominated, C2O if
C2O dominated. Every query from this point carries the fixed segment filters. Each branch is a specific, falsifiable hypothesis about why
that funnel step dropped — **or rose** — in the fixed segment.

**Direction matters for branch selection.** When the primary step moved
positively (CVR improvement RCAs), the default branches are different from the
decline patterns. Consult `hypothesis.md → "Improvement direction — first-pass
branches"` for the parallel branch sets. The data-driven patterns (catalogue
change, supply expansion, pricing/promo levers, channel quality improvement)
are direction-sensitive: a fall in `days_to_first_available_date` is
improvement-relevant; a rise is decline-relevant. The skill is bidirectional
by design.

**Catalogue change is a first-class hypothesis in both directions.** When
the experience-level breakdown shows a top experience whose checkout volume
changed substantially pre/post (≥20% relative or accounting for ≥10% of the
net change), test whether a TGID launched or was disabled within the window.
Use the catalogue-change query in `context.md → "Catalogue change query"` —
no Slack input required to trigger this. It is a data-driven first-pass
branch, not a retrospective check after Slack reconciliation.

A branch is a hypothesis, not an observation. Name the mechanism, the segment
or experience, and the pattern you would expect if it were true:

- *Observation* (wrong): "S2C dropped on mobile"
- *Hypothesis* (right): "The Apr 8 mobile deploy broke date-picker rendering
  on iOS, causing users to see no available slots and abandon the select page"

**Where branches come from:** Open the first set of branches using the
first-pass branch sets in `hypothesis.md` for the primary funnel step — those
patterns are the default starting set. Run the first set in parallel, then read
the results. Each result either opens a new branch, closes one, or concentrates
the investigation — and what the data shows determines what the next branches
are. The branches are not written upfront as a fixed list; they grow level by
level from what the data actually shows. Consult `hypothesis.md` for historical
priors, but don't treat any list as a ceiling.

**First-pass batch — parallel sub-agents**

The first-pass branch set (from `hypothesis.md` for the primary funnel step) is
the only level that runs in parallel via sub-agents. Deeper levels (L2, L3) are
sequential — each builds on what the level above found.

**Step 1 — Write SQL for every cut first.** Before spawning anything, write the
complete SQL for each cut in the first-pass set. Substitute the fixed segment
filters, `ce_id`, and date ranges into every query now. Sub-agents receive
finished SQL — they do not modify it.

**Step 2 — Open the transcript section.** Write `## L2 — First-pass batch
(parallel)` in `transcript.md`. List each cut name and its SQL. Leave the result
field blank — it will be filled after the batch completes.

**Step 3 — Spawn one sub-agent per cut in a single parallel batch.** Each
sub-agent receives exactly three things:

- The complete SQL (verbatim)
- Output path: `<run_dir>/batch_<cut_name>.json`
- Output contract: *"Run this query with `bq query --use_legacy_sql=false
  --format=json --quiet --project_id=headout-analytics`. Write the raw JSON
  output to the output path. Return exactly one line:
  `<cut_name>: <pre_rate>% → <post_rate>% (±Xpp), N post-period sessions`."*

Pass nothing else — no SKILL.md, no context.md, no hypothesis.md. Sub-agents
are query runners. Passing reference files causes them to reason about the
investigation instead of executing the query, which contaminates the synthesis
the main agent does in Step 5.

**Step 4 — Wait for all sub-agents to complete** before reading any result.
Do not act on partial results. The synthesis in Step 5 requires the full picture.

**Step 5 — Fill in transcript and synthesise.** Copy each sub-agent's one-liner
into the transcript section. Then write the hypothesis synthesis from the
combined picture — not from each result in isolation. Read the full
`batch_<cut_name>.json` for any cut you plan to descend into.

**Batch failure handling:** If a sub-agent returns no file or an empty JSON,
log it as a DATA PULL FAILURE in the transcript (same format as the "Data pull
errors" section above) and continue with the remaining results. Do not re-run the
query inline. Adjust confidence language for any branch where the missing cut
was material.

Each result either:
- **Confirms** → descend: open a child branch that tests the mechanism more
  specifically — write that branch from what you just saw, not from a template
- **Rules out** → close the branch, state why in one line, do not revisit
- **Concentrates** → the segment or experience with the largest impact becomes
  the anchor; the next branch asks *why* it concentrated — what mechanism
  explains that specific segment being affected?
- **Surprises** → something unexpected appeared (an unexplained number, a
  pattern inconsistent with the story so far) — open a new branch to test it,
  even if it wasn't in the default set

Continue descending (L2, L3 if needed) until you reach a leaf: a specific
mechanism at a specific segment/experience/URL/date that fully explains both
the rate delta and the volume impact. If you've run the default patterns and
have no leaf, that is a signal to look harder — at cross-cuts not yet tested,
finer grain not yet drilled, or tables beyond the funnel table. Queries at
each level are written from scratch — full table schemas and column
definitions are in `context.md`.

**A leaf for the dominant driver is not the same as a complete
investigation.** After confirming the primary leaf, look back at every signal
you explicitly quantified during the investigation — any experience, funnel
step, or dimension where you computed a specific rate delta or checkout
impact. Each of those is a signal you already judged worth measuring. For any
such signal whose drop is not yet explained by a confirmed mechanism, generate
a new hypothesis from the context you have (the data in the transcript, the
inventory findings, the timing pattern) and test it. Do not investigate
signals you noted but did not quantify — those are observations, not
commitments. "Consistent with X" without a test is an open branch, not a
closed one. Close every quantified signal as CONFIRMED, RULED OUT, or DATA
GAP before declaring the investigation complete.

The question for a secondary funnel step is narrower than for the primary:
not "what broke and why?" but "is this an independent mechanism, or is it
explained by what we already found?" A single decomposition query (e.g.,
reading `c2o_sub` from `summary.json` and running the fixed-segment
aggregate) is usually sufficient to close it. If the secondary step is flat
or improved within the fixed segment, state that the CE-level Shapley figure
originates outside the fixed segment and close the branch. Only descend
further if the secondary step shows a meaningful decline *within the fixed
segment* that is not directionally explained by the primary finding — that is
the signal that an independent mechanism exists. Do not open sub-branches on
noisy data: if the daily volume reaching the secondary step is low (fewer than
~20 events per day on average), note the data limitation and close the branch
as DATA GAP rather than chasing high-variance day-level patterns.

Run queries with:
```bash
bq query --use_legacy_sql=false --format=json --quiet \
  --project_id=headout-analytics \
  <<'SQL'
  ... your query ...
SQL
```

---

## Step 2b — Synthesise findings and review

Before writing HTML, write a structured findings summary. This is not a draft
report — it is a short markdown file that forces every major claim to be made
explicit and checked before it is committed to the report.

Save to: `<run_dir>/findings.md`

**Write the findings summary:**

```markdown
## Root cause
[One sentence: what broke, in which segment, by how much]

## Mechanism
[The causal chain — what actually happened, not just what the data shows]

## Timing
[Sudden / gradual / seasonal — and the key evidence for that classification]

## Evidence inventory
| Claim | Supporting data | Source | Confidence |
|-------|----------------|--------|------------|
| [claim] | [specific numbers or observation] | [summary.json field / query result / report table row] | Confirmed / Consistent with / Unverified |

## Open items
[Each Consistent with / Unverified row that a query could close]
[Any number surfaced in the investigation that has no place in the narrative]
[Any recommendation you plan to make that you have not verified yourself]
```

**Then re-read it critically and resolve each open item:**

- **Query would close it** → write and run it, update Evidence inventory
- **Arithmetic on existing data** → compute it, add result to Evidence inventory
- **Genuinely unresolvable** → accept "Consistent with" and ensure the report
  language reflects that — do not present it as confirmed

**Checks before proceeding to Step 3 (work through in order):**

1. **Weekday composition** — count weekday vs weekend days in pre and post. If
   post has materially more weekends, note this before attributing any rate
   change to a funnel issue.
2. **Seasonal / calendar event claim** — if a seasonal or event-based
   explanation is a primary or secondary driver, is it paired with a
   corresponding data signal? (see `report_structure.md` Styling guidelines rule
   4). A traffic pattern, a CVR break aligned to the event date, or a
   controlled comparison qualifies. Domain knowledge of peak seasons alone does
   not.
3. **Every number has a source** — every count or rate in findings.md must name
   its source (a `summary.json` field, a logged BQ query result, or a specific
   table row). If a source cannot be named, derive it with written arithmetic or
   remove it. A number with no named source must not enter the report.
4. **Every numeric recommendation verified** — if an action card includes a
   specific percentage, count, or dollar figure, derive it with written
   arithmetic before committing it to the report. Do not estimate.
5. **Backlogged branches marked DATA GAP** — any branch whose evidence requires
   a backlogged source must be closed as `DATA GAP` in the tree map, not
   `CONFIRMED` or `LEAF` (see Backlogs section above).
6. **Fixed segment reflected in analysis** — if you declared a fixed segment
   (e.g., MB · Paid · Google Ads) at the end of the mix cascade, check that
   L2+ queries actually apply those filters. If a broader cut was used as a
   proxy (e.g., Paid MB instead of Google Ads), note that explicitly in the
   transcript and confirm it's a reasonable approximation (e.g., Google Ads is
   >80% of Paid volume). Don't leave a silent mismatch between the declared
   segment and the data used.
7. **Action cards reference accessible data** — if an action card asks a team to
   investigate a specific period or data point, confirm that data is actually
   reachable via analytics. If it falls outside the rolling window or a
   backlogged table, note the limitation and name an alternative source (e.g.,
   availability system logs, supplier contracts) so the DRI knows where to look.
8. **Cross-cut run when two cuts both concentrated** — if two dimension cuts for
   the same funnel metric both showed a concentrated drop (≥8pp absolute or
   ≥20% relative), confirm the intersection query was run before both were
   reported as independent findings. See `hypothesis.md → "Dimension cross-cut"`
   for the trigger rule and `context.md → "Cross-cut query template"` for the
   query.

**Context reconciliation (checks #9–#12) — read every available lens.** Checks
#9–#11 each do the same thing with different inputs: reconcile your completed,
data-driven picture against an external **lens** (Slack, perf-audit, CE Health).
Check #12 closes the loop on user context (a different kind of input — see the
exception note below). They share one model and one hard rule.

- **The lens manifest.** Read `<run_dir>/orchestration.json` if it exists and
  use its `context_lenses` array as the authoritative list of lenses to
  reconcile (this is the master-orchestrated case — the CE-RCA umbrella declares
  exactly what ran). If there's no orchestration file (standalone `/cvr-rca`),
  fall back to file-presence detection: reconcile whichever of
  `slack_context.md`, `perf_audit_summary.md` / `perf_audit_report.md`,
  `ce_health_report.md` actually exist in the run dir. Either way, **only
  reconcile lenses that are present** — a lens that didn't run is simply absent,
  not an error. A `user_data_*` entry (a user-provided ad-hoc data pull) is just
  another lens — reconcile it with the same four-pattern model; cite it as
  user-provided (see `visual_kit.md`).
- **One model, applied per lens.** Every lens is reconciled with the same
  four-pattern classification — **A** direct corroboration, **B** mechanism
  explanation, **C** reframing context, **D** testable gap, or **Reject**. The
  pattern definitions are identical across lenses; only the lens's content and
  its cross-tab anchor prefix differ.
- **The hard rule — consult lenses ONLY here.** Never during L0/L1/L2. The
  fire-and-forget timing is deliberate: the data-driven investigation must reach
  its own leaf first, so a lens *corroborates or surprises a completed picture*
  rather than steering branch selection. This is what keeps the investigation
  honest.
- **User context is NOT a lens — it's the one exception.** `user_context.md`
  (the analyst's intent) is read earlier, at L0 (Signal 0), because intent
  legitimately steers where to look — unlike secondhand evidence. Here at Step 2b
  it gets a second pass (check #12): close each prior and corroborate it, with
  proportional output weight. So it appears at *both* ends, by design.
- **Scalable by design.** A future lens (e.g., an AOV-RCA sibling) is one more
  manifest entry reconciled with the same model — not a new mechanism. Checks
  #9–#11 below are the per-lens specifics for the three lenses that exist today;
  check #12 handles user context.
- **Reconcile widest-first, then synthesise together.** Read the lens that can
  most change your interpretation first: **CE Health (widest, upstream — can
  reframe the whole finding) → perf-audit (paid-side mechanism) → Slack
  (operational colour).** This is a reading-order hint, not a rail — the point is
  that a reframe from the widest lens (e.g. CE Health says the headline mover was
  AOV, not CVR) should land *before* you polish narrative the wider lens would
  demote. Then reconcile the lenses *together*, not in isolation: a signal two
  lenses agree on is stronger (raise confidence, no new query); a Pattern D gap
  flagged by two lenses is a priority test (still one query max).
- **Provenance contract — this governs the report, not the investigation.** You
  explored however an analyst would; this rule is purely about *attribution* of
  what you ended up using. **Any external signal that informs a callout, verdict,
  or narrative line must appear in two places: (a) woven in at the point of use,
  and (b) as one row in the Section 3 External Signals & Corroboration table
  (`block-market-context`), with a Source ↗ to the owning tab or thread.** This
  applies to every used signal regardless of pattern — a Pattern A corroboration
  is still a used signal and still earns a row. The table is the report's
  "sources cited": it renders whenever *any* lens contributed a used signal, even
  if other lenses were unavailable (a missing lens becomes a disclosure row, it
  does not suppress the table). If you didn't use a signal, leave it out — the
  table is exactly what you leaned on, nothing more. See `report_structure.md →
  "External signals & corroboration block"` for the HTML and
  `visual_kit.md → "External context integration"` for the four-pattern surfacing.

9. **Slack context reconciliation** — read `<run_dir>/slack_context.md`. If the
   file does not exist yet, wait briefly (the sub-agent may still be running);
   if still missing after a short wait, log "Slack context unavailable — skipped"
   and proceed. **Slack is consulted only at this point** — never during L0/L1/L2
   investigation. The fire-and-forget pattern is deliberate: the data-driven
   investigation must reach its own leaf before Slack is read, so Slack
   corroborates or surprises a *completed* picture rather than steering branch
   selection. For each signal in the file, classify into one of four patterns
   and route to the report per `report_structure.md → "Slack integration &
   link-to-table styling"`:

   **Pattern A — Direct corroboration.** The signal directly names the same
   mechanism, TGID, date, or segment as a finding already in findings.md. Add
   the Slack thread link to the Source column of the evidence inventory row it
   supports. Format: `[Author · date](slack-link)`. **For declines specifically:**
   when Slack corroborates a CONFIRMED finding whose action card is going to a
   DRI, *elevate* the citation in the relevant Section 3 verdict subtext from
   bare `(corroborated ↗)` to a named source `(per [Author · date] ↗)` — this
   moves the finding from "we measured it" to "we measured it AND the
   BDM/Supply/Marketing team has independent corroboration."

   **Pattern B — Mechanism explanation.** The signal names a specific causal
   mechanism (a deploy, an assortment cap, a pricing lever, a content update, a
   supplier API migration, a TGID launch) that explains a finding the
   investigation reached without naming the *why*. Route into Layer 1 narrative
   weaving in the relevant callout/verdict subtext AND surface as a row in the
   Section 3 External Signals block. No second query needed if the data-driven
   finding already exists.

   **Pattern C — Reframing context.** The signal introduces a metric or
   timeframe outside the report's primary comparison (YoY GBV, vs plan, macro
   demand shift) and would cause a stakeholder to act or prioritise differently.
   Route to a Layer 2 Important Context callout-item in Section 1 (high bar —
   apply the four decision-changing tests in `report_structure.md`) AND a row
   in the Section 3 External Signals block. Phrasing the citation correctly (how
   to name the differing timeframe in the same sentence, what counts as a
   silent timeframe switch) is a styling concern, not a process step — see
   `report_structure.md → "Timeframe-citation rule"`.

   **Pattern D — Testable gap.** The signal names a specific causal mechanism,
   TGID, date, or operational event that the investigation did not address.
   Only pursue if it passes all three filters: (a) specific — names a date,
   mechanism, or TGID, not just "things are slow"; (b) within the investigation
   window or causally upstream of it; (c) about this CE or its market category,
   not generic commentary. If it passes: run one query, update the tree map as
   CONFIRMED / RULED OUT / DATA GAP, update findings.md if the finding changes,
   and cite the prompt inline `(prompted by [Author · date] ↗)`. Maximum one
   query per gap signal. High-value gap categories to recognise: operational
   events such as MB assortment changes (cap raises/lowers, new TGID launches,
   TGID removals), pricing levers (5% last-minute discount, promo code
   introduction, fee structure change), content/title updates on top TGIDs,
   product restructures, supplier API migrations, vendor moves (manual FF
   mode, rate-sheet changes). These categories rarely surface in the funnel
   table directly but often explain residual unexplained C2A/C2O/LP2S movement.

   **Reject** — the signal does not pass any of the above patterns, or only
   confirms the symptom ("CVR is down", "bookings dropped"). Write one line in
   the transcript: "Slack signal '[summary]' — not pursued: [reason in 5
   words]." Do not include rejected signals in the report.

   **One citation per concept** — if the same Slack thread is the source for
   three sentences in a paragraph, cite it once at the most natural anchor;
   don't re-cite the same source line after line.

10. **Perf-audit reconciliation** (Paid-side only) — if the perf-audit sub-agent
    was spawned (cascade fixed on Paid), read `<run_dir>/perf_audit_summary.md`.
    If the file does not exist yet, wait briefly (the perf-audit may still be
    running); if still missing after a short wait, log "Perf-audit unavailable —
    skipped" and proceed. **Perf-audit is consulted only at this point** — same
    rationale as Slack: the data-driven branches must reach their own leaves
    first, so the perf-audit verdict corroborates or surprises a completed
    picture rather than steering branch selection.

    Add a dedicated evidence entry to findings.md:

    ```markdown
    ## Evidence: Paid traffic quality (perf-audit)
    - Verdict: [IMPROVED / DEGRADED / STABLE / DATA GAP]
    - Key metrics: SIS [X→Y], CPC [X→Y], Paid CVR [X→Y]
    - Campaign issues: [none / <list>]
    - Implication: [one sentence on what this means for the root cause]
    - Source: <run_dir>/perf_audit_summary.md (full report at perf_audit_report.md)
    ```

    Then route the verdict using the same four-pattern framing as Slack:

    **Pattern A — Direct corroboration.** Perf-audit's traffic-quality
    assessment aligns with a leaf already in findings.md. Example: dimension
    cuts located the LP2S drop on a specific URL set, and perf-audit reports
    `Assessment: IMPROVED` — high confidence the drop is page-driven, not
    traffic-driven. Note the corroboration in the leaf's evidence line and in
    the Section 3 verdict subtext — **and add a row to the External Signals
    table** per the provenance contract (a used corroboration is still a used
    signal; this is exactly the case that was silently dropping out before).

    **Pattern B — Mechanism explanation.** Perf-audit names a specific
    campaign-level event (a campaign paused on a date, tROAS self-suppression,
    budget exhaustion) that explains *why* the data-driven finding looks the
    way it does. Common with routing-exit triggers — CVR-RCA timed the mix
    shift, perf-audit names the campaign that caused it. Weave into Layer 1
    narrative in the relevant callout subtext and surface as a row in the
    Section 3 External Signals block. No second query needed.

    **Pattern C — Reframing context.** Perf-audit reports `Assessment:
    DEGRADED` while the CVR-RCA leaf is page/product-side. Both can be true,
    but the report's root cause callout must reflect both contributors —
    raise it to a Layer 2 Important Context callout-item in Section 1 with
    the perf-audit verdict named explicitly. Action cards may need to split:
    one to the page/product owner, one to the bidding/budget owner.

    **Pattern D — Testable gap (surprise).** Perf-audit's "Surprise / new
    hypothesis" field is non-empty and names something the data-driven
    investigation did not address. Only pursue if the hypothesis is
    CVR-RCA-testable (a date, a URL set, a segment that can be queried in the
    funnel table). If testable: run one query, update the tree map as
    CONFIRMED / RULED OUT / DATA GAP, update findings.md if the leaf changes.
    Maximum one query per surprise. If the surprise names a campaign-level
    event that CVR-RCA can't test (auction-insights competitor surge, creative
    rotation effect), treat it as Pattern B — narrate without re-querying.

    **Reject** — verdict is STABLE and no campaign issues and no surprise.
    Note in findings: "Perf-audit ran; traffic quality stable, no campaign
    issues — finding stands on data-driven evidence." This is a legitimate
    outcome and worth recording so the reader sees the check was performed.

    **DATA GAP outcomes** — if the sub-agent returned `DATA GAP: no campaigns`
    or `Verdict: DATA GAP`, record that in findings as the implication and do
    not infer traffic quality either way. Treat it like any other DATA GAP
    branch — the absence of evidence is not evidence.

    The perf-audit verdict (or its absence) must be reflected in the root cause
    callout of the final report whenever it changes the interpretation — i.e.,
    Pattern A, B, or C. For Pattern D, the surprise either gets folded into a
    leaf or rejected; either way it leaves a trail in the tree map. Reject and
    DATA GAP outcomes get a single line in findings and no special callout.

    **Cross-tab citations.** When the perf-audit report is present, Step 3 will
    emit it as a second tab in `report.html`. Every Pattern A/B/C/D citation
    you write into findings.md (and ultimately the report) must include a
    `↗` linking to the most relevant perf-audit anchor — the JS in the
    report template switches to the perf-audit tab and scrolls automatically.
    Citation phrasing and the anchor routing table (which finding type links
    to which `#perfaudit-*` section) live in
    `report_structure.md → "Tabbed report structure → Citation routing"`. Use
    the table; do not invent anchors. If `perf_audit_report.md` is empty or
    missing, the tab is omitted and citations should reference the
    `perf_audit_summary.md` file inline instead — but this is the rare path.

11. **CE Health reconciliation** (master-orchestrated runs) — if
    `<run_dir>/ce_health_report.md` is present (the CE-RCA umbrella ran CE Health
    first), reconcile your funnel findings against it. CE Health is the **wide,
    upstream** lens: it decomposed the CE's revenue move via Shapley across
    Traffic / CVR / AOV / Completion / Take Rate, and carries CE-level facts your
    funnel investigation doesn't see (per-channel revenue, per-TGID RPC, L12M
    trajectory). It finished in the master's Step 0, so it's always available
    here — no wait needed. Same hard rule: consulted **only** at this point, not
    during L0/L1/L2.

    The two highest-value reconciliations:

    **Entity-level cross-link (most common Pattern A).** When your investigation
    localized a funnel drop to a specific experience or TGID, check whether CE
    Health flagged that same entity at the revenue/RPC level. If CE Health shows,
    say, TGID 7148's RPC dropped 30% and you localized an S2C collapse on that
    same TGID — that's direct corroboration from a different altitude. Cite it on
    the leaf's evidence line and Section 3 verdict subtext:
    `(CE Health: TGID 7148 RPC −30% ↗)`.

    **Headline-driver reframe (Pattern C).** CE Health's Shapley names the
    *headline* mover of CE revenue. If it says CVR drove the revenue change, your
    funnel deep-dive is the headline story — proceed at full confidence. But if
    CE Health says the headline mover was **AOV** or **Completion Rate or Take
    Rate** (factors CVR-RCA doesn't investigate), your funnel finding is real but
    *not the headline* — say so explicitly in the root cause callout, and point
    the reader to the CE Health tab for the dominant driver. This prevents a
    correct-but-secondary funnel finding from being mis-presented as *the* reason
    CE revenue moved.

    Pattern B (CE Health names a mechanism your funnel finding lacked) and
    Pattern D (a CE Health fact you can test in the funnel table with one query)
    apply exactly as for the other lenses. **Reject** CE Health signals that only
    restate the symptom.

    **Cross-tab citations.** CE Health renders as its own tab in the composite
    with `#cehealth-<slug>` anchors. Every CE Health citation carries a `↗`
    linking to the relevant `#cehealth-*` section (e.g.
    `#cehealth-driver-diagnosis-shapley`, `#cehealth-top-tgids`). Slugs follow the
    same rule as perf-audit (lowercase, strip leading "N. ", hyphenate).
    **Standalone safety:** only emit a `#cehealth-*` citation when
    `ce_health_report.md` was actually present. A standalone `/cvr-rca` run has no
    CE Health lens and no CE Health tab, so it emits no such citation — never
    leave a dangling anchor.

12. **User-context reconciliation** (only if `user_context.md` was present) — you
    already read it at L0 (Signal 0) and opened the analyst's priors as
    prioritised branches. Now close the loop:

    **Close every prior.** Each Hypothesis prior and Known event from
    `user_context.md` must be resolved in the tree map as CONFIRMED / RULED OUT /
    DATA GAP — the same closing discipline as the "close every quantified signal"
    rule above. A user prior is never left open or silently dropped; that is the
    guarantee the analyst's input was actually used.

    **Corroborate, don't confirm.** Reconcile each against your data-driven
    findings with the same four-pattern model: **A** the data confirms the prior
    (it was right — say so, weave it in); **B** the prior names a mechanism your
    finding lacked (e.g. "pricing changed Apr 8" explains a price-driven S2C
    drop); **C** the prior reframes (the user pointed at LP2S but the driver is
    S2C — note both); **D** an untested prior worth one query. The prior carries
    no special authority — the data can **RULE IT OUT**.

    **Proportional output (the anti-overwhelm rule).** A user finding gets weight
    proportional to *what the data shows*, not to how strongly the user asserted
    it. Confirmed → woven into the relevant finding's narrative. Ruled out → a
    single line ("Checked LP2S at URL level per the user's note — ruled out; the
    drop was CE-wide, not page-specific"). The report still leads with the
    data-driven primary driver; a prior becomes the headline only if the data
    makes it so. Never let user context inflate the report's emphasis.

    Cite the prior inline where it surfaces — `(per user context)` for a
    corroboration, `(prompted by user context)` for a prior you tested. No
    cross-tab anchor (user context isn't a tab); it's a plain parenthetical.

Once all open items are resolved or explicitly accepted, proceed to Step 3.

---

## Step 3 — Write the report

**Now read the report-writing references:**

```bash
cat "$SKILL_DIR/references/actions.md"
cat "$SKILL_DIR/references/visual_kit.md"
cat "$SKILL_DIR/references/report_structure.md"
```

`actions.md` is deliberately deferred to Step 3 — the Step 2b synthesis you
just completed reached the root cause without being biased toward existing
action templates. Now match the confirmed root cause to its action category
and populate the action cards. Novel root causes can produce novel actions,
not just remixes from the library.

Write `report.html` directly. Follow `references/report_structure.md` exactly —
the file owns the CSS, the HTML patterns for every component, the tab structure,
and the styling guidelines. Source every claim from `findings.md`. Write the
output to: `<run_dir>/report.html`.

**No spec JSON, no render.py.** The report is a single hand-authored HTML
file. The visual primitives (CSS, HTML patterns for metric cards / callouts /
action cards / analysis blocks / tables / tab framework / ↗ link-to-table
pattern / Slack integration / styling rules) live in `visual_kit.md`. The
CVR-RCA-specific structure (Section 1/2/3 macro layout, "What belongs in
Section 3" table, Mix cascade block, Fixed Segment banner, Geo overview,
Shapley flex bar, Hypotheses block, etc.) lives in `report_structure.md`.
Read both — `visual_kit.md` for the shared visual language, `report_structure.md`
for the CVR-RCA-specific layout on top of it. Freedom to add novel evidence
is total: when the investigation surfaces a finding that doesn't match any
standard block, write a custom `.analysis-block` following the HTML pattern
in `visual_kit.md`.

**Tab framework — when to use it.** Inspect `<run_dir>/perf_audit_report.md`.
If the file exists and is non-empty AND the perf-audit verdict was not
`DATA GAP: no campaigns`, write the report as a two-tab document:

- **Tab 1 — CVR RCA**: Sections 1, 2, 3 as documented in `report_structure.md`.
- **Tab 2 — Paid Performance Audit**: read `perf_audit_report.md` and convert
  it to HTML **verbatim** using the conversion mapping in `visual_kit.md →
  "Perf-audit tab rendering"`. Preserve every section, every subsection,
  every table cell, every paragraph, every word. The perf-audit-skill is the
  source of truth for its own structure; CVR-RCA's job is to display it, not
  to re-format it.

**Fallback if the markdown contains a construct that doesn't convert cleanly.**
If any part of the markdown can't be faithfully converted to HTML (rare),
fall back to embedding the raw markdown text directly inside a
`<pre class="md-raw">` block in Tab 2. Better to show raw markdown than a
paraphrased HTML — fidelity beats polish.

Otherwise (perf-audit didn't run, returned empty, was DATA GAP, or the cascade
fixed on Organic), write a single-tab (flat) report — no tab bar. The full HTML
patterns for both shapes are in `report_structure.md → "Tabbed report
structure"` and `→ "Visual Spec — HTML patterns"`.

Cross-tab citation routing — which CVR-RCA finding type links to which
`#perfaudit-*` anchor — and the four-pattern citation phrasings (`(per
perf-audit ↗)`, `(perf-audit named: <event · date> ↗)`, etc.) are documented
in `report_structure.md → "Tabbed report structure → Citation routing"`. Step
2b check #10 produces the citations; this step (Step 3) renders them inline.

**Required-elements check before you finish (output contract, not process).**
After writing `report.html`, verify the always-on elements are actually present
**and rendered** — a placeholder `<div>` with no matching render script is the
most common silent failure (it leaves an empty gap where a chart should be). For
each always-on element, confirm both the container *and*, for charts, the
`Plotly.newPlot('<id>', …)` call exist:

- Five metric cards (CVR · LP2S · S2C · C2O · Traffic)
- **90-day CVR + LY trend chart** — `<div id="trend-90day">` **and**
  `Plotly.newPlot('trend-90day', …)`. This is the one most often dropped because
  it requires pulling the LY series out of `trend_context.series` and applying
  the LY-data guard (see `visual_kit.md → "90-day + LY overlay chart"`). If LY is
  genuinely absent, the chart still renders current-year-only with the amber
  "no LY overlay" badge — the chart is never omitted.
- Root-cause callout (Section 1c)
- Mix cascade block, Shapley flex bar, daily trend chart for the primary step
- Hypotheses explored block (always last)
- External Signals & Corroboration block — present whenever any external lens
  contributed a used signal (per the Step 2b provenance contract)

This is a completeness contract on the finished artifact — it does not constrain
*what* you investigate, only that the report you ship contains what it must.

**Run the advisory linter to check this automatically:**

```bash
python3 "$SKILL_DIR/scripts/validate.py" --report "<run_dir>/report.html" --run-dir "<run_dir>"
```

It runs **only here, after the report is written** — it never sees the
investigation and has no bearing on how you explored. It prints any missing or
orphaned elements (most importantly a chart container with no matching
`Plotly.newPlot` call, which renders as an empty gap). It **never edits the
report and never blocks** (exit code is always 0). For each finding, use your
judgment: add the element, or consciously skip it with a one-line reason — a
report can legitimately omit something, and the linter has no veto. It's a quick
cosmetic pass; resolve the findings, then finalize.

For a concrete walkthrough of how an investigation unfolds end-to-end, see
`references/worked_example.md`.

**End-of-run footer.** Once the report is written, print exactly one line to the
user and stop:

```
Report → <run_dir>/report.html
```

That single pointer is the **only** chat output at the end of the run. Do not
narrate the analysis, summarise the report, recap the Slack reconciliation, or
provide a "highlights" block in chat. The HTML report, the findings.md, and the
transcript.md are the records — the footer just points the user to them.

---

## Quality Evaluation — Maintainer Tool (On-Demand)

> **Not part of the run.** The quality evaluator is **not** executed on
> analyst-facing runs — scoring would cost tokens and time for a record the
> analyst never sees. It is a maintainer tool, run **on demand** against any
> finished run-dir.

A maintainer evaluates a finished run by spawning a sub-agent: *"read
`$SKILL_DIR/evals/evaluator.md` and follow it; run dir `<run_dir>`; write
`<run_dir>/evaluation.md`."* The sub-agent reads only the on-disk artifacts
(the HTML report, `transcript.md`, `summary.json`), so it needs no live session
context. The rubric covers **7 themes**, each scored 1–5.

Run it on a sample of runs while tuning the skill. The signal is not any single
score — it is the **meta-review**: when the same gap recurs across multiple
evaluations (e.g., seasonal events never quantified with a controlled
comparison), that is the cue to update the skill files (`context.md`,
`hypothesis.md`, or `SKILL.md`) so the investigation logic catches it earlier,
rather than adding more loops within the skill.

---

## Backlogs

**Parked for later:**
- Payment gateway error breakdown for A2O (`order_attempted_events_v2`:
  `payment_gateway`, `payment_method`, `fraud_evaluation_result_origin`,
  `failure_reason`)
- LP2S price vs LY baseline
- Bootstrap confidence intervals on Shapley values

**When a branch requires a backlogged source:** Close that branch as `DATA GAP`
in the tree map — not `CONFIRMED` or `LEAF`. In the action card, reference the
relevant root cause from `actions.md` (which contains the manual investigation
steps for each backlogged table) so the DRI receives a specific starting point,
not generic "investigate further" text.

---

## Changelog

| # | Date | Changes |
|---|------|---------|
| c001 | 2026-04-24 | Initial version — investigation framework, 3 mandatory questions, Shapley, mix decomp, custom query patterns, render.py integration, Step 4 evaluator |
| c002 | 2026-04-24 | Added `report_structure.md` to "Before you begin" reads; updated file role descriptions; clarified hypothesis.md is historical priors not a constraint; replaced Step 3 with pointer to `report_structure.md`; updated Backlogs |
| c003 | 2026-04-24 | Added majority-contributor principle; added rate × volume rule; reframed session recordings as required once locus confirmed; added explicit requirement to state why recordings were skipped |
| c004 | 2026-04-24 | Fixed session recordings trigger to disjunctive; added "Data pull errors — log and continue" section |
| c005 | 2026-04-24 | Updated report visual standard; added P1/P2/P3 priority badges |
| c006 | 2026-04-27 | Removed Q2/Q4/Q5/Q6 template pointer; fixed stale summary.json field references in investigation patterns |
| c007 | 2026-04-27 | Stripped SKILL.md to pure process. All domain knowledge, analytical guidance, query rules, dimension guides, investigation patterns, and worked examples moved to context.md and references/worked_example.md. |
| c008 | 2026-04-27 | Removed confusing or redundant lines: "no render.py" negative instruction, internal Q0/Q1/Q3/Q7 stage names, raw stage file paths, Plotly color codes and chart instructions (already in report_structure.md), three-section structure restatement (already in report_structure.md), "Under development" backlog items that implied Claude should add banners for unimplemented features. |
| c009 | 2026-04-27 | Default window changed to 30/30 days. Dates are now optional in the invocation — when omitted, the script computes last 30 days as post and the prior 30 days as pre. |
| c010 | 2026-04-27 | Added Step 2b — Synthesise findings and review. Claude writes a structured findings.md (root cause, mechanism, timing, evidence inventory, open items) before writing HTML. Open items — unverified claims, floating data points, unquantified recommendations — are resolved with follow-up queries or arithmetic before proceeding. Step 3 now writes from findings.md as the source of truth. Step 4 clarified as pure scoring; meta-review pattern documented for updating skill files across runs. |
| c011 | 2026-04-27 | Evidence inventory gains a Source column — every claim with a number must name its source (summary.json field, BQ query result, or report table row). Added fourth specific check: any count or metric with no named source must be derived explicitly or removed before entering the report. Quick Reference block updated: date default changed from weekly Mon–Sun windows to 30/30 days (yesterday − 30 days as post, prior 30 days as pre), matching SKILL.md c009. |
| c016 | 2026-04-28 | Run folder auto-increments when same CE + dates are re-run: base folder keeps no suffix, subsequent runs get _run2, _run3, etc. SKILL.md uses <run_dir> shorthand for all output paths. |
| c012 | 2026-04-27 | Investigation model redesigned from sequential three-question gates to an investigation tree. L0 reads all three orientation signals simultaneously (mix_dominance, shapley, trend_context) then opens parallel L1 branches. Investigation descends level-by-level until a leaf (specific mechanism × segment × date). Transcript format mirrors the tree structure (L0 section, L1/L2 sections with parallel batch labels, Root cause confirmed paragraph). context.md gains "Investigation tree — L0 to L1 branch map" lookup table. worked_example.md rewritten with tree-format transcripts and parallel query batches explicit. |
| c017 | 2026-04-29 | Mix cascade redesigned as mandatory L1 step: three levels (MB/HO → Paid/Organic → Channel within Paid). Fixed segment declared from cascade results; all L2+ funnel queries carry the fixed segment filters. L1 and L2+ steps renamed in Step 2 accordingly. context.md gains full Mix Cascade section with three query templates, decision rule, and fixed segment declaration template. report_structure.md gains Fixed Segment banner HTML spec and updated 90-day chart spec (weekly ticks + LY data guard). |
| c018 | 2026-04-29 | L2+ section rewritten to make hypothesis generation self-extending: context.md patterns are explicitly the default *starting set*, not an exhaustive list. Results themselves generate the next hypothesis. Four result types defined: Confirms, Rules out, Concentrates, and Surprises (the last being new — an unexpected result generates a new branch even if not on the default list). "Investigation ends at the leaf, not at list exhaustion" stated explicitly. context.md Common Investigation Patterns header rewritten to match — replaces weak "not rails" disclaimer with explicit loop logic and three common reasons a list runs out before a leaf is reached. |
| c019 | 2026-04-29 | Removed "write 2–4 specific, falsifiable hypotheses" from L2+ — this was a leftover artifact from the old Q1/Q2/Q3 model that contradicted the tree structure. L2+ now opens branches from the context.md default set and grows them level-by-level from what the data shows. Branches are not a fixed upfront list. |
| c021 | 2026-04-29 | Mix cascade repositioned as the routing vs conversion determination (not a blind segment-fixer). L1 section rewritten with three explicit levels, each with a mix exit condition (mix change → routing story) and a conversion path (fix segment, descend). L0 Signal 1 downgraded from a hard gate to an orientation hint — the cascade, not mix_dominance alone, determines the path. hypothesis.md L0 routing table updated to show cascade exits as the first rows, with Shapley rows applying only after a conversion-path cascade. |
| c020 | 2026-04-29 | Updated file role descriptions: context.md no longer owns "investigation patterns"; hypothesis.md described as two-level branch reference (L0 routing + first-pass branch sets + historical patterns). L2+ pointer updated from context.md to hypothesis.md. |
| c022 | 2026-05-13 | Two investigation completeness changes: (1) L2+ exit condition — a leaf for the dominant driver no longer ends the investigation. After the primary leaf, every signal that was explicitly quantified during the investigation (a specific rate delta or checkout impact was computed) must be closed as CONFIRMED, RULED OUT, or DATA GAP before the investigation is declared complete. Signals noted but not quantified are observations, not commitments. "Consistent with X" without a direct test is an open branch. (2) Tree map format — explicitly quantified signals must appear as named branches in the map; branches may only be closed as CONFIRMED, RULED OUT, or DATA GAP, not left as narrative observations or inline inferences in a detail section. |
| c023 | 2026-05-14 | Secondary funnel step coverage fix: (1) Signal 2 (Shapley) now explicitly states that Shapley deltas are quantified signals and count toward the closing coverage requirement — closes the gap where a secondary step above the ~10% threshold was noted but never tested. (2) L2+ opening changed from "primary funnel step only" to "primary funnel step first" — removes the prohibition that prevented secondary branches from opening. (3) L2+ closing paragraph gains a secondary-step scoping note: the question for a secondary step is "independent mechanism or explained by primary?" not "what broke and why?"; one decomposition query is usually sufficient; only descend further if the secondary step declines within the fixed segment in a direction not explained by the primary finding; close as DATA GAP if daily volume is too low to be reliable (<~20 events/day average). This keeps secondary checks proportional — a dominant single-driver CE does not spin off unnecessary branches. |
| c024 | 2026-05-14 | Backlogs — added DATA GAP closure rule: when a branch's primary evidence path leads to a backlogged source, close the branch as DATA GAP in the tree map (not CONFIRMED or LEAF), and cite the relevant `actions.md` root cause in the action card so the DRI receives specific starting steps rather than generic "investigate further" text. |
| c025 | 2026-05-14 | Step 2b "Specific checks before proceeding" rewritten as a numbered 5-item checklist: (1) weekday composition, (2) seasonal/calendar event claims must be paired with a data signal (cross-reference to report_structure.md Styling rule 4), (3) every number has a named source, (4) every numeric recommendation verified with arithmetic, (5) backlogged branches must be closed as DATA GAP. Replaces the previous unordered prose list. |
| c026 | 2026-05-20 | Cross-cut concept added as a first-class investigation step. hypothesis.md gains "Dimension cross-cut — when two cuts both concentrate" section with a trigger rule (≥8pp absolute or ≥20% relative), enumerated common cross-cuts by funnel step (A2O, S2C, LP2S, C2A), and a three-outcome interpretation guide. context.md gains "Cross-cut query template" section with the generic 2-dimension query, a funnel step substitution table, and a worked A2O example (device_type × experience_id). SKILL.md gains check 8 in Step 2b: "Cross-cut run when two cuts both concentrated." |
| c028 | 2026-05-21 | Slack context layer added. A fire-and-forget sub-agent is spawned at the top of Step 2 (after summary.json is read, before the investigation starts). It runs three searches — CE-specific global (pre_start − 14 days → post_end), market channel read (pre_start → post_end), and #tf-bugalert (post_start − 2 days → post_end) — and writes categorised signals to `<run_dir>/slack_context.md` in four buckets: Platform/Bug, Supply/Inventory, Campaign/Traffic, CE-specific mentions. The main agent never waits for it. Step 2b gains check #9 (Slack context reconciliation): read slack_context.md after findings.md is written; corroborate confirmed findings with thread links, test specific gap signals with one query max, reject vague or symptom-only signals explicitly. report_structure.md gains optional 5th "Source" column in hypotheses explored table (only rendered when a corroboration exists) and inline citation format for analysis block subtext. Sub-agent instruction set lives in `references/slack_context_guide.md`. |
| c029 | 2026-05-22 | Slack reconciliation expanded into four-pattern model and made bidirectional. Step 2b check #9 rewritten: signals classified into Pattern A (direct corroboration), B (mechanism explanation), C (reframing context), D (testable gap), or rejected. Reaffirms that Slack is consulted **only** at this point — never during L0/L1/L2 — the fire-and-forget pattern is deliberate so Slack doesn't steer branch selection. Pattern A on declines gets a citation-elevation rule (bare `(corroborated ↗)` becomes named `(per Author · date ↗)` when the action is going to a DRI). Pattern B routes to Layer 1 narrative weaving + Section 3 Market Context block. Pattern C routes to a Layer 2 Important Context callout-item in Section 1 (high bar — four decision-changing tests); how to phrase the citation when the Slack timeframe differs from the report's pre/post is a styling concern handled in `report_structure.md → "Timeframe-citation rule"` (SKILL.md only points to it; the spec itself lives in the styling file). Added high-value gap categories list (operational events: assortment changes, pricing levers, content updates, product restructures, API migrations, vendor moves) — Pattern D recognises these as good retrospective query candidates. Added "one citation per concept" rule. Step 4 footer hardened: the two output lines are the only chat output — no narrative summary, no Slack recap, no highlights block. Session recordings rule extended explicitly to improvement loci (decline = look for failure; improvement = verify smooth flow + surface new UI elements). L2+ section gains direction-sensitive language and a pointer to `hypothesis.md → "Improvement direction — first-pass branches"` when CVR improved. Catalogue change called out as a first-class data-driven hypothesis (no Slack input required to trigger). |
| c027 | 2026-05-21 | First-pass batch parallelised via sub-agents. "Run all branches within a level in parallel" replaced with a five-step spawning protocol: (1) write SQL for every cut before spawning, (2) open transcript section, (3) spawn one sub-agent per cut — each receives only SQL + output path + output contract (no reference files, context isolation enforced), (4) wait for all sub-agents before reading any result, (5) fill transcript and synthesise from the combined picture. Batch JSON files saved to `<run_dir>/batch_<cut_name>.json`. Failure handling: missing or empty JSON = DATA PULL FAILURE, log and continue, do not re-query inline. Applies to the first-pass branch set only; deeper levels (L2, L3) remain sequential. |
| c030 | 2026-05-22 | Perf-audit companion-skill integration. When the cascade fixes on Paid (conversion path at L2/L3, or routing exit at L2/L3), spawn the perf-audit sub-agent at the end of the cascade and continue immediately — mirrors the Slack fire-and-forget pattern. Sub-agent runs the standalone perf-audit skill ([aaradhyaraiHO/perf-audit-skill](https://github.com/aaradhyaraiHO/perf-audit-skill)) with the CE name and pre/post date windows; returns a structured summary at `<run_dir>/perf_audit_summary.md` and the full report at `<run_dir>/perf_audit_report.md`. Summary shape: overall verdict, traffic-quality assessment (SIS/CPC/Paid CVR trends), campaign status (pauses, tROAS suppression, budget exhaustion), one-sentence key finding, optional surprise hypothesis. Funnel data deliberately excluded from the summary — perf-audit's attribution differs from Mixpanel's, and CVR-RCA owns the funnel numbers. Step 2b gains check #10 (Perf-audit reconciliation): same four-pattern routing as Slack — Pattern A corroborates a leaf, B names the campaign-level *why*, C reframes the root cause when traffic quality degraded alongside a page finding, D tests a surprise hypothesis with one query max. Path resolution: `$PERF_AUDIT_SKILL_PATH` env var → `~/.perf-audit-skill/SKILL.md` (companion install) → sibling directory → legacy `~/Documents/perf-audit-skill/`. If none resolve, log "Perf-audit skill not installed — skipped" and continue. hypothesis.md LP2S and Mix sections gain background-context pointers explaining that the perf-audit verdict folds in at Step 2b, never during dimension-cut phase. INSTALL.md Step 6 adds an optional companion install. Perf-audit is consulted *only* at Step 2b — the data-driven branches must reach their own leaves before the perf-audit verdict is read, so it corroborates or surprises a completed picture rather than steering branch selection. |
| c037 | 2026-05-29 | **Trimmed the "ignore `perf_audit_report.html`" defensive paragraph from Step 3.** The instruction was a one-off guardrail added in c036 (when perf-audit-skill had been emitting `.html` locally) but became obsolete once perf-audit-skill was rolled back to emitting markdown only. Carrying a defensive negation against a failure mode that can't occur is over-specification — it pollutes the spec with a CVR-RCA-vs-perf-audit-skill negotiation that future maintainers shouldn't need to understand. The canonical rule remains: "Tab 2 reads `perf_audit_report.md` and converts verbatim." Skill instructions should describe canonical behavior, not enumerate every potential failure mode. Companion change in `visual_kit.md` c005. |
| c038 | 2026-06-03 | **Orchestration-handshake delegation check in the perf-audit spawn block** — enables CVR-RCA to run as a sub-skill of the new CE-RCA master skill without double-firing perf-audit. Before deciding to spawn the perf-audit sub-agent, CVR-RCA now checks for `<run_dir>/orchestration.json`; if `perf-audit-skill` appears in its `fired_by_master` array, a parent orchestrator is already running perf-audit against the same run directory, so CVR-RCA logs the delegation and skips its own spawn — then consumes the shared `perf_audit_report.md` at Step 2b check #10 as usual (the existing wait-for-file polling handles any timing race). Belt-and-braces secondary check: skip the spawn if `perf_audit_report.md` already exists even without an orchestration file. Standalone `/cvr-rca` runs are unchanged — neither file exists, so the normal spawn fires. This is the only CVR-RCA change required by the CE-RCA umbrella skill (which lives in its own repo and orchestrates CE Health → CVR-RCA + perf-audit → composite tabbed report). Sub-skill outputs remain verbatim; CVR-RCA's report and behavior are otherwise untouched. |
| c042 | 2026-06-03 | **User context as a steering input (dual consumption).** CVR-RCA now reads `<run_dir>/user_context.md` (the analyst's intent, captured by the CE-RCA umbrella's Step 1 pause, or hand-placed in a standalone run) at **two** points. **L0 — new "Signal 0 — user context":** the analyst's Focus / Hypothesis priors / Known events become **prioritised, falsifiable** first-pass branches, opened early and *tested* (can be RULED OUT). This is the **one deliberate exception** to the "lenses consulted only at Step 2b" rule — user context is *intent* (legitimately steers where to look), not secondhand evidence (which must not bias branch selection). Guardrails baked in: **priority not tunnel-vision** (branches appended to, never replacing, the mix/shapley/trend default set; data still decides the leaf), **not narrow** (full orientation still runs), **always closed** (every prior resolved CONFIRMED/RULED OUT/DATA GAP via the close-every-quantified-signal rule). **Step 2b — new check #12:** close each prior + corroborate via the four-pattern model, with **proportional output** (a ruled-out hunch is one line; the report still leads with the data-driven driver — anti-overwhelm). Standalone-safe (no file → skip). Lean by construction (the master writes a short structured file, not a chat transcript). Companion: ce-rca v1.2.0 (m005) captures `user_context.md` at its Step 1 pause + adds the `user_context` pointer to `orchestration.json`. v1 is free-text only; files/Sheets/Slack channels are a deferred v2 slot. |
| c041 | 2026-06-03 | **Sentra dashboard link deprecated.** Sentra is being retired, so the report header's dashboards row no longer creates a Sentra pill — Omni only. `report_structure.md → "Header — CVR-RCA-specific extensions"`: section retitled "Dashboards row — Omni + Sentra" → "Dashboards row — Omni"; the Sentra URL template, the Sentra `<a>` in the emitted HTML, and the pre-write sanity-check "Sentra link" mention all removed; the "render both links" instruction reduced to the Omni link. `visual_kit.md` Page-skeleton doc-comment updated to point at the renamed section. Historical changelog entries that reference Sentra (c032, visual_kit c002) are left intact — history is not rewritten. No code change; standalone and composite headers both render the Omni pill only. Companion ce-rca change: v1.1.2 (same Sentra trim in the master's meta.json instruction + composition docs). |
| c040 | 2026-06-03 | **Provenance contract — source-agnostic External Signals table + required-elements check.** Two output-contract fixes (neither constrains the investigation; both govern what the finished report must contain). **(1) External Signals & Corroboration table.** The Section 3 "Market context & operational signals" block (Slack-only, rendered only when Slack returned a Pattern B/C signal) is generalised into a source-agnostic **"External signals & corroboration"** block that renders whenever **any** external lens (Slack, perf-audit, CE Health, future siblings) contributed a signal you *used* — one row per used signal, with a Source ↗ to the owning tab/thread. The Step 2b checks #9–#11 preamble gains a **provenance contract**: any external signal that informs a callout/verdict/narrative line must appear both woven in at the point of use *and* as a table row; this applies to every used signal regardless of pattern — **Pattern A corroborations now also earn a row** (check #10 Pattern A was previously inline-only, which is exactly why perf-audit signals silently dropped out of the table when Slack was unavailable, e.g. CE 243). A missing/unavailable lens becomes a disclosure row, never suppresses the table. Block keeps id `block-market-context` so existing ↗ citations resolve. Companion change `visual_kit.md` c007 (section renamed "Slack integration" → "External context integration & link-to-table styling", lens-agnostic; four-pattern surfacing table updated so A/B/C all earn a row). Added a **widest-first reading hint** to the preamble (CE Health → perf-audit → Slack, then synthesise together — a reading-order hint, not a rail). **(2) Required-elements check.** Step 3 gains a completeness contract: after writing the report, confirm always-on elements are present *and rendered* — most importantly the 90-day LY trend chart needs both `<div id="trend-90day">` and its `Plotly.newPlot('trend-90day', …)` script (the script was dropped in the CE 243 run, leaving an empty gap). Output contract only — fix before finishing. Backed by a new **advisory linter** `scripts/validate.py`, run at the end of Step 3: it flags missing/orphaned elements (e.g. a chart container with no `Plotly.newPlot` call — the exact 90-day failure mode, caught generically rather than by an enumerated list) and the absence of an External Signals table when external lenses were used. Cosmetic and advisory — runs only after the report is written, never edits, never blocks (exit 0 always); Claude adds or consciously skips each finding. Zero effect on investigation freedom. |
| c039 | 2026-06-03 | **Manifest-driven context layer + CE Health as a new reconciliation lens.** Step 2b's per-lens reconciliation checks (#9 Slack, #10 perf-audit) are reframed under a shared "Context reconciliation — read every available lens" preamble: read the authoritative lens list from `<run_dir>/orchestration.json` `context_lenses` when present (master-orchestrated), else fall back to file-presence detection (standalone). One four-pattern model (A/B/C/D/Reject) applied per lens; lenses consulted ONLY at Step 2b, never during L0/L1/L2. New check #11 — **CE Health reconciliation**: when `ce_health_report.md` is present (CE-RCA umbrella ran CE Health first), reconcile funnel findings against the wide upstream lens. Two highest-value reconciliations: (A) entity-level cross-link — when a funnel drop is localized to an experience/TGID, corroborate against CE Health's revenue/RPC flag for that same entity (`CE Health: TGID 7148 RPC −30% ↗`); (C) headline-driver reframe — if CE Health's Shapley names AOV/Completion/Take Rate (factors CVR-RCA doesn't investigate) as the headline mover, say the funnel finding is real but not the headline and point to the CE Health tab. Cross-tab citations use `#cehealth-<slug>` anchors; standalone-safe (no CE Health present → no citation emitted). Scalable: a future sibling lens is one more manifest entry, same model. Companion change in `visual_kit.md` c006 (registers `summary-*` + `cehealth-*` anchor prefixes and the CE Health citation form). This is the CVR-RCA side of the cross-skill RCA work; the Summary synthesis tab and the orchestration manifest live in the CE-RCA repo. |
| c036 | 2026-05-29 | **Step 3 Tab 2 reverts to verbatim markdown render — partially undoes c035.** Tab 2 now reads `<run_dir>/perf_audit_report.md` (canonical text artifact) and converts markdown → HTML verbatim using the conversion mapping in `visual_kit.md → "Perf-audit tab rendering"`. **`perf_audit_report.html` is explicitly ignored** even if present — the perf-audit-skill's own md→html step may restructure or summarize content (h3/h4 subsections collapsed into parent h2, appendices dropped) and CVR-RCA can't trust that derivative. Fidelity rules added: every section, every subsection (4a, 4b, 5a, 5b, 5c, Appendix, Data Sources), every table cell, every paragraph preserved verbatim. No CVR-RCA chrome wrapped around perf-audit content — the perf-audit's structure is the perf-audit's structure. New fallback rule: if the markdown contains a construct the conversion mapping doesn't cover, embed raw markdown text inside `<pre class="md-raw">`. Companion changes in `visual_kit.md` c004 (Perf-audit tab rendering rewritten; missing `.md-content` and `.md-table` CSS finally added; new `.md-raw` styling; two new Anti-patterns). Driven by CE 3593 RCA where Tab 2 was 31% smaller than the source `.md` (2,051 words vs 2,975) due to perf-audit-skill's html restructuring. perf-audit-skill local Step 6 (added in c035 era) rolled back; perf-audit-skill returns to emitting `.md` only. |
| c035 | 2026-05-29 | **Step 3 Tab 2 rendering switches to HTML embed.** When perf-audit ran successfully, CVR-RCA's Tab 2 now reads `<run_dir>/perf_audit_report.html` (the polished HTML deliverable that perf-audit emits as a sibling of its markdown report), extracts the body content (everything between `<body>` and `</body>`, stripping any `<header>` inside), and pastes verbatim into `<div class="tab-pane" id="tab-perfaudit">`. Byte-paste, not comprehension — the HTML carries its own `perfaudit-<slug>` anchor IDs, headings, and chrome from the shared `visual_kit.md` both skills now reference. Fallback for older perf-audit versions (only emits markdown): legacy v1.16 inline md→HTML render. Companion changes in `report_structure.md` c031 (split into `visual_kit.md` + this file — primitives extracted), new `references/visual_kit.md` (shared design system), perf-audit-skill `perf_audit_structure.md` (new file defines perf-audit's section layout on top of visual_kit), perf-audit-skill SKILL.md (new Step 6 emits HTML alongside markdown). Visual quality goes up (embedded perf-audit content inherits CVR-RCA's visual_kit CSS, so it looks visually identical to surrounding Tab 1 content); Claude's reading load goes down (no markdown→HTML conversion at Step 3 — that work now happens once inside perf-audit, not on every CVR-RCA report write). Markdown artifacts (`perf_audit_summary.md`, `perf_audit_report.md`) unchanged — they remain Claude's input for Step 2b reconciliation reasoning. HTML is a presentation artifact, opaque to Claude at the embed step. |
| c034 | 2026-05-28 | **Lazy-load references by phase.** "Before you begin" rewritten — Claude no longer reads all four references upfront. Per-phase reads: Step 1 reads SKILL.md only; Step 2 reads `context.md` + `hypothesis.md` (both, fully) at the start of investigation; Step 3 reads `actions.md` + `report_structure.md` (both, fully) at the start of report writing; Step 4 reads `evals/evaluator.md`. Files are loaded whole when loaded — section-level reads are explicitly rejected because they would constrain the cross-pattern reasoning that produces non-obvious findings. New "On reading references — a note on freedom" subsection codifies the principle: Claude has complete freedom to form hypotheses, design queries, and follow the data wherever it leads; references provide the shared context that makes the freedom precise rather than vague (data vocabulary in `context.md`, historical patterns as starting points in `hypothesis.md`, cause-to-action library at Step 3 in `actions.md`). The actions library is deliberately deferred to Step 3 so the Step 2b synthesis stays clean of action-template matching bias — Claude reaches its own root-cause conclusions before being shown what actions exist. Driven by the realisation that upfront loading of all four references (~85+ KB) at Step 1 splits attention across irrelevant patterns during early-phase reasoning, subtly biasing hypothesis selection. |
| c033 | 2026-05-28 | **Step 3 reverted to Claude-writes-HTML.** Removed the `report_spec.json` + `scripts/render.py` prescription and the "Investigation drives the report" subsection (escape-hatch components). The report is now a single hand-authored HTML file following the patterns in `report_structure.md`. The v1.14 spec-JSON pipeline was constraining output quality — render.py's built-in component renderers (`metric_cards`, `mbho_channel_table`, `shapley_waterfall`, etc.) ship pre-v1.13 inline-styled HTML that doesn't match the v1.15 template's polished `.analysis-block` chrome, so reports rendered through the pipeline looked visually inconsistent. Claude-writes-HTML produces uniformly polished output (CE 252 was built this way and remains the quality target). The tab framework survives as a documented HTML pattern in `report_structure.md`, not as a render pipeline. Companion changes in `report_structure.md` c029 (tab + perf-audit inline patterns documented), `/cvr-rca` slash-command (Step 3 reverted to write-HTML-directly). Driven by CE 243 (Eiffel Tower) RCA, where the pipeline-rendered output visibly degraded vs CE 252's hand-authored quality. |
| c032 | 2026-05-28 | New Step 3 subsection "Investigation drives the report, not the inverse" introduces the escape-hatch components (`analysis_block`, `raw_html`) with full schemas and a worked cross-cut example. Codifies the principle that the rendering layer serves the investigation: when an investigation surfaces a finding the 19 built-in components can't express, `analysis_block` wraps arbitrary HTML in the standard Section-3 chrome (visual consistency is free) and `raw_html` is pure passthrough for the rare case where the standard chrome is wrong. Includes a guard rail prohibiting cosmetic use — built-ins remain the default for standard cuts; escape hatches are for novel evidence only. Companion changes in `scripts/render.py` c033, `references/report_structure.md` c028. Driven by CE 252 (Louvre) RCA, where the 19-component cap could have silenced novel cross-cut findings. **Superseded by c033 — Step 3 reverted to Claude-writes-HTML; escape-hatch components no longer needed because there is no rendering pipeline to escape from.** |
| c031 | 2026-05-23 | Tabbed report framework. `report_spec.json` accepts a new `tabs[]` shape — each tab has an `id`, `label`, and either inline `sections[]` (Claude-authored components) or a `source` pointer (e.g., `{"type": "markdown", "path": "perf_audit_report.md"}`). `scripts/render.py` gains a markdown-to-HTML renderer (stdlib only — no PyPI dependency; handles headings + GFM tables + lists + bold/italic/code/links/HR), a tab-bar emitter, and per-tab dispatch. Anchor IDs are injected on every markdown heading with a configurable prefix (default `<tab-id>-`) so cross-tab links stay namespaced — perf-audit headings become `#perfaudit-<slug>` (`5. Coverage + Matchmaking` → `perfaudit-coverage-matchmaking`). `templates/report.html` gains sticky tab-bar CSS, `.md-content` + `.md-table` styling for markdown-sourced tabs, and a ~50-line vanilla-JS handler that switches tabs when `.ref-link` anchors target a non-active pane (with Plotly resize for charts in newly-visible panes). Step 3 writes the tabs-shaped spec when `perf_audit_report.md` exists and is non-empty; otherwise it writes the legacy flat spec — backward compatibility is byte-identical for single-tab runs. Step 2b check #10 extended: every perf-audit citation must carry a `↗` linking to the appropriate `#perfaudit-*` anchor per the routing table in `report_structure.md → "Tabbed report structure → Citation routing"`. The framework is scalable — a third tab (future experiment-RCA, supply-RCA, etc.) is one config entry, not a rewrite. |
| c043 | 2026-06-08 | **Additive hooks for CE-RCA's context-ingestion layer (v1.28).** Four small, gated additions — all no-op on a standalone run with no `user_context.md` / `orchestration.json`, so standalone behaviour is unchanged. **(1) User-data lens:** the Step 2b lens manifest note now states a `user_data_*` entry (a user-provided ad-hoc data pull, written by the CE-RCA orchestrator's ingestion sub-agent) is reconciled with the same four-pattern model — no new mechanism, just one more `context_lenses` entry; cite it as user-provided. **(2) User Slack channel:** the fire-and-forget Slack sub-agent now accepts an optional `user_channels` arg (from `orchestration.json → user_slack_channels`) — `slack_context_guide.md` gains a **Search 4** that reads the user-named channel(s) alongside discovery and tags a "User-requested channel signals" section; one Slack pass, one `slack_context.md`. **(3) Known-event chart markers:** Signal 0 + `visual_kit.md` document that a Known event with an in-window date drops a dated `shapes` vline + `annotations` label on the daily/90-day trend charts — **never moves the analysis window** (fixed at Step 0). **(4) User-provided citations:** `visual_kit.md` + `report_structure.md` define a distinct `(per user-provided … ↗)` / `(corroborated by user Sheet: <name> ↗)` tag so analyst-supplied evidence reads distinctly from system-derived. Companion: ce-rca v1.8.0. |
| c044 | 2026-06-08 | **Transcript tree-map is now fenced (v1.29).** The investigation transcript's `## Tree map` block is wrapped in a ` ```text ` code fence (detail sections stay plain markdown). No content change — purely so the CE-RCA umbrella report, which now renders each transcript **as markdown** in its Transcript tab, preserves the `├─ │ └─` alignment (markdown would otherwise collapse the unfenced tree into a paragraph). Standalone CVR-RCA output is unaffected. Companion: ce-rca v1.9.0. |
