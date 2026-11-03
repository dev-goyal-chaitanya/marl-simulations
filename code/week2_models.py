"""WEEK 2 - Do we even need reinforcement learning? Which model is enough?  (Stage B)

Same 7 features, same training runs. We vary two things:

  HOW the target is made
    fqi       : fitted Q-iteration (what the prototype uses). Target = this cycle's
                score + max(0, model's own guess for the next state). Repeated 25 times.
    hindsight : plain supervised regression. Target = the best remaining value we can
                see in hindsight from that moment. One fit, no iterations.

  WHICH model learns it
    linear, random forest, extra trees (current), small neural net (MLP)

Every combination stops at the first cycle where its estimate <= 0.

Run:     python week2_models.py          (about 10-15 min on a laptop)
Output:  results/week2_table.csv, figures/week2_models.png, a printed table
"""
import csv, pickle, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from stopping import (CostModel, COMM_LEVELS, features, rewards, evaluate_stop, oracle_stop,
                      randomised_costs, paired, _first)

MODELS = {
    "linear": lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "random forest": lambda: RandomForestRegressor(n_estimators=80, min_samples_leaf=8, n_jobs=-1, random_state=0),
    "extra trees": lambda: ExtraTreesRegressor(n_estimators=80, min_samples_leaf=8, n_jobs=-1, random_state=0),
    "neural net": lambda: make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=300,
                                         early_stopping=True, random_state=0)),
}


def remaining_best(r):
    """Best total we could still add from each moment t, if we knew the future (>= 0)."""
    out = np.zeros(len(r))
    for t in range(len(r)):
        out[t] = max(0.0, np.cumsum(r[t:]).max())
    return out


class ValueStop:
    def __init__(self, model_name, method, iters=25):
        self.model_name, self.method, self.iters = model_name, method, iters
        self.name = f"{method} + {model_name}"

    def fit(self, runs, costs):
        S, R, S2, D, H = [], [], [], [], []
        for tr, c in paired(runs, costs):
            f, r = features(tr, c), rewards(tr, c)
            T = len(r)
            S.append(f[:T]); R.append(r); S2.append(f[1:T + 1])
            D.append(np.r_[np.zeros(T - 1), 1.0]); H.append(remaining_best(r))
        S, R, S2, D, H = map(np.concatenate, (S, R, S2, D, H))
        if self.method == "hindsight":
            self.model = MODELS[self.model_name]().fit(S, H)
            return self
        self.model = None
        for _ in range(self.iters):
            q_next = np.zeros(len(S2)) if self.model is None else self.model.predict(S2)
            y = R + (1 - D) * np.maximum(0.0, q_next)
            self.model = MODELS[self.model_name]().fit(S, y)
        return self

    def q_values(self, tr, cost):
        return self.model.predict(features(tr, cost))

    def stop_time(self, tr, cost):
        return _first(self.q_values(tr, cost) <= 0, len(tr["outcomes"]))


def score(rule, runs, cost):
    v = np.array([evaluate_stop(t, cost, rule.stop_time(t, cost))["value"] for t in runs])
    o = np.array([evaluate_stop(t, cost, oracle_stop(t, cost))["value"] for t in runs])
    cells = np.array([sum(x["gain"] for x in t["outcomes"]) for t in runs])
    return 100 * v.sum() / o.sum(), float(np.mean(100 * (o - v) / cells))


if __name__ == "__main__":
    t0 = time.time()
    train = pickle.load(open("results/train.pkl", "rb"))
    test = pickle.load(open("results/test.pkl", "rb"))
    runs, costs = randomised_costs(train, copies=4, rng=np.random.default_rng(0))
    medium = CostModel(c_comm=COMM_LEVELS["medium"])
    gen = {(s, n): pickle.load(open(f"results/gen_{s}_{n}.pkl", "rb")) for s in (32, 48, 64) for n in (2, 4, 6, 8)}

    # reference rows: the best hand-tuned baseline and the oracle
    old = pickle.load(open("results/rules.pkl", "rb"))
    coverage = next(r for r in old if "Coverage" in r.name)
    coverage.name = "coverage threshold (tuned baseline)"

    rules = [coverage]
    for method in ("fqi", "hindsight"):
        for m in MODELS:
            t1 = time.time()
            rules.append(ValueStop(m, method).fit(runs, costs))
            print(f"trained {rules[-1].name:26s} in {time.time() - t1:5.0f}s", flush=True)

    rows = []
    for rule in rules:
        pct_train, _ = score(rule, test, medium)
        per_setting = [score(rule, tr, CostModel(c_comm=c)) for tr in gen.values() for c in COMM_LEVELS.values()]
        regrets = np.array([r for _, r in per_setting])
        pcts = np.array([p for p, _ in per_setting])
        row = dict(rule=rule.name, pct_of_best_training_setting=pct_train,
                   mean_regret_pct_of_map=regrets.mean(), worst_regret_pct_of_map=regrets.max(),
                   settings_below_50pct=int((pcts < 50).sum()))
        if hasattr(rule, "q_values"):             # does the estimate track the true remaining value?
            qp, qt = [], []
            for tr in test:
                q, r = rule.q_values(tr, medium), rewards(tr, medium)
                for t in range(len(r)):
                    qp.append(q[t]); qt.append(np.cumsum(r[t:]).max())
            qp, qt = np.array(qp), np.array(qt)
            row["correlation_with_truth"] = float(np.corrcoef(qp, qt)[0, 1])
            row["sign_accuracy_pct"] = float(100 * np.mean((qp > 0) == (qt > 0)))
        rows.append(row)

    keys = ["rule", "pct_of_best_training_setting", "mean_regret_pct_of_map", "worst_regret_pct_of_map",
            "settings_below_50pct", "correlation_with_truth", "sign_accuracy_pct"]
    with open("results/week2_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(r[k], 2) if isinstance(r.get(k), float) else r.get(k, "")) for k in keys})

    print(f"\nWEEK 2 - which model is enough?  (finished in {time.time() - t0:.0f}s)")
    print(f"{'rule':38s} {'%best':>6s} {'regret':>7s} {'worst':>6s} {'<50%':>5s} {'corr':>5s} {'sign':>5s}")
    for r in rows:
        print(f"{r['rule']:38s} {r['pct_of_best_training_setting']:6.1f} {r['mean_regret_pct_of_map']:7.1f} "
              f"{r['worst_regret_pct_of_map']:6.1f} {r['settings_below_50pct']:5d} "
              f"{r.get('correlation_with_truth', float('nan')):5.2f} {r.get('sign_accuracy_pct', float('nan')):5.1f}")

    fig, ax = plt.subplots(figsize=(8, 4.2))
    names = [r["rule"] for r in rows]
    y = np.arange(len(rows))
    ax.barh(y - 0.2, [r["mean_regret_pct_of_map"] for r in rows], 0.4, label="average value lost (% of map)")
    ax.barh(y + 0.2, [r["worst_regret_pct_of_map"] for r in rows], 0.4, label="worst setting")
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlabel("value lost vs best stop in hindsight (% of map)  - lower is better")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    fig.savefig("figures/week2_models.png", dpi=150)
