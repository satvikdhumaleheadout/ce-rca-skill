---
name: ce-rca
description: >
  CE-level Root Cause Analysis for a Headout Combined Entity (CE) — the umbrella
  skill. Use this whenever someone wants a full picture of what's happening with
  a CE, asks "what's going on with CE X", "run a CE RCA", "diagnose this CE", or
  wants health + funnel + paid in one report. It runs CE Health first, shows the
  diagnosis, asks which directions to deep-dive, then fires the matching skills
  (CVR-RCA, perf-audit, and future AOV / completion-rate skills) and assembles
  one tabbed report. Run /ce-rca <CE> to start. For a CVR-only funnel RCA use
  /cvr-rca directly; this skill is the multi-skill umbrella on top of it.
---

# CE Root Cause Analysis — Master Orchestrator

This skill is a **thin orchestrator**. It owns no investigation logic of its own.
It runs CE Health, asks the user which directions to pursue, dispatches the
matching deep-dive skills, and composes their outputs into one tabbed report.

**The cardinal rule: this skill is a composer, not an editor.** Every sub-skill
(CE Health, CVR-RCA, perf-audit, future skills) runs exactly as it does
standalone, and its content appears in the composite report **faithfully** — no
summarizing, no restructuring, no re-wording. The sub-skills are never modified.

The rule has **two render modes**, split by who owns the artifact's *format*:

- **Verbatim-embed (perf-audit).** perf-audit ships freeform prose owned by
  another team. Its markdown is rendered to HTML 1:1 — every section, heading,
  row, and word preserved. Re-rendering would risk fidelity loss, so we never do
  it. This is the strict reading of the cardinal rule.
- **Structured re-render (CE Health, CVR-RCA).** CE Health and CVR-RCA both emit
  *deterministic structured data* (a JSON sidecar + regular GFM tables) that we
  re-render into visual_kit chrome — every number sourced from the data, nothing
  paraphrased. This is a **presentation re-render**, not an edit: CVR-RCA already
  does it on its own `summary.json`, and CE Health's tab is built the same way by
  `scripts/render_ce_health.py` (Step 4, below). Fidelity is still absolute —
  CE Health's sections 1→11, exact headings, exact order, **all** rows. The one
  agreed exception is §7 (Driver Diagnosis): CE Health's own Shapley is
  mis-specified, so the tab shows a corrected canonical 6-factor booking-revenue
  waterfall computed from the same data. See `references/composition_rules.md`.

## Before you begin

Derive the skill directory from the path of this SKILL.md:

```bash
SKILL_DIR=~/.ce-rca   # or wherever this file was read from
```

### Stay on the latest version — do this first, every run

CE-RCA **auto-updates**. Before anything else, check whether the local bundle matches the
published release and silently upgrade if it's behind — so a run never executes a stale skill:

```bash
SKILL_DIR=~/.ce-rca
INSTALLED=$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo "0.0.0")
LATEST=$(curl -s --max-time 3 https://raw.githubusercontent.com/satvikdhumaleheadout/ce-rca-skill/main/VERSION 2>/dev/null || echo "unknown")
NEEDS_UPDATE=$(python3 -c "
a='$INSTALLED'.strip(); b='$LATEST'.strip()
if b in ('','unknown'): print('no')
else:
    pa=[int(x) for x in a.split('.')]; pb=[int(x) for x in b.split('.')]
    n=max(len(pa),len(pb)); pa+=[0]*(n-len(pa)); pb+=[0]*(n-len(pb))
    print('yes' if pa<pb else 'no')
" 2>/dev/null || echo "no")
echo "installed=$INSTALLED latest=$LATEST needs_update=$NEEDS_UPDATE"
```

- **`needs_update=no`** — current, *or* offline (`latest=unknown`): continue to Step 0 on the
  installed version. Never block on the network; the 3-second timeout then proceeds.
- **`needs_update=yes`** — the bundle is stale. Re-install the latest **in place** (the same
  download INSTALL.md uses), tell the user **one line** ("CE-RCA updated v`$INSTALLED` →
  v`$LATEST`"), then **stop following this now-stale copy and re-read `~/.ce-rca/SKILL.md`**,
  continuing from the top of the freshly-installed version. Your run folders under
  `~/Documents/CE RCA Runs/` are never touched.

```bash
curl -L https://github.com/satvikdhumaleheadout/ce-rca-skill/archive/refs/heads/main.zip -o /tmp/ce-rca-update.zip \
  && unzip -q -o /tmp/ce-rca-update.zip -d /tmp/ \
  && rm -rf ~/.ce-rca && mv /tmp/ce-rca-skill-main ~/.ce-rca && rm /tmp/ce-rca-update.zip \
  && echo "updated to $(cat ~/.ce-rca/VERSION)"
```

The bundle is **self-contained and replaced wholesale** — never hand-patch a file to "catch up,"
and after an update obey the freshly-read SKILL.md, not this in-memory copy. (While the repo is
private the version fetch returns `unknown`, so the skill simply runs on the installed bundle;
auto-update activates the moment the repo is public.)

Read references lazily, by phase:

| Phase | Read |
|---|---|
| Step 2 (dispatch) | `references/registry.md` |
| Step 3 (synthesise) | the Summary sub-agent reads `references/summary_guide.md` — you just point it there |
| Step 4 (compose) | `references/composition_rules.md` (and `references/visual_kit.md` is consumed by `compose.py`, not by you) |
| Step 5 (follow-ups) | `references/followup_guide.md` — the in-session playground handler |

You do **not** need to read the sub-skills' SKILL.md files yourself — each
sub-agent reads its own. You only orchestrate.

## Invocation

```
/ce-rca <CE> [date-range]
```

`<CE>` is a CE ID or CE name. `[date-range]` is optional; default is **last 30
days vs prior 30 days** (matching CVR-RCA's default). Examples:

```
/ce-rca 252
/ce-rca "Louvre Museum"
/ce-rca 252 last complete week vs the week before it
```

---

## Step 0 — Resolve CE, confirm window, fire CE Health

**0a. Resolve the CE.** If the user passed a CE name, resolve it to a CE ID via
`dim_combined_entities` (same lookup CVR-RCA uses). If they passed an ID, use it.
Having the CE name makes the window prompt friendlier, but don't block on a
lookup query — CE Health's sidecar carries the canonical name regardless (read
at Step 1 for the preview, and at Step 4a for the report header).

**0b. Confirm the analysis window — ask, then WAIT.** This is the **first thing
you do**, before any directory, file, or sub-agent. Ask the user which period
they want:

- the **default** — last 30 days vs prior 30 days, run as `--range month`, or
- a **custom** window (they give you the post window; pre is the equivalent
  preceding window).

If the invocation already carried a date range, restate it and ask them to
confirm rather than assuming. **Do not proceed — no run dir, no `meta.json`, no
CE Health — until they answer.** Pinning the window up front keeps the whole run
aligned to the period they actually want and avoids redoing work if they'd have
changed the dates.

**0c. [Silent plumbing] Create the run dir.** Once the window is confirmed,
create:

```
~/Documents/CE RCA Runs/<ce-slug>-<post_start>-to-<post_end>/
```

Refer to this as `<run_dir>`. Open `<run_dir>/_run_log.md` (the orchestrator's
own internal run log for debugging/audit — never surfaced to the user) and log the
run start. **Do not write to `<run_dir>/transcript.md`** — that filename belongs to
CVR-RCA's investigation transcript, which the composer surfaces verbatim in the
**Transcript** tab; keeping the orchestrator's log in `_run_log.md` keeps that tab
clean (the underscore name is also excluded from the Transcript tab's `transcript*`
collection).

**Do not write `meta.json` here.** Its *only* consumer is `compose.py`'s header
builder (CE name / dates / market / pills / Omni pill / landing-page link) — a
report-header artifact, nothing between here and compose reads it
(`render_ce_health.py` gets its windows from CE Health's own sidecar, and the
deep dives are passed the windows directly). So `meta.json` is built once, whole,
at **Step 4a**. The confirmed window already lives in the run-dir name and the
run log, so there's nothing to persist early.

**0d. Fire CE Health (foreground — we need it before we can ask the direction).**
CE Health is **vendored inside this bundle** at `$SKILL_DIR/skills/ce-health/` — a
fixed path, no resolution or hunting. Spawn a sub-agent that runs:

```bash
python3 "$SKILL_DIR/skills/ce-health/ce_health.py" --ce-id <id> --range month --output <run_dir>/ce_health_report.md
```

(Use `--range month` for the 30/30 default, or `--start/--end` for the custom
window the user confirmed at 0b.) It runs from any CWD — the vendored copy is
patched to import its own `engine/` and needs no shim. CE Health writes
`ce_health_report.md` + a `.json` sidecar. Wait for it.

**Fail fast, do not improvise.** If `$SKILL_DIR/skills/ce-health/ce_health.py`
doesn't exist, or it errors, tell the user: *"CE Health is missing or broken in
this bundle — reinstall the CE-RCA bundle (or run `scripts/vendor.sh`)."* and
stop. Never hand-build an import shim, hunt for the skill in `~/Documents`, or
patch paths at runtime — the bundle is self-contained by construction; a miss
means the install is broken, not that you should repair it live.

**0e. Fire the CE-history sub-agent (fire-and-forget — do not wait).** Once CE
Health gives you the `ce_id`, spawn a background sub-agent that reads
`$SKILL_DIR/references/ce_history_guide.md` and writes `<run_dir>/ce_history.md` —
a short synthesised trajectory of **prior** RCAs for this CE (trend across runs,
recurring root causes, what was tried, what's open). Pass `ce_id`, `ce_name`,
`run_dir`, `runs_root` (the `CE RCA Runs` parent), `output_path`. **Continue
immediately** — mirrors the Slack pattern; it synthesises in its own context, so
nothing prior-run-related touches yours. `render_ce_health.py` embeds the file at
§8 if present (absent/first-run → §8 unaffected).

**That's all Step 0 does.** CE Health has run; its `.md` + `.json` sidecar are in
`<run_dir>`. **Do not enrich `meta.json` now, and do not build the Omni URL now.**
Everything that reads CE Health's sidecar into `meta.json` (CE name, type,
market, country, the five metadata pills, `top_page_url`) plus the Omni dashboard
URL are **header decorations consumed only by the final report** — nothing
between here and compose reads them. They are all assembled in one place at
**Step 4a**, reading the sidecar (which persists in `<run_dir>`) at that point.
Pulling them forward just adds mid-run plumbing steps and chatter with no payoff,
and risks reflecting a stale window if the user changed dates.

The diagnosis preview at Step 1 reads CE Health's sidecar **directly** for the
CE name / vitals / Shapley — it does **not** need `meta.json` enriched first.

---

## Step 1 — Present the CE Health diagnosis and pause

Read CE Health's JSON sidecar **directly** (`<run_dir>/ce_health_report.json` —
you do not need `meta.json` enriched for this) for the CE identity, vitals, and
Shapley split; skim `ce_health_report.md` only if you need a number the sidecar
doesn't carry. Present the diagnosis **in chat** (not a file) as a **scannable,
table-driven** preview — this is a decision surface for a stakeholder, so it must
be skimmable in seconds, **not** a wall of prose. The numbers do the talking;
your job is to lay them out, not narrate them.

**Format — follow this shape (markdown tables render in the chat):**

```
**CE Health — <CE name> (CE <id>)**
<type> · <market> · <evolution_bucket> · <management_type> · <headout_status>
Window: <pre> vs <post>

**Vitals**

| Metric      | Pre        | Post       | Δ              |
|-------------|------------|------------|----------------|
| Revenue     | $<pre>     | $<post>    | <+/−x%> ↑/↓     |
| Orders      | <pre>      | <post>     | <+/−x%> ↑/↓     |
| CVR         | <pre>%     | <post>%    | <+/−x pp> ↑/↓  |
| AOV         | $<pre>     | $<post>    | <+/−x%> ↑/↓    |
| Completion  | <pre>%     | <post>%    | <+/−x pp> ↑/↓  |
| Take Rate   | <pre>%     | <post>%    | <+/−x pp> ↑/↓  |

<one optional caveat line if it matters, e.g. "YoY revenue is −43% despite the
sequential growth.">

**Shapley driver ranking** (contribution to the revenue change)

| # | Driver          | Contribution | Share | Dir |
|---|-----------------|--------------|-------|-----|
| 1 | <driver>        | $<x>         | <x>%  | ↑/↓ |
| 2 | <driver>        | $<x>         | <x>%  | ↑/↓ |
| ... |

**Primary driver: <driver>.** <one sentence on the mechanism — the single most
useful line of interpretation, e.g. "Paid CVR lifted ~2.9%→3.9% alongside rising
spend; S2C and C2O both improved while LP2S softened.">

**Default deep-dive:** <skills, e.g. "CVR-RCA + perf-audit"> — <half-line why>.

Reply **"continue"** for the default, or steer (e.g. "focus on supply", "skip
perf-audit", "CVR only").

Optional — sharpen the RCA. Add any of:
 • a focus area or hunch   • known dates (deploy / pricing / promo)
 • an MMP doc (link)   • an ad-hoc Sheet (link)   • a Slack channel
What inputs help (examples) → <SKILL_DIR>/references/input_guide.md
Or just "continue" to skip.
```

**Formatting rules for the preview:**
- **Always surface the input guide as a clickable link.** Replace `<SKILL_DIR>`
  with the real absolute skill path (e.g. `/Users/.../ce-rca/references/input_guide.md`)
  so the user can open it — a relative path won't render as clickable, and the
  guide is **never loaded into context**, so this link is the user's only window
  into it. Do not drop or collapse this line.
- Pick the right delta unit per metric: **% change** for revenue/orders/AOV
  (level metrics), **percentage points (pp)** for rates (CVR / completion / take
  rate). Never express a rate move as a % of a %.
- Add a direction glyph (↑/↓) so the table reads at a glance; keep one sentence
  of interpretation max under each table — everything else is the deep dive's job.
- Keep it tight: identity + two tables + a primary-driver line + the prompt.
  Resist adding paragraphs; if a point needs a paragraph, it belongs in the RCA,
  not this preview.

**Then stop and wait for the user's reply.** Do not dispatch until they respond.
Parse their reply in natural language — there's no rigid command set. "continue"
/ empty / "yes" → the default set, no context captured. Anything else → interpret
their intent against the registry and resolve a final dispatch set. If they name a
driver with no registered sub-skill (e.g. AOV today), say so and proceed with what
is available.

### Capturing user context (optional — `user_context.md`)

If the user's reply contains any steering or context beyond a bare
continue/pivot, capture it. **This is optional and additive** — most runs will
skip it, and skipping must stay zero-friction (a bare "continue" writes no file
and changes nothing). When there *is* context, parse the free-form reply into a
**short, structured** `<run_dir>/user_context.md` — labeled slots, a handful of
bullets each, never a transcript of the chat (the deep dives read this file, so
keeping it lean protects their context window):

```markdown
# User Context (provided <date>)

## Focus / direction
[what the user wants prioritised — e.g. "Focus on CVR — user believes it's the
 driver". Also feeds the dispatch decision above.]

## Hypothesis priors
[where the user thinks the problem is — e.g. "LP2S at the landing-page level —
 user's intuition something's broken / always broken here". Each becomes a
 PRIORITISED, FALSIFIABLE branch in the deep dive — tested, can be ruled out.]

## Known events
[operational facts — e.g. "Pricing changed Apr 8", "ran a promo last week".
 Each seeds a hypothesis AND anchors a Step 2b corroboration.]

## Sources
[provenance only — each named source and what became of it, e.g. "MMP doc <link>
 → 2 priors above"; "Sheet <link> → user_data_<slug>.md lens"; "#mkt-france →
 CVR-RCA Slack agent". The distilled content lives in the slots above / the lens
 file — never paste raw source text here.]
```

Only write slots that have content.

### Step 1b — Ingest named sources (optional)

If the reply names a non-Slack source (Drive / MMP doc, Google Sheet), spawn the
ingestion sub-agent (`references/context_ingest_guide.md`) with the pointers + CE
context + `run_dir`; it reads them in its own context and **returns** a lean
distillate (never raw text). Persist by nature: narrative/history → merge into the
Priors / Known events slots above (tag the source); tabular data → a
`<run_dir>/user_data_<slug>.md` lens. Slack channels are read later by CVR-RCA's
Slack agent (Step 2), not here.

### Echo back, then proceed

After parsing (and any ingestion — see Step 1b) confirm your interpretation in one
compact line — parsed focus / known events / sources read / Slack channel to read
— then **dispatch without a hard stop** so a misparse can still be caught. E.g.
*"Got it: focus LP2S; event Apr 8 (→ chart marker); read MMP doc + Sheet; will
read #mkt-france alongside discovery. Proceeding — reply to adjust."* Skip
entirely on a bare "continue".

**How the deep dives use it (so you set expectations correctly):** `user_context.md`
is the analyst's *intent*, not another evidence lens — so CVR-RCA reads it at
**L0** (priors become prioritised, falsifiable branches) **and** corroborates it
at Step 2b. It **steers attention, never the conclusion**: the full data-driven
investigation still runs, the primary driver is whatever the data says, and a
prior can be RULED OUT. See `cvr-rca/SKILL.md → "Signal 0 — user context"`.

---

## Step 2 — Dispatch the matched sub-skills

Read `references/registry.md`. Map the confirmed drivers to sub-skills and apply
the **CVR ⇒ also-fire-perf-audit** pairing rule. Every sub-skill is **vendored
inside this bundle** at a fixed path — `$SKILL_DIR/skills/cvr-rca/`,
`$SKILL_DIR/skills/perf-audit/`, `$SKILL_DIR/skills/ce-health/` — so there is no
path resolution: you already know where each one is. If a chosen sub-skill's
folder is missing, **fail fast** ("reinstall the CE-RCA bundle"); never hunt for
it elsewhere or run it from `~/Documents`.

**Write the orchestration handshake first** — before spawning anything — to
`<run_dir>/orchestration.json`:

```json
{
  "orchestrator": "ce-rca",
  "version": "<this skill's VERSION>",
  "fired_by_master": ["perf-audit-skill", "cvr-rca"],
  "context_lenses": ["ce_health_report.md", "perf_audit_report.md", "slack_context.md", "user_data_<slug>.md"],
  "user_context": "user_context.md",
  "user_slack_channels": ["#mkt-france"],
  "run_dir": "<absolute run_dir path>"
}
```

`fired_by_master` lists every sub-skill you're about to fire. This is the
contract that stops CVR-RCA from double-firing perf-audit: CVR-RCA checks this
file and, seeing `perf-audit-skill` listed, skips its own perf-audit spawn and
consumes the master's output instead.

`user_context` points at the structured `user_context.md` you wrote at Step 1 —
**only include this key if you actually wrote that file** (the user provided
context). It is deliberately **separate from `context_lenses`**: the lenses are
secondhand evidence consumed only at Step 2b, but user context is the analyst's
*intent* — the deep dive reads it earlier, at L0, to prioritise (not narrow)
its branches. Omit the key on a bare-continue run.

`context_lenses` is the **cross-skill manifest** — the list of lens artifacts the
deep dives should reconcile against at their synthesis step. Always include
`ce_health_report.md` (CE Health ran in Step 0, so it's available to every deep
dive). Include `perf_audit_report.md` when perf-audit is firing, and
`slack_context.md` (CVR-RCA's own Slack sub-agent writes it). This is what makes
the tabs talk: CVR-RCA reads this manifest at its Step 2b and folds CE Health's
CE-level facts into its funnel findings (e.g. corroborating a TGID's S2C drop
against CE Health's RPC drop for that same TGID). See `cvr-rca/SKILL.md → Step 2b
→ "Context reconciliation"`. Also append each `user_data_<slug>.md` lens written
at Step 1b — it reconciles with the same model, no new mechanism.

`user_slack_channels` (optional) lists any Slack channel the user named at Step 1;
CVR-RCA's Slack agent reads them alongside its discovery set. Omit when none.

**Spawn the sub-skills in parallel** (one sub-agent each, single message,
multiple Agent calls). Each sub-agent prompt says: read your skill's SKILL.md at
its fixed bundle path (`$SKILL_DIR/skills/cvr-rca/SKILL.md`,
`$SKILL_DIR/skills/perf-audit/SKILL.md`) and run it exactly as written, using
`<run_dir>` as the run directory (do not create your own), for CE `<id>`, pre
`<pre>`, post `<post>`. Pass nothing else — the sub-skills own their own logic.

Wait for **all** sub-agents to finish before synthesising.

Log each spawn in `_run_log.md`. If a sub-skill fails, note it and continue —
the composite simply won't carry that tab.

---

## Step 3 — Synthesise (the Summary tab)

Once every deep dive has finished, fire a **Summary synthesis sub-agent** that
reads all the tab outputs and writes the front-page cross-cutting synthesis. This
is the surface where the tabs truly talk to each other — it traces the headline
revenue driver across CE Health, CVR-RCA, and perf-audit, and builds the
cross-reference table that links every finding to its corroboration.

Spawn one sub-agent with this prompt: read `$SKILL_DIR/references/summary_guide.md`
and follow it exactly. Run dir: `<run_dir>`. Available lens artifacts:
`<the context_lenses list + cvr_rca findings.md/report.html>`. It writes
`<run_dir>/summary_report.html` (a polished HTML body fragment using visual-kit
chrome — vitals cards + root-cause callout + cross-reference table + per-driver
blocks). It is **pure synthesis** — it weaves existing findings and never runs
queries or computes new numbers.

Wait for `summary_report.html`. **Graceful degradation:** if the Summary agent
fails or doesn't produce the file, log it in `_run_log.md` and proceed to
compose — the composite simply won't carry a Summary tab (the deep-dive tabs are
unaffected).

---

## Step 4 — Compose the report

Read `references/composition_rules.md` for the full spec. The mechanics:

**4a. Build the header decorations.** These are the small, last-mile header
bits — all assembled here, at compose time, so they reflect the final confirmed
window and never get narrated mid-run. Do them as one quiet step.

**(i) Create `meta.json` (whole) from what you know + CE Health's sidecar.**
This is the first and only time `meta.json` is written. **`meta.json` is
machine-only plumbing** — its sole consumer is `compose.py`'s header builder; it
is never shown to the user, so write it quietly and don't narrate it. Combine:

- **From the confirmed window + run context:** `ce_id`, `pre_period`,
  `post_period`, `post_start`, `post_end`, `generated_date` (today).
- **From CE Health's sidecar** (`<run_dir>/ce_health_report.json`):
  `combined_entity_name`, `combined_entity_type`, `market`, `country`; the five
  CE-metadata pill fields from the sidecar's `metadata` block —
  `combined_entity_category`, `combined_entity_subcategory`, `evolution_bucket`,
  `management_type`, `headout_status` (`compose.py`'s `build_header` renders any
  present as translucent header pills — this is CE Health's "## 1. CE Metadata",
  since the CE Health tab itself starts at §2, so don't drop them; omit any field
  the sidecar doesn't carry); and `top_page_url` from `metadata.top_page_url` if
  present (the most-visited landing page, derived like CVR-RCA's Q0). If the
  sidecar carries no `top_page_url`, the (iii) back-fill covers it.

```json
{
  "ce_id": 252,
  "combined_entity_name": "<from sidecar>",
  "combined_entity_type": "<from sidecar>",
  "market": "<from sidecar>",
  "country": "<from sidecar>",
  "combined_entity_category": "<from sidecar>",
  "combined_entity_subcategory": "<from sidecar>",
  "evolution_bucket": "<from sidecar>",
  "management_type": "<from sidecar>",
  "headout_status": "<from sidecar>",
  "pre_period": "<pre_start> to <pre_end>",
  "post_period": "<post_start> to <post_end>",
  "post_start": "<post_start>",
  "post_end": "<post_end>",
  "generated_date": "<today>",
  "top_page_url": "<from sidecar, if present>"
}
```

**(ii) Omni dashboard URL.** Build the Omni pill from CVR-RCA's
`report_structure.md → "Dashboards row — Omni"`, which has two templates:
- **Default window** (the user kept the 30/30 default): substitute only
  `<CE_ID>` — the URL keeps Omni's relative `30 complete days ago / 30 days` date
  params so the dashboard runs its own last-30-vs-prior-30 comparison.
- **Custom window** (the user passed a specific date range at Step 0b): use the
  absolute `BETWEEN` template — substitute `<CE_ID>`, `<POST_START>` (post-window
  start, `YYYY-MM-DD`), and `<POST_END_EXCLUSIVE>` (post-window end **+ 1 day** —
  Omni's `BETWEEN` upper bound is exclusive). This makes the Omni link show
  exactly the period the RCA covers.

You know whether the window is custom (from Step 0b) and the post dates (in
`meta.json`), so pick the right template and write
`"dashboards": [{"label": "Omni", "url": "<built Omni URL>"}]` into `meta.json`.
`compose.py`'s `build_header` renders it as the Omni pill.

**(iii) `top_page_url` back-fill — fallback only.** Sub-step (i) already sets
`top_page_url` from CE Health's sidecar in the normal case. This is a **fallback**
for the rare case where CE Health found no landing-page data but CVR-RCA did: if
`<run_dir>/summary.json` exists and `meta.json` still has no `top_page_url`, copy
it across from CVR-RCA's `meta.top_page_url`. (If `top_page_url` is already set,
this is a no-op — the `not meta.get("top_page_url")` guard handles it.)

```bash
python3 - <<'PY'
import json, pathlib
rd = pathlib.Path("<run_dir>")
meta = json.loads((rd/"meta.json").read_text())
summ = rd/"summary.json"
if summ.exists() and not meta.get("top_page_url"):
    tpu = json.loads(summ.read_text()).get("meta",{}).get("top_page_url")
    if tpu:
        meta["top_page_url"] = tpu
        (rd/"meta.json").write_text(json.dumps(meta, indent=2))
        print("back-filled top_page_url:", tpu)
PY
```

(If CVR-RCA didn't run, there's no `summary.json` — the header simply omits the
landing-page link, which is acceptable.)

**4b. Rename CVR-RCA's report** (if cvr-rca ran) so `compose.py` can read it
without a same-path read/write against the composite output:

```bash
mv "<run_dir>/report.html" "<run_dir>/cvr_rca_report.html"
```

(Only if cvr-rca ran and wrote `report.html`. perf-audit, CE Health, and the
Summary write artifacts that need no rename.)

**4c. Render the beautified CE Health tab.** Re-render CE Health's structured
output into visual_kit chrome (the structured-re-render mode of the cardinal
rule):

```bash
python3 "$SKILL_DIR/scripts/render_ce_health.py" --run-dir "<run_dir>"
```

This reads `ce_health_report.json` + `.md` + `meta.json`, runs Query 1 via the
`bq` CLI (CE-level traffic/converters + booking-revenue components for the
windows in `meta.json`), and writes `<run_dir>/ce_health_tab.html` — a body
fragment with metric cards, L12M charts, styled full-fidelity tables, and the
corrected 6-factor Shapley waterfall. **A render failure is non-fatal:** if this
step errors or the file isn't produced, `compose.py` falls back to the verbatim
markdown render of `ce_health_report.md` (the CE Health tab still appears, just
unbeautified). If Query 1 itself fails, the renderer keeps the tab and renders
CE Health's §7 table verbatim instead of the waterfall. Log the outcome in
`_run_log.md`.

**4d. Run the composer:**

```bash
python3 "$SKILL_DIR/scripts/compose.py" --run-dir "<run_dir>"
```

This reads the present artifacts (`summary_report.html`, `ce_health_tab.html`
— or `ce_health_report.md` as fallback, `cvr_rca_report.html`,
`perf_audit_report.md`), builds one tab each in fixed reading order (**Summary →
CE Health → CVR RCA → Paid Performance Audit → Follow-ups → Transcript**), embeds
the Summary and CE Health fragments verbatim, converts the perf-audit markdown
verbatim, extracts CVR-RCA's CVR content + charts, injects the shared visual_kit
styling, and writes the composite to `<run_dir>/report.html`. Every tab is
conditional — emitted only if its artifact exists.

The **Transcript** tab is built automatically and is **always last**: `compose.py`
collects every transcript file in the run dir and renders each verbatim (monospace)
as its own sub-tab, so stakeholders can read what each skill actually did. You do
**not** assemble it by hand. The collection contract is scalable and registry-driven:
- CVR-RCA's generic `<run_dir>/transcript.md` → the **CVR-RCA** sub-tab (by convention).
- Any skill that writes `<run_dir>/transcript_<skill>.md` auto-appears as a sub-tab
  (label humanized from the suffix) — no code change needed.
- The orchestrator's own `_run_log.md` is deliberately excluded (no `transcript` name),
  so it never shows.

**4e. Report the result.** Tell the user where the composite landed and which
tabs it contains. Keep it short — the report is the deliverable, not a chat recap.
Then invite follow-ups (Step 5).

---

## Step 5 — Follow-ups (the playground)

The report is not the end of the conversation — it's a **context-rich playground**.
After 4e, invite the analyst to ask follow-up questions **in this same session**, and
handle each one per **`references/followup_guide.md`**. Read that guide now if you
haven't; the essentials:

- **Answer in chat first, always.** Route each question: *reinterpret* (from
  `findings.md`/`transcript.md`) → *re-aggregate from disk* (daily rows in
  `stage3/stage7`, segment/channel in `summary.json`, **TGID revenue/traffic from
  `ce_health_report.json` §6**) → *bounded re-query* (a small, scoped query using the
  bundled `skills/cvr-rca/references/q{2,4,5,6}.sql` patterns when the cut — per-TGID
  funnel, device, geo, URL, price — isn't on disk) → *cross-tab synthesis*. Stay within
  the run's **fixed segment + window**.
- **Promote only on an explicit ask.** After a substantive answer, offer to add it to the
  report. On yes, append an **audited `.analysis-block` card** (question · answer ·
  how-answered tag pill · date · `↗` citations — **no SQL**) to `<run_dir>/followups.html`
  (a visual-kit HTML fragment, authored like the Summary tab — see `followup_guide.md`),
  then re-run the composer so the **Follow-ups & Q&A** tab refreshes:

  ```bash
  python3 "$SKILL_DIR/scripts/compose.py" --run-dir "<run_dir>"
  ```

  Re-composition is idempotent and **append-only** — the other tabs never change.
- **The pivot rule.** Any question that changes the **time window** or otherwise
  **re-scopes** the run is **not** a follow-up. Do not answer in place and do not recompute.
  Offer to spawn a **fresh `/ce-rca`** run on the new scope, and (if promoted) drop a
  one-line pointer to it in the Follow-ups tab. Every report stays one-window-consistent.

v1 is **in-session only** — a durable `/ce-rca-ask <CE-or-run> "<question>"` re-entry
across sessions is deferred (see Future hooks).

---

## What this skill does NOT do

- **Investigate.** All investigation lives in the sub-skills. The master never
  forms hypotheses or runs diagnostic queries.
- **Edit sub-skill output.** Verbatim, always. The Summary tab synthesises
  *across* tabs but never paraphrases or restyles any tab's own content.
- **Modify the sub-skills.** CE Health, CVR-RCA, and perf-audit run as-is. The
  cross-skill wiring is: CVR-RCA reads `orchestration.json` (to avoid
  double-firing perf-audit, and to pick up the `context_lenses` manifest so it
  reconciles CE Health at its Step 2b). perf-audit and CE Health are untouched.

## Cross-skill data flow (how the tabs talk)

```
CE Health (Step 0, upstream)  ──┐  facts available to all deep dives
                                ▼
CVR-RCA reads the context_lenses manifest at its Step 2b and reconciles its
funnel findings against CE Health + perf-audit + Slack (four-pattern model) →
its tab cites CE Health (e.g. a TGID's RPC drop) inline.

Summary (Step 3, downstream)  ◄── reads ALL finished tabs → cross-reference table
+ headline root cause spanning every tab. The peer↔peer weave lives here.
```

- **Upstream → deep dives:** one-directional, clean (CE Health finished first).
- **Deep dive ↔ deep dive:** CVR reads perf (it fires it); the full peer weave is
  the Summary's job (avoids circular dependency).
- **Everything → Summary:** the front-page synthesis.

## Future hooks (designed-in, deferred)

1. **Summary → arbiter.** Today the Summary is **pure synthesis** — it weaves
   existing findings and never re-queries. The deferred upgrade lets it fire one
   tie-break query when two tabs genuinely contradict. Noted in `summary_guide.md`.
2. **perf-audit cross-skill enrichment (owner hand-off).** perf-audit should also
   read CE Health (and CVR-RCA findings) at its own synthesis and cite them in its
   tab — mirroring CVR-RCA's manifest context layer. perf-audit is owned by
   another team, so this is a hand-off, not our change. See `references/registry.md`.
3. **User context paste — v1 shipped (free-text steering).** The Step 1 pause
   now captures focus / hypothesis priors / known events into a structured
   `user_context.md`, which CVR-RCA consumes at L0 (prioritised falsifiable
   branches) + Step 2b (corroboration). **v2 remainder (deferred):** ingest the
   "Deferred inputs" slot — attached files, Google Sheets, user-named Slack
   channels (files lowest-risk first). And perf-audit should consume
   `user_context.md` the same way (owner hand-off).
4. **More drivers** — AOV-RCA, Completion-RCA, Take-Rate-RCA plug into
   `registry.md` and `compose.py`'s `TAB_SPECS` as one-row / one-entry additions.
5. **Report-as-playground — v1 shipped (in-session follow-ups).** Step 5 lets the
   analyst interrogate a finished report in-session; substantive Q&A is opt-in
   promoted into a Follow-ups tab (`references/followup_guide.md`). **Deferred:** a
   durable `/ce-rca-ask <CE-or-run> "<question>"` re-entry that reopens a past run
   dir outside the original session, and attaching the same playground to a
   standalone CVR-RCA report.

## Changelog

| # | Date | Changes |
|---|------|---------|
| m019 | 2026-06-08 | **Transcript tab: markdown-rendered + perf-audit decision tree (v1.9.0).** Two paired improvements. **(1) Rendering.** `compose.py build_transcript_tab()` now renders each transcript **as markdown** (via the already-imported `render_markdown_tab`, heading ids namespaced per sub-tab as `tr-<skill>-…`) instead of dumping it HTML-escaped in a `<pre>` — so headings, tables, and prose are styled. ASCII tree-maps stay aligned because the skills **fence** them (the renderer emits fenced ` ``` ` blocks as verbatim `<pre><code>`); `templates/report.html` drops `.transcript-raw` and adds a `.subtab-pane .md-content pre` style (scroll + chrome). **(2) Both sub-skills fence their tree-maps** (source-repo edits, re-vendored): **CVR-RCA v1.29** wraps its `## Tree map` in a ` ```text ` fence (c044), and **perf-audit v6.3.0** rewrites its Step 6 transcript into a CVR-RCA-style **fenced tree-map + detail sections** (root verdict → per-lens branches CONFIRMED/RULED OUT → LEAF). Both flagged in `registry.md` for upstreaming. Note: an *old* unfenced transcript in a pre-existing run folder renders with a flattened tree — accepted (historical); new runs are fenced. No template JS change; Transcript tab still always-last; collection mechanism (glob `transcript_*.md`) unchanged. |
| m018 | 2026-06-08 | **Beautified CE Health tables — value+delta cells + grouped headers (v1.8.2).** The data-dense CE Health tables crammed a value and its delta into one cell (e.g. `$195.7K -63%`, `95.8% +3.7pp`), which scanned poorly. `scripts/render_ce_health.py`'s shared `styled_table()` gains two opt-in capabilities: **(1) `split_deltas`** — a cell with a trailing delta renders as a **bold value with a smaller colour-coded delta beneath** (green up / red down / amber near-flat, where near-flat = `|Δ|<1pp` or `<5%`, tunable), and a lone-delta cell renders as a single coloured token; **(2) `groups`** — an ordered `(label, span)` **grouped header band** drawn above the column row, emitted **only when the spans line up with the columns** (else skipped — never a broken table). Applied to **§6 Top TGIDs** (in-cell deltas split + grouped bands *Revenue · Order Metrics · Funnel Metrics · Lead-time mix*, the two frozen identity columns preserved) and **§3 Channel Breakdown** (standalone Δ columns coloured). The new CSS (`.ceh-val` / `.ceh-chg` / `th.ceh-group`) is a `<style>` **scoped to `#tab-cehealth`**, emitted with the fragment — **no shared `visual_kit.md` edit, no `compose.py`/template/sub-skill change** (can't leak to other tabs, survives re-vendoring since `vendor.sh` only syncs `skills/`). Other CE Health tables (§2/§4/§9/§10/§11), the §7 Shapley waterfall and §5 L12M charts are untouched; cells without a delta and unexpected column shapes degrade to plain rendering. **Blast radius: `render_ce_health.py` only.** Verified on CE 243 + CE 3593: two-line cells + grouped bands render, 0 leftover `value delta` literals, section anchors intact. |
| m017 | 2026-06-08 | **Follow-ups tab beautified + two render bugs fixed (v1.8.1).** A real run (Antelope) exposed two faults in the Step 5 output layer, both seeded by `followup_guide.md`, plus a presentation gap. **(1) Backlinks dead:** the guide's citation example used `(per CVR RCA ↗)(#block-cascade)` — not valid markdown, so `helpers.py:_md_inline` (matches only `[text](url)`) left it as literal text and produced no `<a>`. (The tab-switch JS and CVR-RCA's `#block-*` anchors were fine all along.) **(2) SQL junk:** the entry format embedded `<details><summary>Query</summary>…` but the markdown renderer passes through only HTML comments, so it rendered as literal text — and it's unwanted. **(3) Fragile/plain:** the minimal markdown renderer mangled adjacent tables (the literal `|…` artifact) and the tab looked unstyled. **Fix:** the Follow-ups tab switches from a markdown source (`followups.md`) to an **`html-fragment`** (`followups.html`), authored with the **visual-kit chrome the Summary tab already uses** — each Q&A is an `.analysis-block` card (`.block-title` question, a `.delta-*` tag pill, answer prose with `.md-table` tables and **valid `<a class="ref-link" href="#<anchor>">↗</a>`** cross-tab links). The SQL/`<details>` block is **removed**. `compose.py`'s `followups` tab-spec becomes `type: html-fragment`, `source: followups.html` (still conditional, still before the Transcript tab). `followup_guide.md` rewrites the entry format to the HTML card + a valid anchor-id list; `composition_rules.md` updated. **Blast radius: `ce-rca` master only** — no new CSS (all classes exist in `visual_kit.md`), no template/sub-skill change; a run with no promoted follow-ups stays byte-identical. |
| m016 | 2026-06-08 | **Input/context layer v2 — freedom-based ingestion (v1.8.0).** The Step 1 pause graduates from free-text-only to a context intake that reads what the analyst points at and folds it through the whole run. **(1) Intake + guide:** Step 1 gains a compact input menu (focus · known dates · MMP doc · Sheet · Slack channel) and surfaces a **clickable** `references/input_guide.md` (authored static, **never loaded into context** — link-only); plus an **echo-back** line (parsed intent + sources read, proceed-unless-corrected). Bare "continue" stays zero-friction. **(2) Context-frugal ingestion sub-agent** (`references/context_ingest_guide.md`): reads Drive/MMP docs + Sheets in its **own** context and **returns** a lean distillate (return-and-write — no Write tool); the orchestrator persists it **split by nature** — narrative/history → `user_context.md` priors/events (L0 steering); tabular data → a `user_data_<slug>.md` **lens** (Step 2b corroboration). Raw content never enters the orchestrator's context. **(3) Sheets via `scripts/read_sheet.py`** (Sheets API over gcloud ADC — private sheets, no key file) primary, Drive MCP CSV fallback, paste/BQ last resort; one-time setup in INSTALL. **(4) Wiring:** `orchestration.json` gains `user_data_<slug>.md` in `context_lenses` + optional `user_slack_channels` (read by CVR-RCA's existing Slack agent — one pass, no second reader). **(5) CE Health §8 "Historical Context"** filled by `render_ce_health.py`: a synthesised **"Historical trajectory"** narrative (written by a new **fire-and-forget CE-history sub-agent**, Step 0e + `references/ce_history_guide.md` → `ce_history.md`: reads prior runs in its own context, returns trend / recurring causes / what's open — no main-context bloat) **+** a deterministic **"Past RCAs for this CE"** index (prior runs matched by `ce_id` across sibling folders — run + headline + `↗`) **+** a "User-Provided & Recent Context" block (`user_context.md` + `user_data_*` + `slack_context.md`, `↗` to Summary for "what we found"). CE Health's own §8 filesystem search (`thoughts/shared/perf-audits|weekly-reviews`) never resolves in the bundle, so its dead "None found" placeholders are **replaced** once real content exists; a bare run with no prior runs renders §8 as before. **(6) Summary tab** reads user context + Slack and tags user-provided corroboration in the cross-reference. **(7) Provenance + event markers** (companion cvr-rca c043): distinct `(per user-provided … ↗)` citation tag; Known-event dates mark CVR-RCA daily/90-day charts (never move the window). **Deferred:** CE Health L12M event marker (monthly axis → coarse, low value); perf-audit user-context (owner hand-off). **Known coupling:** Slack + user channel depend on CVR-RCA firing (today it always does) — elevating Slack to an orchestrator-level lens is future work. cvr-rca re-vendored at v1.28.0. |
| m015 | 2026-06-08 | **Beautified Summary tab — scannable, not a wall of text (v1.7.2).** Presentation pass on the comprehensive Summary (m013) — *coverage unchanged*, only how it reads. Three blocks restructured in `references/summary_guide.md`: **(1) headline callout** is now bulleted + spaced with key numbers as `.delta` pills, and **colour-coded by direction** (`callout` red = decline / `callout improve` green / `callout neutral` blue) instead of an inline-style hack; **(2) per-tab conclusion digests** drop the long-sentence `<ul>` for a **2-column `.conclusions-table`** (bold aspect label → one tight conclusion + delta pill + `↗`; a `.tag` chip marks Slack-/user-sourced rows) — the eye scans the left rail; **(3) Recommended next steps** render as **`.action-card`s** (the CVR-RCA Section-2 component: `.priority-badge` p1/p2/p3 + `.dri-badge` owner + `.cause` + sizing bullets + `↗`), deduped across CVR-RCA actions + perf-audit Recommended Actions. Driver table contribution also shown as a `.delta` pill. **Additive CSS** added to `references/visual_kit.md` inside the extracted `<style>` (so `compose.py:extract_style_block` injects it page-wide): an unscoped `.delta` pill shape (the existing one is scoped to `.metric-card`), `.callout.improve`/`.neutral`, `.conclusions-table`, `.tag` — all in a clearly-commented **"CE-RCA Summary additions (not in cvr-rca source)"** block that only *adds* classes, so re-vendoring from cvr-rca stays a keep-this-block/replace-above operation. **Blast radius: `ce-rca` master only** (`summary_guide.md` + the additive visual-kit block); no sub-skill behaviour change, no `compose.py`/template change. Verified by re-synthesising CE 243 + CE 3593 into `report_v2.html`: action cards + conclusion tables + colored callout render, 0 dangling `↗`. |
| m014 | 2026-06-08 | **perf-audit emits a transcript → second Transcript sub-tab (v1.7.1).** perf-audit now writes a lightweight decision log to `<run_dir>/transcript_perf_audit.md` (new **Step 6** in its SKILL.md: CE + windows, mode + data pulled, one-line verdict per section, headline finding, what was skipped/ruled out — conclusions only, no table dumps). The Transcript tab's existing `transcript_*.md` glob auto-collects it, so it appears as a **Paid Performance Audit** sub-tab beside CVR-RCA. `compose.py`'s `TRANSCRIPT_LABELS` gains `transcript_perf_audit.md → "Paid Performance Audit"` (nice label + ordering; otherwise the glob would humanize it to "Perf Audit"). The change was made in the **perf-audit source repo** (v6.1.0 → **6.2.0**) and re-vendored via `scripts/vendor.sh` — perf-audit is owned by another team, so it's flagged in `registry.md` for **upstreaming**. No engine change (model-authored transcript); no change to the Transcript-tab collection mechanism (m012). |
| m013 | 2026-06-08 | **Comprehensive standalone Summary tab (v1.7.0).** Reframes the Summary from a thin orientation page into a **standalone digest of the whole RCA** — a reader who never opens another tab still gets every conclusion; tabs are for the evidence/nuance behind one. Operating principle added to `references/summary_guide.md`: **carry every tab's conclusions/callouts in full; leave the supporting analysis (dimension cuts, detailed tables, charts) in the owning tab.** New recommended (non-rigid) structure: vitals cards → **long-term context table** (pre→post Δ + YoY Δ, "is the move real?") → headline callout (TL;DR) → optional **"What we set out to check"** block (only when `user_context.md` exists, closing the loop on the analyst's intent) → **per-tab conclusion digests** (one `analysis-block` each for CE Health / CVR-RCA / Paid Perf-audit, conclusions in full, every claim `↗`-linked; corroborating Slack signals folded in tagged Slack-sourced) → driver decomposition table → **consolidated Recommended next-steps** (deduped from CVR-RCA action cards + perf-audit Recommended Actions — relaxes the old "no actions in Summary" rule) → cross-reference table **last**. **Correctness fix:** stale CE Health cross-tab anchors corrected to the deterministic ids `render_ce_health.py` emits (`#cehealth-vitals`, `#cehealth-l12m`, `#cehealth-shapley`, `#cehealth-tgids`, …) so `↗`s land on the right section, not the tab top. The "Freedom to adapt" clause and the pure-synthesis cardinal rule (no new numbers/queries) are preserved. **Blast radius: `summary_guide.md` only** — no `compose.py`/template change (the Summary is still embedded verbatim as an `html-fragment`; it just carries more). Verified by re-synthesising CE 243 + CE 3593 into `report_v2.html`: all per-tab digests present, next-steps present, cross-ref last, 0 dangling `↗`. |
| m012 | 2026-06-08 | **Transcript tab (per-skill sub-tabs, v1.6.0).** A new **Transcript** tab is appended as the **always-last** tab of the composite, so stakeholders can read what each skill actually did (the decision-making), not just its polished output. It carries **sub-tabs**, one per skill that emitted a transcript, each rendered **verbatim in monospace** (`white-space:pre` so CVR-RCA's tree-maps / indentation stay aligned; HTML-escaped; horizontally scrollable). Collection is **registry + glob driven** in `compose.py`: CVR-RCA's generic `transcript.md` → the **CVR-RCA** sub-tab by convention, and any `transcript_<skill>.md` a future skill drops in the run dir auto-appears with a humanized label — **no per-skill code**. New `compose.py` helpers `collect_transcripts()` + `build_transcript_tab()` (appended after the `TAB_SPECS` loop ⇒ always last; conditional — no transcript files → no tab → byte-identical to before). The template gains scoped `.subtab-*` CSS + `.transcript-raw` style + a **scoped** sub-tab switcher (distinct from the global `.tab-pane` JS, so nesting never clobbers the top-level tabs). **Collision fix:** the orchestrator now writes its own run log to `<run_dir>/_run_log.md` instead of `transcript.md` (Step 0c + the Step 2/3/4 log lines), so CVR-RCA's `transcript.md` stays clean for its sub-tab; the underscore name is also excluded from the `transcript*` collection. **Blast radius: `ce-rca` master only** — no sub-skill change (perf-audit/CE Health emit no transcript today; they appear automatically if/when they write `transcript_<skill>.md`). `composition_rules.md` documents the tab. Rendering chosen verbatim-monospace (not markdown) to preserve the tree-maps; orchestrator log deliberately **not** shown as a sub-tab. |
| m011 | 2026-06-08 | **Output layer — "report as a playground" (in-session follow-ups, v1.5.0).** The orchestrator no longer stops at compose. New **Step 5** invites the analyst to ask follow-up questions **in the same session**, handled per the new **`references/followup_guide.md`**. Routing: *reinterpret* (from `findings.md`/`transcript.md`) → *re-aggregate from disk* (daily rows in `stage3`/`stage7`, segment/channel in `summary.json`, **TGID revenue/traffic from `ce_health_report.json` §6**) → *bounded re-query* (a small, scoped query off the bundled `skills/cvr-rca/references/q{2,4,5,6}.sql` patterns when the cut — per-TGID funnel, device, geo, URL, price — isn't persisted) → *cross-tab synthesis*. All answers stay within the run's **fixed segment + window**. **Explicit promote:** answers are given in chat always; only on the analyst's say-so is an **audited entry** (question · answer · how-answered tag · date · SQL + one-line result · `↗` citations) appended to `<run_dir>/followups.md`, after which `compose.py` is re-run (idempotent, append-only — other tabs unchanged). **Pivot rule:** any time-window/scope change is **not** a follow-up — it spawns a fresh `/ce-rca` run, linked by a one-line pointer in the Follow-ups tab; no report is recomputed in place. `compose.py` gains a conditional last `TAB_SPECS` entry (**Follow-ups & Q&A**, `markdown`, `followups-` anchors); a run with no promoted follow-ups is byte-identical to before (no `followups.md` → no tab). `composition_rules.md` documents the tab. **Blast radius: `ce-rca` master only** — the handler *reads* CVR-RCA's `q*.sql` patterns; no sub-skill changes. Feasibility note: granular cuts (per-TGID funnel, device, geo, URL, price) are not persisted by a run, so those follow-ups are bounded re-queries by design; persisting them in CVR-RCA to make them instant is a recorded deferral. |
| m010 | 2026-06-05 | **`meta.json` built once, at compose — no early write.** Confirmed by reading the scripts that `meta.json`'s *only* consumer is `compose.py`'s `build_header` (header chrome: CE name / dates / market / pills / Omni pill / landing-page link + title/footer); `render_ce_health.py` does **not** read it (it gets windows from CE Health's own sidecar `d["windows"]`), the deep dives are passed windows directly, and `compose.py` degrades gracefully if it's absent (`meta = {}`). So the Step 0c "minimal `meta.json`" write is removed — Step 0c now only creates the run dir + opens `transcript.md`. The whole file (base window fields + sidecar enrichment + Omni URL + back-fill) is written once at **Step 4a(i)**. The confirmed window is already recorded in the run-dir name and transcript, so nothing needs persisting early. Also corrected the stale SKILL.md claim that `render_ce_health.py` reads `meta.json` for windows. No script change. |
| m009 | 2026-06-05 | **Table-driven Step 1 preview + all meta enrichment deferred to compose.** **(1) Preview restructure.** The Step 1 diagnosis preview was wordy paragraph prose; it's now a **scannable, table-driven decision surface** — CE identity line, a **Vitals table** (Metric/Pre/Post/Δ with ↑/↓ glyphs and correct units: % for level metrics, pp for rates), a **Shapley driver table** (rank/driver/contribution/share/dir), one primary-driver interpretation line, then the continue/steer + optional-context prompts. Explicit formatting rules added (per-metric delta unit; one sentence of interpretation max per table; no paragraphs — those belong in the RCA). **(2) Enrichment fully deferred.** Step 0e (mid-run `meta.json` enrichment) is **removed** — nothing between Step 0 and compose reads the enriched fields, so CE name/type/market/country, the 5 metadata pills, and `top_page_url` are now all read from CE Health's persisted sidecar at **Step 4a(i)**, alongside the Omni URL (4a-ii) and the back-fill (4a-iii). Eliminates the mid-run plumbing step and its chat narration ("enriching meta.json…"). Step 1 reads the sidecar **directly** for the preview — it never needed `meta.json` enriched. No script change. |
| m008 | 2026-06-05 | **Window-first ordering + Omni URL deferred to compose.** Two sequencing fixes to Step 0. **(1) Confirm the window before anything.** New Step 0b asks the user which period they want (default 30/30 or custom) and **waits** — no run dir, no `meta.json`, no CE Health fires until they answer. Previously the run defaulted silently and built scaffolding before the user could change the dates, risking redone work. Old 0b/0c/0d renumbered to 0c/0d/0e; 0c is now flagged **[Silent plumbing]** with an explicit note that `meta.json` (windows/name/pills consumed by `render_ce_health.py` + `compose.py`) and `transcript.md` (internal run log) are machine-only and must not be narrated in chat. **(2) Omni URL is end-game, not Step 0.** The `dashboards`/Omni-URL build moved out of enrichment (old 0d) into compose (Step 4a), so the pill reflects the final confirmed window and nothing showcases a header decoration mid-run. `top_page_url` stays a passive sidecar copy at 0e (it's a field read, not a constructed URL). No script change — `build_header` still renders `meta.json.dashboards`/`top_page_url` whenever present. |
| m007 | 2026-06-05 | **Self-contained bundle (v1.4.0).** The three sub-skills are now vendored inside the bundle under `skills/` (`skills/cvr-rca/`, `skills/perf-audit/`, `skills/ce-health/`) at fixed paths — no runtime path resolution, no hunting, no per-run shim. Step 0c fires CE Health from `$SKILL_DIR/skills/ce-health/ce_health.py` (the vendored copy is patched to run standalone — imports its own `engine/`, repo-root = skill dir); Step 2 resolves deep-dives at `$SKILL_DIR/skills/<name>/`. All prior path-resolution hunting (env → `~/.x` → sibling → `~/Documents`) is replaced with fixed bundle paths + a fail-fast rule ("reinstall the bundle" — never improvise a shim or hunt). `scripts/vendor.sh` re-syncs `skills/*` and re-applies the CE Health patch. registry.md pins paths + invocations; INSTALL.md becomes one-step (companion-detect steps removed). Packaging only — RCA logic, report, tabs, composer, orchestration handshake unchanged. Fixes the wall of pre-flight repair steps that ran before every `/ce-rca`. |
| m006 | 2026-06-05 | **Beautified CE Health tab (structured re-render).** The CE Health tab is no longer a wall of verbatim markdown tables — it's re-rendered into visual_kit chrome to match the CVR-RCA / Summary tabs, while preserving CE Health's content exactly (sections 1→11, exact headings, exact order, **all** rows). New deterministic renderer `scripts/render_ce_health.py` (Step 4c) reads CE Health's `.json` + `.md` + `meta.json`, runs Query 1 via the `bq` CLI (CE-level traffic/converters from the funnel + booking-revenue components from `combined_entity_stats`), and writes `ce_health_tab.html`: §1 Metadata → header pills (Step 0d copies the 5 fields into `meta.json`; `build_header` renders them), §2 Vitals → 6 metric cards + the full 4-window table, §5 L12M → 2 Plotly charts (same data as the monthly tables), §6 TGIDs → styled table with the first 2 columns frozen, §7 → the **one agreed exception**, a corrected canonical 6-factor booking-revenue Shapley waterfall (CE Health's own Shapley is mis-specified). `compose.py`'s CE Health `TAB_SPECS` entry switches to `html-fragment` (embedded verbatim, inline Plotly executes) with a **markdown fallback** — if the fragment is absent (render skipped/failed), the tab falls back to the verbatim markdown render, so a failed beautification never costs the tab. If Query 1 fails, the renderer keeps the tab and renders CE Health's §7 table verbatim. The **cardinal rule** is amended with the verbatim-embed (perf-audit) vs structured-re-render (CE Health, CVR-RCA) split. No CE Health skill change; no new CSS; no new compose tab-type. |
| m005 | 2026-06-03 | **User-context input layer v1 (free-text steering).** The Step 1 pause gains an optional context prompt; the user's free-form reply is parsed into a short, structured `<run_dir>/user_context.md` with labelled slots (Focus / Hypothesis priors / Known events / Deferred inputs). `orchestration.json` gains a `user_context` pointer — kept **separate from `context_lenses`** because user context is the analyst's *intent* (read at the deep dive's L0 to prioritise branches), not a Step-2b-only evidence lens. Skipping is zero-friction (bare "continue" → no file, no behaviour change). Files / Google Sheets / Slack channels are captured under "Deferred inputs" with a not-consumed-yet note (v2). CVR-RCA dual-consumes the file (c042): L0 steering (prioritised, falsifiable branches) + Step 2b corroboration; it steers attention, never the conclusion, and the full data-driven investigation still runs. Future-hook #3 promoted from deferred to v1-shipped. |
| m001 | 2026-06-03 | Initial version. Top-down master orchestrator for CE-level RCAs. Step 0 runs CE Health (foreground); Step 1 presents the diagnosis and pauses for free-form user confirmation; Step 2 dispatches matched deep-dive skills (CVR-RCA + perf-audit today) in parallel after writing the `orchestration.json` handshake; Step 3 composes a tabbed report via `scripts/compose.py`. Sub-skill outputs appear verbatim (composer, not editor). Registry-driven dispatch (`references/registry.md`) makes new sub-skills one-row additions. Visual kit vendored from cvr-rca; composite styling extracted from it at build time so the umbrella report is visually identical to a standalone CVR-RCA report. Future hooks (user context paste, cross-skill references, summary skill) designed-in but deferred. |
| m004 | 2026-06-03 | **Header completeness — Omni pill + landing-page link from CE Health (v1.1.3).** Two header elements that were silently missing now render reliably. **(1) Omni dashboard pill:** Step 0d adds the `dashboards` array **unconditionally** (it only needs the CE ID), so every composite header carries the Omni link. **(2) Landing-page link (`top_page_url`):** CE Health now emits the most-visited landing-page URL in its sidecar at `metadata.top_page_url` (derived from the highest-traffic page in its landing-page funnel, mirroring CVR-RCA's Q0), so Step 0d reads it directly — the 🔗 link + clickable CE name render from the start, before the deep dives and even when CVR-RCA isn't dispatched. Step 4a is kept as a `summary.json` fallback only (CE Health found no LP data but CVR-RCA did). No `compose.py` change — `build_header` already renders both when `meta.json` carries them. Paired CE Health change (local skill, not git-versioned): `ce_health.py` derives + injects `top_page_url` into `meta` (flows to sidecar + the "## 1. CE Metadata" markdown table). |
| m003 | 2026-06-03 | **Sentra dashboard link deprecated (v1.1.2).** Step 0d's `meta.json` enrichment now adds the Omni dashboard link only (was Omni + Sentra) — Sentra is being retired. `compose.py` builds the dashboards row generically from `meta.json.dashboards`, so dropping Sentra from the instruction is the only change needed; `composition_rules.md` (header-chrome line + meta.json example) and the `visual_kit.md` Page-skeleton doc-comment are updated to match. Paired with CVR-RCA v1.26 c041 (standalone-side Sentra trim). |
| m002 | 2026-06-03 | **Cross-skill RCA: Summary synthesis tab + context manifest.** Two additions make the tabs talk to each other. **(1) Context manifest:** `orchestration.json` gains a `context_lenses` array listing the lens artifacts deep dives should reconcile against (CE Health + perf-audit + Slack). CVR-RCA reads this at its Step 2b (v1.25) and folds CE Health's CE-level facts into its funnel findings — e.g. corroborating a TGID's S2C drop against CE Health's RPC drop for that same TGID. **(2) Summary tab:** new Step 3 (Synthesise) fires a pure-synthesis sub-agent (`references/summary_guide.md`) that reads every finished tab and writes `summary_report.html` — a polished HTML fragment (vitals cards + root-cause callout + cross-reference table + per-driver blocks) that traces the headline revenue driver across all tabs with `↗` cross-tab links. Compose renumbered to Step 4; `compose.py` adds the Summary as the first tab via a new `html-fragment` type (embedded verbatim). Tab order: Summary → CE Health → CVR RCA → Paid Performance Audit. Summary is the peer↔peer weave surface (avoids circular cross-referencing in individual deep-dive tabs). Graceful degradation: if the Summary agent fails, the composite still builds without that tab. Pure-synthesis for now — an arbiter upgrade (tie-break query on contradiction) is a documented TODO. perf-audit cross-skill enrichment is a hand-off TODO for its owner. |
