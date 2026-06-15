"""
Signal enumeration for the perf-audit coverage gate (Phase 3).

Pure functions: turn the already-fetched engine dicts into the deterministic list
of *material movers* the report must close (CONFIRMED / RULED OUT / DATA GAP). The
engine enumerates (the gate); DIAGNOSTICS.md says how to close each; EVAL.md
hard-gates that every signal is disposed.

No BQ, no IO. L12M trajectory tags are attached separately (see attach_trajectories
in Phase 3.2) — build_signals leaves `trajectory` as None.

Window convention: enumeration is YoY-anchored (L4W vs LY). MoM (L4W vs P4W) only
sets the `mom_recency` flag. channels/cohorts dicts use keys tw/prior_4w/ly;
ce_health/paid_perf use l4w/p4w/ly.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

# ============================================================================
# Materiality thresholds — named so the eval loop can tune them.
# ============================================================================
CONTRIB_PCT = 10.0    # channel/cohort: % of |CE revenue Δ YoY| to be material
CONTRIB_FLOOR = 500.0  # ...and at least this many $ of absolute YoY move (noise guard)
RATE_PP = 3.0         # rate metrics (ROI/TR/CR): pp move YoY
RATIO_PCT = 10.0      # ratio/volume metrics (CPC/RPC/AOV/Rev): % move YoY
SHAPLEY_PCT = 15.0    # paid-CM1 Shapley driver: % of |paid CM1 Δ YoY|
TGID_SHARE_PP = 5.0   # TGID assortment: |Δ share| pp

ALLOWED_TRAJECTORIES = {"cliff", "gradual", "recovering", "volatile", "new", None}

# Headline metrics enumerated directly (clicks/CVR/avg CM1 are deferred to the
# Shapley drivers below — same quantities, better expressed as contribution share).
# (key, source, label, type)  type ∈ {"pp", "pct"}
_METRICS = [
    ("revenue", "ce", "CE revenue", "pct"),
    ("roi_1", "ce", "CE ROI(1)", "pp"),
    ("tr", "ce", "CE take rate", "pp"),
    ("cr", "ce", "CE completion rate", "pp"),
    ("aov", "ce", "CE AOV", "pct"),
    ("paid_roi", "paid", "Paid ROI", "pp"),
    ("cpc", "paid", "Paid CPC", "pct"),
    ("paid_tr", "paid", "Paid take rate", "pp"),
    ("rpc", "paid", "Paid RPC", "pct"),
]

_KIND_ORDER = {"shapley": 0, "channel": 1, "metric": 2, "cohort": 3, "tgid": 4}


def _f(d, k):
    # type: (Any, str) -> Optional[float]
    """Safe float getter."""
    if not isinstance(d, dict):
        return None
    v = d.get(k)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _denom(net, gross):
    # type: (float, float) -> float
    """Share denominator: |net Δ| when it dominates, else gross movement.

    Guards against the offsetting/near-zero-net case (large drivers cancelling)
    where dividing by |net| would explode shares — mirrors the Shapley net-flat rule.
    """
    net = abs(net or 0.0)
    gross = abs(gross or 0.0)
    if net >= 0.2 * gross:
        return net or 1.0
    return gross or 1.0


def _recency(cur, p4w, ly):
    # type: (Optional[float], Optional[float], Optional[float]) -> str
    """MoM recency relative to the YoY move: recovering | worsening | stable | —.

    recovering = the MoM move opposes the YoY move (mitigating it).
    worsening  = the MoM move compounds the YoY move.
    """
    if cur is None or p4w is None:
        return "—"
    mom = cur - p4w
    scale = abs(p4w) if p4w else 1.0
    if abs(mom) < 0.02 * (scale or 1.0):
        return "stable"
    yoy = (cur - ly) if ly is not None else None
    if not yoy:
        return "—"
    return "recovering" if (mom > 0) != (yoy > 0) else "worsening"


def _mk(sid, kind, label, basis, value, recency, severity_hint):
    # type: (str, str, str, str, Optional[float], str, str) -> Dict[str, Any]
    return {
        "id": sid,
        "kind": kind,
        "label": label,
        "basis": basis,
        "value": value,
        "window": "YoY",
        "mom_recency": recency,
        "trajectory": None,   # filled by attach_trajectories (Phase 3.2)
        "severity_hint": severity_hint,
    }


def build_signals(ce_health, channels, cohorts, paid_perf, shapley, tgid):
    # type: (Dict, Dict, Dict, Dict, Dict, Dict) -> List[Dict[str, Any]]
    """Enumerate the material signals the report must close.

    Returns a list of signal dicts (schema in _mk). Deterministic given the inputs.
    """
    signals = []  # type: List[Dict[str, Any]]

    # ── Channels: revenue contribution ≥ CONTRIB_PCT of |CE rev Δ YoY| ──
    if channels:
        tw = {c["channel"]: c for c in (channels.get("tw") or [])}
        ly = {c["channel"]: c for c in (channels.get("ly") or [])}
        p4 = {c["channel"]: c for c in (channels.get("prior_4w") or [])}
        names = set(tw) | set(ly)
        deltas = {n: (_f(tw.get(n), "revenue") or 0.0) - (_f(ly.get(n), "revenue") or 0.0) for n in names}
        net = sum(deltas.values())
        gross = sum(abs(d) for d in deltas.values())
        denom = _denom(net, gross)
        for n, d in deltas.items():
            if abs(d) >= (CONTRIB_PCT / 100.0) * denom and abs(d) >= CONTRIB_FLOOR:
                share = d / denom * 100.0
                rec = _recency(_f(tw.get(n), "revenue"), _f(p4.get(n), "revenue"), _f(ly.get(n), "revenue"))
                sev = "high" if abs(share) >= 25 else "medium"
                signals.append(_mk(f"channel:{n}", "channel", f"{n} revenue",
                                    f"{share:+.0f}% of CE rev Δ YoY", d, rec, sev))

    # ── Cohorts (languages): same contribution rule ──
    if cohorts:
        tw = {c["cohort"]: c for c in (cohorts.get("tw") or []) if c.get("cohort")}
        ly = {c["cohort"]: c for c in (cohorts.get("ly") or []) if c.get("cohort")}
        p4 = {c["cohort"]: c for c in (cohorts.get("prior_4w") or []) if c.get("cohort")}
        names = set(tw) | set(ly)
        deltas = {n: (_f(tw.get(n), "revenue") or 0.0) - (_f(ly.get(n), "revenue") or 0.0) for n in names}
        net = sum(deltas.values())
        gross = sum(abs(d) for d in deltas.values())
        denom = _denom(net, gross)
        for n, d in deltas.items():
            if abs(d) >= (CONTRIB_PCT / 100.0) * denom and abs(d) >= CONTRIB_FLOOR:
                share = d / denom * 100.0
                rec = _recency(_f(tw.get(n), "revenue"), _f(p4.get(n), "revenue"), _f(ly.get(n), "revenue"))
                sev = "high" if abs(share) >= 25 else "medium"
                signals.append(_mk(f"cohort:{n}", "cohort", f"{n} cohort revenue",
                                    f"{share:+.0f}% of cohort rev Δ YoY", d, rec, sev))

    # ── Headline metrics ──
    for key, src, label, typ in _METRICS:
        cur_w = (ce_health if src == "ce" else paid_perf) or {}
        cur = _f(cur_w.get("l4w"), key)
        p4w = _f(cur_w.get("p4w"), key)
        lyv = _f(cur_w.get("ly"), key)
        if cur is None or lyv is None:
            continue
        if typ == "pp":
            move = cur - lyv
            if abs(move) < RATE_PP:
                continue
            basis = f"{move:+.1f}pp YoY"
            sev = "high" if abs(move) >= 6 else "medium"
            value = move
        else:
            if not lyv:
                continue
            movepct = (cur - lyv) / abs(lyv) * 100.0
            if abs(movepct) < RATIO_PCT:
                continue
            basis = f"{movepct:+.0f}% YoY"
            sev = "high" if abs(movepct) >= 25 else "medium"
            value = cur - lyv
        signals.append(_mk(f"metric:{src}:{key}", "metric", label, basis, value,
                           _recency(cur, p4w, lyv), sev))

    # ── Shapley drivers (paid CM1 = Clicks × CVR × Avg CM1) ──
    yoy = (shapley or {}).get("yoy") or {}
    mom = (shapley or {}).get("mom") or {}
    for drv, label in [("clicks", "Clicks"), ("cvr", "CVR"), ("avg_cm1", "Avg CM1")]:
        f = yoy.get(drv) or {}
        share = f.get("share_pct")
        contrib = f.get("contribution")
        if share is None or abs(share) < SHAPLEY_PCT:
            continue
        mom_contrib = (mom.get(drv) or {}).get("contribution") or 0.0
        if contrib and mom_contrib and (mom_contrib > 0) != (contrib > 0):
            rec = "recovering"
        elif contrib and mom_contrib and (mom_contrib > 0) == (contrib > 0):
            rec = "worsening"
        else:
            rec = "—"
        sev = "high" if abs(share) >= 40 else "medium"
        signals.append(_mk(f"shapley:{drv}", "shapley", f"{label} (paid CM1 driver)",
                           f"{share:+.0f}% of paid CM1 Δ YoY", contrib, rec, sev))

    # ── TGID assortment movers ──
    # Enumerate on |Δ share| alone: a genuinely material new SKU already clears the
    # bar (Δ share = its full L4W share) and a material dropped SKU does too
    # (Δ share = −its LY share). is_new/is_dropped only tag + rank — they don't
    # independently flag sub-threshold products (avoids 0.4pp new-SKU noise).
    for r in (tgid or {}).get("rows") or []:
        ds = r.get("delta_share") or 0.0
        new = bool(r.get("is_new"))
        dropped = bool(r.get("is_dropped"))
        if abs(ds) < TGID_SHARE_PP:
            continue
        tag = " (new)" if new else (" (dropped)" if dropped else "")
        sev = "high" if abs(ds) >= 15 else "medium"
        name = r.get("experience_name") or ""
        signals.append(_mk(f"tgid:{r.get('tgid')}", "tgid", f"TGID {r.get('tgid')} {name}",
                           f"Δ share {ds:+.1f}pp{tag}", ds, "—", sev))

    # Dedup same-concept CE-vs-paid metric pairs: the paid view leads a *paid* audit,
    # so when both fire, demote the CE-level twin to the "also enumerated" tier (kept
    # for completeness, but it no longer doubles up the HIGH list). Not a drop —
    # they're different grains (all-channels vs paid-only).
    by_id = {s["id"]: s for s in signals}
    for ce_key, paid_key in (("metric:ce:roi_1", "metric:paid:paid_roi"),
                             ("metric:ce:tr", "metric:paid:paid_tr")):
        if ce_key in by_id and paid_key in by_id:
            twin, paid = by_id[ce_key], by_id[paid_key]
            # Only demote when both move the SAME direction (genuinely redundant). If
            # they diverge (e.g. CE ROI up while Paid ROI down), keep both — the
            # all-channels-vs-paid split is itself the signal.
            if (twin.get("value") or 0) * (paid.get("value") or 0) > 0:
                twin["severity_hint"] = "medium"
                if "(CE-level" not in twin["basis"]:
                    twin["basis"] += " (CE-level; see paid twin)"

    # Stable, readable order: severity (high first), then kind, then magnitude.
    signals.sort(key=lambda s: (
        0 if s["severity_hint"] == "high" else 1,
        _KIND_ORDER.get(s["kind"], 9),
        -abs(s["value"] or 0.0),
    ))
    return signals


# ============================================================================
# L12M trajectory tagging (Phase 3.2)
# ============================================================================

# Trajectory thresholds (tunable).
_RECOVER_FRAC = 0.08   # recent segment must reverse ≥8% of the level to count as recovering
_CLIFF_FRAC = 0.60     # one MoM step ≥60% of the full range → cliff
_VOLATILE_CV = 0.50    # coef. of variation ≥0.5 without a dominant trend → volatile


def classify_trajectory(series):
    # type: (Optional[List[Optional[float]]]) -> str
    """Tag an L12M (or short) series: cliff | gradual | recovering | volatile | new.

    Pure and scale-free (classifies shape, so ratio-vs-% series are fine). <3 points
    → "new" (a SKU/cohort that only recently appeared). Heuristic and tunable; its
    job is context for disposition, not a precise forecast.
    """
    vals = [float(v) for v in (series or []) if v is not None]
    if len(vals) < 3:
        return "new"
    n = len(vals)
    base = abs(statistics.fmean(vals)) or 1.0
    rng = max(vals) - min(vals)
    overall = vals[-1] - vals[0]
    k = max(1, n // 3)
    recent_dir = vals[-1] - vals[-1 - k]   # slope over the last k intervals
    diffs = [vals[i] - vals[i - 1] for i in range(1, n)]
    abs_diffs = [abs(d) for d in diffs]
    total_move = sum(abs_diffs) or 1.0
    # oscillation: count direction reversals in the MoM diffs
    signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in diffs]
    nz = [s for s in signs if s != 0]
    reversals = sum(1 for i in range(1, len(nz)) if nz[i] != nz[i - 1])

    # recovering: a real decline that has materially ticked back up recently
    if overall <= -0.02 * base and recent_dir >= _RECOVER_FRAC * base:
        return "recovering"
    # volatile: many reversals (oscillation), no dominant direction
    if reversals >= max(2, round(0.4 * len(diffs))) and abs(overall) < 0.5 * base:
        return "volatile"
    # cliff: ONE month-over-month step dominates — both the range and the total movement
    if rng > 0 and n >= 4 and max(abs_diffs) >= _CLIFF_FRAC * rng and max(abs_diffs) >= 0.5 * total_move:
        return "cliff"
    return "gradual"


def attach_trajectories(signals, channels=None, cohorts=None, ce_health=None,
                        paid_perf=None, channel_monthly=None, tgid=None):
    # type: (List[Dict], Optional[Dict], Optional[Dict], Optional[Dict], Optional[Dict], Optional[Dict], Optional[Dict]) -> List[Dict]
    """Fill each signal's `trajectory` from the matching L12M series.

    Series sources by signal kind:
      - metric (CE/paid with a monthly column) → channels["monthly"]
      - metric paid_tr / rpc (no monthly column) → 3-window pseudo-series [LY,P4W,L4W]
      - shapley clicks/cvr/avg_cm1 → channels["monthly"] paid columns
      - channel → channel_monthly[name] (Phase 3.2 fetch)
      - cohort → 3-window pseudo-series from cohort window dicts (avoids code/name mismatch)
      - tgid → tgid["monthly"][id] (Phase 3.2 fetch; new SKU → short series → "new")
    """
    monthly = (channels or {}).get("monthly") or []

    def col(name):
        return [_f(m, name) for m in monthly]

    clicks, cvr, cm1 = col("paid_clicks"), col("paid_cvr"), col("paid_cm1")

    def avgcm1_series():
        out = []
        for cl, cv_, c in zip(clicks, cvr, cm1):
            conv = (cl * cv_) if (cl is not None and cv_ is not None) else None
            out.append((c / conv) if (c is not None and conv) else None)
        return out

    ce_paid = {
        "metric:ce:revenue": col("revenue"),
        "metric:ce:roi_1": col("roi_1"),
        "metric:ce:tr": col("tr"),
        "metric:ce:cr": col("cr"),
        "metric:ce:aov": col("aov"),
        "metric:paid:paid_roi": col("paid_roi"),
        "metric:paid:cpc": col("paid_cpc"),
    }
    shap = {"shapley:clicks": clicks, "shapley:cvr": cvr, "shapley:avg_cm1": avgcm1_series()}
    chmon = channel_monthly or {}
    tgmon = (tgid or {}).get("monthly") or {}
    tg_rows = {str(r.get("tgid")): r for r in (tgid or {}).get("rows") or []}

    def cohort_pseudo(name):
        def rev(win):
            for c in (cohorts or {}).get(win) or []:
                if c.get("cohort") == name:
                    return _f(c, "revenue")
            return None
        return [rev("ly"), rev("prior_4w"), rev("tw")]

    def metric_pseudo(src, key):
        w = (ce_health if src == "ce" else paid_perf) or {}
        return [_f(w.get("ly"), key), _f(w.get("p4w"), key), _f(w.get("l4w"), key)]

    for s in signals:
        sid, kind = s["id"], s["kind"]
        series = None
        forced = None
        if kind == "metric":
            if sid in ce_paid:
                series = ce_paid[sid]
            else:
                parts = sid.split(":")  # metric:src:key
                if len(parts) == 3:
                    series = metric_pseudo(parts[1], parts[2])
        elif kind == "shapley":
            series = shap.get(sid)
        elif kind == "channel":
            series = chmon.get(sid.split(":", 1)[1])
        elif kind == "cohort":
            series = cohort_pseudo(sid.split(":", 1)[1])
        elif kind == "tgid":
            tid = sid.split(":", 1)[1]
            # A new SKU is "new" regardless of its short ramp shape (don't mislabel as volatile)
            if tg_rows.get(tid, {}).get("is_new"):
                forced = "new"
            else:
                series = tgmon.get(tid)
        s["trajectory"] = forced or classify_trajectory(series)
    return signals
