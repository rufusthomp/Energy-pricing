"""Every table, figure and headline number in the paper, from the zone-day frame.

    python -m gbmo.analysis.panel_data      # build the frame first
    python -m gbmo.analysis.results

Writes paper/tables/*.md, paper/figures/*.pdf and .png, and paper/results.json. Nothing in
the paper is typed by hand: each number the text quotes comes from results.json.

Treatments are rescaled to "per 10 percentage points" of forecast penetration so the
coefficients read as percentage-point changes in capture per 10 pp of wind or solar.
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gbmo import config
from gbmo.analysis import estimate as E
from gbmo.analysis.panel_data import FRAME_PATH, ratio_keep

PAPER = config.REPO_ROOT / "paper"
TABLES, FIGURES = PAPER / "tables", PAPER / "figures"

# Figure palette: reference categorical slots 1-3, validated all-pairs in light mode
WIND, SOLAR, THIRD = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

CRISIS = ("2021-07-01", "2023-06-30")
REPS = 9999
X_MAIN = ["wind10", "solar10"]
X_DIFF = ["wind10", "vre10"]   # coefficient on wind10 is then beta_w - beta_s


def style():
    plt.rcParams.update({
        "font.family": "serif", "font.size": 9, "axes.edgecolor": INK_2,
        "axes.labelcolor": INK, "xtick.color": INK_2, "ytick.color": INK_2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "legend.frameon": False, "savefig.bbox": "tight", "savefig.dpi": 200,
    })


def load():
    df = pd.read_parquet(FRAME_PATH)
    df["wind10"] = df["wind_pen"] / 10
    df["solar10"] = df["solar_pen"] / 10
    df["vre10"] = df["wind10"] + df["solar10"]
    df["error10"] = df["wind_error"] / 10
    df["kw_c"] = df["k_wind"] - df.groupby("zone")["k_wind"].transform("mean")
    df["wind10_x_k"] = df["wind10"] * (df["k_wind"] - df["k_wind"].mean()) / 10
    return df


def sample(df, y):
    return df.dropna(subset=[y, "wind10", "solar10"])


def with_floor(df, pct, d="2h"):
    """Capture shares recomputed with a different ratio floor (robustness)."""
    out = df.copy()
    pf_ = out[f"v_pf_{d}"]
    keep = ratio_keep(out, d, pct)
    for op in ("td", "ps", "fc"):
        if f"v_{op}_{d}" in out:
            out[f"cap_{op}_{d}"] = np.where(keep, 100 * out[f"v_{op}_{d}"] / pf_, np.nan)
    return out


def estimate_outcome(df, y, fe=E.FE_MAIN, bootstrap=True, vcov=None):
    """beta_w, beta_s and their difference, with WCB p-values."""
    data = sample(df, y)
    m = E.fit(data, y, X_MAIN, fe=fe, vcov=vcov)
    md = E.fit(data, y, X_DIFF, fe=fe, vcov=vcov)
    bw, sw, pw = E.tidy(m, "wind10")
    bs, ss, ps = E.tidy(m, "solar10")
    bd, sd, pd_ = E.tidy(md, "wind10")
    out = {"y": y, "n": int(m._N), "zones": int(data["zone"].nunique()),
           "b_wind": bw, "se_wind": sw, "p_wind": pw,
           "b_solar": bs, "se_solar": ss, "p_solar": ps,
           "b_diff": bd, "se_diff": sd, "p_diff": pd_,
           "mean_y": float(data[y].mean())}
    if bootstrap and fe:
        for name, x, param in (("wind", X_MAIN, "wind10"), ("solar", X_MAIN, "solar10"),
                               ("diff", X_DIFF, "wind10")):
            _, p, _ = E.wild_cluster_bootstrap(data, y, x, param, fe=fe, reps=REPS)
            out[f"wcb_{name}"] = p
    return out


def fmt(b, se, p=None, digits=2):
    stars = "" if p is None else ("***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "")
    return f"{b:.{digits}f}{stars}", f"({se:.{digits}f})"


def table(path, header, rows, notes):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join([":--"] + ["--:"] * (len(header) - 1)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    path.write_text("\n".join(lines) + "\n\n" + notes + "\n", encoding="utf-8")


def regression_table(results, labels, path, notes):
    header = [""] + labels
    rows = []
    for key, name in (("wind", "Wind penetration (per 10 pp)"), ("solar", "Solar penetration (per 10 pp)"),
                      ("diff", "Wind − solar")):
        est = [fmt(r[f"b_{key}"], r[f"se_{key}"], r.get(f"wcb_{key}", r[f"p_{key}"])) for r in results]
        rows.append([name] + [e[0] for e in est])
        rows.append([""] + [e[1] for e in est])
        if all(f"wcb_{key}" in r for r in results):
            rows.append(["  WCB p-value"] + [f"[{r[f'wcb_{key}']:.3f}]" for r in results])
    rows.append(["Mean of outcome"] + [f"{r['mean_y']:.2f}" for r in results])
    rows.append(["Zone-days"] + [f"{r['n']:,}" for r in results])
    rows.append(["Zones"] + [str(r["zones"]) for r in results])
    table(path, header, rows, notes)


# --------------------------------------------------------------------------------------
def descriptives(df):
    rows = []
    for z, g in df.groupby("zone"):
        rows.append([z, f"{g['wind_pen'].mean():.1f}", f"{g['solar_pen'].mean():.1f}",
                     f"{g['v_pf_2h'].mean():.0f}", f"{g['cap_td_2h'].mean():.1f}",
                     f"{g['cap_ps_2h'].mean():.1f}",
                     f"{g['cap_fc_2h'].mean():.1f}" if "cap_fc_2h" in g else "–",
                     f"{g['novelty'].mean():.3f}", f"{len(g):,}"])
    rows.sort(key=lambda r: -float(r[1]) if r[1] != "nan" else 0)
    header = ["Zone", "Wind (%)", "Solar (%)", "V* (€/MW/day)", "TD (%)", "PS (%)", "FC (%)",
              "Novelty", "Days"]
    table(TABLES / "t1_descriptives.md", header, rows,
          "Means over 2019-01-01 to 2026-09-20. Wind and solar are TSO day-ahead forecast "
          "output as a share of forecast load. V* is the perfect-foresight arbitrage value of "
          "a 1 MW / 2 MWh battery at 85% round-trip efficiency. TD, PS and FC are capture "
          "shares of V* for the typical-day, persistence and forecaster operators, on days "
          "above each zone's 5th percentile of V*. Novelty is 1 − corr(day's prices, "
          "typical-day profile). CZ publishes no wind forecast and is outside the "
          "estimation sample.")
    pooled = sample(df, "cap_td_2h")
    return {"days_total": len(df), "zones_total": int(df["zone"].nunique()),
            "vstar_mean": float(df["v_pf_2h"].mean()),
            "cap_td_mean": float(pooled["cap_td_2h"].mean()),
            "cap_ps_mean": float(pooled["cap_ps_2h"].mean()),
            "cap_fc_mean": float(pooled["cap_fc_2h"].mean()) if "cap_fc_2h" in pooled else None,
            "wind_mean": float(pooled["wind_pen"].mean()), "solar_mean": float(pooled["solar_pen"].mean()),
            "wind_sd_within": float(E.demean(pooled, ["wind_pen"])[0]["wind_pen"].std()),
            "solar_sd_within": float(E.demean(pooled, ["solar_pen"])[0]["solar_pen"].std())}


def main_results(df):
    outcomes = [("cap_td_2h", "TD capture"), ("cap_ps_2h", "PS capture"),
                ("cap_fc_2h", "FC capture"), ("log_v_pf_2h", "log V*"),
                ("novelty", "Novelty"), ("spread", "Spread (€/MWh)")]
    outcomes = [(y, lab) for y, lab in outcomes if y in df]
    res = [estimate_outcome(df, y) for y, _ in outcomes]
    regression_table(res, [lab for _, lab in outcomes], TABLES / "t2_main.md",
                     "Each column is one regression of the outcome on forecast wind and solar "
                     "penetration with zone×year, zone×month and date fixed effects. Capture "
                     "shares are in percent of V*; log V* is multiplied by 1; novelty is in "
                     "correlation units. The 'Wind − solar' row is β_w − β_s from the "
                     "re-parameterisation in Section 4. Standard errors clustered by zone in "
                     "parentheses; stars use wild cluster restricted bootstrap p-values "
                     "(Webb weights, 9,999 draws), shown in brackets. * p<0.1, ** p<0.05, "
                     "*** p<0.01.")
    return {y: r for (y, _), r in zip(outcomes, res)}


def fe_buildup(df):
    specs = [("None", None), ("Zone", "zone"), ("+ Zone×month", "zone + zone_month"),
             ("+ Zone×year", "zone_year + zone_month"), ("+ Date (main)", E.FE_MAIN)]
    res = []
    for _, fe in specs:
        res.append(estimate_outcome(df, "cap_td_2h", fe=fe, bootstrap=False,
                                    vcov={"CRV1": "zone"}))
    regression_table(res, [s for s, _ in specs], TABLES / "t3_fe_buildup.md",
                     "Outcome: typical-day capture share (%). Fixed effects added left to "
                     "right. Standard errors clustered by zone; conventional p-values. The "
                     "movement across columns shows which confounders each set of fixed "
                     "effects removes.")
    return [{"fe": s, **r} for (s, _), r in zip(specs, res)]


def placebo(df):
    out = {}
    rows = []
    for y, lab in (("cap_td_2h", "TD capture"), ("log_v_pf_2h", "log V*"), ("novelty", "Novelty"),
                   ("spread", "Spread")):
        data = df.dropna(subset=[y, "wind10", "solar10", "error10"])
        m = E.fit(data, y, ["wind10", "solar10", "error10"])
        b, se, _ = E.tidy(m, "error10")
        bw, _, _ = E.tidy(m, "wind10")
        _, pwcb, _ = E.wild_cluster_bootstrap(data, y, ["wind10", "solar10", "error10"], "error10",
                                              reps=REPS)
        out[y] = {"b_error": b, "se_error": se, "wcb_error": pwcb, "b_wind": bw, "n": int(m._N)}
        rows.append([lab, f"{bw:.3f}", f"{b:.3f} ({se:.3f})", f"[{pwcb:.3f}]", f"{m._N:,}"])
    table(TABLES / "t4_placebo.md",
          ["Outcome", "Forecast wind", "Wind forecast error", "WCB p (error)", "Zone-days"], rows,
          "Adds realised minus forecast wind (per 10 pp of forecast load) to the main "
          "specification. The day-ahead auction clears before the error is realised, so its "
          "coefficient should be zero. Standard errors clustered by zone; WCB p-value for the "
          "error coefficient.")
    return out


def heterogeneity(df):
    data = sample(df, "cap_td_2h")
    m = E.fit(data, "cap_td_2h", ["wind10", "solar10", "wind10_x_k"])
    b, se, _ = E.tidy(m, "wind10_x_k")
    _, pwcb, _ = E.wild_cluster_bootstrap(data, "cap_td_2h", ["wind10", "solar10", "wind10_x_k"],
                                          "wind10_x_k", reps=REPS)
    bw, sw, _ = E.tidy(m, "wind10")
    return {"b_interaction": b, "se_interaction": se, "wcb_interaction": pwcb,
            "b_wind_at_mean": bw, "se_wind_at_mean": sw, "k_wind_mean": float(data["k_wind"].mean()),
            "n": int(m._N)}


def robustness(df):
    variants = [
        ("Baseline (2h)", df, "cap_td_2h", E.FE_MAIN, None),
        ("1h battery", df, "cap_td_1h", E.FE_MAIN, None),
        ("4h battery", df, "cap_td_4h", E.FE_MAIN, None),
        ("Ratio floor 1st pct", with_floor(df, 0.01), "cap_td_2h", E.FE_MAIN, None),
        ("Ratio floor 10th pct", with_floor(df, 0.10), "cap_td_2h", E.FE_MAIN, None),
        ("Excluding gas crisis", df[~pd.to_datetime(df["delivery_date"]).between(*CRISIS)],
         "cap_td_2h", E.FE_MAIN, None),
        ("Two-way cluster (zone, date)", df, "cap_td_2h", E.FE_MAIN, {"CRV1": "zone+date"}),
    ]
    rows, out = [], []
    for name, data, y, fe, vcov in variants:
        boot = vcov is None
        r = estimate_outcome(data, y, fe=fe, bootstrap=boot, vcov=vcov)
        out.append({"spec": name, **r})
        p_diff = r.get("wcb_diff", r["p_diff"])
        rows.append([name, f"{r['b_wind']:.2f} ({r['se_wind']:.2f})", f"{r['b_solar']:.2f} ({r['se_solar']:.2f})",
                     f"{r['b_diff']:.2f} ({r['se_diff']:.2f})", f"{p_diff:.3f}", f"{r['n']:,}"])
    table(TABLES / "t5_robustness.md",
          ["Specification", "β wind", "β solar", "β wind − β solar", "p (diff)", "Zone-days"], rows,
          "Outcome: typical-day capture share (%), per 10 pp of forecast penetration. All "
          "specifications include zone×year, zone×month and date fixed effects. p-values are "
          "wild cluster restricted bootstrap (Webb, 9,999 draws) except the two-way-clustered "
          "row, which reports the conventional p-value.")
    return out


def leave_one_out(df):
    rows = []
    for z in sorted(sample(df, "cap_td_2h")["zone"].unique()):
        r = estimate_outcome(df[df["zone"] != z], "cap_td_2h", bootstrap=False)
        rows.append({"dropped": z, "b_diff": r["b_diff"], "se_diff": r["se_diff"],
                     "b_wind": r["b_wind"], "b_solar": r["b_solar"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
def binscatter(ax, data, y, x, other, color, label, bins=20, digits=2):
    """FWL binned scatter: residualise y and x on the other treatment and all FE."""
    d, _ = E.demean(data, [y, x, other])
    # Partial out the other treatment too, so the slope is the regression coefficient
    for col in (y, x):
        b = np.polyfit(d[other], d[col], 1)[0]
        d[col] = d[col] - b * d[other]
    d["bin"] = pd.qcut(d[x], bins, labels=False, duplicates="drop")
    g = d.groupby("bin")[[x, y]].mean()
    slope = np.polyfit(d[x], d[y], 1)[0]
    xs = np.linspace(g[x].min(), g[x].max(), 50)
    ax.plot(xs, slope * xs, color=color, lw=1.2, alpha=0.9)
    ax.scatter(g[x], g[y], s=22, color=color, edgecolor="white", linewidth=0.8, zorder=3)
    ax.axhline(0, color=INK_2, lw=0.6)
    ax.set_title(f"{label}: slope {slope:.{digits}f} per 10 pp", fontsize=9, color=INK, loc="left")
    return slope


def fig_binscatter(df, y, ylabel, name, digits=2):
    data = sample(df, y)
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=True)
    binscatter(axes[0], data, y, "wind10", "solar10", WIND, "Wind", digits=digits)
    binscatter(axes[1], data, y, "solar10", "wind10", SOLAR, "Solar", digits=digits)
    axes[0].set_ylabel(ylabel)
    for ax in axes:
        ax.set_xlabel("Residual penetration (10 pp)")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(FIGURES / f"{name}.pdf")
    fig.savefig(FIGURES / f"{name}.png")
    plt.close(fig)


def fig_operators(df):
    data = sample(df, "cap_td_2h")
    g = data.groupby("zone").agg(wind=("wind_pen", "mean"), td=("cap_td_2h", "mean"),
                                 ps=("cap_ps_2h", "mean"),
                                 fc=("cap_fc_2h", "mean") if "cap_fc_2h" in data else ("cap_ps_2h", "mean"))
    g = g.sort_values("wind")
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    y = np.arange(len(g))
    series = [("td", "Typical day", WIND), ("ps", "Persistence", SOLAR)]
    if "cap_fc_2h" in data:
        series.append(("fc", "Forecaster", THIRD))
    for col, lab, colr in series:
        ax.scatter(g[col], y, s=26, color=colr, edgecolor="white", linewidth=0.8, zorder=3, label=lab)
    ax.set_yticks(y, [f"{z}  ({w:.0f}%)" for z, w in zip(g.index, g["wind"])])
    ax.set_xlabel("Share of perfect-foresight value captured (%)")
    ax.set_ylabel("Zone (mean forecast wind penetration)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(series), fontsize=8,
              handletextpad=0.3, columnspacing=1.5)
    fig.savefig(FIGURES / "f2_operators.pdf")
    fig.savefig(FIGURES / "f2_operators.png")
    plt.close(fig)


def fig_loo(loo, main_diff):
    loo = loo.sort_values("b_diff")
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    y = np.arange(len(loo))
    ax.errorbar(loo["b_diff"], y, xerr=1.96 * loo["se_diff"], fmt="o", color=WIND, ms=4,
                ecolor=WIND, elinewidth=1, capsize=0)
    ax.axvline(main_diff, color=INK_2, lw=0.8, ls="--")
    ax.axvline(0, color=INK, lw=0.6)
    ax.set_yticks(y, [f"without {z}" for z in loo["dropped"]])
    ax.set_xlabel("β wind − β solar on typical-day capture (pp per 10 pp), 95% CI")
    fig.savefig(FIGURES / "f4_leave_one_out.pdf")
    fig.savefig(FIGURES / "f4_leave_one_out.png")
    plt.close(fig)


def fig_examples(df):
    """One windy and one sunny day in DE_LU, 2024: actual prices against the typical day.

    Chosen mechanically, not by eye: the 2024 day with the highest forecast wind
    penetration and the one with the highest forecast solar penetration.
    """
    from sqlalchemy import create_engine, text

    from gbmo.analysis.panel_data import typical_day_profiles
    from gbmo.arbitrage import panel

    zone = df[(df["zone"] == "DE_LU") & (pd.to_datetime(df["delivery_date"]).dt.year == 2024)]
    picks = [("Windiest day", zone.loc[zone["wind_pen"].idxmax()], WIND),
             ("Sunniest day", zone.loc[zone["solar_pen"].idxmax()], SOLAR)]
    engine = create_engine(config.DATABASE_URL)
    params = {"code": "DE_LU", "start": pd.Timestamp("2023-11-01").date(),
              "end": pd.Timestamp("2024-12-31").date()}
    days = panel.complete_days(pd.read_sql(text(panel.PRICES), engine, params=params),
                               pd.read_sql(text(panel.EXPECTED_HOURS), engine, params=params))
    engine.dispose()
    profiles = typical_day_profiles(days)

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=False)
    for ax, (title, row, colr) in zip(axes, picks):
        day = row["delivery_date"]
        frame = days[day]
        typical = panel.forecast_for(profiles[day], frame)
        hours = np.arange(len(frame))
        ax.plot(hours, typical, color=INK_2, lw=1.2, ls="--")
        ax.plot(hours, frame["price"], color=colr, lw=2)
        # Labels at the line ends, pushed apart vertically when the lines finish close together
        end_t, end_a = typical[-1], frame["price"].iloc[-1]
        span = max(np.nanmax(typical), frame["price"].max()) - min(np.nanmin(typical), frame["price"].min())
        gap = 0.07 * span
        if abs(end_t - end_a) < gap:
            mid = (end_t + end_a) / 2
            end_t, end_a = (mid + gap / 2, mid - gap / 2) if end_t >= end_a else (mid - gap / 2, mid + gap / 2)
        ax.text(hours[-1], end_t, " typical", color=INK_2, fontsize=8, va="center")
        ax.text(hours[-1], end_a, " actual", color=INK, fontsize=8, va="center")
        ax.set_title(f"{title} ({day:%d %b %Y}): wind {row['wind_pen']:.0f}%, "
                     f"solar {row['solar_pen']:.0f}%", fontsize=8.5, loc="left", color=INK)
        ax.set_xlabel("Hour of delivery day (CET)")
        ax.set_xlim(0, len(frame) + 3)
    axes[0].set_ylabel("Day-ahead price (€/MWh)")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(FIGURES / "f0_example_days.pdf")
    fig.savefig(FIGURES / "f0_example_days.png")
    plt.close(fig)
    return {title: {"date": str(row["delivery_date"]), "wind": float(row["wind_pen"]),
                    "solar": float(row["solar_pen"]), "novelty": float(row["novelty"]),
                    "cap_td": float(row["cap_td_2h"])} for title, row, _ in picks}


def figures(df, results):
    style()
    ex = fig_examples(df)
    fig_binscatter(df, "cap_td_2h", "Typical-day capture (pp)", "f1_binscatter_td")
    fig_binscatter(df, "log_v_pf_2h", "log arbitrage value", "f5_binscatter_value", digits=3)
    fig_binscatter(df, "novelty", "Shape novelty", "f3_binscatter_novelty", digits=3)
    fig_operators(df)
    loo = pd.DataFrame(results["leave_one_out"])
    fig_loo(loo, results["main"]["cap_td_2h"]["b_diff"])
    return ex


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    style()
    df = load()
    results = {"descriptives": descriptives(df)}
    print("descriptives done", flush=True)
    results["main"] = main_results(df)
    print("main done", flush=True)
    results["fe_buildup"] = fe_buildup(df)
    results["placebo"] = placebo(df)
    results["heterogeneity"] = heterogeneity(df)
    print("placebo/heterogeneity done", flush=True)
    results["robustness"] = robustness(df)
    print("robustness done", flush=True)
    loo = leave_one_out(df)
    results["leave_one_out"] = loo.to_dict(orient="records")

    results["examples"] = figures(df, results)
    (PAPER / "results.json").write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print("all written")


def figures_only():
    """Redraw figures from results.json without rerunning estimation or the bootstrap."""
    path = PAPER / "results.json"
    results = json.loads(path.read_text(encoding="utf-8"))
    results["examples"] = figures(load(), results)
    path.write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    print("figures redrawn")


if __name__ == "__main__":
    import sys

    figures_only() if "--figures" in sys.argv else main()
