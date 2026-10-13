#!/usr/bin/env python3
"""Compute adoption metrics per group per week and flag groups that need
intervention. Writes data/metrics_weekly.csv, data/flags.csv, and prints a
sponsor-style readout.

The flag logic is the point of this script. It encodes the reading rules in
docs/metric-definitions.md:

  STALL      active users on track but work migrated flat  -> Desire barrier
  SPIKE      active users up, retention falling            -> Reinforcement barrier
  ABILITY    tickets high and feature depth flat           -> Ability barrier
  BEHIND     active users > 1 stage behind the ramp curve  -> re-score readiness
  OVERRIDE   override rate above guardrail                 -> manager conversation
"""
import argparse
import pandas as pd

RAMP_TARGET = {2: 0.30, 6: 0.60, 10: 0.80}   # week -> target weekly-active share
MIGRATE_TARGET_BY_WEEK = {4: 0.25, 8: 0.50, 12: 0.70}
OVERRIDE_GUARDRAIL = 0.25
RETENTION_FLOOR = 0.70
SELF_SERVICE_FLOOR = 0.60


def ramp_target(week):
    t = 0.0
    for w, v in sorted(RAMP_TARGET.items()):
        if week >= w:
            t = v
    return t


def migrate_target(week):
    t = 0.0
    for w, v in sorted(MIGRATE_TARGET_BY_WEEK.items()):
        if week >= w:
            t = v
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--as-of-week", type=int, default=None, help="evaluate flags as of this week (default: last)")
    args = ap.parse_args()

    users = pd.read_csv(f"{args.data}/users.csv", parse_dates=["access_date"])
    ev = pd.read_csv(f"{args.data}/events.csv", parse_dates=["date"])
    mg = pd.read_csv(f"{args.data}/managers.csv")

    start = ev["date"].min()
    ev["week"] = ((ev["date"] - start).dt.days // 7) + 1
    pop = users.groupby("group")["user_id"].nunique().rename("population")

    # Weekly active users per group
    wau = ev.groupby(["group", "week"])["user_id"].nunique().rename("active_users").reset_index()
    wau = wau.merge(pop, on="group")
    wau["active_share"] = wau["active_users"] / wau["population"]

    # Retention: of users active in week N, share active in N+1
    active_sets = ev.groupby(["group", "week"])["user_id"].apply(set)
    ret_rows = []
    for (g, w), s in active_sets.items():
        nxt = active_sets.get((g, w + 1))
        if nxt is not None and len(s) > 0:
            ret_rows.append(dict(group=g, week=w + 1, retention=len(s & nxt) / len(s)))
    ret = pd.DataFrame(ret_rows)

    # Work migrated, overrides, depth, tickets
    agg = ev.groupby(["group", "week"]).agg(
        work_new=("work_items_new", "sum"), work_legacy=("work_items_legacy", "sum"),
        recs=("recommendations", "sum"), overrides=("overrides", "sum"),
        depth=("n_actions", "mean"), active_days=("user_id", "size"),
    ).reset_index()
    agg["work_migrated"] = agg["work_new"] / (agg["work_new"] + agg["work_legacy"]).replace(0, pd.NA)
    agg["override_rate"] = agg["overrides"] / agg["recs"].replace(0, pd.NA)
    tickets = ev[ev["ticket"] != ""].groupby(["group", "week"])["ticket"].count().rename("tickets").reset_index()
    howto = ev[ev["ticket"] == "how_to"].groupby(["group", "week"])["ticket"].count().rename("howto_tickets").reset_index()

    # Time to first use
    first = ev.groupby("user_id")["date"].min().rename("first_use").reset_index().merge(users, on="user_id")
    first["ttfu_days"] = (first["first_use"] - first["access_date"]).dt.days
    ttfu = first.groupby("group")["ttfu_days"].agg(ttfu_median="median", ttfu_p80=lambda s: s.quantile(0.8)).reset_index()

    # Manager coaching
    coach = mg.groupby(["group", "week"])["coached"].mean().rename("coaching_rate").reset_index()

    m = wau.merge(ret, on=["group", "week"], how="left").merge(agg, on=["group", "week"], how="left") \
           .merge(tickets, on=["group", "week"], how="left").merge(howto, on=["group", "week"], how="left") \
           .merge(coach, on=["group", "week"], how="left")
    m["tickets"] = m["tickets"].fillna(0)
    m["howto_tickets"] = m["howto_tickets"].fillna(0)
    m["tickets_per_100_active"] = 100 * m["tickets"] / m["active_users"]
    # self-service proxy: active user-days without a how-to ticket
    m["self_service_rate"] = 1 - m["howto_tickets"] / m["active_days"]
    m["ramp_target"] = m["week"].apply(ramp_target)
    m["migrate_target"] = m["week"].apply(migrate_target)
    m = m.sort_values(["group", "week"])
    m.to_csv(f"{args.data}/metrics_weekly.csv", index=False)

    # Flags as of a week
    as_of = args.as_of_week or int(m["week"].max())
    flags = []
    for g, gm in m.groupby("group"):
        gm = gm[gm["week"] <= as_of].sort_values("week")
        if len(gm) < 2:
            continue
        last, prev = gm.iloc[-1], gm.iloc[-2]
        reasons = []
        # BEHIND: more than one stage behind the ramp curve, two weeks running
        if last["active_share"] < last["ramp_target"] - 0.15 and prev["active_share"] < prev["ramp_target"] - 0.15:
            reasons.append(("BEHIND", f"active {last['active_share']:.0%} vs target {last['ramp_target']:.0%} two weeks running; re-score readiness and talk to the group's leader"))
        # STALL: active on track, migration behind target
        if last["active_share"] >= last["ramp_target"] - 0.10 and pd.notna(last["work_migrated"]) \
                and last["work_migrated"] < last["migrate_target"] - 0.10:
            reasons.append(("STALL", f"active {last['active_share']:.0%} but work migrated {last['work_migrated']:.0%} vs target {last['migrate_target']:.0%}; people are in the tool, not doing the real work there. Desire barrier: check legacy path and override rate"))
        # OVERRIDE
        if pd.notna(last["override_rate"]) and last["override_rate"] > OVERRIDE_GUARDRAIL:
            reasons.append(("OVERRIDE", f"override rate {last['override_rate']:.0%} above guardrail {OVERRIDE_GUARDRAIL:.0%}; manager conversation on override discipline"))
        # SPIKE
        if pd.notna(last["retention"]) and last["retention"] < RETENTION_FLOOR and last["active_share"] > prev["active_share"]:
            reasons.append(("SPIKE", f"retention {last['retention']:.0%} below {RETENTION_FLOOR:.0%} while actives grow; launch spike, not a habit. Reinforcement: check manager coaching ({last['coaching_rate']:.0%})"))
        # ABILITY
        if last["self_service_rate"] < SELF_SERVICE_FLOOR and last["depth"] <= prev["depth"]:
            reasons.append(("ABILITY", f"self-service {last['self_service_rate']:.0%} with flat depth {last['depth']:.1f}; training did not match the job"))
        # COACHING
        if pd.notna(last["coaching_rate"]) and last["coaching_rate"] < 0.5:
            reasons.append(("COACHING", f"only {last['coaching_rate']:.0%} of managers coached this week; sponsor's ask goes to the managers' leader"))
        for code, why in reasons:
            flags.append(dict(as_of_week=as_of, group=g, flag=code, detail=why))
    fl = pd.DataFrame(flags)
    fl.to_csv(f"{args.data}/flags.csv", index=False)

    # Readout
    print(f"\nADOPTION READOUT, week {as_of} of {int(m['week'].max())}\n")
    snap = m[m["week"] == as_of].merge(ttfu, on="group")
    cols = ["group", "active_share", "ramp_target", "work_migrated", "migrate_target", "override_rate", "retention", "self_service_rate", "coaching_rate", "ttfu_median", "ttfu_p80"]
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 200):
        print(snap[cols].to_string(index=False))
    print()
    if fl.empty:
        print("No flags. All groups within tolerance.")
    else:
        for g, gf in fl.groupby("group"):
            print(f"[{g}]")
            for _, r in gf.iterrows():
                print(f"  {r['flag']:9s} {r['detail']}")
    # Headline
    stalled = fl[fl["flag"].isin(["STALL", "BEHIND"])]["group"].unique().tolist()
    print()
    if stalled:
        print(f"HEADLINE: intervene on {', '.join(stalled)} this week. Look at that group's sponsor before looking at that group.")
    else:
        print("HEADLINE: no group needs intervention this week.")


if __name__ == "__main__":
    main()
