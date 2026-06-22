# Context Intake Guide — standalone onboarding questionnaire

The reusable onboarding questionnaire that captures the analyst's context **before**
a skill reads the numbers, and writes it to `<run_dir>/user_context.md` (the shared
8-slot contract every sub-skill already consumes). This is the same questionnaire the
umbrella `/ce-rca` runs at its Step 1 — factored out here so each sub-skill can run it
**when invoked standalone**.

> **Single source of truth.** The umbrella `/ce-rca` SKILL.md §1a–1e is the canonical
> long-form of this flow; this guide is the portable version a standalone sub-skill
> includes. Keep the two aligned — edit the contract here.

---

## When to run it (the standalone gate — READ FIRST)

Run this intake **only on a standalone run**. Detect orchestration and **skip entirely**
if any of these hold (the umbrella already captured context once and wrote
`user_context.md` — never double-ask):

- `<run_dir>/orchestration.json` exists, OR
- the `CE_CONTEXT_RUN_DIR` environment variable is set, OR
- `<run_dir>/user_context.md` already exists (a caller provided it).

Otherwise you are standalone → run the intake below, then continue the skill. The
intake writes `<run_dir>/user_context.md`; the skill's existing consumption picks it up
unchanged.

**Per-skill emphasis.** Every skill runs the *same* flow, but leads the buckets it
actually consumes (the caller passes an `emphasis`):
- `ce-context` → **full** (it is the orientation skill): all four buckets + catch-all + aliases.
- `cvr-rca` → funnel / landing-page / pricing / mix priors + known events (priors drive hypothesis planning).
- `perf-audit` → PPC / budget / campaign constraints (off-the-table levers) + known events.
- `ce-health` → light: About-this-CE + known events + constraints.

---

## The flow

CE Health (or the skill's own first query) can compute in the background while you ask —
the wait is free. **Strict order: 0b goal → 1a ask → (wait) → 1b ingest → 1c buckets →
1d aliases → [skill computes] → 1e hypothesis (after the first data view).**

### 0b — Confirm the goal (one `AskUserQuestion`)
Capture intent — *understand growth · diagnose a decline · general health check ·
investigate a metric · something else*. The goal sets the questionnaire depth (below)
and lands in `## Goal`.

### 1a — Solicit the analyst's context (the input ask)
Ask in chat (paste/dump-shaped, not multiple-choice) for what they already have, framed
to the goal — for a health check it *"sharpens the read"*; for a diagnosis it *"gives
hypotheses to test against the data."*
 • 📄 MMP doc / CE one-pager — link (overview, hypotheses, constraints)
 • 📊 Analysis sheets / dashboards — link (pulled as a lens)
 • 📝 Draft work / a previous RCA — paste or link
 • 💬 Slack — a thread link, or name a channel to read
 • 🎙️ Or just dump what you know — what changed, what you suspect, what usually breaks — free text or a voice note
Reply `skip` = no docs to share (a bare `skip` does **not** bypass intake — 1c still runs).
**STOP and WAIT for their reply before 1b/1c.**

### 1b — Ingest & mine what they shared (only after 1a returns)
For any **non-Slack** source named (doc, sheet, draft, prior RCA, link, file), spawn the
ingestion sub-agent (`references/context_ingest_guide.md`) with the pointers + CE context
+ `run_dir`; it returns a lean distillate (never raw text). For a pasted **Slack thread
link**, read that one thread directly. A free-text / voice dump is mined in place.
Persist: narrative → the matching `user_context.md` slots (tag the source); tabular data →
a `<run_dir>/user_data_<slug>.md` lens. **Mine to pre-fill** the 1c buckets + 1d aliases
(pre-fill never removes a question). Graceful: a missing guide or unreadable source is
logged and skipped, never fatal.

### 1c — Goal-adaptive bucketed questionnaire
The deliberate, structured pass — explicit pop-ups get far better input than a free-text
"continue?". **Depth adapts to the goal:**

- **General health check → LIGHT path:** skip the four buckets and the 1e hypothesis. Ask
  **one soft-context `AskUserQuestion` pop-up** — *"Anything about CE `<id>` that'd help
  me read its health right — what it is, anything notable lately, a constraint worth
  flagging?"* (options: **Nothing to add** / **Let Claude infer from the data** + the auto
  free-text box). Then still do 1d. If 1a already captured rich context you may skip even
  this.
- **All other goals → FULL path:** ask **all four buckets in a SINGLE `AskUserQuestion`
  call** (4 questions / one pop-up), then a **5th "anything else?" pop-up**.

**The four buckets** (`AskUserQuestion`, one call). **ALWAYS include all four — a rich
uploaded doc PRE-FILLS them but never removes them.** Lead each `question` with the
**bold bucket name** (the `header` chip is ~12-char-capped and unreliable):

| # | Bucket | `question` (no-prefill phrasing) |
|---|--------|---|
| 1 | Supply / Availability | "**Supply / Availability** — any constraints or known issues, recently or in general?" |
| 2 | Landing Page | "**Landing Page** — any constraints, changes, or known issues?" |
| 3 | PPC / Paid | "**PPC / Paid** — any restrictions, changes, or known issues?" |
| 4 | Pricing | "**Pricing** — any constraints, changes, or known issues?" |

The **free-text box is the primary answer**. Only **two quick-buttons** accompany it
(the tool requires two), both terminal: **"Let Claude infer"** (no first-hand input) and
**"Nothing to add"** (genuinely nothing / confirms a shown pre-fill). Do **not** add an
"Add context"/"Skip" button. When a bucket is **pre-filled** from 1b, shape it as **bucket
name → observation → "anything to add or correct?"** (drop the generic stem).

**Per-skill emphasis:** reorder/re-lead the buckets toward what the skill consumes (e.g.
`perf-audit` leads PPC/budget; `cvr-rca` leads LP/pricing/mix), but still ask all four on
the full path — a constraint in any bucket can matter.

**5th "anything else?" pop-up** (full path only; the 4/call cap forces a separate call) —
*"Anything else about this CE before I dig in?"* Same 2-button + box shape. Examples:
 • 📅 Known events + dates — *"raised prices in April"*, *"paused a campaign"*
 • 🚧 Constraints — PPC restrictions, single-vendor supply, seasonal closures
 • ⚠️ What usually breaks here — stock-outs, vendor API errors, pricing wars

### 1d — Confirm CE aliases (EVERY run, every path)
The Slack search defaults to the full name + id, so without nicknames it misses threads
using "KSC", "the Vatican", etc. **Auto-propose, then confirm** — generate the obvious
acronym + shortenings yourself and ask the user to confirm or extend: *"I'll also search
Slack for: **KSC**, **Kennedy** — add any other names your team uses, or confirm."*
Skippable (falls back to name + id). Record under `## Aliases`.

### 1e — Grounded driver hypothesis (FULL path only; AFTER the first data view)
Ask **after** the skill shows its first numbers (CE Health reveal / baseline signals /
rendered packet) — a hypothesis is sharpest once the user sees the movement. One tight
`AskUserQuestion` (header "Your read"): plain language, *"what do you think is driving
this, and where should I dig first?"* — two quick-buttons (**Run the default** / **Let
Claude infer the lead**, both = proceed, no steer) + the free-text box. A typed read →
`## Hypothesis priors` / `## Focus / direction`. (Light path / orientation skills have no
1e.) The 1c buckets are the *independent* corroboration (recalled before the numbers); 1e
is the reaction-grounded *steer* — keep both.

---

## The contract — `<run_dir>/user_context.md` (8 slots, unchanged)

Write exactly these `##` headings (consumers split on them; an empty slot is fine — a
"Let Claude infer" / "Nothing to add" answer writes nothing for that slot, and downstream
treats it exactly as a bare run):

```markdown
## Goal
[from 0b]

## Aliases
[from 1d — short list]

## About this CE
[overview, mined or user-given — labeled bullets: What / Market / Paid / Supply / Status]

## Focus / direction
[goal + any steer]

## Hypothesis priors
[grounded hypothesis from 1e, or empty]

## Known events
[dated incidents — these feed the CE Context timeline]

## Constraints
[from the buckets — feeds slack_probes]

## Known failure modes
[from the buckets — feeds slack_probes]

## Important links
[MMP / sheet / thread links]

## Sources
[provenance: where each slot came from]
```

Routing: bucket **constraints** → `## Constraints`; **in-window changes** → `## Known
events` (date them where you can); **failure modes / recurring issues** → `## Known
failure modes`; goal → `## Goal`; free-form focus → `## Focus / direction`; 1e → `##
Hypothesis priors`; aliases → `## Aliases`.

**Graceful everywhere.** Every step is independently skippable; a skip is an empty slot,
never fatal. If `AskUserQuestion` is unavailable, ask the same questions inline in chat
and record the answers the same way.
