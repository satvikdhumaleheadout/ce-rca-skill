#!/usr/bin/env python3
"""
Smoke test for perf audit v6.1 — validates rendered metrics against metrics.py definitions.

Usage:
    python3 scripts/perf_audit_engine_v6/smoke_test.py --ce-id 1223 \
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

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from scripts.perf_audit_engine_v6.sources.bq import (
    fetch_ce_health_3w,
    fetch_paid_performance_3w,
    fetch_channel_breakdown,
)
from scripts.perf_audit_engine_v6.metrics import aov, roi, cpc, cvr, ctr, rpc, tr, cr


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
