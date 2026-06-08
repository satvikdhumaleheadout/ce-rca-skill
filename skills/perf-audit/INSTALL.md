# Installation

## Prerequisites

1. **Claude Code** installed ([docs](https://docs.anthropic.com/en/docs/claude-code))
2. **Python 3.9+** with `google-cloud-bigquery`:
   ```bash
   pip install google-cloud-bigquery
   ```
3. **BigQuery access** to `headout-analytics` project:
   ```bash
   gcloud auth application-default login
   ```
   Verify: `bq query --project_id=headout-analytics --location=EU 'SELECT 1'`

## Install the Skill

### Option A: Claude Code Skill (recommended)

Clone the repo anywhere:
```bash
git clone git@github.com:aaradhyaraiHO/perf-audit-skill.git ~/skills/perf-audit-skill
```

Register in your project's `.claude/settings.json`:
```json
{
  "skills": [
    {
      "path": "~/skills/perf-audit-skill/SKILL.md"
    }
  ]
}
```

Use it:
```
/perf-audit-v6 "Louvre Museum"
```

### Option B: Direct CLI

Run the engine directly without Claude Code:
```bash
cd ~/skills/perf-audit-skill
python3 perf_audit.py render \
  --ce-id <CE_ID> --ce-name "<Name>" --market "<Market>" \
  --l4w-start YYYY-MM-DD --l4w-end YYYY-MM-DD \
  --p4w-start YYYY-MM-DD --p4w-end YYYY-MM-DD \
  --ly-start YYYY-MM-DD --ly-end YYYY-MM-DD \
  --output output.md
```

### Option C: SQL-Only (no Python)

No installation needed. Point Claude at:
- `SKILL.md` — instructions
- `references/sql-reference.md` — queries
- `DIAGNOSTICS.md` — hypothesis trees

Claude runs queries inline and builds the report.

## Optional: MCP Servers

For richer analysis, configure these MCP servers in Claude Code:

- **Ahrefs** — `keywords-explorer-volume-history`, `keywords-explorer-overview` (demand trends in Section 6a)
- **Slack** — `slack_search_public_and_private` (SP context, campaign history)

## Verify Installation

```bash
# Check BQ connectivity
python3 -c "
from google.cloud import bigquery
c = bigquery.Client(project='headout-analytics', location='EU')
rows = list(c.query('SELECT combined_entity_id, combined_entity_name FROM analytics_reporting.dim_combined_entities LIMIT 3').result())
for r in rows: print(f'{r.combined_entity_id}: {r.combined_entity_name}')
"

# Check engine imports
python3 -c "from engine.sources.bq import fetch_ce_health; print('Engine OK')"
```
