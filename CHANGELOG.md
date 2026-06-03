# CE-RCA Skill — Changelog

This file tracks every meaningful change pushed to this repository. Each entry
is written for stakeholder consumption — what changed, why it matters.

---

## [v1.0.0] — 2026-06-03 — Initial release: CE-level RCA umbrella

**Summary:** CE-RCA is a new top-down master skill that gives a C-level reader
one tabbed report for a whole Combined Entity. It runs CE Health first, presents
the diagnosis and asks the user which directions to deep-dive, then fires the
matching sub-skills (CVR-RCA + perf-audit today) in parallel and composes their
outputs into a single tabbed HTML report. Each sub-skill's output appears
**verbatim** — the master is a composer, not an editor. The sub-skills are not
modified (the only cross-skill change is a small `orchestration.json` handshake
in CVR-RCA that prevents perf-audit being fired twice). The composite reuses the
shared `visual_kit.md`, so the umbrella report is visually identical to a
standalone CVR-RCA report.

### What ships

**Orchestrator — `SKILL.md`**
- Step 0: resolve CE + dates, create run dir + `meta.json`, fire CE Health
  (foreground), enrich `meta.json` from CE Health's JSON sidecar.
- Step 1: present the CE Health diagnosis in chat and pause for free-form user
  confirmation (continue with the default deep-dive, or pivot direction).
- Step 2: dispatch matched sub-skills via the registry, after writing the
  `orchestration.json` handshake; spawn them in parallel.
- Step 3: rename CVR-RCA's report, run `compose.py`, write the composite.

**Dispatch — `references/registry.md`**
- Driver → sub-skill table (CVR → cvr-rca, Traffic → perf-audit; AOV /
  Completion / Take Rate reserved for future skills).
- CVR ⇒ also-fire-perf-audit pairing rule.
- The orchestration handshake spec.

**Composition — `references/composition_rules.md` + `scripts/compose.py` + `scripts/helpers.py`**
- `compose.py` builds the tabbed report from run-dir artifacts in fixed reading
  order (CE Health → CVR RCA → Paid Performance Audit), emitting a tab only when
  its source artifact exists.
- Markdown tabs (CE Health, perf-audit) rendered verbatim via a stdlib-only
  markdown→HTML renderer (vendored from cvr-rca, extended with blockquote +
  fenced-code), with namespaced heading anchors (`cehealth-*`, `perfaudit-*`).
- CVR-RCA tab extracted from its standalone `report.html` — the CVR content only
  (`#tab-cvr-rca`, or the `.container` body for single-tab reports), with its
  Plotly chart scripts re-injected so charts render.
- Composite styling extracted from the vendored `visual_kit.md` at build time,
  so a visual_kit sync updates the composite with no template edit.

**Shell — `templates/report.html`**
- Header + dashboards row + sticky left-anchored tab bar + panes + back-to-top +
  tab-switching JS (incl. cross-tab anchor handling), all from visual_kit
  patterns.

**Distribution — `INSTALL.md`, `README.md`**
- Companion installer with steps for CE Health, CVR-RCA (v1.24+), perf-audit.
- Graceful degradation: any uninstalled companion just won't appear as a tab.

### Paired change in CVR-RCA (separate repo)

- CVR-RCA v1.24 (c038): the perf-audit spawn block gains an `orchestration.json`
  delegation check. When the master has pre-fired perf-audit, CVR-RCA skips its
  own spawn and consumes the shared output at Step 2b. Standalone `/cvr-rca`
  runs are unchanged.

### Future hooks (designed-in, deferred)

- User context paste (`user_context.md` slot).
- Cross-skill `↗` references (anchor scheme + tab JS already support it).
- A summary skill synthesising across tabs.
- More dispatch drivers (AOV-RCA, Completion-RCA, Take-Rate-RCA).
