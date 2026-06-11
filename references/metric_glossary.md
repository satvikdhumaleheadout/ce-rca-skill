# CE-RCA Metric Glossary (canonical names + basis tags)

**Maintainer reference — NOT loaded at runtime.** No agent (orchestrator or sub-skill) reads this
file during a run. It is the single source-of-truth for *what* the canonical metric names are; the
report tabs are authored/rendered to conform to it (deterministic code for CE Health & perf-audit;
a few inline lines in `report_structure.md` / `summary_guide.md` for the authored tabs).

## Why this exists
The same word ("CVR", "Traffic", "S2C") was being shown across tabs with genuinely different
values — because the underlying measure differs by **basis** (segment / attribution-source /
grain). A reader saw the same label with two numbers and read it as a contradiction. The rule:

> **A headline metric is shown either under a unique canonical name, or with an explicit basis
> tag — never a bare ambiguous label.** Same label ⇒ same number across every tab.

## Canonical names

| Concept | Canonical name | Definition | Default basis |
|---|---|---|---|
| Conversion (Mixpanel funnel) | **Site CVR** | completed users ÷ LP users (Mixpanel page-funnel, **excludes PERFORMANCE_MAX**, all landing page types) | Mixpanel funnel, **within-session** (CVR-RCA + CE Health — same basis, matches Omni) |
| Conversion (paid platform) | **Paid CVR** | Google-Ads conversions ÷ clicks (paid-platform attribution, **includes PMax**) | Google Ads |
| Top-of-funnel volume (Mixpanel) | **LP Users** | distinct landing-page users (Mixpanel page-funnel) | Mixpanel funnel; grain tag where it differs |
| Top-of-funnel volume (paid) | **Paid sessions** | paid sessions (Google-Ads attributed) | Google Ads |
| Funnel steps | **LP2S / S2C / C2O** *(names kept)* | step-over-step rate (select/LP, checkout/select, completed/checkout) | **must carry a basis tag** — see below |

> Vocabulary is fixed here. To change wording (e.g. "On-site CVR", "Paid LP sessions"), edit this
> file and the conforming labels in the skills.

## Basis-tag vocabulary
Use one of these where a metric is shown on a non-default / potentially-ambiguous basis:
- **within-session** — Mixpanel page funnel, steps within one session (CVR-RCA **and CE Health**,
  matches the Omni dashboard). This is the canonical funnel basis for both Mixpanel tabs.
- **paid-session** — Google-Ads-attributed sessions (perf-audit on-site funnel).
- **cross-session** — Mixpanel funnel stitched across a user's sessions. *(Not currently used — CE
  Health migrated its funnel to within-session in v2.11.2; retained for future reference.)*
- **paid-platform** — Google-Ads clicks→conversions (perf-audit Paid CVR).
- **excl PMax / incl PMax** — whether PERFORMANCE_MAX is excluded (funnel) or included (paid channel tables).
- **fixed-segment** — CVR-RCA's fixed MB·Paid·Google cohort (its "Fixed Segment banner").
- **all-channel** — whole-CE, all channels (CE Health vitals/funnel headline).

## Where each canonical name is enforced (conformance map)
- **CE Health** (`skills/ce-health/ce_health.py`, deterministic): §5 monthly funnel CVR → **Site CVR**,
  paid monthly CVR → **Paid CVR**; §4/§7/§10 funnel CVR → **Site CVR**; "LP Users" kept. Funnel is
  **within-session · excl-PMax** (migrated to the page table in v2.11.2 — matches CVR-RCA/Omni; §4
  header note already present).
- **perf-audit** (`skills/perf-audit/engine/render/audit_skeleton.py`, deterministic): all paid CVR
  columns → **Paid CVR**; "LP Sessions" → **Paid sessions**; on-site funnel gets a paid-session note.
- **CVR-RCA** (`skills/cvr-rca/references/report_structure.md`, authored): cards "CVR" → **Site CVR**,
  "Traffic (users_lp)" → **LP Users**; funnel pill → "within-session · excludes PMax".
- **Orchestrator Summary** (`references/summary_guide.md`, authored): driver table uses **Site CVR** /
  **LP Users**; carry each source's basis tag verbatim; never juxtapose Site vs Paid CVR unlabeled.

## Out of scope (do not relabel)
Single-basis metrics that don't collide: Revenue, AOV, ROI(1), Take Rate, Completion (CR), Orders,
Gross Bookings — already consistent across tabs.
