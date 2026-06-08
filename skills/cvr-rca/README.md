# CVR-RCA Skill

A Claude Code skill for investigating CVR (conversion rate) drops on Headout
Combined Experiences. It runs a structured root-cause analysis — baseline
queries, hypothesis tree, and a stakeholder-ready HTML report — all from a
single command.

---

## What it does

1. Runs BigQuery queries to pull funnel rates, Shapley attribution, mix signals,
   and trend context for the CE and date range you specify.
2. Walks a hypothesis tree (routing vs conversion, by funnel step) to isolate
   the driver.
3. Writes an HTML report with findings, supporting charts, and action cards —
   ready to share with GMs and product.

---

## Install

Open Claude Code or Cowork and paste this message:

> Install the skill from this URL: `https://raw.githubusercontent.com/satvikdhumaleheadout/cvr-rca-skill/refs/heads/main/INSTALL.md`

Claude will handle everything — downloading the files, registering the `/cvr-rca` command, and creating the output folder. Restart Claude Code when it's done.

---

## Usage

```
/cvr-rca <ce_id>
/cvr-rca <ce_id> <window in plain English or exact dates>
```

No dates defaults to last 30 days vs the prior 30 days. Otherwise use plain
English or exact dates — either works:

```
/cvr-rca 167
/cvr-rca 167 last complete week vs the week before it
/cvr-rca 167 this year vs same time last year
/cvr-rca 167 April vs March
/cvr-rca 167 2026-03-01 2026-03-31 2026-04-01 2026-04-30
```

---

## Requirements

- [Claude Code](https://claude.ai/download) (desktop app or CLI)
- `bq` CLI with `gcloud auth application-default login` completed
- Access to the `headout-analytics` BigQuery project

---

## Updating

Paste this in Claude Code or Cowork:

> Update the skill from this URL: `https://raw.githubusercontent.com/satvikdhumaleheadout/cvr-rca-skill/refs/heads/main/INSTALL.md`

Your runs folder is untouched. The skill also checks for updates automatically
on each invocation and will nudge you when a newer version is available.

---

## Current version

See [VERSION](VERSION).
