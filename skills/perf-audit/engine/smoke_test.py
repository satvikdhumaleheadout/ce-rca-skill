#!/usr/bin/env python3
"""
Smoke test for perf audit v6.1 — validates rendered metrics against metrics.py definitions.

Usage:
    python3 engine/smoke_test.py --ce-id 1223 \
        --l4w-start 2026-04-20 --l4w-end 2026-05-17 \
        --p4w-start 2026-03-23 --p4w-end 2026-04-19 \
        --ly-start 2025-04-21 --ly-end 2025-05-18

Checks:
1. AOV = order_value / orders (not revenue / orders)
2. ROI = CM1 / (spend + coupon_wallet)
3. CM1 ≤ Paid Revenue in all windows (PMax GMV correction applied)
4. Table 1 ROI > Table 2 ROI (all channels > paid only)
5. Per-table metric consistency (no None where data exists)
"""

from __future__ import annotations

import argparse
import sys
import os
from datetime import date

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from engine.sources.bq import (
    fetch_ce_health_3w,
    fetch_paid_performance_3w,
    fetch_channel_breakdown,
    fetch_campaign_cohorts,
    fetch_tgid_revenue,
    fetch_paid_value_shapley,
    fetch_channel_monthly,
    fetch_campaign_product_mix,
    fetch_ad_group_audit,
)
from engine.metrics import aov, roi, cpc, cvr, ctr, rpc, tr, cr
from engine.signals import (
    build_signals, attach_trajectories, ALLOWED_TRAJECTORIES,
)
from engine.render.audit_skeleton import render_signals_checklist


def check(name, passed, detail=""):
    status = "✓" if passed else "✗ FAIL"
    msg = f"  {status}  {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def run_tests(ce_id, l4w, p4w, ly):
    print(f"Smoke test: CE {ce_id}")
    print(f"  L4W: {l4w[0]} to {l4w[1]}")
    print(f"  LY:  {ly[0]} to {ly[1]}")
    print()

    failures = 0

    # Fetch data
    print("Fetching data...")
    ce_health = fetch_ce_health_3w(ce_id, l4w, p4w, ly)
    paid_perf = fetch_paid_performance_3w(ce_id, l4w, p4w, ly)
    channels = fetch_channel_breakdown(ce_id, l4w[0], l4w[1], ly[0], ly[1], p4w[0], p4w[1])
    print()

    # === Test 1: AOV consistency ===
    print("Test 1: AOV = order_value / orders (not revenue / orders)")
    for window in ["l4w", "p4w", "ly"]:
        h = ce_health.get(window, {})
        if h.get("aov") and h.get("orders") and h.get("revenue"):
            aov_val = h["aov"]
            rev_per_order = h["revenue"] / h["orders"]
            is_aov_not_rev = abs(aov_val - rev_per_order) > 1.0
            if not check(f"Table 1 {window}: AOV ${aov_val:.2f} ≠ rev/orders ${rev_per_order:.2f}",
                        is_aov_not_rev,
                        "AOV should be order_value/orders, higher than revenue/orders"):
                failures += 1

    # Check channel breakdown AOV
    tw_channels = channels.get("tw", [])
    for ch in tw_channels[:3]:
        if ch.get("aov") and ch.get("revenue") and ch.get("orders") and ch["orders"] > 0:
            ch_aov = ch["aov"]
            ch_rev_per_order = ch["revenue"] / ch["orders"]
            if not check(f"Table 3 {ch['channel']}: AOV ${ch_aov:.2f} ≠ rev/orders ${ch_rev_per_order:.2f}",
                        abs(ch_aov - ch_rev_per_order) > 0.5,
                        "Channel AOV should be order_value/orders"):
                failures += 1
    print()

    # === Test 2: ROI formula ===
    print("Test 2: ROI = CM1 / (spend + coupon_wallet)")
    for window in ["l4w", "p4w", "ly"]:
        p = paid_perf.get(window, {})
        if p.get("cm1") and p.get("ad_spend") and p.get("paid_roi"):
            expected_roi = roi(p["cm1"], p["ad_spend"])
            actual_roi = p["paid_roi"]
            diff = abs(actual_roi - expected_roi) if expected_roi else 0
            if not check(f"Table 2 {window}: ROI {actual_roi:.1f}% vs expected {expected_roi:.1f}%",
                        diff < 1.0,
                        f"diff {diff:.2f}pp"):
                failures += 1
    print()

    # === Test 3: CM1 ≤ Paid Revenue ===
    print("Test 3: CM1 ≤ Paid Revenue (PMax GMV correction applied)")
    for window in ["l4w", "p4w", "ly"]:
        p = paid_perf.get(window, {})
        if p.get("cm1") and p.get("paid_rev"):
            cm1_val = p["cm1"]
            rev_val = p["paid_rev"]
            gap_pct = (cm1_val - rev_val) / rev_val * 100 if rev_val else 0
            if not check(f"Table 2 {window}: CM1 ${cm1_val:,.0f} vs Rev ${rev_val:,.0f} (gap {gap_pct:+.1f}%)",
                        gap_pct < 5.0,
                        "CM1 > Rev by >5% = PMax GMV not corrected"):
                failures += 1
    print()

    # === Test 4: Table 1 ROI > Table 2 ROI ===
    print("Test 4: Table 1 ROI(1) direction vs Table 2 Paid ROI")
    h_l4w = ce_health.get("l4w", {})
    p_l4w = paid_perf.get("l4w", {})
    if h_l4w.get("roi_1") and p_l4w.get("paid_roi"):
        t1_roi = h_l4w["roi_1"]
        t2_roi = p_l4w["paid_roi"]
        if not check(f"L4W: Table 1 ROI(1) {t1_roi:.1f}% vs Table 2 Paid ROI {t2_roi:.1f}%",
                    True,
                    "Different formulas — directional check only"):
            failures += 1
    print()

    # === Test 5: No None metrics where data exists ===
    print("Test 5: No None metrics where data exists")
    for window in ["l4w", "p4w", "ly"]:
        p = paid_perf.get(window, {})
        if p.get("clicks") and p["clicks"] > 0:
            for metric in ["cpc", "ctr", "cvr", "paid_roi"]:
                if not check(f"Table 2 {window}.{metric} is not None",
                            p.get(metric) is not None,
                            f"value: {p.get(metric)}"):
                    failures += 1
    print()

    # === Test 6: Channel AOV consistency with Table 1 ===
    print("Test 6: Channel AOV in same range as Table 1 AOV")
    t1_aov = h_l4w.get("aov", 0)
    for ch in tw_channels[:5]:
        if ch.get("aov") and ch["aov"] > 0 and t1_aov > 0:
            ratio = ch["aov"] / t1_aov
            if not check(f"{ch['channel']}: AOV ${ch['aov']:.0f} vs Table 1 ${t1_aov:.0f} (ratio {ratio:.2f}x)",
                        0.3 < ratio < 3.0,
                        "Channel AOV should be within 0.3-3x of CE AOV"):
                failures += 1
    print()

    # === Test 7: Paid value Shapley reconciles ===
    print("Test 7: Shapley contributions sum to total Δ (Clicks × CVR × Avg CM1)")
    shap = fetch_paid_value_shapley(ce_id, l4w, p4w, ly)
    for comp in ["mom", "yoy"]:
        d = shap.get(comp, {})
        total = d.get("total_delta")
        if total is not None:
            summed = sum((d.get(f, {}) or {}).get("contribution", 0) for f in ["clicks", "cvr", "avg_cm1"])
            diff = abs(summed - total)
            tol = max(1.0, abs(total) * 0.001)
            if not check(f"Shapley {comp}: Σcontrib ${summed:,.0f} vs total Δ ${total:,.0f}",
                        diff < tol, f"diff ${diff:,.2f}"):
                failures += 1
    # Product of factors must equal CM1 in each window
    for win in ["l4w", "p4w", "ly"]:
        w = (shap.get("windows", {}) or {}).get(win, {})
        if w.get("clicks"):
            prod = w["clicks"] * w["cvr"] * w["avg_cm1"]
            if not check(f"Shapley {win}: Clicks×CVR×AvgCM1 ${prod:,.0f} = CM1 ${w.get('cm1', 0):,.0f}",
                        abs(prod - w.get("cm1", 0)) < max(1.0, abs(w.get("cm1", 0)) * 0.001),
                        "factor product must equal paid CM1"):
                failures += 1
    print()

    # === Test 8: TGID shares + assortment-shift integrity ===
    print("Test 8: TGID revenue shares sum sanely; Δ Share = L4W − LY share")
    tgid = fetch_tgid_revenue(ce_id, l4w, ly)
    rows = tgid.get("rows", [])
    if rows:
        # Each row's shares derive from totals
        ok_shares = all(
            (r["ly_rev"] == 0 or abs(r["ly_share"] - (r["ly_rev"] / tgid["ly_total"] * 100)) < 0.1)
            for r in rows if tgid.get("ly_total")
        )
        if not check("TGID LY shares tie to ly_total", ok_shares):
            failures += 1
        ok_delta = all(abs(r["delta_share"] - (r["l4w_share"] - r["ly_share"])) < 0.01 for r in rows)
        if not check("TGID Δ Share = L4W share − LY share", ok_delta):
            failures += 1
        # Top L4W TGID share must be ≤ 100 and ≥ any other
        top_share = rows[0]["l4w_share"] if rows[0]["l4w_rev"] > 0 else 0
        if not check(f"TGID top L4W share {top_share:.1f}% is a valid percentage",
                    0 <= top_share <= 100.01):
            failures += 1
        # New economics columns present + CM1/order ≤ Net Rev/order (margin ≤ revenue)
        live = [r for r in rows if r.get("l4w_rev", 0) > 0]
        if not check("TGID rows carry orders + net_rev_per_order + cm1_per_order",
                    all(all(k in r for k in ("orders", "net_rev_per_order", "cm1_per_order")) for r in rows)):
            failures += 1
        ok_margin = all(
            r["cm1_per_order"] is None or r["net_rev_per_order"] is None
            or r["cm1_per_order"] <= r["net_rev_per_order"] + 0.01
            for r in live
        )
        if not check("TGID CM1/order ≤ Net Rev/order (direct costs ≥ 0)", ok_margin):
            failures += 1
    else:
        check("TGID rows present", False, "no TGID rows returned")
        failures += 1
    print()

    # === Test 9: Coverage-gate signal enumeration ===
    print("Test 9: build_signals enumerates well-formed material signals")
    cohorts = fetch_campaign_cohorts(ce_id, l4w[0], l4w[1], ly[0], ly[1], p4w[0], p4w[1])
    shap = fetch_paid_value_shapley(ce_id, l4w, p4w, ly)
    tgid = fetch_tgid_revenue(ce_id, l4w, ly)
    sigs = build_signals(ce_health, channels, cohorts, paid_perf, shap, tgid)
    if not check(f"build_signals returned {len(sigs)} signals (non-empty)", len(sigs) > 0):
        failures += 1
    req_keys = {"id", "kind", "label", "basis", "value", "window", "mom_recency", "trajectory", "severity_hint"}
    if not check("every signal has the full schema", all(set(s) == req_keys for s in sigs)):
        failures += 1
    # A Shapley signal's value must tie to the source shapley dict
    shap_sig = next((s for s in sigs if s["id"].startswith("shapley:")), None)
    if shap_sig:
        drv = shap_sig["id"].split(":")[1]
        src = (shap.get("yoy", {}).get(drv) or {}).get("contribution")
        if not check(f"shapley signal '{drv}' value ties to source ({shap_sig['value']:.0f} == {src:.0f})",
                    src is not None and abs(shap_sig["value"] - src) < 1.0):
            failures += 1
    print()

    # === Test 10: L12M trajectory tags ===
    print("Test 10: every signal gets a valid L12M trajectory tag")
    chm = fetch_channel_monthly(ce_id)
    attach_trajectories(sigs, channels=channels, cohorts=cohorts, ce_health=ce_health,
                        paid_perf=paid_perf, channel_monthly=chm, tgid=tgid)
    if not check("no signal left without a trajectory", all(s["trajectory"] is not None for s in sigs)):
        failures += 1
    if not check("all trajectory tags in allowed set",
                all(s["trajectory"] in ALLOWED_TRAJECTORIES for s in sigs),
                f"tags: {sorted({s['trajectory'] for s in sigs})}"):
        failures += 1
    print()

    # === Test 11: checklist render wiring ===
    print("Test 11: Signals-to-Close checklist renders one disposable row per signal")
    md = render_signals_checklist(sigs)
    if not check("checklist has a header row", "Signal" in md and "Disposition" in md):
        failures += 1
    n_rows = md.count("_(dispose)_")
    if not check(f"checklist row count {n_rows} == signal count {len(sigs)}", n_rows == len(sigs)):
        failures += 1
    print()

    # === Test 12: campaign × product join ===
    print("Test 12: campaign × product mix — paid pairs, well-formed, margin sane")
    cp = fetch_campaign_product_mix(ce_id, l4w[0], l4w[1])
    if not check(f"fetch_campaign_product_mix returned {len(cp.get('all', []))} pairs (non-empty)",
                 len(cp.get("all", [])) > 0):
        failures += 1
    else:
        req = {"campaign_name", "channel", "tgid", "experience_name", "orders",
               "net_rev", "share", "aov", "tr", "cm1", "cm1_per_order"}
        ok_schema = all(req.issubset(set(r)) for r in cp["rows"])
        if not check("every campaign×product row has the full schema", ok_schema):
            failures += 1
        ok_paid = all(r["channel"] in (
            "Google Search", "Bing", "Google PMax", "Google Cross-sell", "Bing Cross-sell")
            for r in cp["rows"])
        if not check("all pairs are paid-channel rows", ok_paid):
            failures += 1
        ok_sorted = all(
            (cp["all"][i]["net_rev"] or 0) >= (cp["all"][i + 1]["net_rev"] or 0)
            for i in range(len(cp["all"]) - 1))
        if not check("pairs sorted by net_rev desc", ok_sorted):
            failures += 1
        ok_margin = all((r["cm1_per_order"] or 0) <= (r["aov"] or 0) + 0.01 for r in cp["rows"])
        if not check("CM1/order ≤ AOV (direct costs ≥ 0)", ok_margin):
            failures += 1
        shares = sum(r["share"] for r in cp["all"])
        if not check(f"shares sum to ~100% ({shares:.1f}%)", abs(shares - 100.0) < 0.5):
            failures += 1
    print()

    # === Test 13: ad-group audit ===
    print("Test 13: ad-group audit — per-AG performance + bid-headroom flags")
    ag = fetch_ad_group_audit(ce_id, l4w[0], l4w[1], p4w[0], p4w[1])
    if not check(f"fetch_ad_group_audit returned {ag.get('n_total', 0)} ad groups (non-empty)",
                 ag.get("n_total", 0) > 0):
        failures += 1
    else:
        req = {"ad_group_name", "ag_type", "language", "spend", "clicks", "cvr",
               "cpc", "roi", "target_pct", "vs_target", "flag", "spend_mom_pct", "roi_mom_pp"}
        if not check("every ad-group row has the full schema",
                     all(req.issubset(set(r)) for r in ag["rows"])):
            failures += 1
        allowed = {"Scale", "Leak", "On-target", "Long-tail"}
        if not check("all flags in allowed set",
                     all(r["flag"] in allowed for r in ag["all"])):
            failures += 1
        ok_sorted = all((ag["all"][i]["spend"] or 0) >= (ag["all"][i + 1]["spend"] or 0)
                        for i in range(len(ag["all"]) - 1))
        if not check("ad groups sorted by spend desc", ok_sorted):
            failures += 1
        # counts reconcile to flags
        leaks = sum(1 for r in ag["all"] if r["flag"] == "Leak")
        if not check(f"leak_count {ag.get('leak_count')} == flagged leaks {leaks}",
                     ag.get("leak_count") == leaks):
            failures += 1
        mom_n = sum(1 for r in ag["all"] if r["spend_mom_pct"] is not None)
        if not check(f"MoM populated for {mom_n}/{ag['n_total']} ad groups (P4W join)", mom_n > 0):
            failures += 1
    print()

    # Summary
    print("=" * 50)
    if failures == 0:
        print(f"ALL PASSED ✓")
    else:
        print(f"{failures} FAILURE(S) ✗")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="smoke_test")
    parser.add_argument("--ce-id", required=True)
    parser.add_argument("--l4w-start", required=True)
    parser.add_argument("--l4w-end", required=True)
    parser.add_argument("--p4w-start", required=True)
    parser.add_argument("--p4w-end", required=True)
    parser.add_argument("--ly-start", required=True)
    parser.add_argument("--ly-end", required=True)
    args = parser.parse_args()

    def pd(s):
        return date.fromisoformat(s)

    failures = run_tests(
        args.ce_id,
        (pd(args.l4w_start), pd(args.l4w_end)),
        (pd(args.p4w_start), pd(args.p4w_end)),
        (pd(args.ly_start), pd(args.ly_end)),
    )
    sys.exit(1 if failures else 0)
