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
  "run_dir": "<absolute path>"
}
```

This is the contract that stops sub-skills from double-firing each other. CVR-RCA, before spawning its own perf-audit sub-agent, checks this file — if `perf-audit-skill` is in `fired_by_master`, it skips its spawn and consumes the master's perf-audit output at its Step 2b reconciliation instead. See `cvr-rca/SKILL.md → "Perf-audit context"` for the consuming side.
