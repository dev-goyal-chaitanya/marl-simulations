"""Generate exploration runs, train the stopping policy, evaluate every rule.

Protocol (mirrors the generalisation test in the proposal):
  train : 2 robots, 32x32 maps, medium communication cost
  test  : robots in {2,4,6,8} x map size in {32,48,64} x comm cost in {low,medium,high}
          on maps never seen during training, WITHOUT retraining.
Usage:  python run_experiments.py [--quick]
"""
import argparse, json, os, pickle, time
from multiprocessing import Pool
import numpy as np

from mapgen import make_map
from env import run_exhaustive
from stopping import (CostModel, COMM_LEVELS, ALL_RULES, Oracle, evaluate_stop, randomised_costs,
                      LearnedValueStop, rewards)

OUT = "results"


def _one(args):
    size, n, seed = args
    rng = np.random.default_rng(seed)
    tr = run_exhaustive(make_map(size, rng), n, seed=seed + 7)
    tr.pop("frames")
    tr.pop("true_map")
    return tr


def generate(configs, cache):
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    with Pool(os.cpu_count()) as p:
        trajs = p.map(_one, configs, chunksize=4)
    pickle.dump(trajs, open(cache, "wb"))
    return trajs


def summarise(rule, trajs, cost):
    ev = [evaluate_stop(tr, cost, rule.stop_time(tr, cost)) for tr in trajs]
    orc = [evaluate_stop(tr, cost, Oracle().stop_time(tr, cost)) for tr in trajs]
    tot_oracle = sum(o["value"] for o in orc)
    pct = 100 * sum(e["value"] for e in ev) / tot_oracle if tot_oracle > 0 else float("nan")
    return dict(pct_oracle=pct,
                coverage=100 * np.mean([e["coverage"] for e in ev]),
                cycles=float(np.mean([e["cycles"] for e in ev])),
                steps=float(np.mean([e["steps"] for e in ev])),
                oracle_coverage=100 * np.mean([o["coverage"] for o in orc]),
                oracle_cycles=float(np.mean([o["cycles"] for o in orc])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small run for a smoke test")
    a = ap.parse_args()
    n_train, n_test, n_gen = (40, 20, 8) if a.quick else (300, 100, 40)
    os.makedirs(OUT, exist_ok=True)
    tag = "_quick" if a.quick else ""
    t0 = time.time()

    train = generate([(32, 2, 1000 + i) for i in range(n_train)], f"{OUT}/train{tag}.pkl")
    test = generate([(32, 2, 50000 + i) for i in range(n_test)], f"{OUT}/test{tag}.pkl")
    print(f"generated train/test runs in {time.time() - t0:.0f}s")

    cost = CostModel(c_comm=COMM_LEVELS["medium"])
    # every rule is fitted / tuned on exactly the same data: the training runs,
    # each re-scored under 4 randomly drawn cost settings
    tr_runs, tr_costs = randomised_costs(train, copies=4, rng=np.random.default_rng(0))
    # Baselines are tuned the way an engineer would: on the training setting itself.
    # The learned rule sees the same runs re-scored under random costs (cost randomisation).
    rules = [R().fit(tr_runs, tr_costs) if R is LearnedValueStop else R().fit(train, cost)
             for R in ALL_RULES]
    # sensitivity check: baselines tuned on the randomised data instead
    alt = [R().fit(tr_runs, tr_costs) for R in ALL_RULES if R is not LearnedValueStop]
    for r in rules:
        if hasattr(r, "param"):
            print(f"  tuned {r.name}: {r.param}")

    results = {"in_distribution": {r.name: summarise(r, test, cost) for r in rules},
               "in_distribution_alt_tuning": {r.name: summarise(r, test, cost) for r in alt}}

    # Is the learned value meaningful? Compare Q(s_t) with the true best achievable
    # remaining value from t (known in hindsight on test maps).
    learned = rules[-1]
    q_pred, q_true = [], []
    for tr in test:
        q = learned.q_values(tr, cost)
        rr = rewards(tr, cost)
        for t in range(len(rr)):
            q_pred.append(float(q[t]))
            q_true.append(float(max(0.0, np.cumsum(rr[t:]).max())))
    results["value_check"] = dict(pred=q_pred, true=q_true,
                                  pearson=float(np.corrcoef(q_pred, q_true)[0, 1]))
    print(f"  learned value vs true remaining value: Pearson r = {results['value_check']['pearson']:.2f}")
    print("\nIn-distribution test (2 robots, 32x32, medium comm):")
    for name, s in results["in_distribution"].items():
        print(f"  {name:38s} {s['pct_oracle']:6.1f}% of oracle | coverage {s['coverage']:5.1f}% "
              f"| cycles {s['cycles']:5.1f}")

    # ----------------------------------------------------------- generalisation
    gen = []
    for size in (32, 48, 64):
        for n in (2, 4, 6, 8):
            trajs = generate([(size, n, 90000 + 100 * size + 10000 * n + i) for i in range(n_gen)],
                             f"{OUT}/gen_{size}_{n}{tag}.pkl")
            for lvl, c in COMM_LEVELS.items():
                cm = CostModel(c_comm=c)
                for r in rules:
                    s = summarise(r, trajs, cm)
                    gen.append(dict(size=size, n=n, comm=lvl, rule=r.name, tuning="train", **s))
                for r in alt:
                    s = summarise(r, trajs, cm)
                    gen.append(dict(size=size, n=n, comm=lvl, rule=r.name, tuning="randomised", **s))
            print(f"  generalisation {size}x{size}, {n} robots done ({time.time() - t0:.0f}s)")
    results["generalisation"] = gen
    pickle.dump(rules, open(f"{OUT}/rules{tag}.pkl", "wb"))
    json.dump(results, open(f"{OUT}/results{tag}.json", "w"), indent=1)
    print(f"\nfinished in {time.time() - t0:.0f}s -> {OUT}/results{tag}.json")


if __name__ == "__main__":
    main()
