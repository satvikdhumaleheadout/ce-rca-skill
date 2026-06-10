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

Derive the skill directory from the path of this SKILL.md. **Set `SKILL_DIR` to the
absolute directory THIS SKILL.md was read from** — not a hardcoded path. Every later
`$SKILL_DIR/...` reference (the vendored engine, sub-skills, references) depends on it,
so it must point at the bundle you are actually running:

```bash
SKILL_DIR="<absolute dir this SKILL.md was read from>"   # e.g. ~/.ce-rca for downloaded installs
```

### Stay on the latest version — do this first, every run

CE-RCA **auto-updates — but only for the canonical install at `~/.ce-rca`.** The auto-update
rewrites `~/.ce-rca` wholesale, so it must never fire against a dev/local copy. Guard it on
`SKILL_DIR`:

- **If `SKILL_DIR` is *not* `~/.ce-rca`** (a dev checkout or any other location): **skip the
  version check entirely and proceed** to Step 0 on the copy you're running. No curl, no
  comparison, no "stale" warning — a local copy is intentional, and the canonical-install
  updater would be wrong here (it would clobber `~/.ce-rca`, not your copy). This avoids both a
  false "out of date" alarm and the denied-curl dead-end.
- **If `SKILL_DIR` *is* `~/.ce-rca`** (the downloaded install): run the check below and silently
  upgrade if behind — so a run never executes a stale skill. For downloaded users this is
  unchanged.

```bash
# Only run this block when SKILL_DIR == ~/.ce-rca (canonical install). Otherwise skip it.
INSTALLED=$(cat "$SKILL_DIR/VERSION" 2>/dev/null || echo "0.0.0")
LATEST=$(curl -s --max-time 3 https://raw.githubusercontent.com/satvikdhumaleheadout/ce-rca-skill/main/VERSION 2>/dev/null | tr -d '[:space:]')
echo "$LATEST" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || LATEST="unknown"   # offline/empty -> unknown
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
and after an update obey the freshly-read SKILL.md, not this in-memory copy.

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

**0c. [Silent plumbing — batch it] Create the run dir.** Once the window is
confirmed, create:

```
~/Documents/CE RCA Runs/<ce-slug>-<post_start>-to-<post_end>/
```

Refer to this as `<run_dir>`. Create the `logs/` subfolder and open
`<run_dir>/logs/_run_log.md` (the orchestrator's own internal run log for
debugging/audit — never surfaced to the user) and log the run start.

**Batch the independent pre-CE-Health plumbing into one bash call** rather than
several sequential round-trips. The version/freshness check (above), CE-slug
resolution, `mkdir -p`, and the run-log seed are all independent — fold them into
a **single** `bash` invocation (one or two at most), e.g.:

```bash
# one round-trip: make the run dir + logs, seed the run log
RUN_DIR="$HOME/Documents/CE RCA Runs/<ce-slug>-<post_start>-to-<post_end>"
mkdir -p "$RUN_DIR/logs" \
  && printf '# CE-RCA run log — %s\n- started %s\n' "<ce-slug>" "$(date -u +%FT%TZ)" \
       >> "$RUN_DIR/logs/_run_log.md" \
  && echo "run_dir=$RUN_DIR"
```

Do **not** spread these across one-step-per-call; the only thing that must stand
alone as a blocking pause is the window confirm (0b).

Write all run-log lines to `<run_dir>/logs/_run_log.md` throughout the run.
**Do not write to `<run_dir>/transcript.md`** — that filename belongs to CVR-RCA's
investigation transcript, which the composer surfaces verbatim in the **Transcript**
tab; keeping the orchestrator's log in `logs/_run_log.md` keeps that tab clean (the
underscore name is also excluded from the Transcript tab's `transcript*` collection).
The final **Organize** step (Step 4f) tidies every other artifact into subfolders;
`logs/_run_log.md` is written there from the start so the actively-appended log never
needs moving.

**Do not write `meta.json` here.** Its *only* consumer is `compose.py`'s header
builder (CE name / dates / market / pills / Omni pill / landing-page link) — a
report-header artifact, nothing between here and compose reads it
(`render_ce_health.py` gets its windows from CE Health's own sidecar, and the
deep dives are passed the windows directly). So `meta.json` is built once, whole,
at **Step 4a**. The confirmed window already lives in the run-dir name and the
run log, so there's nothing to persist early.

**0d. Fire CE Health (foreground — one run, then read the sidecar).**
CE Health is **vendored inside this bundle** at `$SKILL_DIR/skills/ce-health/` — a
fixed path, no resolution or hunting. Run it **in the foreground** and wait for it
to finish — it's fast (its ~30 BigQuery queries run concurrently on an internal
thread pool, ~11 s on CE 252/month), so there's no need to background it or split
it into phases:

```bash
python3 "$SKILL_DIR/skills/ce-health/ce_health.py" --ce-id <id> --range month \
  --output <run_dir>/ce_health_report.md
```

(Use `--range month` for the 30/30 default, or `--start/--end` for the custom
window the user confirmed at 0b.) It runs from any CWD — the vendored copy is
patched to import its own `engine/` and needs no shim.

When it returns, both `<run_dir>/ce_health_report.md` and its JSON sidecar
`<run_dir>/ce_health_report.json` (carrying `vitals + shapley + windows +
metadata`) are complete on disk. Proceed to Step 1 and read the sidecar.

**Fail fast, do not improvise.** If `$SKILL_DIR/skills/ce-health/ce_health.py`
doesn't exist, or it errors, tell the user: *"CE Health is missing or broken in
this bundle — reinstall the CE-RCA bundle (or run `scripts/vendor.sh`)."* and
stop. Never hand-build an import shim, hunt for the skill in `~/Documents`, or
patch paths at runtime — the bundle is self-contained by construction; a miss
means the install is broken, not that you should repair it live.

**0e. Fire the CE-history sub-agent (fire-and-forget — do not wait).** Once CE
Health gives you the `ce_id`, spawn a background sub-agent that reads
`$SKILL_DIR/references/ce_history_guide.md` and writes `<run_dir>/ce_history.md` —
a short synthesised trajectory of **prior** RCAs for this CE. Pass `ce_id`,
`ce_name`, `run_dir`, `runs_root` (the `CE RCA Runs` parent), `output_path`, then
**continue immediately** (like the Slack agent — it works in its own context, so
your context stays clean). Compose surfaces it later; first runs simply have none.

**That's all Step 0 does.** CE Health's `.md` + JSON sidecar are both complete in
`<run_dir>` (the foreground run finished before you reach Step 1). **Do not enrich
`meta.json` now, and do not build the Omni URL now.**
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
doesn't carry. **CVR is now in the sidecar** — read it straight from
`vitals.current.cvr` / `vitals.prior.cvr` (the funnel CVR, orders/users, a 0–100
percentage like the other rate vitals); do not spelunk the `.md` funnel section for
it. Present the diagnosis **in chat** (not a file) as a **scannable,
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

**Want to sharpen this RCA?** *(optional — or just reply **"continue"** for defaults)*
The more I know about this CE, the better I investigate. Most useful first:
 • **📄 MMP doc / CE one-pager** — paste the link; I'll pull the CE overview, your hypotheses, and known constraints from it.
 • **🎯 A hunch / focus** — *"probably LP2S on mobile"*, *"focus on supply"*.
 • **📅 Known events + dates** — *"raised prices Apr 8"*, *"ran a promo last week"*.
 • **🚧 Constraints to respect** — *PPC restrictions, no ticket-only product, no same-day inventory…*
 • **⚠️ What usually breaks here** — *"check inventory stock-outs first"*, *"vendor API errors"*, *"pricing wars"* — I'll hunt these in Slack.
 • **🔗 Where to look** — a Slack channel/thread, an ad-hoc Sheet, a dashboard.
Just drop any of these in plain English (links welcome), or **"continue"** to run with defaults.
```

**Formatting rules for the preview:**
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

## About this CE
[a 2–4 line overview of what this CE is / how it's run — e.g. "Heavily PPC-driven
 city-attraction CE; supply is single-vendor; historically seasonal Apr–Sep peak".
 Best sourced from an MMP doc / one-pager. Orientation, not a hypothesis.]

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

## Constraints
[things the investigation must respect — e.g. "PPC restrictions on this CE",
 "no ticket-only product", "no same-day inventory". These bound what's a plausible
 cause AND seed Slack probes (Step 2).]

## Known failure modes
[what usually breaks here — e.g. "inventory stock-outs first", "vendor API errors",
 "pricing wars". Each becomes a PRIORITISED branch AND a Slack probe (Step 2).]

## Important links
[durable references — a `link · what it gives` line each, e.g.
 "MMP doc <link> · CE history + supply notes"; "Omni dashboard <link> · daily CVR".
 Distinct from Sources (provenance): these are links worth keeping in the report.]

## Sources
[provenance only — each named source and what became of it, e.g. "MMP doc <link>
 → About-this-CE + 2 priors above"; "Sheet <link> → user_data_<slug>.md lens"; "#mkt-france →
 CVR-RCA Slack agent". The distilled content lives in the slots above / the lens
 file — never paste raw source text here.]
```

Only write slots that have content.

### Step 1b — Ingest named sources (optional)

If the reply points at any non-Slack source (a doc, a sheet, a link, a file — MMP
docs and ad-hoc Sheets are the common ones, but it's open-ended), spawn the
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

CVR-RCA and perf-audit read `ce_health_report.md` as a **context lens**, so the
complete report must exist before they start — which it already does: CE Health ran
to completion in the foreground at Step 0d, so `<run_dir>/ce_health_report.md` and
its sidecar are on disk before you ever reach this step. No gating or polling is
needed.

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
  "slack_probes": ["inventory stock-out", "vendor API errors", "PPC restriction"],
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

`slack_probes` (optional) is an array of short standing-context search terms
**derived from the `Constraints` + `Known failure modes` slots** of
`user_context.md` — e.g. Constraints "PPC restrictions" and failure modes
"inventory stock-outs", "vendor API errors" yield
`["PPC restriction", "inventory stock-out", "vendor API errors"]`. CVR-RCA's Slack
agent runs each as a CE-scoped, ~90-day standing-context query (see
`cvr-rca/SKILL.md` → Slack guide) and writes a "Standing context — known-issue
checks" bucket. Keep each probe a short noun phrase (the recurring failure/quirk),
not a full sentence. **Omit the key entirely when both slots are empty** (a bare
run has no probes — the Slack agent then behaves exactly as today).

**Spawn the sub-skills in parallel** (one sub-agent each, single message,
multiple Agent calls). Each sub-agent prompt says: read your skill's SKILL.md at
its fixed bundle path (`$SKILL_DIR/skills/cvr-rca/SKILL.md`,
`$SKILL_DIR/skills/perf-audit/SKILL.md`) and run it exactly as written, using
`<run_dir>` as the run directory (do not create your own), for CE `<id>`, pre
`<pre>`, post `<post>`. Pass nothing else — the sub-skills own their own logic.

Wait for **all** sub-agents to finish before synthesising.

Log each spawn in `logs/_run_log.md`. If a sub-skill fails, note it and continue —
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
fails or doesn't produce the file, log it in `logs/_run_log.md` and proceed to
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

*If* a maintainer ran CVR-RCA's on-demand eval against this run, it lands as a bare
`evaluation.md` (CVR-RCA does not write one during the run itself). Namespace it
to its owner — so it reads as CVR-RCA's and never collides with the CE-level
`ce_rca_evaluation.md` a maintainer may later write on demand (see `evals/evaluator.md`)
— run the rename only if that file exists (the Step 4f organize move is `[ -f ]`-guarded
and skips cleanly when it does not):

```bash
mv "<run_dir>/evaluation.md" "<run_dir>/cvr_rca_evaluation.md"
```

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
`logs/_run_log.md`.

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
- CVR-RCA's `transcript.md` (renamed to `transcripts/transcript_cvr_rca.md` at Step 4f)
  → the **CVR-RCA** sub-tab.
- Any skill that writes `transcript_<skill>.md` auto-appears as a sub-tab (label humanized
  from the suffix) — no code change needed. `compose.py` looks in `transcripts/` first, then
  the run-dir root (older / standalone runs).
- The orchestrator's own `logs/_run_log.md` is deliberately excluded (no `transcript` name),
  so it never shows.

**4e. Report the result.** Tell the user where the composite landed and which
tabs it contains. Keep it short — the report is the deliverable, not a chat recap.
Then invite follow-ups (Step 5).

**4f. Organize the run folder (silent tidy).** A finished run leaves ~25 files in
`<run_dir>`. Tidy them so **`report.html` is the only top-level file** and everything
else lives in by-type subfolders — the deliverable is unmistakable, and the run
folder is navigable. Run this once, after compose; it is **idempotent** (only moves
what exists) and uses **paths relative to `<run_dir>`** (so it works on any machine).
Use `find` for globbed names (a bare `*.md` glob errors under zsh when nothing matches):

```bash
cd "<run_dir>"
mkdir -p transcripts tabs reports data        # logs/ already created at Step 0c
# tabs/ — the HTML fragments compose inlines
for f in summary_report.html ce_health_tab.html cvr_rca_report.html; do [ -f "$f" ] && mv "$f" tabs/; done
# reports/ — human-readable artifacts (incl. evaluations)
for f in ce_health_report.md findings.md perf_audit_report.md perf_audit_skeleton.md \
         cvr_rca_evaluation.md ce_rca_evaluation.md slack_context.md user_context.md ce_history.md; do
  [ -f "$f" ] && mv "$f" reports/; done
find . -maxdepth 1 -name 'user_data_*.md' -exec mv {} reports/ \;
# data/ — machine JSON
for f in summary.json ce_health_report.json meta.json orchestration.json; do [ -f "$f" ] && mv "$f" data/; done
find . -maxdepth 1 \( -name 'stage*.json' -o -name 'batch_*.json' -o -name '_*.json' \) -exec mv {} data/ \;
# transcripts/ — rename CVR-RCA's generic transcript to its owner name
[ -f transcript.md ] && mv transcript.md transcripts/transcript_cvr_rca.md
[ -f transcript_perf_audit.md ] && mv transcript_perf_audit.md transcripts/
```

`report.html` stays at root. `compose.py` is **layout-aware** (it resolves every input
subfolder-first, root-fallback), so the Step-5 follow-up re-compose still finds
everything, and older flat runs still compose unchanged. Do this quietly — it is
plumbing, not something to narrate.

---

## Step 5 — Follow-ups (the playground)

The report is not the end of the conversation — it's a **context-rich playground**.
After 4e, invite the analyst to ask follow-up questions **in this same session**, and
handle each one per **`references/followup_guide.md`**. Read that guide now if you
haven't; the essentials:

- **Answer in chat first, always.** Route each question: *reinterpret* (from
  `reports/findings.md`/`transcripts/transcript_cvr_rca.md`) → *re-aggregate from disk*
  (daily rows in `data/stage3.json`/`data/stage7.json`, segment/channel in
  `data/summary.json`, **TGID revenue/traffic from `data/ce_health_report.json` §6**) →
  *bounded re-query* (a small, scoped query using the bundled
  `skills/cvr-rca/references/q{2,4,5,6}.sql` patterns when the cut — per-TGID funnel,
  device, geo, URL, price — isn't on disk) → *cross-tab synthesis*. (Run-dir artifacts
  live in the by-type subfolders after Step 4f; fall back to the run-dir root for older
  runs.) Stay within the run's **fixed segment + window**.
- **Promote only on an explicit ask.** After a substantive answer, offer to add it to the
  report. On yes, append an **audited `.analysis-block` card** (question · answer ·
  how-answered tag pill · date · `↗` citations — **no SQL**) to `<run_dir>/tabs/followups.html`
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
| m038 | 2026-06-10 | **CE Health funnel → within-session basis + transient-404 resilience + deterministic PMax pill (v2.11.2).** `ce_health.py` `fetch_ce_funnel` / `fetch_tgid_funnel` now query the within-session `mixpanel_user_page_funnel_progression` (`event_date`) instead of the cross-session `mixpanel_user_funnel_progression` (`session_date`), so the CE Health funnel matches Omni + the CVR-RCA tab (CE 3593: **89,268 → 82,520 LP**; no whitelist, PMax-excluded). The funnel-CVR feeds the Shapley → §7 basis stays consistent. `scripts/render_ce_health.py` renders the **"EXCLUDES PMAX"** pill on the §5 Funnel header **deterministically** (a prior markdown note was dropped by the renderer) and removes a stale `page_type` whitelist from `_FUNNEL_SQL` (Shapley traffic input). **Transient-404 resilience:** `run_bq_query` in ce-health + perf-audit `engine/sources/bq.py` retries BigQuery `NotFound` (zero-copy CLONE tables 404 briefly mid-refresh; 4×, 10/20/30s backoff) then re-raises; `cvr-rca/scripts/run_analysis.sh` gains a `bq_q` CLI retry wrapper on its four query stages. Blast radius: ce-health engine + `render_ce_health.py` + perf-audit bq + cvr-rca run_analysis; no `compose.py` / template change. |
| m037 | 2026-06-10 | **Summary vitals wrap to 6/row — ROI to next line, no overshoot (v2.11.1).** The CVR card (v2.10.0/v2.11.0) made the Summary's vitals **7** cards, forced onto one row via an inline `grid-template-columns:repeat(7,1fr)` — which overshoots the Summary tab's narrower (`.container`-width) pane. Fix caps the row at **6 equal columns** so the 7th (ROI(1)) wraps to a second row, all cards equal width. **`references/visual_kit.md`** additive block gains `.metric-cards.summary-vitals { grid-template-columns: repeat(6, 1fr); }` (+ `max-width:800px`→3-col); two-class selector beats base `.metric-cards`, additive-only. **`references/summary_guide.md`** block #2 switches the vitals container to `class="metric-cards summary-vitals"` and **forbids an inline `grid-template-columns`** (inline would override the cap); 7 cards → 6 + ROI(1) on row 2, 6 cards (CVR absent) → one row. **Blast radius: `ce-rca` master only** (additive CSS + guide); no `compose.py`/template/sub-skill change. Verified the rule reaches the composite's injected `<style>` and no inline 7-col override remains. |
| m036 | 2026-06-10 | **Shapley CVR-basis correctness fix + CVR in vitals/card + foreground CE Health + scoped auto-update (v2.10.0).** Four fixes. **(1) Shapley CVR basis — CORRECTNESS (`ce-health-skill-main/ce_health.py`, re-vendored).** `compute_shapley_for_ce` used a **clicks** basis (`traffic = paid clicks`, `cvr = orders/clicks`) that could diverge in **sign** from the vitals/funnel CVR. Rewritten to the **funnel basis** matching `render_ce_health._facs` / §7: `traffic = funnel (LP) users`, `cvr = converted_users/users` (the funnel CVR — same metric as the new `vitals.cvr`), plus `orders_per_converter = orders/converted_users` when funnel converter counts are present, with `aov`/`cr`/`tr` from vitals — toward §7's 6-factor identity `revenue = traffic × cvr × orders_per_converter × aov × completion × take_rate`. `calc_shapley_decomposition` (the engine) is unchanged; only the factor dicts changed. **Invariant guaranteed + verified on CE 252/month:** the multiplicative Shapley CVR factor's sign now equals `sign(post_cvr − pre_cvr)` — funnel CVR rose 4.08%→4.52%, and the CVR factor flipped from the old **−$2.3K** to **+$10.0K** (total $16,966.74 unchanged). The §7 engine table now reads on the funnel basis (Traffic = Users, new Orders/User factor). **(2) CVR into vitals + a CVR card (engine + `scripts/render_ce_health.py`).** `fetch_ce_funnel` now emits `cvr` (orders/users ×100); each window's `vitals` dict carries `cvr` in the sidecar (`vitals.current.cvr` etc.). `render_ce_health` §2 adds a **CVR metric card** among the rate cards (Revenue · Orders · **CVR** · AOV · Take Rate · Completion · ROI(1)) using `card()` + `pp_delta`; grid widens to 7. None-safe for old sidecars. **(3) Foreground CE Health (`SKILL.md` Step 0d + 2).** Step 0d is now a **single foreground run** (no background/two-phase/poll/PREVIEW_READY/bounded-fallback; `--preview-marker` dropped from the orchestrator call — the engine flag stays defined but dormant). Step 2's "wait for FULL_READY" gate removed — the report is already complete on disk. **(4) Scoped auto-update (`SKILL.md`).** `SKILL_DIR` is set to the absolute dir THIS SKILL.md was read from; the version check + in-place update **only run when `SKILL_DIR == ~/.ce-rca`** (canonical install). Any other location (dev/local copy) **skips the check and proceeds** — no false "stale" alarm, no denied-curl dead-end. **Blast radius:** `ce-health` engine (re-vendored) + `render_ce_health.py` §2 + `SKILL.md` Step 0/1/2 + version block + changelog. No `compose.py` / template / CVR-RCA / perf-audit change; the full CE Health `.md` is unchanged **except §7** (now funnel-basis Shapley). |
| m035 | 2026-06-10 | **Summary vitals cards mirror CE Health §2 (order + formatting) (v2.9.1).** The Summary tab's vitals cards picked their own order/labels/decimals (ROI shown 3rd as `159.7%`, AOV `$334.59`, label "CR") — inconsistent with the CE Health §2 cards. `references/summary_guide.md` block #2 now prescribes the **exact CE Health card order** (Revenue · Orders · AOV · Take Rate · Completion · ROI(1)), **verbatim labels** ("Completion", "ROI(1)"), and **matching decimals** (Revenue `money()` `$286.5K`; Orders comma-int; AOV `$`+0-dp; Take Rate/Completion 1-dp; ROI(1) 0-dp) — sourced from CE Health's vitals so values are identical too. **Blast radius: `summary_guide.md` only** (authoring spec; no code/template/sub-skill change). Verified on CE 3593: Summary vitals order, labels, decimals, and values match the CE Health §2 cards exactly. |
| m034 | 2026-06-10 | **CE-RCA latency — parallelize CE Health + preview-first two-phase + batched Step-0 bash (v2.9.0).** Cuts the time-to-preview without changing a single output byte. **(1) Engine parallelization (`ce-health-skill-main/ce_health.py` `run_ce_health`, re-vendored via `scripts/vendor.sh`).** The ~30 independent BigQuery fetches (vitals ×4, channels ×4, funnel ×4, trajectory + monthly-CVR, TGIDs/funnel/lead-time, vendors, funnel-by-dim, lead-time cohorts, LP funnel, customer countries, metadata) now run concurrently in a `concurrent.futures.ThreadPoolExecutor(max_workers=8)` — the bq client is a thread-safe module singleton. Each future's result is assigned back into the **exact** local variable the sequential code used; render order, query SQL, fetch args, and the one-shot `.md`/`.json` assembly are **untouched**. Pure-compute steps (`compute_shapley_for_ce`, `find_historical_context`) run after their inputs resolve; a fetch error re-raises at `.result()` exactly as before. **Measured 73s → ~11s (~6.6×) on CE 252 / month.** **(2) Two-phase preview (new `--preview-marker` CLI flag, default OFF).** When set, the engine resolves the **preview set** (metadata, vitals ×4, channels ×4, funnel ×4 → Shapley) first, **atomically** writes the JSON sidecar (temp + `os.replace`) with exactly today's preview keys (`ce_id, ce_name, range, generated_at, windows, metadata, vitals, shapley`), prints **`PREVIEW_READY`**, then finishes the rest, **rewrites the complete `.md` + `.json`** identically to the one-shot path (adding `history_months`/`has_ly`), and prints **`FULL_READY`**. Flag OFF = today exactly: single final write, no markers, no early sidecar — standalone CE Health unchanged. **(3) Orchestrator (`SKILL.md`).** Step 0d now launches CE Health **in the background** with `--preview-marker`, polls for `PREVIEW_READY` / the early sidecar, and proceeds to the Step-1 preview while CE Health keeps running (bounded ~90s fallback to foreground so it never hangs). A new gate **before Step 2 dispatch** waits for `FULL_READY` so CVR-RCA / perf-audit always read the complete `ce_health_report.md` lens. Step 0c collapses the independent pre-CE-Health plumbing (run-dir/`mkdir -p logs`/run-log seed) into a **single** bash call; 0b (window confirm) stays the blocking pause, 0e (`ce_history`) stays fire-and-forget. **Hard invariant verified:** final `.md` + `.json` are **byte-identical** before vs after (plain) vs after (`--preview-marker`) on CE 252/month (`diff` clean on all three); `PREVIEW_READY` prints before `FULL_READY`; the at-`PREVIEW_READY` sidecar carries `vitals`+`shapley`+`windows`+`metadata` (no full-pass keys). **Blast radius:** `ce-health` engine (re-vendored) + `SKILL.md` Step 0/2 + changelog. No `render_ce_health.py` / `compose.py` / template / CVR-RCA / perf-audit / query-SQL / sidecar-schema change. |
| m033 | 2026-06-10 | **CE Health — Driver Diagnosis + Funnel default-open, and the real fix for the waterfall not spanning the card (v2.8.1).** Two changes in `scripts/render_ce_health.py`. **(1)** `CEH_DEFAULT_OPEN` gains `cehealth-shapley` + `cehealth-funnel` (now `{vitals, l12m, shapley, funnel}`) — so they're expanded on tab open. **(2) Root-cause fix for the waterfall rendering at ~700px with whitespace:** the Plotly waterfall is drawn at load while inside a hidden tab **and** a collapsed `.ceh-body`, so `autosize` falls back to its ~700px default and bakes it in; the collapse toggle (`setOpen`) flipped the section visible but **never told Plotly to resize**, so it stayed stuck. `setOpen` now, on expand, resizes every `.js-plotly-plot` inside the block (`Plotly.Plots.resize`, `setTimeout(…,30)` so the display change applies first, try/caught, `window.Plotly`-guarded). Combined with the tab-activate resize (template) and the two sections now default-open, the waterfall spans full width on first view, and **any** chart in a later-expanded section self-heals. **Blast radius:** `render_ce_health.py` only. Verified on a flat run (ce-243): shapley + funnel render open, channels/TGIDs stay collapsed, `chart-cehealth-shapley` carries `width:100%`, resize-on-expand present. **Noted (not fixed here):** `render_ce_health.py` reads its inputs (`ce_health_report.json/.md`) from the run-dir **root**, so re-rendering a v2.4.0 **organized** run (inputs under `data/`+`reports/`) raises `FileNotFoundError` — harmless in the live flow (render runs at Step 4c *before* the Organize step 4f), but a re-render/idempotency gap worth a follow-up (reuse `compose.py`'s `resolve()`/`_SUBDIR`). |
| m032 | 2026-06-10 | **Hardening — chart-render confirmation + Summary text + render_ce_health de-rigidifying (v2.8.0).** Presentation/robustness only; no engine change. **(1) Chart render in hidden tabs (#3 + #4) — confirmed already fixed.** The composite's `templates/report.html` `activateTab()` already resizes every `.js-plotly-plot` in a pane after it becomes visible (`Plotly.Plots.resize`, idempotent, try/caught), driven on button-click, cross-tab `↗` anchor routing, and the load-time hash handler — so the CE Health waterfall renders full-width and the CVR-RCA 90-day annotations position on first open of each tab. No separate load-time `#tab-cehealth` handler exists; **no template change needed**. **(2) Summary text (`references/summary_guide.md`).** §3 block renamed **"Long-term context — is the move real?" → "Short-term vs long-term context"** (dropped the "is the move real?" framing in the heading + flow table; pre→post Δ + YoY Δ content kept). §4 headline callout now instructs a **plain heading** (just `The Story`, or a one-line factual headline like "Revenue −28%, traffic-led") — removed the clever `<h2>The Story — <metaphor>` instruction + example; What-moved / Why / Action `callout-item`s kept. Hardcoded **"flagship TGID 3909"** in all 5 examples → `<top-TGID>` placeholder. **(3) De-rigidified `scripts/render_ce_health.py`** (all graceful fallbacks preserved). **Column indices → name lookups via the existing `_col_idx`:** `build_funnel_cards` current/prior windows now located by header (first two value cols, skipping Stage/Δ/LY/prior) instead of `cur_i,pri_i=1,2`; L12M parsing + L12M hover metadata now build header→index maps (Month/Revenue/Orders/ROI/TR/CR/AOV for the health table; Month/Clicks/CVR/Paid-ROI for the paid table) instead of fixed `r[1..6]` — an absent column omits that series/hover-field rather than crashing. **Channel rules (`channel_flags_and_summary`):** cross-sell leakage = sum of **every** channel whose name ends in "Cross-sell" (was Google+Bing only); **highest-share channel** treated as primary (flag "primary is X, not search-led" only when no search channel is top) instead of hardcoding "Google Search"; known-channel benchmark dict kept, unmapped channels degrade silently; channel-name + Share columns located via `_col_idx`. **Lead-time (`leadtime_summary`):** band column located via `_col_idx` (was position 0); `_tgid_groups` already routes unmatched columns into a blank band — preserved. **Magic thresholds → documented module constants:** `TGID_CONCENTRATION_PCT` (80%), `TGID_LOW_S2O_PCT` (8%), `NEAR_FLAT_PP`/`NEAR_FLAT_PCT` (1pp / 5%), each commented as tunable. **Blast radius:** `references/summary_guide.md` + `scripts/render_ce_health.py` (template unchanged). **Verified** on ce-3593 + ce-243 → `report_v2.html`: `ast.parse` OK; template carries the per-pane resize once in `activateTab`; waterfall + CVR 90-day annotations markup intact; guide §3 = "Short-term vs long-term context", §4 plain `<h2>The Story</h2>`, no "3909"; zero residual literal indices (`=1,2`, `r[1..6]`) in the touched functions; channel rules confirmed — ce-3593 top-share Google Search treated as primary, ce-243 Google+Bing Cross-sell summed to 12% → leakage flag fires; both reports render with charts + anchors unchanged. **Deferred:** persistent CE-context store; perf-audit consuming `user_context.md` (carried from m031). |
| m031 | 2026-06-09 | **Wave C — CE context capture → structured Historical Context (per-run) (v2.7.0).** Refines *what* CE context we capture at the Step 1 pause and *how §8 presents it* — additive + backward-compatible (a bare-"continue" run is byte-identical to before). **(1) Step 1 prompt inlined.** The optional-input prompt is now written **verbatim into SKILL.md** (MMP doc · hunch · known events · constraints · known failure modes · where-to-look) and `references/input_guide.md` is **deleted** (the pointer is gone). **(2) 8-slot `user_context.md`.** The template expands to **About this CE · Focus / direction · Hypothesis priors · Known events · Constraints · Known failure modes · Important links · Sources** (only write slots with content). Step 2 derives a **`slack_probes`** array from the **Constraints + Known failure modes** slots and writes it into `orchestration.json` (alongside `user_slack_channels`; omitted when empty). **(3) MMP-doc extraction enriched.** `references/context_ingest_guide.md`'s `<<<USER_CONTEXT>>>` return contract now yields **About-this-CE overview + Hypothesis priors + Constraints + Known failure modes + Important links** from a doc (was priors/events only); the `<<<USER_DATA_LENS>>>` Sheets path is unchanged. **(4) CVR-RCA Slack agent — probe-driven standing-context search (the one cross-skill touch).** `slack_context_guide.md` (edited in the **canonical CVR source**, re-vendored via `scripts/vendor.sh`) reads `slack_probes` from `orchestration.json` and, for each, runs a CE-scoped `"{ce_name}" AND <probe>` query over a **~90-day lookback from `post_end`** (reads user-pasted thread links directly), writing a new **"Standing context — known-issue checks"** bucket (each probe: found+links / none). **Backward-compatible:** no `slack_probes` → probe search skipped, the existing 3 window-tied searches unchanged. **(5) Structured §8.** `scripts/render_ce_health.py`'s `user_context_subsection` now **splits `user_context.md` by its `##` slot headings** and renders each as its own labelled sub-block inside the `cehealth-history` block (order: About this CE · Constraints · Known failure modes · Analyst priors & focus · Known events · Important links) — **Constraints** as warning chips/callout, **Important links** as a small `link · what-it-gives` `<table>`. Keeps the Slack-signals embed (now incl. the standing-context bucket) + `ce_history_block` / `prior_runs_block`. Graceful: missing slots omitted; a file with no recognizable slots falls back to the verbatim embed; bare-continue → §8 byte-identical. **Blast radius:** `ce-rca` (SKILL.md, `context_ingest_guide.md`, `render_ce_health.py`) + **one CVR-RCA sub-skill touch** (`slack_context_guide.md`, re-vendored). No `compose.py` / template / CE-Health-engine / perf-audit change; CE Health anchor ids unchanged. Verified: rich 8-slot fixture renders structured sub-blocks (chips + links table + standing-context bucket), bare-continue §8 byte-identical, probe-derivation maps Constraints+Failure-modes → non-empty / empty → none, vendor.sh mirrored the slack guide. **Deferred:** persistent (cross-run) CE context store; perf-audit consuming `user_context.md` (owner hand-off). |
| m030 | 2026-06-09 | **CE Health Wave B — engine data layer (v2.6.0).** Adds the data CE Health couldn't show before, across `ce-health-skill-main` (re-vendored via `scripts/vendor.sh`) + `scripts/render_ce_health.py`. **(1) Multi-year trajectory:** monthly lookback 13→36 months + new `fetch_monthly_cvr` (CVR-RCA's CVR) → Revenue Trajectory gains a Predicted-Revenue × CVR YoY pivot; engine emits `history_months`/`has_ly`. **(2) Vendor Breakdown (new display §7):** `fetch_vendor_breakdown` from `fct_orders` (Omni measures — revenue=`amount_revenue_usd`, TR=rev/completed-gross, CR=completed/gross), vendor attributed to each order's **primary booking** (`fct_bookings_v2.vendor_id`, lowest `booking_id` — avoids fan-out) + `dim_vendors.fulfilment_type`; renderer block bumps Lead-time/Historical/Countries to 8/9/10. **(3) Funnel by dimension:** §5 gains a "Break funnel down by" dropdown — Landing page (existing) + new Channel + Language cuts (`_fetch_funnel_by_dim` on `mixpanel_user_page_funnel_progression`, per-user MAX-flag dedup). **(4) TGID corrections:** all deltas now **MoM (pre/post)**, not YoY (fixes the unlabeled "+142%") — added prior-window aggregates to `fetch_top_tgids` (`gbv_pri`/`completed_gbv_pri`→`aov_pri`/`tr_pri`/`cr_pri`) + `fetch_tgid_funnel` (prior window + true `s2o`); **RPC redefined to S2O×AOV×TR** (interim per-select-view); experience names emitted **untruncated** (renderer ellipsis+hover); **Predicted/Actual Revenue** labels on the §1 note + §7. **(5) Renderer hardening:** `section()` header match made single-line (`[^\n]*`) so same-prefix sections ("Funnel" vs "Funnel by Language") don't collide. **Blast radius:** ce-health engine (re-vendored) + `render_ce_health.py`; no compose/template/other-sub-skill change. Verified end-to-end on CE 243 + CE 3593 via the **vendored** engine. **Deferred:** exact RPC, funnel platform/page-type cuts, historical-context memory (Wave C). |
| m029 | 2026-06-09 | **CE Health tab — Driver Diagnosis promoted to position 3 + Shapley waterfall un-truncated (v2.5.4).** Two presentation tweaks in `scripts/render_ce_health.py`. **(1) Reorder:** the §ordered list moves **Driver Diagnosis (Shapley)** to **right after Revenue Trajectory** — new display order **1 CE Vitals · 2 Revenue Trajectory · 3 Driver Diagnosis · 4 Channel Breakdown · 5 Funnel · 6 Top TGIDs · 7 Lead Time Cohorts · 8 Historical Context · 9 Customer Countries** (block titles renumbered to match; **anchor `bid`s unchanged**, so cross-tab `↗` links still resolve). **(2) Waterfall fix:** the Plotly revenue waterfall was clipping on the right (last bar's `$` label + the long "Post (dates)" x-tick). The first/last x-ticks are shortened to **Pre / Post** (the full dates remain in the chart subtitle), and the layout widens to `margin r:80, b:104, height:440, autosize:true`. **Blast radius: `render_ce_health.py` only** — no compose/template/sub-skill/engine change. Verified on ce-243 + ce-3593: titles read 1..9 in the new order, 9 `cehealth-*` anchors unchanged, waterfall renders Pre/Post ticks with the wider margins. |
| m028 | 2026-06-09 | **CE Health tab — reverted the non-functional TGID metric selector (v2.5.3).** Reverted **only** the v2.5.2 part-(C) TGID metric selector from `scripts/render_ce_health.py` — it rendered the column checkboxes **unchecked** and the show/hide toggle **did not work**, so it's removed and **parked for a later wave**; **all other CE Health table changes are retained**. **Removed:** the `_tgid_metric_selector` function (the `.ceh-msel` checkbox bar above the TGID main table, its scoped CSS, and its toggle `<script>`) and its wiring in `build_tgid_main` (the `col_data`/`metric_cols` slug loop + the `selector` in the return). The supporting `styled_table` additions were also removed **cleanly** rather than left inert, since nothing else used them: the `table_id` + `col_data` params, the `_dcol` helper, the `#ceh-tgid-main` id, and the `data-col="<slug>"` stamping on `<th>`/`<td>`. **No inert leftovers.** **Retained unchanged:** section titles 1..9 in display order (Vitals="1."), the derived **S2O = S2C × C2O** colour-scaled column inside Funnel Metrics, the **CR<80% red** highlight (`td.ceh-cr-low`), blue group dividers (`ceh-gdiv`), grouped header bands (`ceh-group`), sticky/frozen identity columns, landing-URL ellipsis + hover (`ceh-lpurl`), collapsible sections, all Plotly charts. **Verified** on ce-243 + ce-3593 → `report_v2.html`: `ast.parse` OK; **zero `ceh-msel` / `_tgid_metric_selector` / `ceh-tgid-main` / `data-col` / `Columns` residue** in the rendered tab; S2O colour-scaled column, CR<80% red, blue dividers (37), grouped headers (5), sticky columns (44) all present; titles read 1..9 with Vitals="1."; landing-URL `title=` present; collapse JS (`ceh-toggle`) + 3 Plotly plots intact; other tabs unaffected (selector-related diff vs prior reports = 0 lines). **Blast radius: `scripts/render_ce_health.py` only.** |
| m027 | 2026-06-09 | **CE Health tab — four presentation refinements (v2.5.2).** Presentation-only polish on `scripts/render_ce_health.py` — **no `compose.py` / template / shared `visual_kit` / sub-skill / engine change**. **(A) Section titles renumbered to display order.** The page was reordered in Wave A but `block()` titles still carried CE Health's original section numbers. The visible leading "N." in each title is now sequential **1..9 in `build_fragment`'s actual return order**, CE Vitals = "1.": Vitals 2→1, Revenue Trajectory (L12M) (was unnumbered)→2, Channels 3→3, Funnel 4→4, Top TGIDs 6→5, Lead Time Cohorts 9→6, Historical 8→7, Driver Diagnosis (Shapley) 7→8, Customer Countries 11→9. **Anchor `bid`s are unchanged** (`cehealth-vitals`/`-l12m`/`-channels`/`-funnel`/`-tgids`/`-leadtime`/`-history`/`-shapley`/`-countries`) so cross-tab `↗` links keep working — only the human-readable number changes. **(B) Derived S2O column in the TGID main table.** S2O is not in source data; it's derived **S2O = S2C × C2O** per row (new `_lead_rate` parses the leading rate, ignoring the trailing delta), inserted right after C2O so it lands in the **Funnel Metrics** group, and given the **same green→amber→red colour scale** as S2C/C2O (`_scale_bg`). Note added that S2O is presentation-derived (S2C×C2O), pending an exact engine figure (Wave B). The existing **CR<80% red** highlight (`td.ceh-cr-low`) and high-traffic-low-S2O flag still fire. **(C) TGID metric-selector toggle** (the deferred "optional"): a compact `.ceh-msel` checkbox bar above the main table, one checkbox per non-identity metric column (TGID/Experience frozen, excluded), **all checked by default**. `styled_table` gained `table_id` + `col_data` params; the main table is `#ceh-tgid-main` and every metric `<th>`/`<td>` carries `data-col="<slug>"`. A small `<script>` scoped to that table flips `display` on the matching `data-col` cells — does not touch the collapse JS, sticky columns, grouped header bands, or blue dividers. **(D) Landing-page URL ellipsis + hover.** URL cell in the (Funnel-folded) Landing Pages table wrapped in `<span class="ceh-lpurl" title="<full url>">…</span>` with scoped `max-width`/`overflow:hidden`/`text-overflow:ellipsis`/`white-space:nowrap` — source URLs are full (unlike experience names) so the hover recovers the whole URL. **Not attempted:** experience-name full-text-on-hover — the name is truncated in source `ce_health_report.md` (literal "…"), unrecoverable by the renderer; left as-is for an engine/Wave B fix. **Verified** on ce-243 + ce-3593: ast.parse OK; titles read 1..9 in display order with Vitals="1."; anchor-id set byte-identical to before (9 ids); S2O column inside Funnel Metrics band (band span 5→6) with colour-scale backgrounds on all rows; CR<80% red rule present; metric selector renders all-checked above the table and the toggle JS passes `node --check`; landing-URL cells carry `title=`; collapse/sticky/blue-dividers/grouped-headers intact; 5 Plotly plots present; non-CE-Health source artifacts byte-identical. **Blast radius: `scripts/render_ce_health.py` only.** |
| m026 | 2026-06-09 | **CE Health tab — seven presentation refinements (v2.5.1).** Targeted polish on `scripts/render_ce_health.py` only — **no `compose.py` / template / shared `visual_kit` / sub-skill / engine change**. **(1) Primary driver from the §7 Shapley, not the largest vitals Δ.** The old `vitals_primary_mover` picked the vitals row with the largest \|Δ vs Prior\|, which mislabelled **Revenue** as the mover. The 6-factor Shapley `contrib` is now computed **once** near the top of `build_fragment` (via `query_raw`, reused by `build_shapley_block` — no double-query); the top driver is the factor with the largest \|contribution\| (`shapley_top_driver`). A **"Primary driver (Shapley): {label} ({±$})"** note renders under the 4-window vitals table; if the factor maps to a vitals row (AOV/Take Rate/Completion/Orders via `shapley_top_vitals_row`) that row is also bolded with a "primary driver" pill — Traffic/CVR have no vitals row so they render note-only, and **Revenue is never auto-bolded** (not a Shapley factor). On Query-1 failure: no note (no fallback to the largest-Δ guess), §7 verbatim table intact. **(2) Collapsible headers read as real section headers** — `CEH_COLLAPSE_STYLE` `.ceh-toggle` gets a 16px/700 `.block-title`, 16px chevron, vertical padding, subtle hover background, light bottom divider (scoped to `#tab-cehealth`; toggle JS unchanged). **(3) Cryptic "step down" funnel flag** replaced with **"↓ X.Xpp vs prior"**, firing only when a rate stage is materially below prior (>1pp). **(4) Funnel cards** relabelled `LP→Select`/`Select→Cart`/`Cart→Order` → **LP2S / S2C / C2O** (LP Users volume card kept). **(5) TGID Experience column** truncates with ellipsis but exposes the full name on hover via `<span class="ceh-exp" title="…">` + scoped `max-width`/`overflow`/`text-overflow` CSS. **(6) "new"/"—" cell clutter** cleaned in `_cell_split`: trailing lone em-dash ("no prior") → dropped (bare value); trailing `new` → value + a small muted `.ceh-new` badge — normal `±x%`/`pp` deltas still split into the two-line coloured cell, §3 Channels unaffected. **(7) Window-agnostic delta label** — one `period_label` derived once in `build_fragment` from the sidecar's `range` (`"month"` → "MoM", else **"vs prior"**), substituted into the vitals cards, funnel cards (`build_funnel_cards(..., period_label)`), and the vitals note; the hardcoded literal "MoM" is gone from rendered output (columns/Shapley/4-window table stay date-driven). **Verified** on ce-243 + ce-3593 (both `range: custom`): ast.parse OK; Shapley primary-driver note present (ce-243 → "Orders / User +$56.6K" bolds the Orders row; ce-3593 → "Traffic −$131.3K" note-only); Revenue never auto-bolded; headers larger/clickable; no "step down" literal; LP2S/S2C/C2O cards; `title=` on experience cells; 0 `"K new"`/`"% —"` literals (new=badge, —=dropped); **rendered deltas read "vs prior", no "MoM" on either custom-window run**; Plotly intact (3 charts); CE-health fragment embedded verbatim, other tabs unaffected by construction. **Blast radius: `scripts/render_ce_health.py` only.** |
| m025 | 2026-06-09 | **CE Health revamp — Wave A (presentation-only) (v2.5.0).** Reorganised the CE Health tab around how a BGM reads a CE's contours, entirely in `scripts/render_ce_health.py` (+ fragment-scoped CSS/JS) — **no engine / new query / `compose.py` / template / sub-skill change**. **(1) Collapsible sections** via a central `block(title, bid, inner, verdict=None, summary=None, collapsed=False)`: each title is a `<button class="ceh-toggle">` (not an `<a>`, so the template's anchor router never eats the click) with a chevron, `inner` wrapped in `.ceh-body`, and an optional `.ceh-summary` rendered **between header and body** so it stays visible while collapsed. Fragment-scoped `<style>` (`.ceh-collapsed .ceh-body{display:none}`, chevron rotate) + `<script>` scoped to `#tab-cehealth` toggles on header click **and auto-expands a block when targeted** — a doc-level listener on `a[href^="#cehealth-"]` clicks plus an initial/`hashchange` `location.hash` check (the router `preventDefault()`s cross-tab links, so `:target` CSS alone won't fire). **Default open: Vitals + Revenue-trajectory; everything else collapsed** — set centrally in `CEH_DEFAULT_OPEN`. **(2) Page reorder:** Vitals → Revenue trajectory → Channels → Funnel (Landing Pages folded in) → TGID (+ separate TGID×Lead-time table) → Lead-time cohorts → Historical → Driver diagnosis → Customer countries. **(3) Vitals** cards reordered Revenue·Orders·AOV·Take Rate·Completion·ROI; the 4-window table bolds the largest-magnitude MoM mover with a "primary mover" marker. **(4) Revenue trajectory** moved up; the L12M revenue chart's Plotly `hovertemplate` now shows Revenue·Orders·ROI·TR·CR·AOV on hover. **(5) Channels:** Revenue + Share moved left, rule-based benchmark flag chips on Share (Google Search top/~50%, PMax/Bing ~10%, Organic ~5%, Google+Bing cross-sell >10% leakage) and a deterministic 2–3 line `summary` shown while collapsed. **(6) Funnel:** 4 KPI cards (LP→Select·Select→Cart·Cart→Order·LP Users, MoM Δ) over the 4-window YoY table, the §10 Landing Pages table folded in, and a "step down" flag on the worst rate stage. **(7) TGID:** single main table keeps the Order/Funnel groups with **blue vertical dividers**, RPC moved into the Funnel group, lead-time buckets split into a **separate TGID×Lead-time table**, rows sorted desc by Share with **~80%-cumulative concentration highlighted green**, a CE classification pill (Concentrated/Normal/Fragmented), CR<80% red + S2C/C2O colour scale, and a derived **S2O = S2C×C2O** high-traffic-low-S2O flag (presentation approximation, exact engine value deferred). **(8) Lead-time** cohorts table kept by the TGID block with a rule-based dominant-band callout shown collapsed. Preserved verbatim: §7 Shapley + Query-1 path and its fallback, §5 charts, `styled_table`'s m018 `split_deltas` + `groups`. **Verified** on ce-243 (growth/leakage) and ce-3593 (decline) — composed reports show collapsible sections, correct default-open set, correct order, blue dividers, separate lead-time table, folded Landing Pages, funnel KPI cards, channel/lead-time summaries, no leftover raw `$X -Y%` literals, all charts intact, and **non-CE-Health tabs byte-identical** (apples-to-apples compose). **Deferred (Waves B/C):** multi-year YoY, funnel by-dimension, vendor breakdown, exact S2O/RPC, the "+142%" fix, historical-context memory subsystem. **Blast radius: `ce-rca` CE-Health renderer only.** |
| m024 | 2026-06-09 | **Structured run folder — `report.html` at top, everything else in by-type subfolders (v2.4.0).** A finished run dumped ~25 files flat into `<run_dir>`, burying the deliverable. New **Step 4f (Organize)** — a silent, idempotent, run-dir-relative tidy the orchestrator runs after compose — leaves **`report.html` as the only top-level file** and groups the rest: `transcripts/` (CVR-RCA's `transcript.md` **renamed `transcript_cvr_rca.md`**, `transcript_perf_audit.md`), `tabs/` (the HTML fragments compose inlines), `reports/` (`ce_health_report.md`, `findings.md`, `perf_audit_report.md`, `*_evaluation.md`, `slack_context.md`, …), `data/` (`summary.json`, `stage*.json`, `ce_health_report.json`, `meta.json`, `orchestration.json`), `logs/` (`_run_log.md`, now written there from Step 0c so the actively-appended log never moves). `compose.py` is made **layout-aware** — a new `resolve()` + `_SUBDIR` map resolve every input **subfolder-first, root-fallback** (TAB_SPECS sources, `meta.json`, and `collect_transcripts()` which now globs `transcripts/` and maps `transcript_cvr_rca.md → "CVR-RCA"`, keeping `transcript.md` for back-compat) — so the Step-5 follow-up re-compose finds everything and **older flat / standalone runs still compose byte-identically** (verified A/B: flat vs organized compose produce identical `report.html`). `followup_guide.md` + `composition_rules.md` updated to the subfolder paths (Follow-ups card now appended to `tabs/followups.html`). **Blast radius: `ce-rca` master only** — no sub-skill edit (CVR-RCA / perf-audit / CE-Health standalone output unchanged; their flat files are reorganized only inside a CE-RCA run), no `templates/`/CSS change. Ships in versioned skill files (relative paths, no machine config), so every install gets the identical structure on every run. |
| m023 | 2026-06-09 | **CE-RCA-level evaluator — maintainer on-demand tool (v2.3.0).** A way to score the *whole* orchestrated RCA (not just each sub-skill's own investigation, which already self-evaluates). New rubric **`evals/evaluator.md`** — 7 orchestration-level themes × 1–5 → **/35** (Direction & Dispatch · Cross-Tab Synthesis & Corroboration · CE-Level Diagnostic Correctness · Coverage · Actionability & Ownership · Report Integrity & Navigability · Evidence Integrity) with the CVR-style failure-mode tags (`MISSING_INSTRUCTION`/`AMBIGUOUS_INSTRUCTION`/`EXEC_ERROR`/`DATA_LIMIT`) grounded in CE-RCA file citations. **Deliberately NOT wired into the GM run flow** — it is a quality-tracking tool for *maintainers*, run **on demand** against any finished run-dir by a dedicated sub-agent (it reads only on-disk artifacts, so it needs no live context); writes **`<run_dir>/ce_rca_evaluation.md`**, never a tab, never shown to the GM. Keeping it off the auto path avoids spending ~150K tokens + minutes on every GM run for a record the GM never sees. Invocation + rubric are self-contained in `evals/evaluator.md`. **Naming hygiene:** CVR-RCA's bare `evaluation.md` is renamed at Step 4b → **`cvr_rca_evaluation.md`** (orchestrator `mv`, mirroring `report.html → cvr_rca_report.html`) so each eval reads as its owner's and the CE-level eval never collides. **Blast radius: `ce-rca` master only** — no `compose.py` / `templates/` / sub-skill change; Follow-ups stays Step 5. |
| m022 | 2026-06-08 | **Follow-ups delta colouring made automatic (v2.2.3).** v2.1.1 relied on Claude hand-classing each delta cell in Follow-ups tables — fragile: a real run coloured the first table but left a later `−0.14pp` table plain (the "near-flat → plain" nuance made it look broken). Now deterministic: new **`helpers.py:autocolor_delta_cells()`** colours any `<td>` whose value starts with a sign (`−3.13pp`→red, `+0.6pp`→green, `+$111.3K`, `(−$708.8K)`); plain counts/levels/`—` stay neutral; **author-set `.neg`/`.pos`/`.delta-flat` is never overridden** (semantic loss columns like a positive "lost checkouts" count stay author-red). `compose.py` applies it to the **Follow-ups `html-fragment` only** (`spec["id"]=="followups"`). `followup_guide.md` relaxed: don't hand-class signed deltas (composer does it, consistently), only hand-class semantic exceptions; the brittle near-flat threshold removed. **Blast radius: `ce-rca` master only** — no template / shared CSS / sub-skill change (uses shared `.neg`/`.pos`). Verified: 12-case unit test + integration compose (both tables coloured incl. the previously-plain `−0.14pp`, loss cols author-red, counts/levels neutral, no double-class, idempotent). |
| m021 | 2026-06-08 | **Colour-coded deltas across all CE Health tables + §8 prompt removed (v2.1.2).** Extends the v1.8.2 delta-colouring (which only covered §3 Channel Breakdown + §6 Top TGIDs) to **every** CE Health table: `split_deltas=True` now also applies to **§2 Full 4-window comparison, §4 Funnel, §9 Lead Time Cohorts, §10 Landing Pages, §11 Customer Countries** and the §7 verbatim-fallback table — so all `Δ (MOM / YoY / LY)` and `pp` columns render green (up) / red (down) / amber (near-flat) consistently. **Bug fix in `_cell_split`:** a lone-delta cell with a trailing parenthetical (e.g. `+31% (+$32.1K)`) dropped the parenthetical when coloured; it now colours the whole token, preserving the figure. **§8 fix:** CE Health's interactive `> **Add your context:** …` CLI prompt was leaking into the rendered §8 — `_clean_history_md` now drops it (with the existing "None found" placeholders) and runs **unconditionally** (Slack/user context is surfaced below via the user-context subsection). **Blast radius: `scripts/render_ce_health.py` only** — the scoped `#tab-cehealth .ceh-chg` CSS already existed (v1.8.2); no `compose.py`/template/shared-`visual_kit.md`/sub-skill change; non-delta cells degrade plainly. Verified on CE 243 + CE 3593. |
| m020 | 2026-06-08 | **Colour-coded delta cells in Follow-ups tables (v2.1.1).** Follow-up answer tables rendered delta / lost-checkout columns in plain black, unlike the CE Health tables. `followup_guide.md`'s entry-card table template + a new rule now instruct Claude to colour every directional cell when authoring a Follow-ups card: **`.neg`** (red) for declines/losses (negative Δ, "lost checkouts", drops), **`.pos`** (green) for gains, plain text for near-flat, plus **`.num`** for right-aligned numerics. The sign convention follows business-outcome direction (more lost checkouts / falling rate = red). **No code change** — `.neg`/`.pos`/`.num` already live unscoped in `visual_kit.md`, so they render in the Follow-ups `.md-table` exactly as in the CE Health tab (verified: classes + red/green CSS reach the composite). Guide-only; no `compose.py`/template/sub-skill change. |
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
