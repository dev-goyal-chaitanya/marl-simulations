"""Extra evaluation metrics on the cached runs: per-map scores, regret, stop-time error,
win rate, bootstrap confidence intervals. Writes results/extra_metrics.json."""
import json, pickle
import numpy as np
from stopping import CostModel, COMM_LEVELS, evaluate_stop, oracle_stop, rewards

rules = pickle.load(open("results/rules.pkl", "rb"))
names = [r.name for r in rules]
rng = np.random.default_rng(0)


def per_map(trajs, cost):
    out = {}
    orc = np.array([evaluate_stop(tr, cost, oracle_stop(tr, cost))["value"] for tr in trajs])
    t_orc = np.array([oracle_stop(tr, cost) for tr in trajs])
    for r in rules:
        ts = np.array([r.stop_time(tr, cost) for tr in trajs])
        ev = [evaluate_stop(tr, cost, t) for tr, t in zip(trajs, ts)]
        v = np.array([e["value"] for e in ev])
        out[r.name] = dict(value=v, t=ts, cov=np.array([e["coverage"] for e in ev]),
                           steps=np.array([e["steps"] for e in ev]))
    return orc, t_orc, out


def boot_ratio(v, o, B=5000):
    idx = rng.integers(0, len(v), (B, len(v)))
    return np.percentile(100 * v[idx].sum(1) / o[idx].sum(1), [2.5, 97.5])


def boot_diff(v1, v2, o, B=5000):
    idx = rng.integers(0, len(v1), (B, len(v1)))
    d = 100 * (v1[idx].sum(1) - v2[idx].sum(1)) / o[idx].sum(1)
    return np.percentile(d, [2.5, 97.5])


test = pickle.load(open("results/test.pkl", "rb"))
cost = CostModel(c_comm=COMM_LEVELS["medium"])
orc, t_orc, pm = per_map(test, cost)
L = pm["Learned value-aware stopping"]
res = {"in_distribution": {}}
for n, d in pm.items():
    v = d["value"]
    ratio = 100 * v / orc
    err = d["t"] - t_orc
    res["in_distribution"][n] = dict(
        pct_total=float(100 * v.sum() / orc.sum()),
        ci95=[float(x) for x in boot_ratio(v, orc)],
        mean_per_map_pct=float(ratio.mean()),
        median_per_map_pct=float(np.median(ratio)),
        p10_per_map_pct=float(np.percentile(ratio, 10)),
        share_maps_ge90=float((ratio >= 90).mean()),
        mean_regret_cells=float((orc - v).mean()),
        mean_stop_error_cycles=float(err.mean()),
        mean_abs_stop_error=float(np.abs(err).mean()),
        share_early=float((err < 0).mean()), share_exact=float((err == 0).mean()),
        share_late=float((err > 0).mean()),
        coverage=float(100 * d["cov"].mean()), cycles=float(d["t"].mean()),
        steps=float(d["steps"].mean()),
        win_vs_learned=float((v > L["value"]).mean()) if n != "Learned value-aware stopping" else None,
        loss_vs_learned=float((v < L["value"]).mean()) if n != "Learned value-aware stopping" else None,
        diff_learned_minus_this_ci95=[float(x) for x in boot_diff(L["value"], v, orc)]
        if n != "Learned value-aware stopping" else None,
    )
res["in_distribution_oracle"] = dict(mean_value=float(orc.mean()), cycles=float(t_orc.mean()))
steps_per_cycle = []
# messages per run = cycles * N(N-1)
res["messages_per_run"] = {n: float(d["t"].mean() * 2) for n, d in pm.items()}

# generalisation: per setting
gen = []
for size in (32, 48, 64):
    for nrob in (2, 4, 6, 8):
        trajs = pickle.load(open(f"results/gen_{size}_{nrob}.pkl", "rb"))
        for lvl, c in COMM_LEVELS.items():
            cm = CostModel(c_comm=c)
            o, to, p = per_map(trajs, cm)
            row = dict(size=size, n=nrob, comm=lvl, oracle_mean=float(o.mean()),
                       n_maps_oracle_nonpos=int((o <= 0).sum()))
            for n, d in p.items():
                row[n] = float(100 * d["value"].sum() / o.sum()) if o.sum() > 0 else None
                row[n + "|stoperr"] = float((d["t"] - to).mean())
            gen.append(row)
res["generalisation"] = gen
agg = {}
for n in names:
    vals = np.array([g[n] for g in gen if g[n] is not None])
    best = np.array([max(g[m] for m in names) for g in gen if g[n] is not None])
    agg[n] = dict(mean=float(vals.mean()), median=float(np.median(vals)), worst=float(vals.min()),
                  n_negative=int((vals < 0).sum()), n_below50=int((vals < 50).sum()),
                  n_best_or_within2=int((vals >= best - 2).sum()),
                  mean_clipped=float(np.maximum(vals, 0).mean()))
res["generalisation_summary"] = agg
json.dump(res, open("results/extra_metrics.json", "w"), indent=1)

print("IN-DISTRIBUTION")
for n, d in res["in_distribution"].items():
    print(f"{n[:30]:30s} tot {d['pct_total']:5.1f} CI {d['ci95'][0]:5.1f}-{d['ci95'][1]:5.1f} "
          f"mean/map {d['mean_per_map_pct']:6.1f} med {d['median_per_map_pct']:5.1f} p10 {d['p10_per_map_pct']:6.1f} "
          f">=90 {d['share_maps_ge90']:.2f} regret {d['mean_regret_cells']:6.1f} err {d['mean_stop_error_cycles']:+5.1f} "
          f"|err| {d['mean_abs_stop_error']:4.1f} E/X/L {d['share_early']:.2f}/{d['share_exact']:.2f}/{d['share_late']:.2f} "
          f"win {d['win_vs_learned']} loss {d['loss_vs_learned']} diffCI {d['diff_learned_minus_this_ci95']}")
print(res["in_distribution_oracle"])
print("GENERALISATION")
for n, a in agg.items():
    print(f"{n[:30]:30s}", {k: round(v, 1) for k, v in a.items()})
for g in gen:
    if g["comm"] == "high" or g["n"] == 2:
        print(g["size"], g["n"], g["comm"], round(g["oracle_mean"]), g["n_maps_oracle_nonpos"],
              {n[:8]: round(g[n], 1) for n in names})
