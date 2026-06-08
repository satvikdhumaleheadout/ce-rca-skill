"""
CLI for perf-audit v6.1.

Two subcommands:
    python3 perf_audit.py data <command>   — fetch raw BQ data as JSON
    python3 perf_audit.py render ...        — fetch data + render markdown skeleton
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional


# =============================================================================
# DATA SUBCOMMAND — raw BQ queries as JSON
# =============================================================================

def build_data_parser():
    # type: () -> argparse.ArgumentParser
    """CLI for individual data queries. Used by SKILL.md during skill execution."""
    parser = argparse.ArgumentParser(
        prog="perf_audit data",
        description="Fetch perf audit data from BQ. Returns JSON to stdout.",
    )
    sub = parser.add_subparsers(dest="command", help="Data command")

    def add_3w_dates(p):
        p.add_argument("--ce-id", required=True, help="Combined entity ID")
        p.add_argument("--l4w-start", required=True, help="L4W start (YYYY-MM-DD)")
        p.add_argument("--l4w-end", required=True, help="L4W end (YYYY-MM-DD)")
        p.add_argument("--p4w-start", required=True, help="P4W start (YYYY-MM-DD)")
        p.add_argument("--p4w-end", required=True, help="P4W end (YYYY-MM-DD)")
        p.add_argument("--ly-start", required=True, help="LY start (YYYY-MM-DD)")
        p.add_argument("--ly-end", required=True, help="LY end (YYYY-MM-DD)")

    def add_single_dates(p):
        p.add_argument("--ce-id", required=True, help="Combined entity ID")
        p.add_argument("--start", required=True, help="Start (YYYY-MM-DD)")
        p.add_argument("--end", required=True, help="End (YYYY-MM-DD)")

    p1 = sub.add_parser("ce-health", help="Table 1: CE Health from combined_entity_stats")
    add_3w_dates(p1)

    p2 = sub.add_parser("paid-performance", help="Table 2: Paid Performance from ads_campaign_stats")
    add_3w_dates(p2)

    p3 = sub.add_parser("channel-breakdown", help="Table 3: Channel Breakdown (revenue + paid metrics)")
    add_3w_dates(p3)

    p4 = sub.add_parser("cohorts", help="Section 4a: Campaign cohorts by language")
    add_3w_dates(p4)

    p5 = sub.add_parser("customer-country", help="Customer country distribution from fct_orders")
    add_single_dates(p5)

    p6 = sub.add_parser("geo-coverage", help="Geographic ad coverage from google_ads_ad_group_geo_stats")
    p6.add_argument("--ce-id", required=True)
    p6.add_argument("--l4w-start", required=True)
    p6.add_argument("--l4w-end", required=True)
    p6.add_argument("--ly-start", required=True)
    p6.add_argument("--ly-end", required=True)

    p7 = sub.add_parser("budget", help="Budget + bidding status per campaign")
    add_single_dates(p7)

    p8 = sub.add_parser("benchmarks", help="Market benchmarks (median SIS, CPC, CTR, CVR)")
    p8.add_argument("--ce-id", required=True)
    p8.add_argument("--market", required=True, help="Market name (e.g., 'North America')")
    p8.add_argument("--l4w-start", required=True)
    p8.add_argument("--l4w-end", required=True)
    p8.add_argument("--ly-start", required=True)
    p8.add_argument("--ly-end", required=True)

    return parser


def data_main(argv=None):
    # type: (Optional[List[str]]) -> None
    """Entry point for `perf_audit.py data <command>` subcommand."""
    import json
    from datetime import date as d

    from engine.sources.bq import (
        fetch_ce_health_3w,
        fetch_paid_performance_3w,
        fetch_channel_breakdown,
        fetch_campaign_cohorts,
        fetch_customer_country_distribution,
        fetch_geo_coverage_3w,
        fetch_budget_bidding,
        fetch_market_benchmarks,
    )

    parser = build_data_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    def pd(s):
        return d.fromisoformat(s)

    cmd = args.command
    result = None

    if cmd == "ce-health":
        result = fetch_ce_health_3w(
            args.ce_id,
            (pd(args.l4w_start), pd(args.l4w_end)),
            (pd(args.p4w_start), pd(args.p4w_end)),
            (pd(args.ly_start), pd(args.ly_end)),
        )
    elif cmd == "paid-performance":
        result = fetch_paid_performance_3w(
            args.ce_id,
            (pd(args.l4w_start), pd(args.l4w_end)),
            (pd(args.p4w_start), pd(args.p4w_end)),
            (pd(args.ly_start), pd(args.ly_end)),
        )
    elif cmd == "channel-breakdown":
        result = fetch_channel_breakdown(
            args.ce_id,
            pd(args.l4w_start), pd(args.l4w_end),
            pd(args.ly_start), pd(args.ly_end),
            pd(args.p4w_start), pd(args.p4w_end),
        )
    elif cmd == "cohorts":
        result = fetch_campaign_cohorts(
            args.ce_id,
            pd(args.l4w_start), pd(args.l4w_end),
            pd(args.ly_start), pd(args.ly_end),
            pd(args.p4w_start), pd(args.p4w_end),
        )
    elif cmd == "customer-country":
        result = fetch_customer_country_distribution(
            args.ce_id,
            pd(args.start), pd(args.end),
        )
    elif cmd == "geo-coverage":
        result = fetch_geo_coverage_3w(
            args.ce_id,
            (pd(args.l4w_start), pd(args.l4w_end)),
            (pd(args.ly_start), pd(args.ly_end)),
        )
    elif cmd == "budget":
        result = fetch_budget_bidding(
            args.ce_id,
            pd(args.start), pd(args.end),
        )
    elif cmd == "benchmarks":
        result = fetch_market_benchmarks(
            args.market,
            int(args.ce_id),
            pd(args.l4w_start), pd(args.l4w_end),
            pd(args.ly_start), pd(args.ly_end),
        )
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, default=str, indent=2))


# =============================================================================
# RENDER SUBCOMMAND — produces markdown skeleton (v6.1)
# =============================================================================

def render_main(argv=None):
    # type: (Optional[List[str]]) -> None
    """Entry point for `perf_audit.py render`. Fetches data + renders skeleton."""
    from datetime import date as d

    from engine.sources.bq import (
        fetch_ce_health_3w,
        fetch_paid_performance_3w,
        fetch_channel_breakdown,
        fetch_campaign_cohorts,
        fetch_customer_country_distribution,
        fetch_geo_coverage_3w,
        fetch_budget_bidding,
        fetch_landing_page_performance,
        fetch_campaign_targeting,
        fetch_ad_group_performance,
    )
    from engine.render.audit_skeleton import render_audit

    parser = argparse.ArgumentParser(prog="perf_audit render")
    parser.add_argument("--ce-id", required=True)
    parser.add_argument("--ce-name", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--lp-url", default="")
    parser.add_argument("--l4w-start", required=True)
    parser.add_argument("--l4w-end", required=True)
    parser.add_argument("--p4w-start", required=True)
    parser.add_argument("--p4w-end", required=True)
    parser.add_argument("--ly-start", required=True)
    parser.add_argument("--ly-end", required=True)
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args(argv)

    def pd(s):
        return d.fromisoformat(s)

    ce_id = args.ce_id
    l4w = (pd(args.l4w_start), pd(args.l4w_end))
    p4w = (pd(args.p4w_start), pd(args.p4w_end))
    ly = (pd(args.ly_start), pd(args.ly_end))

    sys.stderr.write("1. Fetching data from BigQuery...\n")
    sys.stderr.flush()

    ce_health = fetch_ce_health_3w(ce_id, l4w, p4w, ly)
    paid_perf = fetch_paid_performance_3w(ce_id, l4w, p4w, ly)
    channels = fetch_channel_breakdown(
        ce_id, l4w[0], l4w[1], ly[0], ly[1], p4w[0], p4w[1])
    cohorts = fetch_campaign_cohorts(
        ce_id, l4w[0], l4w[1], ly[0], ly[1], p4w[0], p4w[1])
    budget = fetch_budget_bidding(ce_id, l4w[0], l4w[1])
    geo = fetch_geo_coverage_3w(ce_id, l4w, ly)
    customers = fetch_customer_country_distribution(ce_id, l4w[0], l4w[1])
    customers_ly = fetch_customer_country_distribution(ce_id, ly[0], ly[1])
    landing_pages = fetch_landing_page_performance(
        ce_id, l4w[0], l4w[1], ly[0], ly[1])
    targeting = fetch_campaign_targeting(ce_id)
    ad_groups = fetch_ad_group_performance(ce_id, l4w[0], l4w[1])

    sys.stderr.write("2. Rendering skeleton...\n")
    sys.stderr.flush()

    output = render_audit(
        ce_name=args.ce_name,
        market=args.market,
        today=d.today().isoformat(),
        l4w=(args.l4w_start, args.l4w_end),
        p4w=(args.p4w_start, args.p4w_end),
        ly=(args.ly_start, args.ly_end),
        lp_url=args.lp_url,
        ce_health=ce_health,
        paid_perf=paid_perf,
        channels=channels,
        cohorts=cohorts,
        budget=budget,
        geo=geo,
        customers=customers,
        customers_ly=customers_ly,
        landing_pages=landing_pages,
        targeting=targeting,
        ad_groups=ad_groups,
    )

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(output)
        sys.stderr.write("3. Output -> %s\n" % args.output)
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
