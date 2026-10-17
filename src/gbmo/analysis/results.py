"""Every table, figure and headline number in the paper, from the zone-day frame.

    python -m gbmo.analysis.panel_data      # build the frame first
    python -m gbmo.analysis.results         # everything
    python -m gbmo.analysis.results --figures
    python -m gbmo.analysis.results --extra placebo heterogeneity   # rerun named steps

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
    df["v_td_2h_eur"] = df["v_td_2h"]
    df["log_load_fc"] = np.log(df["load_fc_mwh"].where(df["load_fc_mwh"] > 0))
    df["zone_id"] = pd.factorize(df["zone"])[0]
    df["date_id"] = pd.factorize(df["date"], sort=True)[0]
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
    # Text columns align left and numeric ones right; the first column is always text
    text = [i == 0 or any(r[i][:1].isalpha() for r in rows[1:]) for i in range(len(widths))]
    return "|" + "|".join((":" + "-" * max(3, w)) if t else ("-" * max(3, w) + ":")
                          for w, t in zip(widths, text)) + "|"


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
    table(TABLES / "t01_descriptives.md", header, rows,
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
    regression_table(res, [lab for _, lab, _ in outcomes], TABLES / "t02_main.md",
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
    regression_table(res, [s for s, _ in specs], TABLES / "t04_fe_buildup.md",
                     "EXPLORATORY in presentation (the final column is the registered "
                     "specification). Outcome: typical-day capture share (%). Fixed effects "
                     "added left to right. Zone-clustered standard errors. Unlike Table 2, "
                     "stars here use conventional cluster-robust p-values, which overstate "
                     "significance with 18 clusters. " + STARS_NOTE + ".")
    return [{"fe": s, **r} for (s, _), r in zip(specs, res)]


def placebo_cell(e, digits):
    return f"{e['b']:.{digits}f} ({e['se']:.{digits}f}) [{pfmt(e['wcb'])}]"


def tost_p(b, se, bound, df_t):
    """Two one-sided tests of |beta| < bound; small p means equivalence is shown."""
    from scipy import stats
    if bound <= 0:
        return 1.0
    return float(max(stats.t.sf((b + bound) / se, df_t), stats.t.cdf((b - bound) / se, df_t)))


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
        # Equivalence: can the error coefficient be shown smaller than the forecast effect?
        entry["tost_error"] = tost_p(entry["error10"]["b"], entry["error10"]["se"],
                                     abs(entry["b_wind_main"]), df_t=17)
        out[y] = entry
        digits = 3 if y in ("log_v_pf_2h", "novelty") else 2
        rows.append([lab, f"{entry['b_wind_main']:.{digits}f}", placebo_cell(entry["error10"], digits),
                     f"{entry['tost_error']:.3f}",
                     *(placebo_cell(entry[t], digits) for t in ("wind_lead10", "solar_lead10"))])
    table(TABLES / "t08_placebo.md",
          ["Outcome", "Forecast wind (main)", "Wind forecast error", "Equivalence p",
           "Next day's wind", "Next day's solar"],
          rows,
          "The forecast-error column is REGISTERED; the lead columns are EXPLORATORY. Each "
          "placebo is added to the main specification. The forecast error is realised minus "
          "forecast wind; next day's wind and solar are day d+1's forecast penetration, "
          "published after day d's auction. Coefficient (zone-clustered s.e.) [WCB p-value]. "
          "Equivalence p is a two-one-sided test (EXPLORATORY) that the error coefficient lies "
          "within ± the absolute forecast-wind coefficient, with 17 degrees of freedom; a large "
          "value means the placebo cannot be distinguished from the effect it is meant to "
          "benchmark. Next-day forecasts exist at gate closure, so the lead columns test "
          "intertemporal dependence rather than serving as clean placebos; see the text.")
    return out


def heterogeneity(df):
    """H4 (registered, first row) and the referee's checks on it (exploratory)."""
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

    # Non-parametric: a separate wind slope for each tercile of zone-year K
    data = df.dropna(subset=["cap_td_2h", "wind10", "solar10", "k_wind"]).copy()
    zy = data.groupby("zone_year")["k_wind"].first()
    cuts = zy.quantile([1 / 3, 2 / 3]).to_numpy()
    data["k_tercile"] = np.digitize(data["k_wind"], cuts)
    for t in range(3):
        data[f"wind10_t{t}"] = data["wind10"] * (data["k_tercile"] == t)
    slopes = E.fit(data, "cap_td_2h", ["wind10_t0", "wind10_t1", "wind10_t2", "solar10"])
    xd = ["wind10", "wind10_t1", "wind10_t2", "solar10"]   # wind10_t2 is then high - low
    b_hl, se_hl, _ = E.tidy(E.fit(data, "cap_td_2h", xd), "wind10_t2")
    _, p_hl, *_ = E.wild_cluster_bootstrap(data, "cap_td_2h", xd, "wind10_t2", reps=REPS)
    top = data[data["k_tercile"] == 2].groupby("zone").size()
    out["terciles"] = {"cuts": cuts.tolist(), "n": int(slopes._N),
                       **{f"t{t}": dict(zip(("b", "se"), E.tidy(slopes, f"wind10_t{t}")[:2]))
                          for t in range(3)},
                       "high_minus_low": {"b": b_hl, "se": se_hl, "wcb": p_hl},
                       "top_tercile_zone_days": {z: int(n) for z, n in top.items()}}

    # The H4 analogue on the forecaster's gain over the calendar operator
    for y in ("capgain_fc_2h", "gain_fc_2h"):
        d = df.dropna(subset=[y, *x])
        m = E.fit(d, y, x)
        b, se, _ = E.tidy(m, "wind10_x_k")
        _, p, *_ = E.wild_cluster_bootstrap(d, y, x, "wind10_x_k", reps=REPS)
        out[f"fc_{y}"] = {"b_interaction": b, "se_interaction": se, "wcb_interaction": p,
                          "n": int(m._N)}

    def row(outcome, lab, b, se, p, n, dg=2):
        return [outcome, lab, f"{b:.{dg}f} ({se:.{dg}f})", "–" if p is None else pfmt(p), f"{n:,}"]

    def inter(key, outcome, lab):
        e = out[key]
        return row(outcome, lab, e["b_interaction"], e["se_interaction"], e["wcb_interaction"], e["n"])

    t, a = out["terciles"], out["all"]
    rows = [inter("all", "TD capture", "Wind × K, all 18 zones (registered)"),
            inter("without_DK_1", "TD capture", "Wind × K, without DK_1"),
            inter("without_DK", "TD capture", "Wind × K, without DK_1 and DK_2"),
            row("TD capture", "Wind effect at DK_1's K (registered model)",
                a["effect_at_dk1"]["b"], a["effect_at_dk1"]["se"], None, a["n"]),
            row("TD capture", "Wind slope, lowest tercile of K", t["t0"]["b"], t["t0"]["se"], None, t["n"]),
            row("TD capture", "Wind slope, middle tercile of K", t["t1"]["b"], t["t1"]["se"], None, t["n"]),
            row("TD capture", "Wind slope, highest tercile of K", t["t2"]["b"], t["t2"]["se"], None, t["n"]),
            row("TD capture", "Highest minus lowest tercile", t["high_minus_low"]["b"],
                t["high_minus_low"]["se"], t["high_minus_low"]["wcb"], t["n"]),
            inter("fc_capgain_fc_2h", "FC − TD (pp)", "Wind × K, all 18 zones"),
            inter("fc_gain_fc_2h", "FC − TD (€)", "Wind × K, all 18 zones")]
    table(TABLES / "t07_heterogeneity.md", ["Outcome", "Term", "Estimate (s.e.)", "WCB p", "Zone-days"], rows,
          "Interaction of forecast wind penetration (per 10 pp) with K, the zone-year's mean wind "
          "penetration (per 10 pp, centred at the estimation-sample mean). The first row is "
          "REGISTERED (H4); all others are EXPLORATORY. Tercile cut-points are over zone-years: "
          f"K below {cuts[0]:.1f}%, {cuts[0]:.1f}–{cuts[1]:.1f}%, and above {cuts[1]:.1f}%. The FC − TD "
          "rows ask whether the forecaster's advantage over the calendar operator grows with a "
          "system's wind share. Zone-clustered standard errors; – where no bootstrap was run.")
    return out


def identification_extras(df):
    """EXPLORATORY, at the referee's request: the load denominator, spatial spillovers,
    and Driscoll-Kraay standard errors."""
    import pyfixest as pf

    d = df.copy()
    # Neighbours: the leave-self-out mean penetration of the other zones in the same
    # coupling region on the same day. It varies within date, so date effects keep it.
    for v in ("wind10", "solar10"):
        grp = d.groupby(["region", "date"])[v]
        total, count = grp.transform("sum"), grp.transform("count")
        own = d[v].notna().astype(int)
        others = count - own
        d[f"{v}_nbr"] = ((total - d[v].fillna(0)) / others).where(others > 0)
    specs = [("Baseline", X_MAIN), ("+ log load forecast", X_MAIN + ["log_load_fc"]),
             ("+ neighbours' penetration", X_MAIN + ["wind10_nbr", "solar10_nbr"])]
    outcomes = [("cap_td_2h", "TD capture", 2), ("log_v_pf_2h", "log V*", 3), ("novelty", "Novelty", 3)]
    out, rows = {}, []
    for name, x in specs:
        cells, entry = [name], {}
        for y, _, dg in outcomes:
            data = d.dropna(subset=[y, *X_MAIN, "log_load_fc", "wind10_nbr", "solar10_nbr"])
            m = E.fit(data, y, x)
            res = {"n": int(m._N)}
            for term in x:
                b, se, _ = E.tidy(m, term)
                res[term] = {"b": b, "se": se}
            for term in X_MAIN:
                _, p, *_ = E.wild_cluster_bootstrap(data, y, x, term, reps=REPS)
                res[term]["wcb"] = p
                cells.append(f"{res[term]['b']:.{dg}f} [{pfmt(p)}]")
            entry[y] = res
        out[name] = entry
        rows.append(cells)
    header = ["Specification"] + [f"{lab}: {t}" for _, lab, _ in outcomes for t in ("wind", "solar")]
    n_common = out["Baseline"]["cap_td_2h"]["n"]
    table(TABLES / "t14_identification.md", header, rows,
          "EXPLORATORY. Coefficient per 10 pp [WCB p-value], main fixed effects, on the common "
          "sample where the load forecast and neighbours' penetration are defined "
          f"({n_common:,} zone-days for TD capture). Neighbours' penetration is the mean forecast "
          "penetration of the other zones in the same coupling region on the same day.")

    # The denominator itself: does forecast load move with the treatments?
    data = d.dropna(subset=["log_load_fc", *X_MAIN])
    m = E.fit(data, "log_load_fc", X_MAIN)
    out["load_on_treatments"] = {t: dict(zip(("b", "se", "p"), E.tidy(m, t))) for t in X_MAIN}
    # Driscoll-Kraay: robust to same-day dependence across all zones, but to serial
    # dependence only within the lag window, so it is not conservative in this design
    data = sample(df, "cap_td_2h")
    out["driscoll_kraay"] = {}
    for lag in (7, 28):
        m = pf.feols(f"cap_td_2h ~ {' + '.join(X_DIFF)} | {E.FE_MAIN}", data=data, vcov="DK",
                     vcov_kwargs={"lag": lag, "time_id": "date_id", "panel_id": "zone_id"})
        out["driscoll_kraay"][f"lag{lag}"] = dict(zip(("b", "se", "p"), E.tidy(m, "wind10")))
    return out


def cluster_leverage(df):
    """EXPLORATORY: each zone's partial leverage for the wind and solar coefficients
    (MacKinnon, Nielsen and Webb 2023). With 18 equal clusters each would be 1/18."""
    data = sample(df, "cap_td_2h").reset_index(drop=True)
    d, zones = E.demean(data, X_MAIN)
    out = {}
    for k, other in (("wind10", "solar10"), ("solar10", "wind10")):
        b = np.polyfit(d[other], d[k], 1)[0]
        r = d[k] - b * d[other]
        share = (r ** 2).groupby(zones).sum() / (r ** 2).sum()
        out[k] = share.to_dict()
    lev = pd.DataFrame(out).sort_values("solar10", ascending=False)
    days = data.groupby("zone").size()
    rows = [[z, f"{r['wind10']:.3f}", f"{r['solar10']:.3f}", f"{days[z]:,}"] for z, r in lev.iterrows()]
    table(TABLES / "t12_leverage.md", ["Zone", "Partial leverage, wind", "Partial leverage, solar", "Zone-days"],
          rows,
          "EXPLORATORY. Share of the residualised variation in each treatment (within the fixed "
          "effects, partialled on the other treatment) that each zone contributes, in the "
          "typical-day capture sample. Equal clusters would each have 0.056. Sorted by solar.")
    return out


QUANTILES = (0.25, 0.5, 0.75)
QR_BOOT = 199


def _two_step_quantiles(data, y, x, fe=E.FE_MAIN):
    """Canay (2011) two-step: strip the OLS fixed-effect component, then quantile-regress.

    The fixed effects are treated as pure location shifts, estimated once by OLS, which is
    the estimator's assumption. Returns {tau: coefficient vector} over `x`.
    """
    import statsmodels.api as sm

    ids = E._fe_ids(data, fe)
    raw = data[[y, *x]].to_numpy(dtype=float)
    d = E._demean_values(raw, ids)
    beta = np.linalg.lstsq(d[:, 1:], d[:, 0], rcond=None)[0]
    resid_level = raw[:, 0] - raw[:, 1:] @ beta            # y - X b = FE part + error
    fe_part = resid_level - E._demean_values(resid_level[:, None], ids)[:, 0]
    X = sm.add_constant(raw[:, 1:])
    return {q: sm.QuantReg(raw[:, 0] - fe_part, X).fit(q=q, max_iter=5000).params[1:]
            for q in QUANTILES}


def quantile_checks(df):
    """EXPLORATORY, at the referee's request: typical-day capture at its quartiles.

    The capture share is capped at 100 and unbounded below, so OLS means lean on the left
    tail. Inference is a pairs cluster bootstrap over zones (each draw re-estimates both
    steps; a zone drawn twice enters as two distinct zones with the same dates).
    """
    data = sample(df, "cap_td_2h").reset_index(drop=True)
    x = X_DIFF   # coefficient on wind10 is beta_w - beta_s; on vre10 it is beta_s
    point = _two_step_quantiles(data, "cap_td_2h", x)
    rng = np.random.default_rng(20260929)
    zones = data["zone"].unique()
    groups = {z: data[data["zone"] == z] for z in zones}
    draws = {q: [] for q in QUANTILES}
    for _ in range(QR_BOOT):
        pick = rng.choice(zones, size=len(zones), replace=True)
        parts = []
        for i, z in enumerate(pick):
            g = groups[z].copy()
            for col in ("zone", "zone_year", "zone_month"):
                g[col] = g[col] + f"#{i}"
            parts.append(g)
        boot = pd.concat(parts, ignore_index=True)
        for q, b in _two_step_quantiles(boot, "cap_td_2h", x).items():
            draws[q].append(b)
    out, rows = {}, []
    for q in QUANTILES:
        se = np.std(np.array(draws[q]), axis=0, ddof=1)
        diff, solar = point[q][0], point[q][1]
        # beta_w = (beta_w - beta_s) + beta_s; its s.e. from the same draws
        wind_draws = np.array(draws[q])[:, 0] + np.array(draws[q])[:, 1]
        out[str(q)] = {"b_diff": float(diff), "se_diff": float(se[0]),
                       "b_solar": float(solar), "se_solar": float(se[1]),
                       "b_wind": float(diff + solar), "se_wind": float(np.std(wind_draws, ddof=1))}
        e = out[str(q)]
        rows.append([f"Quantile {q:.2f}", f"{e['b_wind']:.2f} ({e['se_wind']:.2f})",
                     f"{e['b_solar']:.2f} ({e['se_solar']:.2f})", f"{e['b_diff']:.2f} ({e['se_diff']:.2f})"])
    main = E.fit(data, "cap_td_2h", X_MAIN)
    b_d, se_d, _ = E.tidy(E.fit(data, "cap_td_2h", X_DIFF), "wind10")
    rows.insert(0, ["Mean (OLS, Table 2)", *(f"{E.tidy(main, t)[0]:.2f} ({E.tidy(main, t)[1]:.2f})"
                                            for t in X_MAIN), f"{b_d:.2f} ({se_d:.2f})"])
    out["n"], out["reps"] = len(data), QR_BOOT
    table(TABLES / "t11_quantile.md", ["Estimator", "β wind", "β solar", "β wind − β solar"], rows,
          "EXPLORATORY. Outcome: typical-day capture share (%), per 10 pp. Quantile rows use "
          "the two-step estimator of Canay (2011): the fixed effects are estimated by OLS "
          "and removed as location shifts, then the quantile regression is run. Standard "
          f"errors from a pairs cluster bootstrap over zones ({QR_BOOT} draws, both steps "
          "re-estimated). The mean row uses zone-clustered standard errors.")
    return out


def with_weather(df):
    """The frame with weather instruments, scaled to penetration units.

    Each instrument is the day's weather relative to its zone-year mean, times the
    zone-year's mean forecast penetration: z = w / mean_zy(w) * mean_zy(pen). It varies
    within a zone-year only through weather, and the scaling puts it in the treatment's
    units so that a first-stage coefficient near 1 means the weather proxy tracks the
    forecast one for one.
    """
    from gbmo.analysis.weather_days import WEATHER_PATH

    w = pd.read_parquet(WEATHER_PATH)
    w["delivery_date"] = w["delivery_date"].astype(str)
    d = df.copy()
    d["_date"] = d["delivery_date"].astype(str)
    d = d.merge(w.rename(columns={"delivery_date": "_date"}), on=["zone", "_date"], how="left")
    for proxy, pen, z in (("wind_cf", "wind_pen", "zw10"), ("solar_kwh", "solar_pen", "zs10")):
        valid = d[proxy].notna() & d[pen].notna()
        mean_w = d[proxy].where(valid).groupby(d["zone_year"]).transform("mean")
        mean_p = d[pen].where(valid).groupby(d["zone_year"]).transform("mean")
        d[z] = np.where(valid & (mean_w > 0), d[proxy] / mean_w * mean_p / 10,
                        np.where(valid, 0.0, np.nan))
    return d


def iv_2sls(data, y, x, z, fe=E.FE_MAIN):
    """2SLS with several endogenous regressors on fixed-effect-demeaned data.

    pyfixest instruments only one endogenous variable, and the weather design has two.
    Demeaning y, x and z on the fixed effects first is exact by Frisch-Waugh-Lovell.
    Zone-clustered standard errors with the usual small-sample factor.
    Returns {name: (coef, se, p)} over `x`.
    """
    from scipy import stats

    d = E._demean_values(data[[y, *x, *z]].to_numpy(dtype=float), E._fe_ids(data, fe))
    Y, X, Z = d[:, 0], d[:, 1:1 + len(x)], d[:, 1 + len(x):]
    Xhat = Z @ np.linalg.lstsq(Z, X, rcond=None)[0]
    bread = np.linalg.inv(Xhat.T @ X)
    beta = bread @ Xhat.T @ Y
    u = Y - X @ beta
    groups = pd.factorize(data["zone"])[0]
    G, n, k = groups.max() + 1, len(Y), len(x)
    scores = np.zeros((G, k))
    np.add.at(scores, groups, Xhat * u[:, None])
    # Degrees of freedom as pyfixest counts them, so these standard errors are comparable
    # with Table 2's: fixed effects nested in the zone clusters cost nothing, the others
    # (date) cost one per level beyond the first
    k_fe = sum(data[f].nunique() - 1 for f in fe.split(" + ")
               if (data.groupby(f)["zone"].nunique() > 1).any())
    c = G / (G - 1) * (n - 1) / (n - k - k_fe)
    V = c * bread @ (scores.T @ scores) @ bread.T
    se = np.sqrt(np.diag(V))
    p = 2 * stats.t.sf(np.abs(beta / se), G - 1)
    return {name: (float(b), float(s_), float(pv)) for name, b, s_, pv in zip(x, beta, se, p)}


def weather_iv(df):
    """EXPLORATORY, at the referee's request: identification from realised weather.

    Reduced form: outcomes on the weather instruments directly, with WCB p-values. With
    two instruments for two treatments this is the weak-instrument-robust test of each
    treatment's effect. 2SLS: the forecast penetrations instrumented by weather, with
    zone-clustered standard errors.
    """
    d = with_weather(df)
    Z = ["zw10", "zs10"]
    base = d.dropna(subset=["wind10", "solar10", *Z])
    out = {"first_stage": {}}
    for t in X_MAIN:
        m = E.fit(base, t, Z)
        wald = m.wald_test(R=np.eye(2))
        out["first_stage"][t] = {z: dict(zip(("b", "se", "p"), E.tidy(m, z))) for z in Z}
        out["first_stage"][t]["F"] = float(wald["statistic"])
    outcomes = [("cap_td_2h", "TD capture", 2), ("log_v_pf_2h", "log V*", 3),
                ("novelty", "Novelty", 3), ("gap_td_2h", "V* − TD (€)", 2),
                ("capgain_fc_2h", "FC − TD (pp)", 2)]
    rows = []
    for y, lab, dg in outcomes:
        data = base.dropna(subset=[y])
        entry = {"n": len(data)}
        for x, key in ((X_MAIN, "iv"), (X_DIFF, "iv_diff")):
            entry[key] = {t: dict(zip(("b", "se", "p"), v))
                          for t, v in iv_2sls(data, y, x, Z).items()}
        rf = E.fit(data, y, Z)
        entry["reduced_form"] = {}
        for z in Z:
            b, se, _ = E.tidy(rf, z)
            _, p, *_ = E.wild_cluster_bootstrap(data, y, Z, z, reps=REPS)
            entry["reduced_form"][z] = {"b": b, "se": se, "wcb": p}
        out[y] = entry
        iv, rfz = entry["iv"], entry["reduced_form"]
        rows.append([lab,
                     f"{iv['wind10']['b']:.{dg}f} ({iv['wind10']['se']:.{dg}f})",
                     f"{iv['solar10']['b']:.{dg}f} ({iv['solar10']['se']:.{dg}f})",
                     f"{entry['iv_diff']['wind10']['b']:.{dg}f} ({entry['iv_diff']['wind10']['se']:.{dg}f})",
                     pfmt(rfz["zw10"]["wcb"]), pfmt(rfz["zs10"]["wcb"]), f"{len(data):,}"])
    fs = out["first_stage"]
    table(TABLES / "t15_weather.md",
          ["Outcome", "β wind (IV)", "β solar (IV)", "β wind − β solar (IV)",
           "Wind weather: RF p", "Solar weather: RF p", "Zone-days"], rows,
          "EXPLORATORY. Forecast wind and solar penetration instrumented by ERA5 reanalysis "
          "weather at fixed points in each zone: a notional turbine's capacity factor at 100 m "
          "and daily shortwave radiation, each scaled by its zone-year mean penetration. Main "
          "fixed effects; zone-clustered standard errors in parentheses. RF p is the WCB "
          "p-value of the weather instrument in the reduced form (the outcome regressed on "
          "the instruments), which is robust to weak instruments. First stage: wind "
          f"penetration on wind weather {fs['wind10']['zw10']['b']:.2f} "
          f"(s.e. {fs['wind10']['zw10']['se']:.2f}), joint F = {fs['wind10']['F']:.0f}; solar "
          f"penetration on solar weather {fs['solar10']['zs10']['b']:.2f} "
          f"(s.e. {fs['solar10']['zs10']['se']:.2f}), joint F = {fs['solar10']['F']:.0f}.")
    return out


def shape_forecaster(df):
    """EXPLORATORY, at the referee's request: a forecaster aimed at what arbitrage pays for.

    `gbm_shape` is trained on the within-day price shape, not the level. If wind-driven
    value were informational but our squared-error forecaster simply failed to extract it,
    a shape-targeted forecaster should gain more on windy days. Rank correlations between
    each plan and the realised prices measure directly how well each operator orders the
    day's hours, which is what capture depends on (Falezza 2026).
    """
    d = df.copy()
    d["gain_fcs_2h"] = d["v_fcs_2h"] - d["v_td_2h"]
    d["capgain_fcs_2h"] = d["cap_fcs_2h"] - d["cap_td_2h"]
    d["rho_gain_fc"] = d["rho_fc"] - d["rho_td"]
    d["rho_gain_fcs"] = d["rho_fcs"] - d["rho_td"]
    outcomes = [("capgain_fc_2h", "FC − TD (pp)", 2), ("capgain_fcs_2h", "Shape − TD (pp)", 2),
                ("gain_fcs_2h", "Shape − TD (€)", 2), ("rho_td", "Rank corr., TD", 3),
                ("rho_gain_fc", "Rank gain, FC", 3), ("rho_gain_fcs", "Rank gain, shape", 3)]
    res = [estimate_outcome(d, y) for y, _, _ in outcomes]
    regression_table(res, [lab for _, lab, _ in outcomes], TABLES / "t06_shape.md",
                     "EXPLORATORY. 'Shape' is the forecaster trained on the within-day price "
                     "shape (each day's mean removed from the target); FC is the registered "
                     "forecaster. Capture gains are differences in capture shares (percentage "
                     "points) over the typical-day operator; the euro gain is per MW per day. "
                     "Rank correlation is Spearman's, across the day's hours, between an "
                     "operator's plan prices and realised prices; rank gains are over the "
                     "typical-day plan. Specification and inference as Table 2. " + STARS_NOTE + ".",
                     digits=[dg for _, _, dg in outcomes])
    common = d.dropna(subset=["cap_td_2h", "cap_fc_2h", "cap_fcs_2h"])
    out = {y: r for (y, _, _), r in zip(outcomes, res)}
    out["summary"] = {
        "n_common": len(common),
        "cap_td": float(common["cap_td_2h"].mean()), "cap_fc": float(common["cap_fc_2h"].mean()),
        "cap_fcs": float(common["cap_fcs_2h"].mean()),
        **{f"vw_{k}": float(100 * common[f"v_{k}_2h"].sum() / common["v_pf_2h"].sum())
           for k in ("td", "fc", "fcs")},
        "gain_fc_eur": float((common["v_fc_2h"] - common["v_td_2h"]).mean()),
        "gain_fcs_eur": float((common["v_fcs_2h"] - common["v_td_2h"]).mean()),
        **{f"rho_{k}": float(d[f"rho_{k}"].mean()) for k in ("td", "fc", "fcs")},
    }
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
    table(TABLES / "t10_robustness.md",
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
        ("V_TD in €", df, "v_td_2h_eur", E.FE_MAIN, 2),
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
    table(TABLES / "t13_scale.md", ["Outcome / specification", "β wind [WCB p]", "β solar [WCB p]", "Zone-days"],
          rows,
          "The first row is REGISTERED (H3, no directional prediction); the rest are EXPLORATORY. "
          "Per 10 pp of forecast penetration. log(1+V*) and V* in € keep the zero-value days "
          "that log V* drops. V_TD is the typical-day operator's revenue; it is reported in euros "
          "because it is zero or negative on 7% of zone-days, which a log would drop.")
    return out


def value_of_information(df):
    """EXPLORATORY: the value that needs information, in euros and in capture points."""
    outcomes = [("gap_td_2h", "V* − TD (€)"), ("gap_fc_2h", "V* − FC (€)"),
                ("gain_fc_2h", "FC − TD (€)"), ("capgain_fc_2h", "FC − TD (pp)")]
    res = [estimate_outcome(df, y) for y, _ in outcomes]
    regression_table(res, [lab for _, lab in outcomes], TABLES / "t05_information.md",
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
                     TABLES / "t03_mechanism.md",
                     "EXPLORATORY except the first column (REGISTERED, H2). Rank novelty uses "
                     "Spearman rather than Pearson correlation with the typical-day profile, so it "
                     "responds to timing but not amplitude; peak and trough shifts are the hour "
                     "distances between the day's actual and typical maximum and minimum. The last "
                     "column replaces date with region×date fixed effects. " + STARS_NOTE + ".",
                     digits=[dg for _, _, dg in outcomes] + [3])
    return {**{y: r for (y, _, _), r in zip(outcomes, res)}, "novelty_region_date": res_rd}


def lead_conditional(df):
    """EXPLORATORY: today's coefficients holding tomorrow's forecast penetration fixed.

    Tomorrow's forecasts turned out not to be a valid placebo. Weather forecasts for d+1
    exist when day d's auction clears, and prices with hydro reservoirs and multi-day
    commitment respond to anticipated wind. So the lead is a test of intertemporal
    dependence, and conditioning on it separates day-specific effects from multi-day
    weather regimes.
    """
    x = ["wind10", "solar10", "wind_lead10", "solar_lead10"]
    outcomes = [("cap_td_2h", "TD capture", 2), ("log_v_pf_2h", "log V*", 3),
                ("novelty", "Novelty", 3), ("spread", "Spread (€)", 2), ("gap_td_2h", "V* − TD (€)", 2)]
    rows, out = [], {}
    for y, lab, dg in outcomes:
        data = df.dropna(subset=[y, *x])
        m = E.fit(data, y, x)
        entry = {}
        for term in ("wind10", "solar10"):
            b, se, _ = E.tidy(m, term)
            _, p, *_ = E.wild_cluster_bootstrap(data, y, x, term, reps=REPS)
            entry[term] = {"b": b, "se": se, "wcb": p}
        base = E.fit(data, y, X_MAIN)
        entry["wind_uncond"], entry["solar_uncond"] = E.tidy(base, "wind10")[0], E.tidy(base, "solar10")[0]
        entry["n"] = int(m._N)
        out[y] = entry
        rows.append([lab, f"{entry['wind_uncond']:.{dg}f}",
                     f"{entry['wind10']['b']:.{dg}f} ({entry['wind10']['se']:.{dg}f}) [{pfmt(entry['wind10']['wcb'])}]",
                     f"{entry['solar_uncond']:.{dg}f}",
                     f"{entry['solar10']['b']:.{dg}f} ({entry['solar10']['se']:.{dg}f}) [{pfmt(entry['solar10']['wcb'])}]",
                     f"{entry['n']:,}"])
    d, _ = E.demean(df.dropna(subset=["wind10", "wind_lead10"]), ["wind10", "wind_lead10"])
    out["wind_persistence"] = float(d.corr().iloc[0, 1])
    table(TABLES / "t09_lead.md",
          ["Outcome", "Wind", "Wind, given tomorrow", "Solar", "Solar, given tomorrow", "Zone-days"], rows,
          "EXPLORATORY. Columns 2 and 4 repeat the main-specification coefficients on the same "
          "sample; columns 3 and 5 add the next day's forecast wind and solar penetration as "
          "controls. Coefficient (zone-clustered s.e.) [WCB p-value]. Within the fixed effects, "
          f"today's and tomorrow's forecast wind penetration correlate at {out['wind_persistence']:.2f}.")
    return out


STEPS = {"placebo": placebo, "heterogeneity": heterogeneity, "scale": scale_robustness,
         "lead_conditional": lead_conditional, "identification": identification_extras,
         "leverage": cluster_leverage, "quantile": quantile_checks,
         "weather": weather_iv, "shape": shape_forecaster}


def extra_only(names):
    """Rerun the named steps alone and merge them into results.json."""
    path = PAPER / "results.json"
    results = json.loads(path.read_text(encoding="utf-8"))
    df = load()
    for name in names:
        results[name] = STEPS[name](df)
        print(f"{name} written", flush=True)
    path.write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")


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
                    "cap_td": float(row["cap_td_2h"]), "v_pf": float(row["v_pf_2h"]),
                    "spread": float(row["spread"])} for title, row, _ in picks} | {
        "DE_LU 2024": {"v_pf_mean": float(zone["v_pf_2h"].mean()),
                       "novelty_mean": float(zone["novelty"].mean()),
                       "spread_mean": float(zone["spread"].mean())}}


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
             ("mechanism", mechanism_variants), ("lead_conditional", lead_conditional),
             ("identification", identification_extras), ("leverage", cluster_leverage),
             ("quantile", quantile_checks), ("weather", weather_iv),
             ("shape", shape_forecaster)]
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

    if "--figures" in sys.argv:
        figures_only()
    elif "--extra" in sys.argv:
        extra_only(sys.argv[sys.argv.index("--extra") + 1:])
    else:
        main()
