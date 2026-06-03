# Sub-skill Registry

The master reads this table at Step 2 to decide which deep-dive skills to fire,
based on the drivers CE Health surfaces. **Adding a future skill is a one-row
edit** — no code change. This is the scalability contract.

## Driver → sub-skill dispatch

| Driver (from CE Health Shapley) | Sub-skill | Install resolution (first match wins) | Invocation | Output artifact in run dir | Composite tab |
|---|---|---|---|---|---|
| `CVR` | cvr-rca | `$CVR_RCA_SKILL_PATH` → `~/.cvr-rca/SKILL.md` → `$SKILL_DIR/../cvr-rca/SKILL.md` | sub-agent reads the SKILL.md and runs it, pointed at the shared `<run_dir>` | `report.html` → master renames to `cvr_rca_report.html` | CVR RCA |
| `Traffic` | perf-audit-skill | `$PERF_AUDIT_SKILL_PATH` → `~/.perf-audit-skill/SKILL.md` → `$SKILL_DIR/../perf-audit-skill/SKILL.md` | sub-agent reads the SKILL.md and runs it, pointed at the shared `<run_dir>` | `perf_audit_report.md` | Paid Performance Audit |
| `AOV` | *(future: aov-rca)* | — | — | `aov_rca_report.md` (planned) | AOV RCA |
| `Completion Rate` | *(future: completion-rca)* | — | — | `completion_rca_report.md` (planned) | Completion RCA |
| `Take Rate` | *(future: take-rate-rca)* | — | — | `take_rate_rca_report.md` (planned) | Take Rate RCA |

CE Health itself is **not** in this table — it always runs first (Step 0), unconditionally, and is always Tab 1. The table governs only the *deep-dive* skills dispatched after the user confirms direction.

## Special-case pairing: CVR ⇒ also fire perf-audit

When `cvr-rca` is on the dispatch list, **always also fire `perf-audit-skill`**, even if `Traffic` wasn't flagged as a driver. CVR-RCA consults perf-audit during its own Step 2b reconciliation regardless of the cascade outcome; pre-firing perf-audit guarantees CVR-RCA has a real reconciliation source and that the perf-audit appears as its own composite tab. (Revisit this rule if other paired-skill dependencies emerge.)

## Driver-name matching

CE Health's Shapley section names drivers as **Traffic, CVR, AOV, Completion Rate, Take Rate**. Match case-insensitively and tolerate minor wording ("Conversion" ≈ CVR, "Order Value" ≈ AOV). When CE Health flags a driver with no registered sub-skill (e.g., AOV today), note it in the chat preview as "no deep-dive skill available yet for AOV" and skip it — don't block the run.

## How the master uses this table

1. Read CE Health's Shapley driver ranking from `ce_health_report.md` (and its JSON sidecar).
2. Map each **material** driver (meaningful Shapley share — use judgment, not a hard cutoff) to its sub-skill via the table.
3. Apply the CVR⇒perf-audit pairing rule.
4. Present the resulting default dispatch set to the user (Step 1) and let them confirm or pivot.
5. Resolve each chosen sub-skill's install path; if a path doesn't resolve, log it and skip that skill (the composite simply won't have that tab).
6. Write `orchestration.json` listing the skills being fired, then spawn them in parallel (Step 2).

## The orchestration handshake

Before firing any sub-agent, the master writes `<run_dir>/orchestration.json`:

```json
{
  "orchestrator": "ce-rca",
  "version": "<master VERSION>",
  "fired_by_master": ["perf-audit-skill", "cvr-rca"],
  "context_lenses": ["ce_health_report.md", "perf_audit_report.md", "slack_context.md"],
  "run_dir": "<absolute path>"
}
```

Two fields, two jobs:

- **`fired_by_master`** stops sub-skills double-firing each other. CVR-RCA, before spawning its own perf-audit sub-agent, checks this — if `perf-audit-skill` is listed, it skips its spawn and consumes the master's perf-audit output at Step 2b instead. See `cvr-rca/SKILL.md → "Perf-audit context"`.
- **`context_lenses`** is the **cross-skill manifest** — the lens artifacts deep dives reconcile against at their synthesis step. Always include `ce_health_report.md` (CE Health ran in Step 0, available to all). CVR-RCA reads this at its Step 2b "Context reconciliation" and folds CE Health + perf-audit + Slack into its funnel findings with the four-pattern model. This is what makes a deep-dive tab cite CE Health (e.g. a TGID's S2C drop corroborated against CE Health's RPC drop for that TGID). See `cvr-rca/SKILL.md → Step 2b → "Context reconciliation"`.

## The Summary synthesis pass (Step 3)

After the deep dives finish, the master fires a **Summary synthesis sub-agent**
(`references/summary_guide.md`) that reads every finished tab and writes
`summary_report.html` — the front-page cross-cutting synthesis. This is the
**peer↔peer weave surface**: individual deep-dive tabs reference *upstream* (CE
Health) inline, but the full "CVR found X, corroborated by perf Y, links to CE
Health Z" cross-referencing lives in the Summary, which runs last and sees
everything. Pure synthesis (no re-query); arbiter upgrade is a TODO.

## TODO — perf-audit cross-skill enrichment (owner hand-off)

perf-audit is owned by another team and is **not modified** by this work. Today
its tab doesn't cite CE Health or CVR-RCA — the Summary covers those cross-links.
The deferred enrichment: perf-audit should read the `context_lenses` manifest at
its own synthesis (mirroring CVR-RCA's Step 2b context layer) and cite CE Health /
CVR-RCA in its tab. This requires changes in the perf-audit repo by its owner.
