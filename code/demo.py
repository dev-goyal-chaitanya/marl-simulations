"""Live demo: robots explore a NEW random map and the learned policy decides when to stop.

    python demo.py                          # 3 robots, 40x40 map, random new map
    python demo.py --robots 6 --size 48     # try a bigger team / map
    python demo.py --comm high              # make communication expensive
    python demo.py --seed 7                 # replay the same map again
    python demo.py --fast                   # one frame per cycle (quicker)
    python demo.py --save demo.gif          # also save the animation

At every cycle the stop decision uses ONLY what the team knows at that moment.
The exploration is simulated all the way to the end beforehand, so that after the
STOP we can also show what would have happened if the team had kept going.
"""
import argparse, os, sys, time
import numpy as np

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--robots", type=int, default=3)
p.add_argument("--size", type=int, default=40, help="map side in cells (24 to 64 works well)")
p.add_argument("--comm", choices=["low", "medium", "high"], default="medium")
p.add_argument("--seed", type=int, default=None, help="map number; omit for a new random map")
p.add_argument("--fast", action="store_true", help="draw one frame per cycle")
p.add_argument("--save", default=None, help="save the animation as a GIF")
p.add_argument("--no-show", action="store_true", help="do not open a window (for testing)")
a = p.parse_args()

import matplotlib
if a.no_show:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mapgen import make_map
from env import run_exhaustive, UNKNOWN, FREE, OBST
from stopping import CostModel, COMM_LEVELS, rewards, oracle_stop, evaluate_stop

BLUE, AMBER, TEAL, PURPLE = "#3A4AA8", "#A86E10", "#0E8E83", "#8E5BB5"
INK, MUTED, GRID = "#1A1A2E", "#5B6070", "#E6E8EE"
ROBOT = [BLUE, AMBER, TEAL, PURPLE]


def load_model():
    import joblib
    import warnings
    path = "results/stop_model.joblib"
    if os.path.exists(path):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")          # a version mismatch -> retrain below
                return joblib.load(path)
        except Exception:
            print("Saved model was made with a different scikit-learn version.")
    print("Training the stopping policy once (about 30-60 seconds)...")
    import pickle
    from stopping import LearnedValueStop, randomised_costs
    train = pickle.load(open("results/train.pkl", "rb"))
    runs, costs = randomised_costs(train, copies=4, rng=np.random.default_rng(0))
    model = LearnedValueStop().fit(runs, costs)
    joblib.dump(model, path, compress=3)
    return model


def map_rgb(known):
    img = np.empty(known.shape + (3,))
    img[known == UNKNOWN] = matplotlib.colors.to_rgb("#DDE0E7")
    img[known == FREE] = (1, 1, 1)
    img[known == OBST] = matplotlib.colors.to_rgb("#3C3F48")
    return img


# ------------------------------------------------------------------ simulate
seed = a.seed if a.seed is not None else int(np.random.default_rng().integers(1, 10**6))
cost = CostModel(c_comm=COMM_LEVELS[a.comm])
print(f"\nMap #{seed}: {a.size}x{a.size} cells, {a.robots} robots, {a.comm} communication cost")
print("Loading the learned stopping policy...")
model = load_model()
print("Simulating exploration...")
tr = run_exhaustive(make_map(a.size, np.random.default_rng(seed)), a.robots, seed=seed + 7, record_frames=True)

r = rewards(tr, cost)
net = np.r_[0, np.cumsum(r)]
T = len(r)
q = model.q_values(tr, cost)                     # Q(s_t) from information available at cycle t
t_learned = model.stop_time(tr, cost)
t_best = oracle_stop(tr, cost)
cov = [100 * o["free_coverage"] for o in tr["obs"]]

# ------------------------------------------------------------------ animate
plt.ion()
fig, (ax_map, ax_val) = plt.subplots(1, 2, figsize=(12, 6.3), gridspec_kw=dict(width_ratios=[1, 1.15]))
fig.suptitle(f"Map #{seed}  ·  {a.robots} robots  ·  {a.size}x{a.size}  ·  {a.comm} communication cost",
             fontsize=12, color=MUTED)
frames_out = []


def draw(cycle, known, pos, trails, stopped):
    ax_map.clear()
    ax_map.imshow(map_rgb(known), interpolation="nearest")
    for i, trail in enumerate(trails):
        ys, xs = zip(*trail)
        ax_map.plot(xs, ys, color=ROBOT[i % 4], lw=1.2, alpha=0.7)
        ax_map.plot(pos[i][1], pos[i][0], "o", color=ROBOT[i % 4], ms=8, mec="white", mew=1.4)
    ax_map.axis("off")
    if stopped:
        ax_map.set_title("Learned policy said STOP. Showing what continuing would cost.",
                         fontsize=11, color=AMBER, loc="left")
    else:
        decision = "continue" if q[min(cycle, T)] > 0 else "STOP"
        ax_map.set_title(f"Cycle {cycle}  ·  {cov[min(cycle, T)]:.0f}% mapped  ·  "
                         f"Q = {q[min(cycle, T)]:+.0f}  ->  {decision}", fontsize=11, color=INK, loc="left")

    ax_val.clear()
    upto = min(cycle, t_learned)
    ax_val.plot(range(upto + 1), net[:upto + 1], color=TEAL, lw=2.4, label="net value (learned policy)")
    if cycle > t_learned:
        ax_val.plot(range(t_learned, cycle + 1), net[t_learned:cycle + 1], color=AMBER, lw=2.4, ls="--",
                    label="if the team kept going")
    if cycle >= t_learned:
        ax_val.axvline(t_learned, color=TEAL, lw=1.4)
        ax_val.text(t_learned + 0.3, net.max() * 1.02, "learned STOP", color=TEAL, fontsize=11)
    ax_val.set_xlim(0, T)
    ax_val.set_ylim(min(net.min(), 0) - 20, net.max() * 1.12 + 20)
    ax_val.set_xlabel("Exploration cycle")
    ax_val.set_ylabel("Net value so far (cells found - costs)")
    ax_val.grid(axis="y", color=GRID)
    ax_val.spines[["top", "right"]].set_visible(False)
    ax_val.legend(loc="lower right", frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, 0.15, 1, 0.95))
    if not a.no_show:
        plt.pause(0.001)
    if a.save:
        fig.canvas.draw()
        frames_out.append(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())


print("\n cycle | mapped | new cells | cycle cost | net so far |     Q | decision")
for cycle, cycle_frames in enumerate(tr["frames"]):
    if cycle >= 1:
        o = tr["outcomes"][cycle - 1]
        c = o["gain"] - r[cycle - 1]
        if cycle == t_learned + 1:
            print("  ----- the team has stopped; rows below show what continuing would have done -----")
        if cycle <= t_learned:
            dec = "STOP   <- learned policy stops here" if cycle == t_learned else "continue"
            qs = f"{q[cycle]:+5.0f}"
        else:
            dec, qs = "(not run)", "    -"
        print(f"  {cycle:4d} | {cov[cycle]:5.0f}% | {o['gain']:9d} | {c:10.1f} | {net[cycle]:10.1f} | {qs} | {dec}")
    stopped = cycle > t_learned
    frames = cycle_frames if not a.fast else cycle_frames[-1:]
    for known, pos, trails in frames:
        draw(cycle, known, pos, trails, stopped)
        if not a.no_show:
            time.sleep(0.02 if not stopped else 0.005)
    if cycle == t_learned and not a.no_show:
        plt.pause(2.0)                                     # hold on the STOP moment

# ------------------------------------------------------------------ summary
res = {name: evaluate_stop(tr, cost, t) for name, t in
       [("Learned stop", t_learned), ("Explore until done", T), ("Best in hindsight", t_best)]}
best = res["Best in hindsight"]["value"]
lines = ["", f"{'':20s} {'cycles':>6s} {'mapped':>7s} {'net value':>10s} {'% of best':>9s}"]
for name, e in res.items():
    pct = 100 * e["value"] / best if best > 0 else float("nan")
    lines.append(f"{name:20s} {e['cycles']:6d} {100 * e['coverage']:6.0f}% {e['value']:10.0f} {pct:8.0f}%")
print("\n".join(lines))
print("\n'Best in hindsight' needs to know the future; it is the 100% reference, not a real policy.")

summary = "\n".join(l for l in lines[1:])
fig.text(0.5, 0.015, summary, fontsize=10, family="monospace", ha="center", va="bottom", color=INK,
         bbox=dict(facecolor="#F4F5F9", edgecolor=GRID, boxstyle="round,pad=0.5"))
if not a.no_show:
    plt.pause(0.001)
if a.save:
    fig.canvas.draw()
    frames_out += [np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()] * 25
    import imageio.v2 as imageio
    imageio.mimsave(a.save, frames_out, duration=0.08, loop=0)
    print(f"saved {a.save}")
if not a.no_show:
    plt.ioff()
    plt.show()
