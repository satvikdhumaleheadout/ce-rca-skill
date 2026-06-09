# CE-RCA Quality Evaluator

> **Maintainer tool — on-demand, not part of the GM run flow.** This evaluator is **not** run
> automatically on GM-facing runs (it would cost tokens + time for a record the GM never sees). A
> maintainer runs it on demand against any finished run-dir — it reads only on-disk artifacts, so it
> needs no live session context. To run: spawn a sub-agent with *"read this file and follow it; run
> dir `<run_dir>`; write `<run_dir>/ce_rca_evaluation.md`."* Use it on a sample of runs while tuning;
> recurring gaps across evaluations are the signal to fix the named CE-RCA skill file (see
> Meta-review). Output goes to **`ce_rca_evaluation.md`** — distinct from CVR-RCA's own
> `cvr_rca_evaluation.md`.

## Your role

A CE-level Root Cause Analysis has just finished — CE Health ran, the orchestrator chose a
direction, the deep-dive skills (CVR-RCA ± perf-audit) ran in parallel, the Summary agent wove the
tabs together, and `compose.py` produced the composite `report.html`. Your job: step back and grade
the **orchestration** honestly — not any single sub-skill's internal investigation (each sub-skill
self-evaluates), but **how well the whole CE-RCA came together** as one coherent, correct,
actionable answer.

This is not a formality. The purpose is to surface where the orchestrated RCA fell short of what a
sharp analyst would expect from a stand-alone CE report — not to ratify the choices made. Be harder
on it than a colleague would be. If the Summary claimed agreement the tabs don't support, say so. If
a material driver was never covered, name it.

You are **not** re-running the investigation and **not** re-scoring CVR-RCA's or perf-audit's
internal work. You are scoring the **seams**: direction, dispatch, cross-tab synthesis, CE-level
correctness, coverage, actionability, report integrity, and evidence discipline.

---

## What to review

Before scoring, read these in order:

1. **The CE-RCA skill files** — read them first, so you know what instructions existed (this is what
   makes the failure-mode classification possible):
   - `SKILL.md` — the orchestration process (Step 0 resolve/window → Step 1 direction → Step 2
     dispatch → Step 3 Summary → Step 4 compose → … ).
   - `references/summary_guide.md` — the Summary contract (pure synthesis, per-tab conclusion
     digests, cross-reference table, the cardinal rule about surfacing tensions).
   - `references/composition_rules.md` — tab order, verbatim-vs-re-render rules, header chrome.
   - `references/registry.md` — which sub-skills exist and when each should be dispatched.
2. **The composite `report.html`** — read it as if you've never seen this CE before. Do the tabs
   cohere? Do the cross-tab `↗` links resolve? Does the Summary stand alone?
3. **The Summary fragment** (`summary_report.html`) — the front-page synthesis you're chiefly judging.
4. **The source tabs** — `ce_health_report.md` (+ `.json`), `findings.md` / `cvr_rca_report.html`,
   `perf_audit_report.md` — to verify the Summary's conclusions and numbers actually trace back.
5. **The run scaffolding** — `orchestration.json` (what was dispatched, the context handshake),
   `_run_log.md` (the orchestrator's decisions), `meta.json`, and `user_context.md` /
   `slack_context.md` / `followups.html` if present.

Reading the skill files first is what makes the failure-mode classification (Section 4) possible.
You cannot say "the instruction was missing" unless you have actually looked.

---

## Direction-aware scoring note

The 7 themes apply to **both** revenue-decline and revenue-improvement RCAs. The examples below are
written neutrally; when scoring, translate "the story" / "the driver" to the actual direction. The
structural criteria are identical — the Summary must still commit to a specific CE-level story, the
tabs must still corroborate (or the tension be surfaced), the drivers must still be quantified, and
the next steps must still be specific and owned.

One calibration note — **Theme 4 (Coverage)**: coverage is judged against what the diagnosis
*warranted*. A clean single-driver CE that needed only CVR-RCA should **not** be marked down for not
running perf-audit; an unrun tab is a gap only when the Step 1 diagnosis pointed at it.

## Scoring

For each of the 7 themes below, give:
- **Score: 1–5**
- **Justification**: 2–3 sentences citing specific content from the report / Summary / tabs. Vague
  justifications ("the summary was clear") are not acceptable.
- **Gap** (required if score ≤ 4): describe specifically what was missing or wrong.
- **Why** (required for every gap): classify the root cause using one of the four tags below, backed
  by a citation.

**Scale:**
| Score | Meaning |
|-------|---------|
| 5 | Exemplary — hard to do better given the tabs available |
| 4 | Good — clear execution, one or two minor gaps |
| 3 | Adequate — meets the minimum bar but nothing exceptional |
| 2 | Weak — some effort but significant gaps or errors |
| 1 | Poor — fundamental failure of this dimension |

---

## Failure Mode Classification

Every gap gets a **`Why`** line. Use exactly one of these four tags:

| Tag | Meaning |
|-----|---------|
| `[MISSING_INSTRUCTION]` | The CE-RCA skill files contain no instruction for this behaviour. The orchestrator/Summary had no way to know it was expected. |
| `[AMBIGUOUS_INSTRUCTION]` | An instruction exists but is vague, incomplete, or conflicting enough that it was reasonably interpreted differently. |
| `[EXEC_ERROR]` | The instruction was clear and present. It was attempted but executed incorrectly (mis-synthesis, wrong dispatch, broken link, mis-stated number). |
| `[DATA_LIMIT]` | The input needed was unavailable (a tab didn't run, `findings.md` absent, CE Health data gap). Skipping or noting the absence was the right call — not a skill flaw. |

### Grounding requirement

**Never assign a tag without citing the source** (the CE-RCA file + section/line):

- **`[MISSING_INSTRUCTION]`** — name the files you checked and confirm absence:
  > *"Searched SKILL.md, summary_guide.md, composition_rules.md, registry.md — no instruction to [behaviour]."*
- **`[AMBIGUOUS_INSTRUCTION]`** — quote the instruction, then state the missing constraint:
  > *"summary_guide.md, 'Per-tab conclusion digests': 'carry each tab's conclusions in full' — does not say whether a tab that returned a DATA_LIMIT should still get a digest stub; Summary omitted it silently."*
- **`[EXEC_ERROR]`** — name the file/section that gave the instruction, then what went wrong:
  > *"summary_guide.md cardinal rule: 'every number must already appear in a source tab.' The Summary's driver table shows a +$X figure that appears in no tab — a computed/invented number."*
- **`[DATA_LIMIT]`** — name the instruction that needed the input, and why it was unavailable:
  > *"summary_guide.md lists findings.md as the CVR-RCA conclusion source; findings.md was absent this run (sub-agent write-block), so the Summary correctly fell back to cvr_rca_report.html."*

If you cannot write a specific citation, you have not checked enough. Go back to the skill files.

---

## Theme 1: Direction & Dispatch Quality

*Did the orchestrator point the RCA at the right thing?*

Score high if:
- The Step 1 direction matches what CE Health actually showed (the chosen driver pattern is the one the diagnosis surfaced).
- The dispatched sub-skills fit the diagnosis — CVR-RCA when the funnel/conversion moved; perf-audit added when the paid/traffic side was implicated; neither over- nor under-dispatched.
- The `orchestration.json` handshake passed the correct window, fixed segment, and context lenses, so the deep dives ran on the right scope.

Score low if:
- The RCA chased a driver the CE Health vitals/Shapley did not support.
- A clearly-implicated tab was never dispatched (e.g. paid was the story but perf-audit didn't run), or a tab was run that the diagnosis gave no reason to run.
- The window/segment handed to the sub-skills disagrees with the confirmed window.

---

## Theme 2: Cross-Tab Synthesis & Corroboration

*Does the Summary make the tabs genuinely talk to each other?*

Score high if:
- The Summary traces the headline driver across CE Health → CVR-RCA → perf-audit and shows where they corroborate, with working `↗` links.
- Where two tabs disagree, the tension is **surfaced and framed**, not papered over (per the summary_guide cardinal rule).
- User-context priors and Slack signals, when present, are reconciled — confirmed, refuted, or noted as uncorroborated — not ignored.

Score low if:
- The Summary asserts agreement the tabs don't actually support, or invents a consensus.
- A real contradiction between tabs is hidden or silently resolved without evidence.
- The cross-reference / corroboration table is missing, thin, or its sources don't match the tabs.

---

## Theme 3: CE-Level Diagnostic Correctness

*Is the CE-level story right and internally consistent?*

Score high if:
- The headline revenue story and the driver decomposition are consistent across the Summary, CE Health's Shapley, and the deep-dive tabs (same direction, compatible magnitudes).
- The long-term / YoY framing is correct (a sequential move isn't misread in isolation).
- The conclusion commits to a specific CE-level finding, not "multiple factors."

Score low if:
- The Summary's stated driver contradicts CE Health's Shapley ranking or a deep-dive conclusion without explanation.
- Magnitudes are mutually inconsistent across tabs and the discrepancy is neither reconciled nor flagged.
- The story is non-committal or could describe any CE.

---

## Theme 4: Coverage & Completeness

*Were all the material drivers and warranted tabs covered — and gaps owned?*

Score high if:
- Every material driver from CE Health's decomposition is addressed somewhere in the Summary.
- Tabs that the diagnosis warranted all ran; tabs that didn't run are absent for a defensible reason.
- Data gaps / absent tabs (e.g. missing `findings.md`, a skipped perf-audit) are acknowledged honestly rather than silently dropped (graceful degradation).

Score low if:
- A material driver is never mentioned.
- A diagnosis-warranted tab is silently missing.
- A gap is hidden — the report reads as complete when a tab failed or data was unavailable.

---

## Theme 5: Actionability & Ownership

*Does the RCA leave the reader knowing what to do, and who does it?*

Score high if:
- The consolidated next steps are concrete and testable, each tied to the tab that owns the detail via `↗`.
- Actions are prioritised, and each names a DRI / team and a clear reason.
- The single headline action in the callout is the genuinely most-important next step.

Score low if:
- Next steps are generic ("investigate further", "monitor").
- Actions have no owner, or the priority order is arbitrary.
- The consolidated list contradicts or omits a tab's own recommended actions.

---

## Theme 6: Report Integrity & Navigability

*Does the composite hold together as one document?*

Score high if:
- Tabs are in the intended reading order; the Summary stands alone per its contract (a reader of only the Summary gets the whole story).
- Every cross-tab `↗` resolves to a real anchor (no dangling links).
- No tab's supporting analysis is wholesale-duplicated into the Summary; each tab's role is distinct.

Score low if:
- Cross-tab links dangle or point to the wrong section.
- The Summary duplicates entire tables from the tabs rather than digesting conclusions.
- Tabs are mis-ordered, mislabelled, or the composite is visually broken.

---

## Theme 7: Evidence Integrity (pure synthesis)

*Did the Summary stay honest to its sources?*

Score high if:
- Every number in the Summary traces to a figure that already appears in a source tab.
- No new numbers were computed or invented at the Summary layer.
- Provenance (the cross-reference table's Source / Corroborated-by) is accurate and checkable.

Score low if:
- The Summary shows a number that appears in no tab (computed or hallucinated).
- A citation points to a tab/section that doesn't contain the claimed figure.
- The Summary adjudicated a contradiction with a number it derived itself.

---

## Output format

Write the evaluation to `<run_dir>/ce_rca_evaluation.md` as a structured assessment (not a bare
score table):

```markdown
# CE-RCA Evaluation
CE [id] · [CE name] | [pre window] vs [post window] | [date]

## Overall verdict
[3–4 sentences: what did this CE-RCA get right at the orchestration level, what was the main
failure mode, what would a senior analyst say after reading the composite?]

## Theme scores

### 1. Direction & Dispatch Quality — [score]/5
[justification; + Gap/Why block if ≤ 4]
### 2. Cross-Tab Synthesis & Corroboration — [score]/5
### 3. CE-Level Diagnostic Correctness — [score]/5
### 4. Coverage & Completeness — [score]/5
### 5. Actionability & Ownership — [score]/5
### 6. Report Integrity & Navigability — [score]/5
### 7. Evidence Integrity — [score]/5

## Total: [X]/35

## Top improvements for next run
1. [most impactful, concrete]
2. [second]
3. [third if applicable]

## Failure Mode Summary
| Gap (short label) | Theme | Tag | Fix target |
|-------------------|-------|-----|------------|
| [gap name] | T[N] | [TAG] | [CE-RCA file + one-phrase edit] |
```

Each gap block within a theme:
```
**Gap:** [what was missing or wrong — specific, not vague]
**Why:** [TAG] — [citation proving you checked the skill files] — [one sentence on the fix]
```

The fix-target column names the specific CE-RCA file (`SKILL.md`, `summary_guide.md`,
`composition_rules.md`, `registry.md`) and a one-phrase description of the edit. This is what turns
into a skill improvement next iteration.

---

## Meta-review

When the same gap recurs across multiple `ce_rca_evaluation.md` files (e.g. the Summary repeatedly
omits the user-context reconciliation, or cross-tab links repeatedly dangle), that is the signal to
update the CE-RCA skill files — `SKILL.md` or `summary_guide.md` — so the orchestration catches it
earlier, rather than relying on the evaluator to flag it every run.

---

## Self-honesty check

Before submitting:
- Did I score the **orchestration** (seams, synthesis, coverage) — not re-litigate a sub-skill's internal investigation (each self-evaluates)?
- Did I cite specific report/tab content, or write vague justifications?
- Did I verify the Summary's numbers actually appear in a source tab (Theme 7)?
- For every `[MISSING_INSTRUCTION]`: did I actually check all four CE-RCA skill files?
- For every `[AMBIGUOUS_INSTRUCTION]`: did I quote the real instruction?
- Does every Failure-Mode row map to a concrete edit in a named CE-RCA file?

An evaluation where every theme scores 4–5 with no improvements identified is almost certainly not
honest. Failure-mode tags without citations are not grounded — recheck before submitting.
