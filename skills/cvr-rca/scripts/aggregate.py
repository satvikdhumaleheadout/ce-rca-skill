"""
aggregate.py — Converts raw BQ JSON output into summary.json for Claude.

Claude only ever sees summary.json. It never sees raw rows.
All rate computation, Shapley math, mix decomp, and trend processing happens here.

Active pipeline stages (auto-run):
  stage0 — CE metadata + top page URL
  stage1 — base funnel, Shapley, MB/HO + paid/non-paid mix
  stage3 — daily pre/post trend (short window)
  stage7 — 90-day rolling trend + LY equivalent (seasonal context)

Demoted stages (reference-only SQL templates, not auto-run):
  stage2 — dimension cuts (device / language / page_type)
  stage4 — experience-level breakdown
  stage5 — price analysis
  stage6 — URL-level funnel
  Claude queries these directly when investigation hypotheses lead there.

Usage:
  python aggregate.py
    --stage0 ~/Documents/RCA skill/Test Runs/ce167_2024-04-01_2024-04-14/stage0.json
    --stage1 ~/Documents/RCA skill/Test Runs/ce167_2024-04-01_2024-04-14/stage1.json
    --stage3 ~/Documents/RCA skill/Test Runs/ce167_2024-04-01_2024-04-14/stage3.json
    --stage7 ~/Documents/RCA skill/Test Runs/ce167_2024-04-01_2024-04-14/stage7.json
    --ce_id 167
    --pre_start 2024-04-01 --pre_end 2024-04-07
    --post_start 2024-04-08 --post_end 2024-04-14
    --primary_mbho HO
    --output ~/Documents/RCA skill/Test Runs/ce167_2024-04-01_2024-04-14/summary.json
"""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def r(v, n=4):
    """Round to n decimal places, return None if value is None/NaN."""
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def safe_div(num, den, decimals=4):
    try:
        v = float(num) / float(den)
        return round(v, decimals)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def call_helpers(script_dir: Path, *args) -> dict:
    """Call helpers.py and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, str(script_dir / "helpers.py"), *args],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"helpers.py failed: {result.stderr}")
    return json.loads(result.stdout)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 0: CE metadata + top page URL
# ─────────────────────────────────────────────────────────────────────────────

def process_stage0(rows: list[dict]) -> dict:
    """
    Extract CE identity and top-trafficked page URL from Q0.

    Returns a flat dict that populates the report header:
      combined_entity_name  → displayed prominently in the title bar
      combined_entity_type  → sub-label (e.g. "City", "Attraction")
      market                → e.g. "EUR"
      country               → e.g. "France"
      top_page_url          → most-visited page URL in the post period (clickable link)
      top_url_users         → distinct users who visited that URL in the post period

    If Q0 returned no rows (CE not found or query error), returns safe fallbacks.
    """
    if not rows:
        return {
            "combined_entity_name": None,
            "combined_entity_type": None,
            "market":               None,
            "country":              None,
            "top_page_url":         None,
            "top_url_users":        None,
        }

    row = rows[0]  # Q0 returns a single row (LEFT JOIN top_url ON TRUE)
    return {
        "combined_entity_name": row.get("combined_entity_name") or None,
        "combined_entity_type": row.get("combined_entity_type") or None,
        "market":               row.get("market")               or None,
        "country":              row.get("country")              or None,
        "top_page_url":         row.get("top_page_url")         or None,
        "top_url_users":        int(row["top_url_users"]) if row.get("top_url_users") else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Funnel rates + Shapley + mix decomp
# ─────────────────────────────────────────────────────────────────────────────

def process_stage1(rows: list[dict], script_dir: Path, primary_mbho: str) -> dict:
    """Extract headline funnel rates, Shapley, MB/HO + channel mix."""

    def get_row(mb_ho, channel, period):
        for r_ in rows:
            if r_["mb_ho"] == mb_ho and r_["channel"] == channel and r_["period"] == period:
                return r_
        return None

    # CE-level rates from the ALL rows
    def rates(row) -> dict:
        if row is None:
            return {}
        lp  = int(row.get("users_lp") or 0)
        sel = int(row.get("users_select") or 0)
        chk = int(row.get("users_checkout") or 0)
        oa  = int(row.get("users_order_attempted") or 0)
        oc  = int(row.get("users_order_completed") or 0)
        return {
            "users_lp":               lp,
            "users_select":           sel,
            "users_checkout":         chk,
            "users_order_attempted":  oa,
            "users_order_completed":  oc,
            "lp2s": safe_div(sel, lp,  4),
            "s2c":  safe_div(chk, sel, 4),
            "c2o":  safe_div(oc,  chk, 4),
            "cvr":  safe_div(oc,  lp,  6),
        }

    pre_all  = rates(get_row("ALL", "ALL", "pre"))
    post_all = rates(get_row("ALL", "ALL", "post"))

    headline = {
        "pre":  pre_all,
        "post": post_all,
        "delta": {
            k: r(post_all.get(k, 0) - pre_all.get(k, 0), 6)
            for k in ("cvr", "lp2s", "s2c", "c2o", "users_lp")
        },
    }

    # Shapley
    shapley_result = None
    if all(pre_all.get(k) is not None and post_all.get(k) is not None
           for k in ("lp2s", "s2c", "c2o")):
        shapley_result = call_helpers(
            script_dir, "shapley",
            "--pre_lp2s",  str(pre_all["lp2s"]),
            "--pre_s2c",   str(pre_all["s2c"]),
            "--pre_c2o",   str(pre_all["c2o"]),
            "--post_lp2s", str(post_all["lp2s"]),
            "--post_s2c",  str(post_all["s2c"]),
            "--post_c2o",  str(post_all["c2o"]),
        )

    # C2O sub-decomp (uses ALL row, no extra query)
    c2o_sub = None
    if pre_all.get("users_checkout") and post_all.get("users_checkout"):
        c2o_sub = {
            "pre": {
                "c2a": safe_div(pre_all["users_order_attempted"], pre_all["users_checkout"]),
                "a2o": safe_div(pre_all["users_order_completed"], pre_all["users_order_attempted"]),
            },
            "post": {
                "c2a": safe_div(post_all["users_order_attempted"], post_all["users_checkout"]),
                "a2o": safe_div(post_all["users_order_completed"], post_all["users_order_attempted"]),
            },
        }
        if c2o_sub["pre"]["c2a"] and c2o_sub["post"]["c2a"]:
            c2o_sub["delta_c2a"] = r(c2o_sub["post"]["c2a"] - c2o_sub["pre"]["c2a"], 4)
            c2o_sub["delta_a2o"] = r(c2o_sub["post"]["a2o"] - c2o_sub["pre"]["a2o"], 4)

    # MB/HO mix (compute total LP per period for share)
    mbho_segments = sorted({row["mb_ho"] for row in rows if row["mb_ho"] != "ALL"})
    total_lp = {
        "pre":  sum(int(row.get("users_lp") or 0) for row in rows
                    if row["mb_ho"] != "ALL" and row["period"] == "pre"),
        "post": sum(int(row.get("users_lp") or 0) for row in rows
                    if row["mb_ho"] != "ALL" and row["period"] == "post"),
    }

    mbho_mix = []
    for seg in mbho_segments:
        pre_row  = get_row(seg, _any_channel(rows, seg, "pre"),  "pre")
        post_row = get_row(seg, _any_channel(rows, seg, "post"), "post")
        pre_lp   = sum(int(rr.get("users_lp") or 0) for rr in rows
                       if rr["mb_ho"] == seg and rr["period"] == "pre")
        post_lp  = sum(int(rr.get("users_lp") or 0) for rr in rows
                       if rr["mb_ho"] == seg and rr["period"] == "post")
        pre_oc   = sum(int(rr.get("users_order_completed") or 0) for rr in rows
                       if rr["mb_ho"] == seg and rr["period"] == "pre")
        post_oc  = sum(int(rr.get("users_order_completed") or 0) for rr in rows
                       if rr["mb_ho"] == seg and rr["period"] == "post")

        pre_share  = safe_div(pre_lp,  total_lp["pre"])
        post_share = safe_div(post_lp, total_lp["post"])
        pre_cvr    = safe_div(pre_oc,  pre_lp)
        post_cvr   = safe_div(post_oc, post_lp)

        mix_data = None
        if all(v is not None for v in (pre_share, post_share, pre_cvr, post_cvr)):
            mix_data = call_helpers(
                script_dir, "mix",
                "--segment",    seg,
                "--pre_share",  str(pre_share),
                "--post_share", str(post_share),
                "--pre_rate",   str(pre_cvr),
                "--post_rate",  str(post_cvr),
            )

        mbho_mix.append({
            "segment":   seg,
            "is_primary": seg == primary_mbho,
            "pre_lp":    pre_lp,
            "post_lp":   post_lp,
            "pre_share": pre_share,
            "post_share":post_share,
            "pre_cvr":   pre_cvr,
            "post_cvr":  post_cvr,
            "mix":       mix_data,
        })

    # Channel mix (within primary MB/HO)
    channel_segments = sorted({row["channel"] for row in rows
                                if row["mb_ho"] == primary_mbho and row["channel"] != "ALL"})
    total_ch_lp = {
        "pre":  sum(int(rr.get("users_lp") or 0) for rr in rows
                    if rr["mb_ho"] == primary_mbho and rr["channel"] != "ALL" and rr["period"] == "pre"),
        "post": sum(int(rr.get("users_lp") or 0) for rr in rows
                    if rr["mb_ho"] == primary_mbho and rr["channel"] != "ALL" and rr["period"] == "post"),
    }

    channel_mix = []
    for ch in channel_segments:
        pre_lp  = sum(int(rr.get("users_lp") or 0) for rr in rows
                      if rr["mb_ho"] == primary_mbho and rr["channel"] == ch and rr["period"] == "pre")
        post_lp = sum(int(rr.get("users_lp") or 0) for rr in rows
                      if rr["mb_ho"] == primary_mbho and rr["channel"] == ch and rr["period"] == "post")
        pre_oc  = sum(int(rr.get("users_order_completed") or 0) for rr in rows
                      if rr["mb_ho"] == primary_mbho and rr["channel"] == ch and rr["period"] == "pre")
        post_oc = sum(int(rr.get("users_order_completed") or 0) for rr in rows
                      if rr["mb_ho"] == primary_mbho and rr["channel"] == ch and rr["period"] == "post")

        pre_share  = safe_div(pre_lp,  total_ch_lp["pre"])
        post_share = safe_div(post_lp, total_ch_lp["post"])
        pre_cvr    = safe_div(pre_oc,  pre_lp)
        post_cvr   = safe_div(post_oc, post_lp)

        mix_data = None
        if all(v is not None for v in (pre_share, post_share, pre_cvr, post_cvr)):
            mix_data = call_helpers(
                script_dir, "mix",
                "--segment",    ch,
                "--pre_share",  str(pre_share),
                "--post_share", str(post_share),
                "--pre_rate",   str(pre_cvr),
                "--post_rate",  str(post_cvr),
            )

        channel_mix.append({
            "segment":    ch,
            "pre_lp":     pre_lp,
            "post_lp":    post_lp,
            "pre_share":  pre_share,
            "post_share": post_share,
            "pre_cvr":    pre_cvr,
            "post_cvr":   post_cvr,
            "mix":        mix_data,
        })

    # Mix dominance flags
    total_delta = abs(headline["delta"].get("cvr") or 0)
    mbho_mix_total = sum(abs(s["mix"]["mix_effect"]) for s in mbho_mix
                         if s.get("mix") and s["mix"].get("mix_effect") is not None)
    ch_mix_total   = sum(abs(s["mix"]["mix_effect"]) for s in channel_mix
                         if s.get("mix") and s["mix"].get("mix_effect") is not None)

    mix_dominance = {
        "mbho_mix_share":    r(safe_div(mbho_mix_total, total_delta), 3) if total_delta else 0,
        "channel_mix_share": r(safe_div(ch_mix_total,   total_delta), 3) if total_delta else 0,
        "is_dominant":       (mbho_mix_total / total_delta > 0.50) if total_delta else False,
    }

    return {
        "headline":       headline,
        "shapley":        shapley_result,
        "c2o_sub":        c2o_sub,
        "mbho_mix":       mbho_mix,
        "channel_mix":    channel_mix,
        "mix_dominance":  mix_dominance,
    }


def _any_channel(rows, mb_ho, period):
    """Return first channel found for this mb_ho/period (for lookup fallback)."""
    for row in rows:
        if row["mb_ho"] == mb_ho and row["period"] == period:
            return row["channel"]
    return "ALL"


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Dimension cuts → top-5 per dimension per step
# ─────────────────────────────────────────────────────────────────────────────

def process_stage2(rows: list[dict], significant_steps: list[str]) -> dict:
    """For each significant step × each dimension, return top 5 by |delta_rate|."""
    result = {}

    step_num_map = {
        "LP2S": ("users_select",         "users_lp"),
        "S2C":  ("users_checkout",       "users_select"),
        "C2O":  ("users_order_completed","users_checkout"),
    }

    dims = ["language", "page_type", "device"]

    for step in significant_steps:
        num_col, den_col = step_num_map[step]
        result[step] = {}

        for dim in dims:
            dim_rows = [rr for rr in rows if rr.get("dimension") == dim]

            # Pivot: {dim_value: {pre: {...}, post: {...}}}
            pivot: dict[str, dict] = {}
            for rr in dim_rows:
                val    = rr.get("dimension_value") or "(unknown)"
                period = rr.get("period")
                if period not in ("pre", "post"):
                    continue
                if val not in pivot:
                    pivot[val] = {}
                pivot[val][period] = rr

            rows_out = []
            for val, periods in pivot.items():
                pre_row  = periods.get("pre",  {})
                post_row = periods.get("post", {})

                pre_num  = int(pre_row.get(num_col)  or 0)
                pre_den  = int(pre_row.get(den_col)  or 0)
                post_num = int(post_row.get(num_col) or 0)
                post_den = int(post_row.get(den_col) or 0)

                pre_rate  = safe_div(pre_num,  pre_den)
                post_rate = safe_div(post_num, post_den)

                if pre_rate is None and post_rate is None:
                    continue

                delta = r((post_rate or 0) - (pre_rate or 0), 4)

                rows_out.append({
                    "value":      val,
                    "pre_users":  pre_den,
                    "post_users": post_den,
                    "pre_rate":   pre_rate,
                    "post_rate":  post_rate,
                    "delta":      delta,
                })

            # Top 5 by |delta|, only values with meaningful traffic (≥50 users)
            rows_out = [rr for rr in rows_out
                        if (rr["pre_users"] or 0) >= 50 or (rr["post_users"] or 0) >= 50]
            rows_out.sort(key=lambda rr: abs(rr["delta"] or 0), reverse=True)
            result[step][dim] = rows_out[:5]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4: Experience-level breakdown (S2C + C2O per individual experience)
# ─────────────────────────────────────────────────────────────────────────────

def process_stage4(rows: list[dict], significant_steps: list[str]) -> dict:
    """
    For each significant step in [S2C, C2O], return top experiences by |delta_rate|.
    LP2S is excluded — experience_id is only set after a user reaches the select page,
    so LP users are CE-level, not experience-level.
    """
    step_num_map = {
        "S2C": ("users_checkout",        "users_select"),
        "C2O": ("users_order_completed", "users_checkout"),
    }

    # Pivot by experience_id: {exp_id: {pre: row, post: row}}
    pivot: dict[str, dict] = {}
    for row in rows:
        exp_id   = row.get("experience_id") or "(unknown)"
        exp_name = row.get("experience_name") or exp_id
        period   = row.get("period")
        if period not in ("pre", "post"):
            continue
        if exp_id not in pivot:
            pivot[exp_id] = {"name": exp_name}
        pivot[exp_id][period] = row

    result = {}
    for step in significant_steps:
        if step not in step_num_map:
            continue  # LP2S not applicable at experience level
        num_col, den_col = step_num_map[step]
        rows_out = []

        for exp_id, periods in pivot.items():
            pre_row  = periods.get("pre",  {})
            post_row = periods.get("post", {})
            exp_name = periods.get("name", exp_id)

            pre_num  = int(pre_row.get(num_col)  or 0)
            pre_den  = int(pre_row.get(den_col)  or 0)
            post_num = int(post_row.get(num_col) or 0)
            post_den = int(post_row.get(den_col) or 0)

            pre_rate  = safe_div(pre_num,  pre_den)
            post_rate = safe_div(post_num, post_den)

            if pre_rate is None and post_rate is None:
                continue

            delta = r((post_rate or 0) - (pre_rate or 0), 4)

            rows_out.append({
                "experience_id":   exp_id,
                "experience_name": exp_name,
                "pre_users":       pre_den,
                "post_users":      post_den,
                "pre_rate":        pre_rate,
                "post_rate":       post_rate,
                "delta":           delta,
            })

        # Top 8 by |delta|, filter experiences with <50 users in either period
        rows_out = [rr for rr in rows_out
                    if (rr["pre_users"] or 0) >= 50 or (rr["post_users"] or 0) >= 50]
        rows_out.sort(key=lambda rr: abs(rr["delta"] or 0), reverse=True)
        result[step] = rows_out[:8]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5: LP2S price sensitivity (product_rankings_features)
# ─────────────────────────────────────────────────────────────────────────────

def process_stage5(rows: list[dict], stage4_rows: list[dict]) -> dict:
    """
    Price sensitivity analysis for LP2S from product_rankings_features.

    Mirrors the Hex Revenue RCA approach:
      - Traffic-weighted average final_price_usd per period (CE level)
      - Per-experience pre/post price to identify which products drove the change
      - Daily price trend (pre + post) for the chart

    Traffic weights = users_select per experience from stage4 (pre period only,
    as a stable denominator). This weights the CE-level price by how much traffic
    each experience actually attracted at the listing stage.

    If Q5 returned no rows (table unavailable or CE has no priced experiences),
    returns {"available": False} so render.py skips the price section gracefully.
    """
    if not rows:
        return {"available": False}

    # ── Build traffic weights from stage4 pre-period select users ──────────────
    traffic_weights: dict[str, int] = {}
    for row in stage4_rows:
        if str(row.get("period", "")).lower() == "pre":
            exp_id = str(row.get("experience_id") or "").strip()
            users  = int(row.get("users_select") or 0)
            if exp_id and users > 0:
                traffic_weights[exp_id] = traffic_weights.get(exp_id, 0) + users

    # ── Accumulate daily prices per experience/period ──────────────────────────
    # exp_period: {exp_id: {pre: [{final, original},...], post: [...], name: str}}
    exp_period: dict[str, dict] = {}
    daily_map:  dict[str, dict] = {}  # {date: {period, weighted_sum, orig_sum, weight_sum}}

    for row in rows:
        exp_id = str(row.get("experience_id") or "").strip()
        period = str(row.get("period") or "").lower()
        fp     = row.get("final_price_usd")
        op     = row.get("original_price_usd")
        date   = str(row.get("event_date") or "")

        if not exp_id or period not in ("pre", "post") or fp is None:
            continue
        fp = float(fp)
        op = float(op) if op is not None else fp

        # Per-experience accumulator
        if exp_id not in exp_period:
            exp_period[exp_id] = {
                "pre": [], "post": [],
                "name": str(row.get("experience_name") or exp_id),
            }
        exp_period[exp_id][period].append({"final": fp, "original": op})

        # Daily accumulator — weight by pre-period traffic (fixed weight)
        w = traffic_weights.get(exp_id, 1)
        if date:
            if date not in daily_map:
                daily_map[date] = {"period": period, "weighted_sum": 0.0,
                                   "orig_sum": 0.0, "weight_sum": 0}
            daily_map[date]["weighted_sum"] += fp * w
            daily_map[date]["orig_sum"]     += op * w
            daily_map[date]["weight_sum"]   += w

    # ── Per-experience price summary (need both periods) ───────────────────────
    exp_prices: dict[str, dict] = {}
    for exp_id, data in exp_period.items():
        pre_rows  = data["pre"]
        post_rows = data["post"]
        if not pre_rows or not post_rows:
            continue

        pre_final  = sum(d["final"]    for d in pre_rows)  / len(pre_rows)
        post_final = sum(d["final"]    for d in post_rows) / len(post_rows)
        pre_orig   = sum(d["original"] for d in pre_rows)  / len(pre_rows)
        post_orig  = sum(d["original"] for d in post_rows) / len(post_rows)
        delta_pct  = (post_final - pre_final) / pre_final if pre_final > 0 else None

        exp_prices[exp_id] = {
            "experience_id":          exp_id,
            "experience_name":        data["name"],
            "pre_final_price_usd":    r(pre_final,  2),
            "post_final_price_usd":   r(post_final, 2),
            "pre_original_price_usd": r(pre_orig,   2),
            "post_original_price_usd":r(post_orig,  2),
            "delta_pct":              r(delta_pct,  4),
            "select_users":           traffic_weights.get(exp_id, 0),
        }

    if not exp_prices:
        return {"available": False}

    # ── CE-level traffic-weighted average price ────────────────────────────────
    w_pre_sum = w_post_sum = total_w = 0.0
    for exp_id, ep in exp_prices.items():
        w = float(traffic_weights.get(exp_id, 0)) or 1.0
        w_pre_sum  += ep["pre_final_price_usd"]  * w
        w_post_sum += ep["post_final_price_usd"] * w
        total_w    += w

    pre_avg  = w_pre_sum  / total_w if total_w > 0 else None
    post_avg = w_post_sum / total_w if total_w > 0 else None
    delta_pct = ((post_avg - pre_avg) / pre_avg
                 if pre_avg and pre_avg > 0 else None)

    # ── Daily trend series ─────────────────────────────────────────────────────
    daily_trend = []
    for date in sorted(daily_map):
        d  = daily_map[date]
        wt = d["weight_sum"]
        daily_trend.append({
            "date":                   date,
            "period":                 d["period"],
            "avg_final_price_usd":    r(d["weighted_sum"] / wt if wt > 0 else None, 2),
            "avg_original_price_usd": r(d["orig_sum"]     / wt if wt > 0 else None, 2),
        })

    # ── Top experiences sorted by |delta_pct| (most changed first) ────────────
    exp_list = sorted(
        exp_prices.values(),
        key=lambda ep: abs(ep.get("delta_pct") or 0),
        reverse=True,
    )[:8]

    return {
        "available":          True,
        "pre_avg_price_usd":  r(pre_avg,   2),
        "post_avg_price_usd": r(post_avg,  2),
        "delta_pct":          r(delta_pct, 4),
        "daily_trend":        daily_trend,
        "experiences":        exp_list,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stage 6: URL-level funnel breakdown
# ─────────────────────────────────────────────────────────────────────────────

def process_stage6(rows: list[dict], significant_steps: list[str]) -> dict:
    """
    Pivot the URL-level funnel data into a structured list for the url_table component.

    For each URL we want:
      - Pre and post user counts + funnel rates for LP2S, S2C, C2O
      - An `anomalies` list flagging steps where the rate dropped substantially vs pre
        (≥15% relative decline AND ≥3pp absolute) — so Claude can call them out

    The list is sorted by pre_users_lp descending (same as the BQ ORDER BY) so the
    report always shows the highest-traffic URLs first.

    If Q6 returned no rows (PRIMARY_MBHO='ALL' edge case or data gap), returns
    {"available": False} and render.py will skip the url_table gracefully.
    """
    if not rows:
        return {"available": False}

    # Anomaly thresholds — a rate is "anomalously low" if both are true:
    RELATIVE_DROP_THRESHOLD = 0.15   # 15% relative drop (post/pre − 1 ≤ −0.15)
    ABSOLUTE_DROP_THRESHOLD = 0.03   # 3 percentage-point absolute drop

    step_rate_map = {
        "LP2S": "lp2s_rate",
        "S2C":  "s2c_rate",
        "C2O":  "c2o_rate",
    }

    # Pivot by (page_url, page_type, page_sub_type)
    pivot: dict[tuple, dict] = {}
    for row in rows:
        key = (
            row.get("page_url")      or "",
            row.get("page_type")     or "",
            row.get("page_sub_type") or "",
        )
        period = row.get("period")
        if period not in ("pre", "post"):
            continue
        if key not in pivot:
            pivot[key] = {
                "page_url":      key[0],
                "page_type":     key[1],
                "page_sub_type": key[2] if key[2] else None,
                "pre_users_lp":  int(row.get("pre_users_lp") or 0),  # pre_users_lp is same on both rows
            }
        pivot[key][period] = row

    url_rows = []
    for key, data in pivot.items():
        pre_row  = data.get("pre",  {})
        post_row = data.get("post", {})

        # Build per-step metrics
        steps_data = {}
        anomalies  = []
        for step in ["LP2S", "S2C", "C2O"]:
            rate_col = step_rate_map[step]
            num_col  = {"LP2S": "users_select", "S2C": "users_checkout", "C2O": "users_order_completed"}[step]
            den_col  = {"LP2S": "users_lp",     "S2C": "users_select",   "C2O": "users_checkout"}[step]

            pre_num  = int(pre_row.get(num_col)  or 0)
            pre_den  = int(pre_row.get(den_col)  or 0)
            post_num = int(post_row.get(num_col) or 0)
            post_den = int(post_row.get(den_col) or 0)

            pre_rate  = r(float(pre_row.get(rate_col))  if pre_row.get(rate_col)  is not None else safe_div(pre_num,  pre_den),  4)
            post_rate = r(float(post_row.get(rate_col)) if post_row.get(rate_col) is not None else safe_div(post_num, post_den), 4)

            delta_abs = r((post_rate or 0) - (pre_rate or 0), 4) if post_rate is not None and pre_rate is not None else None
            delta_rel = r((post_rate / pre_rate) - 1, 4) if pre_rate and pre_rate > 0 and post_rate is not None else None

            steps_data[step] = {
                "pre_users":  pre_den,
                "post_users": post_den,
                "pre_rate":   pre_rate,
                "post_rate":  post_rate,
                "delta_abs":  delta_abs,
                "delta_rel":  delta_rel,
            }

            # Flag anomaly if this is a significant step and the drop is substantial
            if step in significant_steps:
                if (delta_rel is not None and delta_rel <= -RELATIVE_DROP_THRESHOLD
                        and delta_abs is not None and delta_abs <= -ABSOLUTE_DROP_THRESHOLD):
                    anomalies.append(step)

        url_rows.append({
            "page_url":      data["page_url"],
            "page_type":     data["page_type"],
            "page_sub_type": data["page_sub_type"],
            "pre_users_lp":  data.get("pre_users_lp") or int(pre_row.get("users_lp") or 0),
            "post_users_lp": int(post_row.get("users_lp") or 0),
            "steps":         steps_data,
            "anomalies":     anomalies,  # list of step names with significant drops
        })

    if not url_rows:
        return {"available": False}

    # Sort by pre-period LP traffic (highest first)
    url_rows.sort(key=lambda rr: rr["pre_users_lp"], reverse=True)

    return {
        "available": True,
        "urls":      url_rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Daily trend
# ─────────────────────────────────────────────────────────────────────────────

def process_stage3(rows: list[dict]) -> dict:
    """Return pre/post daily series for LP2S, S2C, C2O."""
    series: dict[str, dict] = {"pre": [], "post": []}
    for row in sorted(rows, key=lambda rr: (rr.get("period",""), str(rr.get("event_date","")))):
        period = row.get("period")
        if period not in ("pre", "post"):
            continue
        series[period].append({
            "date":      str(row.get("event_date", "")),
            "lp2s_rate": r(row.get("lp2s_rate"), 4),
            "s2c_rate":  r(row.get("s2c_rate"),  4),
            "c2o_rate":  r(row.get("c2o_rate"),  4),
            "users_lp":  int(row.get("users_lp") or 0),
        })
    return series


# ─────────────────────────────────────────────────────────────────────────────
# Stage 7: 90-day rolling trend + last-year equivalent
# ─────────────────────────────────────────────────────────────────────────────

def process_stage7(rows: list[dict], pre_start: str, pre_end: str,
                   post_start: str, post_end: str) -> dict:
    """
    90-day rolling trend + LY overlay for seasonal context.

    Produces three analytical outputs:
      current_delta_cvr    — avg(post CVR) − avg(pre CVR) for current year
      ly_delta_cvr         — same delta for LY-equivalent window
      structural_delta_cvr — current_delta − ly_delta
        Negative = structural deterioration beyond seasonal pattern.
        Near-zero = drop is consistent with last year's seasonal movement.

      pre_period_healthy   — True unless the pre-window avg CVR is more than
        5% below the preceding 60-day trend, which would mean Shapley
        understates the true structural change (pre was already degraded).

    The series list contains both 'current' and 'ly' rows, sorted by date.
    LY dates are already shifted +364 days in SQL so they plot on the same
    x-axis as current year.
    """
    from datetime import datetime, timedelta

    if not rows:
        return {"available": False}

    current = sorted(
        [rr for rr in rows if rr.get("series") == "current"],
        key=lambda rr: str(rr.get("event_date", "")),
    )
    ly = sorted(
        [rr for rr in rows if rr.get("series") == "ly"],
        key=lambda rr: str(rr.get("event_date", "")),
    )

    def avg_metric(row_list, key):
        vals = [float(rr[key]) for rr in row_list if rr.get(key) is not None]
        return round(sum(vals) / len(vals), 6) if vals else None

    # Pre/post subsets within the current 90-day series
    pre_rows  = [rr for rr in current if pre_start  <= str(rr.get("event_date", "")) <= pre_end]
    post_rows = [rr for rr in current if post_start <= str(rr.get("event_date", "")) <= post_end]

    # LY rows aligned to same calendar dates (dates shifted +364 in SQL)
    ly_pre  = [rr for rr in ly if pre_start  <= str(rr.get("event_date", "")) <= pre_end]
    ly_post = [rr for rr in ly if post_start <= str(rr.get("event_date", "")) <= post_end]

    cur_pre_cvr  = avg_metric(pre_rows,  "cvr")
    cur_post_cvr = avg_metric(post_rows, "cvr")
    ly_pre_cvr   = avg_metric(ly_pre,   "cvr")
    ly_post_cvr  = avg_metric(ly_post,  "cvr")

    cur_delta  = r((cur_post_cvr - cur_pre_cvr), 6) if (cur_post_cvr is not None and cur_pre_cvr is not None) else None
    ly_delta   = r((ly_post_cvr  - ly_pre_cvr),  6) if (ly_post_cvr  is not None and ly_pre_cvr  is not None) else None
    structural = r((cur_delta - ly_delta), 6) if (cur_delta is not None and ly_delta is not None) else None

    # Pre-period health: compare pre-window avg to the 60 days before pre_start
    pre_period_healthy = True
    try:
        pre_start_dt   = datetime.strptime(pre_start, "%Y-%m-%d")
        lb_start       = (pre_start_dt - timedelta(days=60)).strftime("%Y-%m-%d")
        lb_end         = (pre_start_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        lookback_rows  = [rr for rr in current if lb_start <= str(rr.get("event_date", "")) <= lb_end]
        lookback_cvr   = avg_metric(lookback_rows, "cvr")
        if lookback_cvr and cur_pre_cvr:
            pre_period_healthy = cur_pre_cvr >= lookback_cvr * 0.95
    except (ValueError, TypeError):
        pass

    series_out = []
    for rr in current + ly:
        series_out.append({
            "date":      str(rr.get("event_date", "")),
            "series":    rr.get("series"),
            "cvr":       r(rr.get("cvr"),       6),
            "lp2s_rate": r(rr.get("lp2s_rate"), 4),
            "s2c_rate":  r(rr.get("s2c_rate"),  4),
            "c2o_rate":  r(rr.get("c2o_rate"),  4),
            "users_lp":  int(rr.get("users_lp") or 0),
        })
    series_out.sort(key=lambda rr: (rr["date"], rr["series"]))

    return {
        "available":            True,
        "window_days":          90,
        "current_delta_cvr":    cur_delta,
        "ly_delta_cvr":         ly_delta,
        "structural_delta_cvr": structural,
        "pre_period_healthy":   pre_period_healthy,
        "series":               series_out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage0",        required=False, default=None)
    p.add_argument("--stage1",        required=True)
    p.add_argument("--stage3",        required=True)
    p.add_argument("--stage7",        required=False, default=None)
    p.add_argument("--ce_id",         required=True, type=int)
    p.add_argument("--pre_start",     required=True)
    p.add_argument("--pre_end",       required=True)
    p.add_argument("--post_start",    required=True)
    p.add_argument("--post_end",      required=True)
    p.add_argument("--primary_mbho",  required=True)
    p.add_argument("--output",        required=True)
    args = p.parse_args()

    script_dir = Path(__file__).parent

    stage0 = json.loads(Path(args.stage0).read_text()) if args.stage0 else []
    stage1 = json.loads(Path(args.stage1).read_text())
    stage3 = json.loads(Path(args.stage3).read_text())
    stage7 = json.loads(Path(args.stage7).read_text()) if args.stage7 else []

    # Stage 0: CE identity (populates report header)
    ce_meta = process_stage0(stage0)

    # Stage 1: funnel rates, Shapley, mix decomp
    s1 = process_stage1(stage1, script_dir, args.primary_mbho)

    sig_steps = (s1.get("shapley") or {}).get("significant_steps", [])
    if not sig_steps:
        sig_steps = ["LP2S", "S2C", "C2O"]

    # Stage 3: daily pre/post trend (short window, for sudden-vs-gradual Q3)
    trend = process_stage3(stage3)

    # Stage 7: 90-day rolling trend + LY overlay (seasonal context)
    trend_context = process_stage7(
        stage7,
        args.pre_start, args.pre_end,
        args.post_start, args.post_end,
    )

    summary = {
        "meta": {
            "ce_id":                 args.ce_id,
            "combined_entity_name":  ce_meta.get("combined_entity_name"),
            "combined_entity_type":  ce_meta.get("combined_entity_type"),
            "market":                ce_meta.get("market"),
            "country":               ce_meta.get("country"),
            "top_page_url":          ce_meta.get("top_page_url"),
            "top_url_users":         ce_meta.get("top_url_users"),
            "pre_period":            f"{args.pre_start} to {args.pre_end}",
            "post_period":           f"{args.post_start} to {args.post_end}",
            "primary_mbho":          args.primary_mbho,
        },
        "headline":          s1["headline"],
        "shapley":           s1["shapley"],
        "c2o_sub":           s1["c2o_sub"],
        "mbho_mix":          s1["mbho_mix"],
        "channel_mix":       s1["channel_mix"],
        "mix_dominance":     s1["mix_dominance"],
        "significant_steps": sig_steps,
        "trend":             trend,
        "trend_context":     trend_context,
    }

    Path(args.output).write_text(json.dumps(summary, indent=2))
    print(f"summary.json written → {args.output}")
    ce_name = ce_meta.get("combined_entity_name") or "(unknown CE)"
    print(f"CE: {ce_name} (ID {args.ce_id})")
    print(f"Significant steps: {sig_steps}")
    print(f"Mix dominant: {s1['mix_dominance']['is_dominant']}")
    if trend_context.get("available"):
        sc = trend_context.get("structural_delta_cvr")
        healthy = trend_context.get("pre_period_healthy")
        print(f"Structural delta CVR: {sc}  |  Pre-period healthy: {healthy}")


if __name__ == "__main__":
    main()
