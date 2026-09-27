"""Every table, figure and headline number in the paper, from the zone-day frame.

    python -m gbmo.analysis.panel_data      # build the frame first
    python -m gbmo.analysis.results         # everything
    python -m gbmo.analysis.results --figures

Writes paper/tables/*.md, paper/figures/*.pdf and .png, and paper/results.json. Nothing in
the paper is typed by hand: each number the text quotes comes from results.json.

Every table is labelled REGISTERED (fixed in docs/preregistration.md before any outcome
existed) or EXPLORATORY (added after results were seen, most at a referee's request).
Treatments are per 10 percentage points of forecast penetration.
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
MTU_15 = "2025-10-01"
REPS = 9999
X_MAIN = ["wind10", "solar10"]
X_DIFF = ["wind10", "vre10"]   # coefficient on wind10 is then beta_w - beta_s

# Coupling regions for the region-by-date robustness check. Date effects remove only what
# is common to all zones on a day; region-by-date effects also remove what is common within
# a region, so identification comes only from zones compared with their own neighbours.
REGION = {
    "DK_1": "nordic", "DK_2": "nordic", "NO_2": "nordic", "SE_3": "nordic", "SE_4": "nordic",
    "FI": "nordic", "EE": "nordic",
    "DE_LU": "cwe", "NL": "cwe", "BE": "cwe", "FR": "cwe", "AT": "cwe", "CH": "cwe",
    "CZ": "cwe", "PL": "cwe",
    "ES": "iberia", "PT": "iberia",
    "GR": "south", "IT_NORD": "south",
}
FE_REGION_DATE = "zone_year + zone_month + region_date"
FE_ZYM = "zone_ym + date"

STARS_NOTE = "* p<0.1, ** p<0.05, *** p<0.01"


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
    df["wind_lead10"] = df["wind_pen_lead"] / 10
    df["solar_lead10"] = df["solar_pen_lead"] / 10
    df["region"] = df["zone"].map(REGION)
    df["region_date"] = df["region"] + "_" + df["date"]
    df["zone_ym"] = df["zone_year"] + "_" + df["month"].astype(str)
    df["v_pf_2h_eur"] = df["v_pf_2h"]
    df["gap_td_2h"] = df["v_pf_2h"] - df["v_td_2h"]
    df["gap_fc_2h"] = df["v_pf_2h"] - df["v_fc_2h"]
    df["gain_fc_2h"] = df["v_fc_2h"] - df["v_td_2h"]
    df["capgain_fc_2h"] = df["cap_fc_2h"] - df["cap_td_2h"]
    # H4: centred at the estimation-sample mean, the point the paper evaluates it at
    est = df.dropna(subset=["cap_td_2h", "wind10", "solar10"])
    df.attrs["k_centre"] = float(est["k_wind"].mean())
    df["wind10_x_k"] = df["wind10"] * (df["k_wind"] - df.attrs["k_centre"]) / 10
    return df


def sample(df, y, x=X_MAIN):
    return df.dropna(subset=[y, *x])


def with_floor(df, pct, d="2h"):
    """Capture shares recomputed with a different ratio floor (robustness)."""
    out = df.copy()
    pf_ = out[f"v_pf_{d}"]
    keep = ratio_keep(out, d, pct)
    for op in ("td", "ps", "fc", "td14"):
        if f"v_{op}_{d}" in out:
            out[f"cap_{op}_{d}"] = np.where(keep, 100 * out[f"v_{op}_{d}"] / pf_, np.nan)
    return out


def fixed_denominator(df):
    """Treatments over the zone-year's mean daily load forecast (exploratory E2)."""
    d = df.copy()
    mean_load = d.groupby("zone_year")["load_fc_mwh"].transform("mean")
    valid = d["wind10"].notna() & d["solar10"].notna()
    d["wind10"] = np.where(valid, 100 * d["wind_fc_mwh"] / mean_load / 10, np.nan)
    d["solar10"] = np.where(valid, 100 * d["solar_fc_mwh"] / mean_load / 10, np.nan)
    d["vre10"] = d["wind10"] + d["solar10"]
    return d


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
            _, p, *_ = E.wild_cluster_bootstrap(data, y, x, param, fe=fe, reps=REPS)
            out[f"wcb_{name}"] = p
    return out


def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def fmt(b, se, p=None, digits=2):
    return f"{b:.{digits}f}{'' if p is None else stars(p)}", f"({se:.{digits}f})"


def separator(rows):
    """Pipe-table separator whose dash counts track each column's widest cell.

    When a table is wider than the page, pandoc sets column widths in proportion to these
    dash counts, so equal dashes squeeze a long first column into ragged wrapping.
    """
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "|" + "|".join([":" + "-" * max(3, widths[0])]
                          + [("-" * max(3, w)) + ":" for w in widths[1:]]) + "|"


def escape_notes(notes):
    """Markdown-safe notes: a bare V* pairs with the next asterisk and italicises text."""
    return notes.replace("V*", "V\\*")


def table(path, header, rows, notes):
    lines = ["| " + " | ".join(header) + " |", separator([header, *rows])]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    path.write_text("\n".join(lines) + "\n\n" + escape_notes(notes) + "\n", encoding="utf-8")


def regression_table(results, labels, path, notes, digits=None):
    """Columns of estimate_outcome results. `digits` sets decimals per column."""
    digits = digits or [2] * len(results)
    header = [""] + labels
    rows = []
    for key, name in (("wind", "Wind (per 10 pp)"), ("solar", "Solar (per 10 pp)"),
                      ("diff", "Wind − solar")):
        est = [fmt(r[f"b_{key}"], r[f"se_{key}"], r.get(f"wcb_{key}", r[f"p_{key}"]), dg)
               for r, dg in zip(results, digits)]
        rows.append([name] + [e[0] for e in est])
        rows.append([""] + [e[1] for e in est])
        if all(f"wcb_{key}" in r for r in results):
            rows.append(["  WCB p-value"] + [f"[{pfmt(r[f'wcb_{key}'])}]" for r in results])
    rows.append(["Mean of outcome"] + [f"{r['mean_y']:.{max(dg, 2)}f}" for r, dg in zip(results, digits)])
    rows.append(["Zone-days"] + [f"{r['n']:,}" for r in results])
    rows.append(["Zones"] + [str(r["zones"]) for r in results])
    table(path, header, rows, notes)


# --------------------------------------------------------------------------------------
def descriptives(df):
    rows = []
    for z, g in df.groupby("zone"):
        td = g.dropna(subset=["cap_td_2h"])
        vw = 100 * td["v_td_2h"].sum() / td["v_pf_2h"].sum()
        wind = "–" if g["wind_pen"].isna().all() else f"{g['wind_pen'].mean():.1f}"
        rows.append([z, wind, f"{g['solar_pen'].mean():.1f}", f"{g['v_pf_2h'].mean():.0f}",
                     f"{g['cap_td_2h'].mean():.1f}", f"{g['cap_td_2h'].median():.1f}", f"{vw:.1f}",
                     f"{g['cap_ps_2h'].mean():.1f}", f"{g['cap_fc_2h'].mean():.1f}",
                     f"{g['novelty'].mean():.3f}", f"{int((g['v_pf_2h'] <= 0).sum())}", f"{len(g):,}"])
    rows.sort(key=lambda r: -float(r[1]) if r[1] != "–" else 1)
    header = ["Zone", "Wind (%)", "Solar (%)", "V* (€)", "TD mean", "TD median", "TD value-wtd",
              "PS mean", "FC mean", "Novelty", "V* = 0", "Days"]
    table(TABLES / "t1_descriptives.md", header, rows,
          "Means over 2019-01-01 to 2026-09-20. Wind and solar: TSO day-ahead forecast output "
          "as a share of forecast load. V*: perfect-foresight arbitrage value of a 1 MW / 2 MWh "
          "battery at 85% round-trip efficiency, € per day. TD, PS, FC: capture shares (%) of "
          "the typical-day, persistence and forecaster operators, on days with V* > 0 and above "
          "the zone's 5th percentile of positive V*; value-weighted TD is ΣV_TD / ΣV* over those "
          "days. The forecaster's sample starts in May 2019 for DE_LU. V* = 0 counts days on which "
          "no intraday spread covers the round-trip loss. CZ publishes no wind forecast and is "
          "outside the estimation sample.")
    pooled = sample(df, "cap_td_2h")
    zero = df[df["v_pf_2h"] <= 0]
    return {"days_total": len(df), "zones_total": int(df["zone"].nunique()),
            "vstar_mean": float(df["v_pf_2h"].mean()),
            "cap_td_mean": float(pooled["cap_td_2h"].mean()),
            "cap_ps_mean": float(pooled["cap_ps_2h"].mean()),
            "cap_fc_mean": float(pooled["cap_fc_2h"].mean()),
            "cap_td_value_weighted": float(100 * pooled["v_td_2h"].sum() / pooled["v_pf_2h"].sum()),
            "cap_fc_value_weighted": float(100 * pooled["v_fc_2h"].sum() / pooled["v_pf_2h"].sum()),
            "zero_days": len(zero), "zero_zones": int(zero["zone"].nunique()),
            "zero_days_est": int(len(sample(df, "novelty")) - len(sample(df, "log_v_pf_2h"))),
            "wind_mean": float(pooled["wind_pen"].mean()), "solar_mean": float(pooled["solar_pen"].mean()),
            "wind_sd_within": float(E.demean(pooled, ["wind_pen"])[0]["wind_pen"].std()),
            "solar_sd_within": float(E.demean(pooled, ["solar_pen"])[0]["solar_pen"].std())}


def main_results(df):
    outcomes = [("cap_td_2h", "TD capture", 2), ("cap_ps_2h", "PS capture", 2),
                ("cap_fc_2h", "FC capture", 2), ("log_v_pf_2h", "log V*", 3),
                ("novelty", "Novelty", 3), ("spread", "Spread (€)", 2)]
    res = [estimate_outcome(df, y) for y, _, _ in outcomes]
    regression_table(res, [lab for _, lab, _ in outcomes], TABLES / "t2_main.md",
                     "REGISTERED. Each column regresses the outcome on forecast wind and solar "
                     "penetration with zone×year, zone×month and date fixed effects. Capture "
                     "shares in percent of V*; novelty in correlation units; spread in €/MWh. "
                     "log V* excludes the 1,008 zone-days with V* = 0 (see Table 6 for log(1+V*)). "
                     "'Wind − solar' is the wind coefficient minus the solar coefficient. "
                     "Zone-clustered standard errors in parentheses; wild cluster restricted "
                     "bootstrap p-values (Webb weights, 9,999 draws, fixed effects re-projected "
                     "in every draw) in brackets, and stars use them. " + STARS_NOTE + ".",
                     digits=[dg for _, _, dg in outcomes])
    return {y: r for (y, _, _), r in zip(outcomes, res)}


def inference_checks(df):
    """H1 under alternative inference: CV3 (jackknife) and full Rademacher enumeration."""
    data = sample(df, "cap_td_2h")
    m3 = E.fit(data, "cap_td_2h", X_DIFF, vcov={"CRV3": "zone"})
    b, se3, p3 = E.tidy(m3, "wind10")
    t, p_enum, _, n = E.wild_cluster_bootstrap(data, "cap_td_2h", X_DIFF, "wind10",
                                               weights="rademacher", enumerate_all=True)
    return {"b_diff": b, "se_cv3": se3, "p_cv3": p3, "t": t,
            "p_rademacher_enumerated": p_enum, "draws": n}


def fe_buildup(df):
    specs = [("None", None), ("Zone", "zone"), ("+ Zone×month", "zone + zone_month"),
             ("+ Zone×year", "zone_year + zone_month"), ("+ Date (main)", E.FE_MAIN)]
    res = [estimate_outcome(df, "cap_td_2h", fe=fe, bootstrap=False, vcov={"CRV1": "zone"})
           for _, fe in specs]
    regression_table(res, [s for s, _ in specs], TABLES / "t3_fe_buildup.md",
                     "EXPLORATORY in presentation (the final column is the registered "
                     "specification). Outcome: typical-day capture share (%). Fixed effects "
                     "added left to right. Zone-clustered standard errors. Unlike Table 2, "
                     "stars here use conventional cluster-robust p-values, which overstate "
                     "significance with 18 clusters. " + STARS_NOTE + ".")
    return [{"fe": s, **r} for (s, _), r in zip(specs, res)]


def placebo_cell(e, digits):
    return f"{e['b']:.{digits}f} ({e['se']:.{digits}f}) [{pfmt(e['wcb'])}]"


def placebo(df):
    out, rows = {}, []
    for y, lab in (("cap_td_2h", "TD capture"), ("cap_ps_2h", "PS capture"),
                   ("log_v_pf_2h", "log V*"), ("novelty", "Novelty"), ("spread", "Spread")):
        entry = {}
        for kind, extra in (("error", ["error10"]), ("lead", ["wind_lead10", "solar_lead10"])):
            data = df.dropna(subset=[y, "wind10", "solar10", *extra])
            m = E.fit(data, y, ["wind10", "solar10", *extra])
            for term in extra:
                b, se, _ = E.tidy(m, term)
                _, p, *_ = E.wild_cluster_bootstrap(data, y, ["wind10", "solar10", *extra], term,
                                                    reps=REPS)
                entry[term] = {"b": b, "se": se, "wcb": p}
            entry[f"n_{kind}"] = int(m._N)
        entry["b_wind_main"] = E.tidy(E.fit(sample(df, y), y, X_MAIN), "wind10")[0]
        out[y] = entry
        digits = 3 if y in ("log_v_pf_2h", "novelty") else 2
        rows.append([lab, f"{entry['b_wind_main']:.{digits}f}",
                     *(placebo_cell(entry[t], digits) for t in ("error10", "wind_lead10", "solar_lead10"))])
    table(TABLES / "t4_placebo.md",
          ["Outcome", "Forecast wind (main)", "Wind forecast error", "Next day's wind", "Next day's solar"],
          rows,
          "The forecast-error column is REGISTERED; the lead columns are EXPLORATORY. Each "
          "placebo is added to the main specification. The forecast error is realised minus "
          "forecast wind; next day's wind and solar are day d+1's forecast penetration, "
          "published after day d's auction. Coefficient (zone-clustered s.e.) [WCB p-value]. "
          "A placebo that cannot be distinguished from the forecast coefficient is weak "
          "evidence either way; see the text.")
    return out


def heterogeneity(df):
    x = ["wind10", "solar10", "wind10_x_k"]
    out = {}
    for label, drop in (("all", []), ("without_DK_1", ["DK_1"]), ("without_DK", ["DK_1", "DK_2"])):
        data = df[~df["zone"].isin(drop)].dropna(subset=["cap_td_2h", *x])
        m = E.fit(data, "cap_td_2h", x)
        b, se, _ = E.tidy(m, "wind10_x_k")
        _, p, *_ = E.wild_cluster_bootstrap(data, "cap_td_2h", x, "wind10_x_k", reps=REPS)
        entry = {"b_interaction": b, "se_interaction": se, "wcb_interaction": p, "n": int(m._N)}
        if label == "all":
            coef, vcov = m.coef(), m._vcov
            names = list(coef.index)
            iw, ik = names.index("wind10"), names.index("wind10_x_k")
            for k_label, k_val in (("k_centre", df.attrs["k_centre"]), ("dk1", float(
                    data.loc[data["zone"] == "DK_1", "k_wind"].mean())), ("low", 5.0)):
                g = np.zeros(len(names))
                g[iw], g[ik] = 1.0, (k_val - df.attrs["k_centre"]) / 10
                entry[f"effect_at_{k_label}"] = {"k": k_val, "b": float(g @ coef.to_numpy()),
                                                 "se": float(np.sqrt(g @ vcov @ g))}
        out[label] = entry
    rows = [[lab, f"{out[k]['b_interaction']:.2f} ({out[k]['se_interaction']:.2f})",
             pfmt(out[k]["wcb_interaction"]), f"{out[k]['n']:,}"]
            for k, lab in (("all", "All 18 zones (registered)"), ("without_DK_1", "Without DK_1"),
                           ("without_DK", "Without DK_1 and DK_2"))]
    table(TABLES / "t9_heterogeneity.md", ["Sample", "Wind × K (s.e.)", "WCB p", "Zone-days"], rows,
          "Outcome: typical-day capture (%). Interaction of forecast wind penetration (per 10 pp) "
          "with the zone-year's mean wind penetration K (per 10 pp, centred at the estimation-"
          "sample mean). The first row is REGISTERED (H4); the others are EXPLORATORY.")
    return out


def robustness(df):
    pre_mtu = df[pd.to_datetime(df["delivery_date"]) < pd.Timestamp(MTU_15)]
    no_neg = df[df["negative_day"] == 0]
    variants = [
        ("Baseline (2h)", "R", df, "cap_td_2h", E.FE_MAIN, None),
        ("1h battery", "R", df, "cap_td_1h", E.FE_MAIN, None),
        ("4h battery", "R", df, "cap_td_4h", E.FE_MAIN, None),
        ("14-day typical day", "R", df, "cap_td14_2h", E.FE_MAIN, None),
        ("Ratio floor 1st pct", "R", with_floor(df, 0.01), "cap_td_2h", E.FE_MAIN, None),
        ("Ratio floor 10th pct", "R", with_floor(df, 0.10), "cap_td_2h", E.FE_MAIN, None),
        ("Excluding gas crisis", "R", df[~pd.to_datetime(df["delivery_date"]).between(*CRISIS)],
         "cap_td_2h", E.FE_MAIN, None),
        ("Two-way cluster (zone, date)", "R", df, "cap_td_2h", E.FE_MAIN, {"CRV1": "zone+date"}),
        ("Region × date FE", "E", df, "cap_td_2h", FE_REGION_DATE, None),
        ("Zone × year × month FE", "E", df, "cap_td_2h", FE_ZYM, None),
        ("Fixed load denominator", "E", fixed_denominator(df), "cap_td_2h", E.FE_MAIN, None),
        ("Before 15-min MTU", "E", pre_mtu, "cap_td_2h", E.FE_MAIN, None),
        ("Excluding negative-price days", "E", no_neg, "cap_td_2h", E.FE_MAIN, None),
    ]
    rows, out = [], []
    for name, kind, data, y, fe, vcov in variants:
        r = estimate_outcome(data, y, fe=fe, bootstrap=vcov is None, vcov=vcov)
        out.append({"spec": name, "kind": kind, **r})
        p_diff = r.get("wcb_diff", r["p_diff"])
        rows.append([name + ("" if kind == "R" else " †"),
                     f"{r['b_wind']:.2f} ({r['se_wind']:.2f})", f"{r['b_solar']:.2f} ({r['se_solar']:.2f})",
                     f"{r['b_diff']:.2f} ({r['se_diff']:.2f})", pfmt(p_diff), f"{r['n']:,}"])
    table(TABLES / "t5_robustness.md",
          ["Specification", "β wind", "β solar", "β wind − β solar", "p (diff)", "Zone-days"], rows,
          "Outcome: typical-day capture share (%), per 10 pp of forecast penetration. Rows "
          "without a dagger are the REGISTERED robustness set; rows marked † are EXPLORATORY. "
          "Unless stated, zone×year, zone×month and date fixed effects. p-values are WCB "
          "(Webb, 9,999 draws) except the two-way-clustered row (conventional).")
    return out


def scale_robustness(df):
    """EXPLORATORY: does 'solar raises V*' survive the identification checks?"""
    no_neg = df[df["negative_day"] == 0]
    variants = [
        ("log V* (registered)", df, "log_v_pf_2h", E.FE_MAIN, 3),
        ("log(1 + V*)", df, "log1p_v_pf_2h", E.FE_MAIN, 3),
        ("V* in €", df, "v_pf_2h_eur", E.FE_MAIN, 2),
        ("log V*, region × date FE", df, "log_v_pf_2h", FE_REGION_DATE, 3),
        ("log V*, zone × year × month FE", df, "log_v_pf_2h", FE_ZYM, 3),
        ("log V*, fixed load denominator", fixed_denominator(df), "log_v_pf_2h", E.FE_MAIN, 3),
        ("log V*, no negative-price days", no_neg, "log_v_pf_2h", E.FE_MAIN, 3),
    ]
    rows, out = [], {}
    for name, data, y, fe, dg in variants:
        r = estimate_outcome(data, y, fe=fe)
        out[name] = r
        rows.append([name, f"{r['b_wind']:.{dg}f} [{pfmt(r['wcb_wind'])}]",
                     f"{r['b_solar']:.{dg}f} [{pfmt(r['wcb_solar'])}]", f"{r['n']:,}"])
    table(TABLES / "t6_scale.md", ["Outcome / specification", "β wind [WCB p]", "β solar [WCB p]", "Zone-days"],
          rows,
          "The first row is REGISTERED (H3, no directional prediction); the rest are EXPLORATORY. "
          "Per 10 pp of forecast penetration. log(1+V*) and V* in € keep the zero-value days "
          "that log V* drops.")
    return out


def value_of_information(df):
    """EXPLORATORY: the value that needs information, in euros and in capture points."""
    outcomes = [("gap_td_2h", "V* − TD (€)"), ("gap_fc_2h", "V* − FC (€)"),
                ("gain_fc_2h", "FC − TD (€)"), ("capgain_fc_2h", "FC − TD (pp)")]
    res = [estimate_outcome(df, y) for y, _ in outcomes]
    regression_table(res, [lab for _, lab in outcomes], TABLES / "t7_information.md",
                     "EXPLORATORY. Euro outcomes are per MW per day for the 2-hour battery: the "
                     "value the typical-day and forecaster operators leave on the table, and the "
                     "forecaster's gain over typical day. The last column is the difference in "
                     "capture shares. Specification and inference as Table 2. " + STARS_NOTE + ".")
    return {y: r for (y, _), r in zip(outcomes, res)}


def mechanism_variants(df):
    """EXPLORATORY: separate amplitude from timing in the novelty result."""
    outcomes = [("novelty", "Novelty (Pearson)", 3), ("novelty_rank", "Novelty (rank)", 3),
                ("peak_shift", "Peak shift (h)", 3), ("trough_shift", "Trough shift (h)", 3)]
    res = [estimate_outcome(df, y) for y, _, _ in outcomes]
    res_rd = estimate_outcome(df, "novelty", fe=FE_REGION_DATE)
    regression_table(res + [res_rd], [lab for _, lab, _ in outcomes] + ["Novelty, region×date"],
                     TABLES / "t8_mechanism.md",
                     "EXPLORATORY except the first column (REGISTERED, H2). Rank novelty uses "
                     "Spearman rather than Pearson correlation with the typical-day profile, so it "
                     "responds to timing but not amplitude; peak and trough shifts are the hour "
                     "distances between the day's actual and typical maximum and minimum. The last "
                     "column replaces date with region×date fixed effects. " + STARS_NOTE + ".",
                     digits=[dg for _, _, dg in outcomes] + [3])
    return {**{y: r for (y, _, _), r in zip(outcomes, res)}, "novelty_region_date": res_rd}


def leave_one_out(df):
    rows = []
    for z in sorted(sample(df, "cap_td_2h")["zone"].unique()):
        r = estimate_outcome(df[df["zone"] != z], "cap_td_2h", bootstrap=False)
        rows.append({"dropped": z, "b_diff": r["b_diff"], "se_diff": r["se_diff"],
                     "b_wind": r["b_wind"], "b_solar": r["b_solar"]})
    return pd.DataFrame(rows)


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
    results = {"k_centre": df.attrs["k_centre"], "descriptives": descriptives(df)}
    steps = [("main", main_results), ("inference", inference_checks), ("fe_buildup", fe_buildup),
             ("placebo", placebo), ("heterogeneity", heterogeneity), ("robustness", robustness),
             ("scale", scale_robustness), ("information", value_of_information),
             ("mechanism", mechanism_variants)]
    for name, step in steps:
        results[name] = step(df)
        print(f"{name} done", flush=True)
    results["leave_one_out"] = leave_one_out(df).to_dict(orient="records")
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
