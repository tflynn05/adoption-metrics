#!/usr/bin/env python3
"""Generate a synthetic 90-day platform rollout event log.

Simulates five impacted groups adopting a new platform at different rates.
One group (configurable) stalls: its users log in but keep doing the real
work on the legacy path, and its managers do not coach. This is the pattern
the analysis is meant to catch by week four.

Output: data/events.csv (one row per user-day with any activity),
        data/users.csv  (one row per user with group, access date, manager)
        data/managers.csv (manager coaching touchpoints by week)

No real data. Every name is a group label, every number is drawn from a
distribution described in the README.
"""
import argparse
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

CORE_ACTIONS = ["author_action", "approve_item", "deploy_item", "review_results"]

# Each group's adoption profile. plateau = share of users who become regular
# users; ramp_weeks = how fast they get there; migrate = share of real work
# that moves to the new path by day 90; override = share of recommendations
# overridden at steady state; coaching = share of managers who coach weekly.
GROUPS = {
    "channel_managers":   dict(n=60, plateau=0.80, ramp_weeks=6,  migrate=0.85, override=0.15, coaching=0.70),
    "campaign_ops":       dict(n=40, plateau=0.90, ramp_weeks=4,  migrate=0.92, override=0.05, coaching=0.75),
    "analysts":           dict(n=30, plateau=0.75, ramp_weeks=8,  migrate=0.70, override=0.10, coaching=0.60),
    "lob_marketing_leads": dict(n=20, plateau=0.70, ramp_weeks=5, migrate=0.80, override=0.10, coaching=0.65),
    "compliance_approvers": dict(n=25, plateau=0.85, ramp_weeks=5, migrate=0.88, override=0.08, coaching=0.70),
}

STALL_PROFILE = dict(plateau=0.65, ramp_weeks=5, migrate=0.35, override=0.45, coaching=0.25)


def logistic(day, plateau, ramp_weeks):
    """Share of the group active on a given day, S-curve to plateau."""
    mid = ramp_weeks * 7 / 2
    k = 8 / (ramp_weeks * 7)
    return plateau / (1 + np.exp(-k * (day - mid)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--stall", default="channel_managers", choices=list(GROUPS) + ["none"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--start", default="2026-01-05")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)
    start = date.fromisoformat(args.start)

    groups = {g: dict(p) for g, p in GROUPS.items()}
    if args.stall != "none":
        groups[args.stall].update(STALL_PROFILE)

    users, events, coaching = [], [], []
    uid = 0
    for g, p in groups.items():
        n_managers = max(2, p["n"] // 8)
        managers = [f"{g}_mgr_{i+1}" for i in range(n_managers)]
        for i in range(p["n"]):
            uid += 1
            # Access is granted in two batches: day 0 and day 7
            access_day = 0 if i < p["n"] * 0.6 else 7
            # Individual propensity: some people are early, some late
            propensity = rng.beta(2, 2)
            users.append(dict(user_id=f"u{uid:04d}", group=g, manager=managers[i % n_managers],
                              access_date=(start + timedelta(days=access_day)).isoformat(),
                              propensity=round(float(propensity), 3)))
            for d in range(access_day, args.days):
                day_in = d - access_day
                p_active = logistic(day_in, p["plateau"], p["ramp_weeks"]) * (0.6 + 0.8 * propensity)
                # weekends quieter
                if (start + timedelta(days=d)).weekday() >= 5:
                    p_active *= 0.15
                if rng.random() < min(p_active, 0.98):
                    # how many distinct core actions today (depth)
                    depth_mean = 1.2 + 1.8 * logistic(day_in, 1.0, p["ramp_weeks"]) * (1 - 0.5 * (p["override"] > 0.3))
                    n_actions = int(np.clip(rng.poisson(depth_mean), 1, 4))
                    actions = random.sample(CORE_ACTIONS, n_actions)
                    # work items: new-path vs legacy-path
                    work_items = rng.poisson(1.5)
                    migrate_today = p["migrate"] * logistic(day_in, 1.0, p["ramp_weeks"] + 2)
                    new_path = int(rng.binomial(work_items, min(migrate_today, 0.98)))
                    legacy = work_items - new_path
                    recs = rng.poisson(3) if "review_results" in actions or "author_action" in actions else 0
                    overrides = int(rng.binomial(recs, p["override"]))
                    ticket = ""
                    t = rng.random()
                    if day_in < 10 and t < 0.04:
                        ticket = "access"
                    elif t < 0.03 + 0.05 * (1 - logistic(day_in, 1.0, p["ramp_weeks"])):
                        ticket = "how_to"
                    elif t < 0.035:
                        ticket = "defect"
                    events.append(dict(date=(start + timedelta(days=d)).isoformat(), user_id=f"u{uid:04d}", group=g,
                                       actions="|".join(actions), n_actions=n_actions,
                                       work_items_new=new_path, work_items_legacy=legacy,
                                       recommendations=recs, overrides=overrides, ticket=ticket))
        # manager coaching, weekly
        for w in range(args.days // 7):
            for m in managers:
                coached = rng.random() < p["coaching"]
                coaching.append(dict(week=w + 1, group=g, manager=m, coached=int(coached)))

    import os
    os.makedirs(args.out, exist_ok=True)
    pd.DataFrame(users).to_csv(f"{args.out}/users.csv", index=False)
    pd.DataFrame(events).to_csv(f"{args.out}/events.csv", index=False)
    pd.DataFrame(coaching).to_csv(f"{args.out}/managers.csv", index=False)
    print(f"wrote {len(users)} users, {len(events)} event rows, {len(coaching)} coaching rows to {args.out}/ "
          f"(stalled group: {args.stall})")


if __name__ == "__main__":
    main()
