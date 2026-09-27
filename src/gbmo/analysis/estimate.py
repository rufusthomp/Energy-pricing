"""Estimation for the wind/solar composition study.

Every specification here is pre-registered in docs/preregistration.md; anything added
after results were seen is marked exploratory where it is reported.

Inference. Standard errors are clustered by zone. With 18 clusters the reported p-values
for key coefficients come from a wild cluster bootstrap (WCB) with Webb six-point weights
and the null imposed (WCR), computed on the fixed-effect-demeaned data. Frisch-Waugh-Lovell
makes that equivalent to bootstrapping the full model with the fixed effects as nuisance
parameters, and it avoids refitting ~3,000 date dummies 9,999 times.
"""

import numpy as np
import pandas as pd
import pyfixest as pf

FE_MAIN = "zone_year + zone_month + date"
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def fit(df, y, x, fe=FE_MAIN, vcov=None):
    """OLS with high-dimensional fixed effects, zone-clustered by default."""
    rhs = " + ".join(x)
    formula = f"{y} ~ {rhs}" + (f" | {fe}" if fe else "")
    data = df.dropna(subset=[y, *x])
    return pf.feols(formula, data=data, vcov=vcov or {"CRV1": "zone"})


def demean(df, cols, fe=FE_MAIN):
    """Columns residualised on the fixed effects (alternating projections)."""
    data = df.dropna(subset=cols).reset_index(drop=True)
    fe_ids = pd.DataFrame({f: pd.factorize(data[f])[0] for f in fe.split(" + ")})
    values = data[cols].to_numpy(dtype=float)
    weights = np.ones(len(data))
    demeaned, success = pf.estimation.demean(values, fe_ids.to_numpy(dtype=np.uint64), weights,
                                              tol=1e-10)
    if not success:
        raise RuntimeError("fixed-effect demeaning did not converge")
    return pd.DataFrame(demeaned, columns=cols), data["zone"].to_numpy()


def wild_cluster_bootstrap(df, y, x, param, fe=FE_MAIN, reps=9999, seed=20260927):
    """WCR p-value for H0: coefficient on `param` = 0. Webb weights, clustered by zone.

    Restricted residuals (null imposed) are resampled with one Webb draw per cluster; the
    statistic is the cluster-robust t. Returns (t_observed, p_value, n_clusters).
    """
    d, clusters = demean(df, [y, *x], fe)
    Y, X = d[y].to_numpy(), d[x].to_numpy()
    k = x.index(param)
    groups, inverse = np.unique(clusters, return_inverse=True)
    G = len(groups)
    n, p = X.shape
    # The design never changes between draws, so its inverse and projection are computed
    # once; each draw is then two matrix-vector products and a cluster sum.
    xtx_inv = np.linalg.inv(X.T @ X)
    projection = xtx_inv @ X.T
    small_sample = G / (G - 1) * (n - 1) / (n - p)
    # Cluster membership as a sparse-free summing matrix: scores = M @ (X * u)
    membership = np.zeros((G, n))
    membership[inverse, np.arange(n)] = 1.0

    def cluster_t(yv):
        beta = projection @ yv
        u = yv - X @ beta
        scores = membership @ (X * u[:, None])
        v = small_sample * xtx_inv @ (scores.T @ scores) @ xtx_inv
        return beta[k] / np.sqrt(v[k, k])

    t_obs = cluster_t(Y)
    Xr = np.delete(X, k, axis=1)
    beta_r, *_ = np.linalg.lstsq(Xr, Y, rcond=None) if Xr.shape[1] else (np.zeros(0),)
    fitted_r = Xr @ beta_r if Xr.shape[1] else np.zeros_like(Y)
    u_r = Y - fitted_r

    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(reps):
        w = rng.choice(WEBB, size=G)[inverse]
        if abs(cluster_t(fitted_r + u_r * w)) >= abs(t_obs):
            exceed += 1
    return float(t_obs), (exceed + 1) / (reps + 1), G


def tidy(model, param):
    """(coef, se, p) for one parameter of a fitted pyfixest model."""
    t = model.tidy()
    row = t.loc[param]
    return float(row["Estimate"]), float(row["Std. Error"]), float(row["Pr(>|t|)"])
