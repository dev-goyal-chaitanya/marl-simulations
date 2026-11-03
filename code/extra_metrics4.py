"""Control: re-tune the coverage threshold and gain-vs-cost rule separately for every test setting,
on that setting's own 40 maps (optimistic: tuned on the test data). Shows what re-tuning buys."""
import json, pickle, numpy as np
from stopping import CostModel, COMM_LEVELS, evaluate_stop, oracle_stop, CoverageThreshold, InfoGainHeuristic, FixedBudget
E = json.load(open("results/extra_metrics.json"))
out = {"Coverage threshold (re-tuned per setting)": [], "Info-gain vs cost (re-tuned per setting)": [],
       "Fixed budget (re-tuned per setting)": []}
pctv = {k: [] for k in out}
for size in (32, 48, 64):
    for n in (2, 4, 6, 8):
        tr = pickle.load(open(f"results/gen_{size}_{n}.pkl", "rb"))
        cells = np.array([sum(o["gain"] for o in t["outcomes"]) for t in tr], float)
        for lvl, c in COMM_LEVELS.items():
            cm = CostModel(c_comm=c)
            ov = np.array([evaluate_stop(t, cm, oracle_stop(t, cm))["value"] for t in tr])
            for name, R in zip(out, (CoverageThreshold, InfoGainHeuristic, FixedBudget)):
                r = R().fit(tr, cm)
                v = np.array([evaluate_stop(t, cm, r.stop_time(t, cm))["value"] for t in tr])
                out[name].append(float(np.mean(100 * (ov - v) / cells)))
                pctv[name].append(float(100 * v.sum() / ov.sum()))
def iqm(x):
    x = np.sort(x); n = len(x); return x[int(n * .25):int(np.ceil(n * .75))].mean()
res = {}
for k in out:
    v, p = np.array(out[k]), np.array(pctv[k])
    res[k] = dict(mean_regret=float(v.mean()), worst_regret=float(v.max()), iqm=float(iqm(p)),
                  n_ge80=int((p >= 80).sum()), n_below50=int((p < 50).sum()), worst_pct=float(p.min()))
    print(k, {a: round(b, 1) for a, b in res[k].items()})
E["retuned_per_setting"] = res
json.dump(E, open("results/extra_metrics.json", "w"), indent=1)
