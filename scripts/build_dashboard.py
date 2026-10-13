#!/usr/bin/env python3
"""Render data/metrics_weekly.csv and data/flags.csv into a self-contained
HTML dashboard (inline SVG, no external libraries): one small-multiple line
chart per headline metric, a flags panel, and a table view.
"""
import argparse
import html
import pandas as pd

LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]
W, H, PAD_L, PAD_R, PAD_T, PAD_B = 420, 220, 44, 16, 22, 30

PANELS = [
    ("active_share", "Weekly active users", "share of group", "ramp_target"),
    ("work_migrated", "Work migrated to new path", "share of work items", "migrate_target"),
    ("override_rate", "Override rate", "share of recommendations, 3-week trailing", None),
    ("coaching_rate", "Managers coaching", "share of managers, 3-week trailing", None),
]


def line_chart(m, metric, title, subtitle, target_col, groups, flagged):
    weeks = sorted(m["week"].unique())
    x0, x1 = PAD_L, W - PAD_R
    y0, y1 = H - PAD_B, PAD_T

    def sx(w): return x0 + (w - weeks[0]) / (weeks[-1] - weeks[0]) * (x1 - x0)
    def sy(v): return y0 - v * (y0 - y1)

    out = [f'<figure class="chart"><figcaption><strong>{html.escape(title)}</strong><span>{html.escape(subtitle)}</span></figcaption>']
    out.append(f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)} by group by week">')
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line class="grid" x1="{x0}" y1="{sy(t):.1f}" x2="{x1}" y2="{sy(t):.1f}"/>')
        out.append(f'<text class="tick" x="{x0-6}" y="{sy(t)+4:.1f}" text-anchor="end">{int(t*100)}%</text>')
    for w in weeks:
        if w % 2 == 1:
            out.append(f'<text class="tick" x="{sx(w):.1f}" y="{H-10}" text-anchor="middle">w{w}</text>')
    if target_col:
        pts = " ".join(f"{sx(w):.1f},{sy(m[m['week']==w][target_col].iloc[0]):.1f}" for w in weeks)
        out.append(f'<polyline class="target" points="{pts}"/>')
        out.append(f'<text class="tick" x="{x1}" y="{sy(m[m["week"]==weeks[-1]][target_col].iloc[0])-5:.1f}" text-anchor="end">target</text>')
    for i, g in enumerate(groups):
        gm = m[m["group"] == g].sort_values("week")
        rows = [r for r in gm.itertuples() if pd.notna(getattr(r, metric))]
        pts = [(sx(r.week), sy(getattr(r, metric))) for r in rows]
        if not pts:
            continue
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        cls = "series flagged" if g in flagged else "series"
        out.append(f'<polyline class="{cls}" style="stroke:var(--s{i+1})" points="{poly}" data-group="{g}"/>')
        for (x, y), r in zip(pts, rows):
            v = getattr(r, metric)
            out.append(f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent" data-tip="{html.escape(g.replace("_"," "))} · week {r.week}: {v:.0%}"/>')
        if g in flagged:
            x, y = pts[-1]
            out.append(f'<text class="label" x="{x-4:.1f}" y="{y-7:.1f}" text-anchor="end">{html.escape(g.replace("_"," "))}</text>')
    out.append("</svg></figure>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="dashboard.html")
    args = ap.parse_args()
    m = pd.read_csv(f"{args.data}/metrics_weekly.csv")
    # Display smoothing: 3-week trailing mean for the two noisy weekly rates;
    # week 1 of work_migrated is a handful of items and not meaningful.
    for c in ("coaching_rate", "override_rate"):
        m[c] = m.groupby("group")[c].transform(lambda s: s.rolling(3, min_periods=1).mean())
    m.loc[m["week"] == 1, "work_migrated"] = pd.NA
    fl = pd.read_csv(f"{args.data}/flags.csv")
    groups = sorted(m["group"].unique())
    flagged = set(fl[fl["flag"].isin(["STALL", "BEHIND"])]["group"]) if not fl.empty else set()
    as_of = int(fl["as_of_week"].iloc[0]) if not fl.empty else int(m["week"].max())

    legend = "".join(f'<li><i style="background:var(--s{i+1})"></i>{html.escape(g.replace("_"," "))}</li>' for i, g in enumerate(groups))
    charts = "\n".join(line_chart(m, *p, groups, flagged) for p in PANELS)
    if fl.empty:
        flags_html = "<p>No flags. All groups within tolerance.</p>"
    else:
        rows = "".join(f'<tr><td>{html.escape(r.group.replace("_"," "))}</td><td><code>{r.flag}</code></td><td>{html.escape(r.detail)}</td></tr>' for r in fl.itertuples())
        flags_html = f"<table><thead><tr><th>Group</th><th>Flag</th><th>What it means and what to do</th></tr></thead><tbody>{rows}</tbody></table>"
    snap = m[m["week"] == as_of].sort_values("group")
    tcols = ["group", "active_share", "work_migrated", "override_rate", "retention", "self_service_rate", "coaching_rate", "tickets_per_100_active"]
    trows = "".join("<tr>" + "".join(f"<td>{html.escape(str(r[c]).replace('_',' ')) if c=='group' else (f'{r[c]:.0%}' if c!='tickets_per_100_active' else f'{r[c]:.1f}')}</td>" for c in tcols) + "</tr>" for _, r in snap.iterrows())
    headline = (f"Intervene on {', '.join(g.replace('_',' ') for g in sorted(flagged))} this week. Look at that group's sponsor before looking at that group."
                if flagged else "No group needs intervention this week.")
    s_light = "".join(f"--s{i+1}:{c};" for i, c in enumerate(LIGHT))
    s_dark = "".join(f"--s{i+1}:{c};" for i, c in enumerate(DARK))

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adoption Readout</title>
<style>
:root{{color-scheme:light;--bg:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--grid:#e6e5e1;--line:#d6d5d0;--warn:#b45309;{s_light}}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#1a1a19;--panel:#222221;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8d8c86;--grid:#33332f;--line:#3d3d38;--warn:#f0a35a;{s_dark}}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#1a1a19;--panel:#222221;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8d8c86;--grid:#33332f;--line:#3d3d38;--warn:#f0a35a;{s_dark}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:24px 16px}}
main{{max-width:960px;margin:0 auto}}h1{{font-size:22px;margin:0 0 4px}}.sub{{color:var(--ink2);margin:0 0 16px}}
.headline{{border-left:4px solid var(--warn);padding:10px 14px;background:var(--panel);border-radius:6px;margin:0 0 20px;font-weight:600}}
.legend{{list-style:none;display:flex;flex-wrap:wrap;gap:6px 16px;padding:0;margin:0 0 12px;color:var(--ink2);font-size:13px}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.grid4{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}}
.chart{{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}}.chart figcaption{{display:flex;justify-content:space-between;gap:8px;font-size:13px;margin-bottom:4px}}.chart figcaption span{{color:var(--muted)}}
svg{{width:100%;height:auto;display:block}}.grid{{stroke:var(--grid);stroke-width:1}}.tick{{fill:var(--muted);font-size:10px}}.target{{fill:none;stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:4 4}}
.series{{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}}.series.flagged{{stroke-width:3}}.label{{fill:var(--ink);font-size:11px;font-weight:600}}
.pt:hover{{fill:var(--ink);fill-opacity:.15}}#tip{{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:4px 8px;border-radius:4px;font-size:12px;display:none;z-index:9}}
section{{margin-top:24px}}h2{{font-size:16px;margin:0 0 8px}}table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:8px;font-size:13px}}th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--ink2);font-weight:600}}code{{font-size:12px}}
details summary{{cursor:pointer;color:var(--ink2)}}
</style></head><body><main>
<h1>Adoption readout</h1><p class="sub">Week {as_of} of a 90-day platform rollout · five impacted groups · synthetic data</p>
<p class="headline">{html.escape(headline)}</p>
<ul class="legend">{legend}</ul>
<div class="grid4">{charts}</div>
<section><h2>Flags this week</h2>{flags_html}</section>
<section><details><summary>Table view, week {as_of}</summary><table><thead><tr><th>Group</th><th>Active</th><th>Migrated</th><th>Override</th><th>Retention</th><th>Self-service</th><th>Coaching</th><th>Tickets /100</th></tr></thead><tbody>{trows}</tbody></table></details></section>
<div id="tip"></div>
<script>
const tip=document.getElementById('tip');document.querySelectorAll('.pt').forEach(p=>{{p.addEventListener('mousemove',e=>{{tip.textContent=p.dataset.tip;tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';}});p.addEventListener('mouseleave',()=>tip.style.display='none');}});
</script></main></body></html>"""
    with open(args.out, "w") as f:
        f.write(page)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
