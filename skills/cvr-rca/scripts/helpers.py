"""
CVR-RCA math helpers — called by Claude via Bash tool.

Claude cannot reliably do exact floating-point Shapley arithmetic across
6 permutations, so it delegates the calculation here and reads back JSON.

Usage
-----
python helpers.py shapley \
  --pre_lp2s 0.35 --pre_s2c 0.40 --pre_c2o 0.30 \
  --post_lp2s 0.29 --post_s2c 0.38 --post_c2o 0.28

python helpers.py mix \
  --segment "Mobile" \
  --pre_share 0.60 --post_share 0.72 \
  --pre_rate 0.042 --post_rate 0.031

Outputs JSON to stdout. Claude reads and interprets the result.
"""

import argparse
import json
import sys
from itertools import permutations
from math import factorial


def shapley(pre_lp2s, pre_s2c, pre_c2o, post_lp2s, post_s2c, post_c2o):
    """
    3-factor Shapley for CVR = LP2S × S2C × C2O.
    Guarantees shapley_LP2S + shapley_S2C + shapley_C2O == post_cvr - pre_cvr exactly.
    """
    pre  = {"LP2S": pre_lp2s,  "S2C": pre_s2c,  "C2O": pre_c2o}
    post = {"LP2S": post_lp2s, "S2C": post_s2c, "C2O": post_c2o}
    factors = ["LP2S", "S2C", "C2O"]
    sv = {f: 0.0 for f in factors}

    def cvr(r):
        return r["LP2S"] * r["S2C"] * r["C2O"]

    for perm in permutations(factors):
        for i, factor in enumerate(perm):
            with_f    = {f: (post[f] if j <= i else pre[f]) for j, f in enumerate(perm)}
            without_f = {f: (post[f] if j <  i else pre[f]) for j, f in enumerate(perm)}
            sv[factor] += cvr(with_f) - cvr(without_f)

    for f in factors:
        sv[f] /= factorial(3)

    pre_cvr  = cvr(pre)
    post_cvr = cvr(post)
    total_delta = post_cvr - pre_cvr

    result = {
        "pre_cvr":     round(pre_cvr,  6),
        "post_cvr":    round(post_cvr, 6),
        "total_delta": round(total_delta, 6),
        "shapley": {f: round(sv[f], 6) for f in factors},
        "pct_contribution": {
            f: round(sv[f] / total_delta, 4) if total_delta != 0 else 0
            for f in factors
        },
        "significant_steps": [
            f for f in factors
            if total_delta != 0 and abs(sv[f] / total_delta) >= 0.30
        ],
        "check_sum_matches": round(sum(sv.values()) - total_delta, 10) == 0,
    }
    return result


def mix(segment, pre_share, post_share, pre_rate, post_rate):
    """
    Mix-effect decomposition for one segment at one funnel step.
    mix + conversion + interaction == total contribution of this segment.
    """
    d_share = post_share - pre_share
    d_rate  = post_rate  - pre_rate

    mix_effect          = d_share * pre_rate
    conversion_effect   = pre_share * d_rate
    interaction_effect  = d_share * d_rate
    total_effect        = mix_effect + conversion_effect + interaction_effect

    return {
        "segment":            segment,
        "pre_share":          round(pre_share, 4),
        "post_share":         round(post_share, 4),
        "delta_share":        round(d_share, 4),
        "pre_rate":           round(pre_rate, 6),
        "post_rate":          round(post_rate, 6),
        "delta_rate":         round(d_rate, 6),
        "mix_effect":         round(mix_effect, 6),
        "conversion_effect":  round(conversion_effect, 6),
        "interaction_effect": round(interaction_effect, 6),
        "total_effect":       round(total_effect, 6),
        "dominant_driver":    (
            "mix"        if abs(mix_effect) >= abs(conversion_effect) else "conversion"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    # shapley sub-command
    sp = sub.add_parser("shapley")
    for period in ("pre", "post"):
        for step in ("lp2s", "s2c", "c2o"):
            sp.add_argument(f"--{period}_{step}", type=float, required=True)

    # mix sub-command
    mp = sub.add_parser("mix")
    mp.add_argument("--segment",    type=str,   required=True)
    mp.add_argument("--pre_share",  type=float, required=True)
    mp.add_argument("--post_share", type=float, required=True)
    mp.add_argument("--pre_rate",   type=float, required=True)
    mp.add_argument("--post_rate",  type=float, required=True)

    args = parser.parse_args()

    if args.cmd == "shapley":
        result = shapley(
            args.pre_lp2s,  args.pre_s2c,  args.pre_c2o,
            args.post_lp2s, args.post_s2c, args.post_c2o,
        )
    elif args.cmd == "mix":
        result = mix(
            args.segment,
            args.pre_share, args.post_share,
            args.pre_rate,  args.post_rate,
        )
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
