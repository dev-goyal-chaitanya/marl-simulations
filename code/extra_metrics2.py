import json, pickle, numpy as np
from stopping import CostModel, COMM_LEVELS, evaluate_stop, oracle_stop
E = json.load(open("results/extra_metrics.json"))
rules = pickle.load(open("results/rules.pkl", "rb"))
names = [r.name for r in rules]
gen = E["generalisation"]
rng = np.random.default_rng(1)
def iqm(x):
    x = np.sort(x); n = len(x); lo, hi = int(np.floor(n*0.25)), int(np.ceil(n*0.75))
    return x[lo:hi].mean()
out = {}
L = np.array([g["Learned value-aware stopping"] for g in gen])
for n in names:
    v = np.array([g[n] for g in gen])
    B = [iqm(v[rng.integers(0, 36, 36)]) for _ in range(3000)]
    out[n] = dict(iqm=float(iqm(v)), iqm_ci=[float(np.percentile(B, 2.5)), float(np.percentile(B, 97.5))],
                  opt_gap=float(np.mean(100 - np.minimum(v, 100))),
                  n_ge80=int((v >= 80).sum()), n_ge90=int((v >= 90).sum()),
                  p_learned_better=float((L > v).mean()) if n != names[-1] else None,
                  stoperr_mean=float(np.mean([g[n + "|stoperr"] for g in gen])))
    print(f"{n[:30]:30s}", {k: (round(x, 2) if isinstance(x, float) else x) for k, x in out[n].items()})
print("learned stop error by robots/size:")
for g in gen:
    if g["comm"] == "medium":
        print(g["size"], g["n"], "learned err", round(g["Learned value-aware stopping|stoperr"], 1),
              "coverage err", round(g["Coverage threshold (tuned)|stoperr"], 1))
# pooled in-distribution: test (100) + gen_32_2 medium (40)
cost = CostModel(c_comm=COMM_LEVELS["medium"])
for label, trajs in [("test100", pickle.load(open("results/test.pkl", "rb"))),
                     ("gen40", pickle.load(open("results/gen_32_2.pkl", "rb")))]:
    trajs_all = trajs
    o = np.array([evaluate_stop(t, cost, oracle_stop(t, cost))["value"] for t in trajs_all])
    vals = {r.name: np.array([evaluate_stop(t, cost, r.stop_time(t, cost))["value"] for t in trajs_all]) for r in rules}
    idx = rng.integers(0, len(o), (5000, len(o)))
    for n in ["Coverage threshold (tuned)", "Learned value-aware stopping"]:
        v = vals[n]
        ci = np.percentile(100 * v[idx].sum(1) / o[idx].sum(1), [2.5, 97.5])
        print(label, n, round(100 * v.sum() / o.sum(), 1), np.round(ci, 1))
    d = 100 * (vals["Learned value-aware stopping"][idx].sum(1) - vals["Coverage threshold (tuned)"][idx].sum(1)) / o[idx].sum(1)
    print(label, "learned-coverage diff CI", np.round(np.percentile(d, [2.5, 97.5]), 1))
    if label == "test100": T1 = (o, vals)
    else: T2 = (o, vals)
o = np.r_[T1[0], T2[0]]
vals = {k: np.r_[T1[1][k], T2[1][k]] for k in T1[1]}
idx = rng.integers(0, len(o), (5000, len(o)))
for n in names:
    v = vals[n]
    ci = np.percentile(100 * v[idx].sum(1) / o[idx].sum(1), [2.5, 97.5])
    print("pooled140", n[:30], round(100 * v.sum() / o.sum(), 1), np.round(ci, 1))
d = 100 * (vals[names[-1]][idx].sum(1) - vals["Coverage threshold (tuned)"][idx].sum(1)) / o[idx].sum(1)
print("pooled diff CI", np.round(np.percentile(d, [2.5, 97.5]), 1))
E["robust_generalisation"] = out
E["pooled_in_distribution_140"] = {n: float(100 * vals[n].sum() / o.sum()) for n in names}
json.dump(E, open("results/extra_metrics.json", "w"), indent=1)
