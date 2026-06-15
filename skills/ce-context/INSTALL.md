# CE Context — install / prerequisites

`/ce-context` is a vendored sub-skill of the CE-RCA bundle. It is normally
dispatched automatically by `/ce-rca` (right after the diagnosis pause), but can
also be run standalone for a lightweight context-only report.

## Prerequisites

- **BigQuery (`bq` CLI / gcloud ADC)** — only for the standalone CE-name → id
  resolution (`dim_combined_entities`). Under the umbrella, CE Health already
  resolved the CE, so no BQ call is needed here.
- **Slack MCP (any connected Slack server)** — required for the Slack
  standing-context stream. The tools are discovered **dynamically by name** at run
  time (`ToolSearch("+slack search read channel thread")`), so **any** Slack MCP
  works regardless of its server-id namespace — no specific plugin is required. The
  base tool names are `slack_search_public_and_private`, `slack_read_channel`,
  `slack_read_thread`, `slack_search_channels`. **This skill owns the Slack collector
  for the whole CE-RCA run** (CVR-RCA defers to it under the umbrella). If no Slack
  MCP is **connected**, the Slack stream is skipped and the report states "Slack
  context unavailable" — the run is never blocked (honesty rule in
  `references/slack_context_guide.md`).
- **Prior RCA runs on disk** (`~/Documents/CE RCA Runs/`) — optional; the CE-history
  stream synthesises them. None present → "No prior RCAs found", not an error.

## Outputs

Into the run dir:
- `slack_context.md` — Slack signals (also consumed by CVR-RCA's Step 2b).
- `ce_history.md` — synthesised prior-RCA trajectory.
- `ce_context_timeline.json` — normalised dated events for the timeline chart.
- `ce_context_report.html` — the CE Context tab fragment (rendered by the CE-RCA
  bundle's `scripts/render_ce_context.py`).

## Graceful degradation

Every stream is independently optional. A standalone run with no Slack MCP, no
prior runs, and no user context still produces a (sparse) report — it never errors.
