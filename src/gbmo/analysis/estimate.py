"""Estimation for the wind/solar composition study.

Every specification here is pre-registered in docs/preregistration.md; anything added
after results were seen is marked exploratory where it is reported.

Inference. Standard errors are clustered by zone. With 18 clusters the reported p-values
for key coefficients come from a wild cluster restricted bootstrap (WCR) with Webb
six-point weights, computed on fixed-effect-demeaned data.

Demeaning once is valid for the coefficient but not, on its own, for the variance. By
Frisch-Waugh-Lovell the bootstrap coefficient is unchanged whether or not the bootstrap
outcome is re-projected off the fixed effects. But date effects are not nested within zone
clusters, so the reweighted residual u_r * w is no longer orthogonal to them, and without
re-projection every bootstrap t-statistic uses the wrong residuals. An earlier version of
this module made exactly that mistake, which a referee caught. It understated every WCB
p-value (H1 0.099 against a correct 0.120). The fix is cheap because demeaning is linear:
M_D(u_r * w) = sum_g w_g M_D(u_r * 1_g), so the G cluster-restricted vectors are demeaned
once and each draw is a linear combination of them.
"""

import itertools

import numpy as np
import pandas as pd
import pyfixest as pf

FE_MAIN = "zone_year + zone_month + date"
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
BATCH = 250


def fit(df, y, x, fe=FE_MAIN, vcov=None):
    """OLS with high-dimensional fixed effects, zone-clustered by default."""
    rhs = " + ".join(x)
    formula = f"{y} ~ {rhs}" + (f" | {fe}" if fe else "")
    data = df.dropna(subset=[y, *x])
    return pf.feols(formula, data=data, vcov=vcov or {"CRV1": "zone"})


def _fe_ids(data, fe):
    return pd.DataFrame({f: pd.factorize(data[f])[0] for f in fe.split(" + ")}).to_numpy(dtype=np.uint64)


def _demean_values(values, fe_ids):
    demeaned, success = pf.estimation.demean(np.ascontiguousarray(values, dtype=float), fe_ids,
                                             np.ones(values.shape[0]), tol=1e-10)
    if not success:
        raise RuntimeError("fixed-effect demeaning did not converge")
    return demeaned


def demean(df, cols, fe=FE_MAIN):
    """Columns residualised on the fixed effects (alternating projections)."""
    data = df.dropna(subset=cols).reset_index(drop=True)
    demeaned = _demean_values(data[cols].to_numpy(dtype=float), _fe_ids(data, fe))
    return pd.DataFrame(demeaned, columns=cols), data["zone"].to_numpy()


def wild_cluster_bootstrap(df, y, x, param, fe=FE_MAIN, reps=9999, seed=20260927,
                           weights="webb", enumerate_all=False):
    """WCR p-value for H0: coefficient on `param` = 0, clustered by zone.

    weights="webb" draws `reps` six-point Webb weights per cluster. weights="rademacher"
    with enumerate_all=True evaluates every one of the 2^G sign patterns exactly, which
    at G = 18 is 262,144 and removes simulation error entirely.
    Returns (t_observed, p_value, n_clusters, n_draws).
    """
    data = df.dropna(subset=[y, *x]).reset_index(drop=True)
    fe_ids = _fe_ids(data, fe) if fe else None
    raw = data[[y, *x]].to_numpy(dtype=float)
    d = _demean_values(raw, fe_ids) if fe else raw - raw.mean(axis=0)
    Y, X = d[:, 0], d[:, 1:]
    k = x.index(param)
    groups, inverse = np.unique(data["zone"].to_numpy(), return_inverse=True)
    G = len(groups)
    n, p = X.shape

    # Only the variance of coefficient k is needed. With A = (X'X)^-1 and h = X A e_k,
    # var_k = c * sum_g (sum_{i in g} h_i u_i)^2, so each draw needs one cluster sum.
    xtx_inv = np.linalg.inv(X.T @ X)
    projection = xtx_inv @ X.T
    h = X @ xtx_inv[:, k]
    c = G / (G - 1) * (n - 1) / (n - p)
    membership = np.zeros((G, n))
    membership[inverse, np.arange(n)] = 1.0

    def t_stats(Yb):
        betas = projection @ Yb
        U = Yb - X @ betas
        q = membership @ (h[:, None] * U)
        return betas[k] / np.sqrt(c * (q ** 2).sum(axis=0))

    t_obs = float(t_stats(Y[:, None])[0])

    # Null imposed: restricted fit without `param`
    Xr = np.delete(X, k, axis=1)
    beta_r = np.linalg.lstsq(Xr, Y, rcond=None)[0] if Xr.shape[1] else np.zeros(0)
    fitted_r = Xr @ beta_r if Xr.shape[1] else np.zeros_like(Y)
    u_r = Y - fitted_r
    # Re-project each cluster's reweightable residual block off the fixed effects
    blocks = np.zeros((n, G))
    blocks[np.arange(n), inverse] = u_r
    Z = _demean_values(blocks, fe_ids) if fe else blocks - blocks.mean(axis=0)

    if enumerate_all:
        if weights != "rademacher":
            raise ValueError("full enumeration is defined for Rademacher weights")
        patterns = np.array(list(itertools.product((-1.0, 1.0), repeat=G)))
    else:
        rng = np.random.default_rng(seed)
        support = WEBB if weights == "webb" else np.array([-1.0, 1.0])
        patterns = rng.choice(support, size=(reps, G))

    exceed = 0
    for start in range(0, len(patterns), BATCH):
        W = patterns[start:start + BATCH]
        Yb = fitted_r[:, None] + Z @ W.T
        exceed += int((np.abs(t_stats(Yb)) >= abs(t_obs) - 1e-12).sum())
    n_draws = len(patterns)
    # Enumeration includes the identity pattern, so the observed statistic is already one
    # of the draws; with random draws it is added, as usual for a bootstrap p-value.
    p_value = exceed / n_draws if enumerate_all else (exceed + 1) / (n_draws + 1)
    return t_obs, p_value, G, n_draws


def tidy(model, param):
    """(coef, se, p) for one parameter of a fitted pyfixest model."""
    t = model.tidy()
    row = t.loc[param]
    return float(row["Estimate"]), float(row["Std. Error"]), float(row["Pr(>|t|)"])
