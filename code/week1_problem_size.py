"""WEEK 1 - Is the problem real, and how big is it?  (Stage A in the professor's report)

No learning here. For every finished exploration run we look back and ask:
  * where was the best moment to stop?            (T* = hindsight-best stop)
  * what did exploring to the very end cost us?   (value lost, effort wasted)

We do this for 2/4/6/8 robots, 32/48/64 maps and low/medium/high message cost
(40 maps each = 1,440 scored runs), using the cached runs in results/.

Run:     python week1_problem_size.py
Output:  results/week1_table.csv, figures/week1_*.png, a printed summary
"""
import csv, os, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stopping import CostModel, COMM_LEVELS, rewards, oracle_stop

SIZES, TEAMS = (32, 48, 64), (2, 4, 6, 8)
os.makedirs("figures", exist_ok=True)


def one_run(tr, cost):
    """Everything we want to know about one run, in plain numbers."""
    r = rewards(tr, cost)
    value = np.concatenate([[0.0], np.cumsum(r)])        # value[T] = net value if we stop after T cycles
    T_end = len(r)                                       # 'explore until done' stops here
    T_best = oracle_stop(tr, cost)                       # best stop, known only afterwards
    cells = sum(o["gain"] for o in tr["outcomes"])        # cells revealed by full exploration
    steps = np.array([o["steps"] for o in tr["outcomes"]])
    return dict(
        lost_pct_map=100 * (value[T_best] - value[T_end]) / cells,   # value thrown away, as % of the map
        wasted_steps_pct=100 * steps[T_best:].sum() / steps.sum(),   # share of all driving done after T*
        extra_map_pct=100 * (1 - tr["obs"][T_best]["free_coverage"]),# map still unknown at T*
        stop_point=T_best / T_end,                                    # 0 = stop at once, 1 = explore to the end
        best_value=value[T_best], full_value=value[T_end])


rows, stop_points = [], {lvl: [] for lvl in COMM_LEVELS}
for size in SIZES:
    for n in TEAMS:
        runs = pickle.load(open(f"results/gen_{size}_{n}.pkl", "rb"))
        for lvl, c in COMM_LEVELS.items():
            per = [one_run(tr, CostModel(c_comm=c)) for tr in runs]
            stop_points[lvl] += [p["stop_point"] for p in per]
            best, full = sum(p["best_value"] for p in per), sum(p["full_value"] for p in per)
            rows.append(dict(
                map_size=size, robots=n, msg_cost=lvl, maps=len(per),
                value_lost_pct_of_map=np.mean([p["lost_pct_map"] for p in per]),
                driving_after_best_stop_pct=np.mean([p["wasted_steps_pct"] for p in per]),
                map_left_at_best_stop_pct=np.mean([p["extra_map_pct"] for p in per]),
                best_stop_at_pct_of_mission=100 * np.mean([p["stop_point"] for p in per]),
                full_exploration_pct_of_best=100 * full / best if best > 0 else float("nan"),
                maps_where_full_is_negative=sum(p["full_value"] < 0 for p in per)))

with open("results/week1_table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()})

# ------------------------------------------------------------------ summary
A = lambda key: np.array([r[key] for r in rows])
lost, drive, left = A("value_lost_pct_of_map"), A("driving_after_best_stop_pct"), A("map_left_at_best_stop_pct")
print("WEEK 1 - what does 'explore until done' cost?  (36 settings x 40 maps)\n")
print(f"value thrown away (% of map):        mean {lost.mean():5.1f}   min {lost.min():5.1f}   max {lost.max():6.1f}")
print(f"driving done after the best stop:    mean {drive.mean():5.1f}%  min {drive.min():5.1f}%  max {drive.max():5.1f}%")
print(f"map still unknown at the best stop:  mean {left.mean():5.1f}%  min {left.min():5.1f}%  max {left.max():5.1f}%")
print(f"settings where >10% of map value is lost: {(lost > 10).sum()} of {len(rows)}")
print(f"settings where >30% of driving is wasted: {(drive > 30).sum()} of {len(rows)}\n")
print("by team size (averaged over map sizes and message costs):")
for n in TEAMS:
    m = [r for r in rows if r["robots"] == n]
    print(f"  {n} robots: value lost {np.mean([r['value_lost_pct_of_map'] for r in m]):5.1f}% of map, "
          f"driving after best stop {np.mean([r['driving_after_best_stop_pct'] for r in m]):5.1f}%")
print("by message cost:")
for lvl in COMM_LEVELS:
    m = [r for r in rows if r["msg_cost"] == lvl]
    print(f"  {lvl:6s}: value lost {np.mean([r['value_lost_pct_of_map'] for r in m]):5.1f}% of map, "
          f"driving after best stop {np.mean([r['driving_after_best_stop_pct'] for r in m]):5.1f}%")

# ------------------------------------------------------------------ figures
fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
for ax, lvl in zip(axes, COMM_LEVELS):
    for n in TEAMS:
        ys = [next(r["value_lost_pct_of_map"] for r in rows
                   if r["robots"] == n and r["map_size"] == s and r["msg_cost"] == lvl) for s in SIZES]
        ax.plot(SIZES, ys, marker="o", label=f"{n} robots")
    ax.set_title(f"message cost: {lvl}")
    ax.set_xlabel("map side (cells)")
    ax.set_xticks(SIZES)
    ax.grid(alpha=.3)
axes[0].set_ylabel("value lost by exploring to the end\n(% of map)")
axes[0].legend(frameon=False)
fig.tight_layout()
fig.savefig("figures/week1_value_lost.png", dpi=150)

fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
for ax, lvl in zip(axes, COMM_LEVELS):
    for n in TEAMS:
        ys = [next(r["driving_after_best_stop_pct"] for r in rows
                   if r["robots"] == n and r["map_size"] == s and r["msg_cost"] == lvl) for s in SIZES]
        ax.plot(SIZES, ys, marker="o", label=f"{n} robots")
    ax.set_title(f"message cost: {lvl}")
    ax.set_xlabel("map side (cells)")
    ax.set_xticks(SIZES)
    ax.grid(alpha=.3)
axes[0].set_ylabel("% of all driving done\nafter the best stop")
axes[0].legend(frameon=False)
fig.tight_layout()
fig.savefig("figures/week1_wasted_driving.png", dpi=150)

fig, ax = plt.subplots(figsize=(6, 3.8))
ax.hist([np.array(stop_points[l]) * 100 for l in COMM_LEVELS], bins=20, range=(0, 100),
        label=[f"message cost {l}" for l in COMM_LEVELS])
ax.set_xlabel("best stop, as % of the full mission length")
ax.set_ylabel("number of runs")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("figures/week1_where_best_stop_falls.png", dpi=150)
print("\nsaved results/week1_table.csv and figures/week1_*.png")

# ------------------------------------------------------------------ honesty check
# The size of the problem depends on how expensive we say driving is.
# Re-score the same runs with cheaper and dearer motion (medium message cost).
print("\nsensitivity to the price of driving (medium message cost, all 12 team/map combos):")
sens = []
for c_move in (0.5, 1.0, 2.0, 3.0):
    lost_m, drive_m = [], []
    for size in SIZES:
        for n in TEAMS:
            runs = pickle.load(open(f"results/gen_{size}_{n}.pkl", "rb"))
            per = [one_run(tr, CostModel(c_move=c_move, c_comm=COMM_LEVELS["medium"])) for tr in runs]
            lost_m.append(np.mean([p["lost_pct_map"] for p in per]))
            drive_m.append(np.mean([p["wasted_steps_pct"] for p in per]))
    sens.append((c_move, np.mean(lost_m), np.mean(drive_m)))
    print(f"  cost per robot step {c_move:3.1f}: value lost {np.mean(lost_m):5.1f}% of map, "
          f"driving after best stop {np.mean(drive_m):5.1f}%")
with open("results/week1_sensitivity.csv", "w") as f:
    f.write("cost_per_step,value_lost_pct_of_map,driving_after_best_stop_pct\n")
    for c, l, d in sens:
        f.write(f"{c},{l:.1f},{d:.1f}\n")
