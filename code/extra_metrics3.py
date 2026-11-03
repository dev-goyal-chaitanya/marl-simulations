import json, pickle, numpy as np
from stopping import CostModel, COMM_LEVELS, evaluate_stop, oracle_stop, rewards
E = json.load(open("results/extra_metrics.json"))
rules = pickle.load(open("results/rules.pkl", "rb"))
names = [r.name for r in rules]
rng = np.random.default_rng(2)
cost = CostModel(c_comm=COMM_LEVELS["medium"])

def nfree(tr):  # free cells of the map = free coverage denominator; recover from obs
    # known free cells at the end / free_coverage at the end (== 1 for exhaustive)
    return None

# pooled in-distribution (140 maps): full summary with CIs
trajs = pickle.load(open("results/test.pkl", "rb")) + pickle.load(open("results/gen_32_2.pkl", "rb"))
o = np.array([evaluate_stop(t, cost, oracle_stop(t, cost))["value"] for t in trajs])
to = np.array([oracle_stop(t, cost) for t in trajs])
oc = np.array([t["obs"][oracle_stop(t, cost)]["free_coverage"] for t in trajs])
idx = rng.integers(0, len(o), (5000, len(o)))
pooled = {}
for r in rules:
    ts = np.array([r.stop_time(t, cost) for t in trajs])
    ev = [evaluate_stop(t, cost, s) for t, s in zip(trajs, ts)]
    v = np.array([e["value"] for e in ev])
    ci = np.percentile(100 * v[idx].sum(1) / o[idx].sum(1), [2.5, 97.5])
    ratio = 100 * v / o
    pooled[r.name] = dict(pct=float(100 * v.sum() / o.sum()), ci=[float(c) for c in ci],
                          median_map=float(np.median(ratio)), p10_map=float(np.percentile(ratio, 10)),
                          ge90=float((ratio >= 90).mean()),
                          regret=float((o - v).mean()),
                          coverage=float(100 * np.mean([e["coverage"] for e in ev])),
                          cycles=float(ts.mean()), steps=float(np.mean([e["steps"] for e in ev])),
                          messages=float(2 * ts.mean()),
                          stop_err=float((ts - to).mean()), abs_err=float(np.abs(ts - to).mean()),
                          early=float((ts < to).mean()), exact=float((ts == to).mean()), late=float((ts > to).mean()))
    print(f"{r.name[:28]:28s} {pooled[r.name]['pct']:5.1f} [{ci[0]:5.1f},{ci[1]:5.1f}] med {pooled[r.name]['median_map']:5.1f} "
          f"p10 {pooled[r.name]['p10_map']:6.1f} ge90 {pooled[r.name]['ge90']:.2f} regret {pooled[r.name]['regret']:5.1f} "
          f"cov {pooled[r.name]['coverage']:5.1f} cyc {ts.mean():5.1f} steps {pooled[r.name]['steps']:5.0f} "
          f"err {pooled[r.name]['stop_err']:+5.1f} |err| {pooled[r.name]['abs_err']:4.1f} "
          f"E/X/L {pooled[r.name]['early']:.2f}/{pooled[r.name]['exact']:.2f}/{pooled[r.name]['late']:.2f}")
L = np.array([evaluate_stop(t, cost, rules[-1].stop_time(t, cost))["value"] for t in trajs])
C = np.array([evaluate_stop(t, cost, rules[2].stop_time(t, cost))["value"] for t in trajs])
print("learned better / worse / equal vs coverage on maps:", (L > C).mean(), (L < C).mean(), (L == C).mean())
pooled["_oracle"] = dict(value=float(o.mean()), coverage=float(100 * oc.mean()), cycles=float(to.mean()),
                         steps=float(np.mean([evaluate_stop(t, cost, s)["steps"] for t, s in zip(trajs, to)])))
print("oracle", pooled["_oracle"])

# sign accuracy of Q: does Q(s_t) > 0 agree with "true best continuation value > 0"?
q_pred, q_true = [], []
for t in trajs:
    q = rules[-1].q_values(t, cost); rr = rewards(t, cost)
    for k in range(len(rr)):
        q_pred.append(q[k]); q_true.append(np.cumsum(rr[k:]).max())
q_pred, q_true = np.array(q_pred), np.array(q_true)
sign_acc = float(((q_pred > 0) == (q_true > 0)).mean())
mae = float(np.abs(q_pred - np.maximum(q_true, 0)).mean())
print("sign accuracy", sign_acc, "MAE", mae, "pearson(continuation, not clipped)", np.corrcoef(q_pred, q_true)[0, 1])

# normalized regret across settings: (oracle - rule) / free cells of the map, in %
norm = {}
for size in (32, 48, 64):
    for n in (2, 4, 6, 8):
        tr = pickle.load(open(f"results/gen_{size}_{n}.pkl", "rb"))
        # free cells: total gain from exhaustive run counts obstacles too; use final known free
        for lvl, c in COMM_LEVELS.items():
            cm = CostModel(c_comm=c)
            ov = np.array([evaluate_stop(t, cm, oracle_stop(t, cm))["value"] for t in tr])
            for r in rules:
                v = np.array([evaluate_stop(t, cm, r.stop_time(t, cm))["value"] for t in tr])
                cells = np.array([sum(o["gain"] for o in t["outcomes"]) + 0.0 for t in tr])  # all cells revealed by full exploration
                norm.setdefault(r.name, []).append(float(np.mean(100 * (ov - v) / cells)))
print("normalized regret (% of cells revealed by full exploration), across 36 settings")
for n, vals in norm.items():
    vals = np.array(vals)
    print(f"{n[:28]:28s} mean {vals.mean():6.1f} median {np.median(vals):5.1f} worst {vals.max():6.1f}")
E["pooled_in_distribution"] = pooled
E["value_check_extra"] = dict(sign_accuracy=sign_acc, mae=mae, n_points=int(len(q_pred)))
E["normalized_regret"] = norm
json.dump(E, open("results/extra_metrics.json", "w"), indent=1)
