"""Figures and the exploration animation used in the proposal slides.
Run after run_experiments.py:   python make_figures.py
"""
import json, os, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import imageio.v2 as imageio

from mapgen import make_map
from env import run_exhaustive, UNKNOWN, FREE, OBST
from stopping import CostModel, rewards, oracle_stop, evaluate_stop

OUT = "figures"
BLUE, AMBER, TEAL, PURPLE = "#3A4AA8", "#A86E10", "#0E8E83", "#8E5BB5"   # validated palette
GRAY, INK, MUTED, GRID = "#B8BDCB", "#1A1A2E", "#5B6070", "#E6E8EE"
ROBOT = [BLUE, AMBER, TEAL, PURPLE]
plt.rcParams.update({"font.size": 13, "axes.edgecolor": "#9AA0AE", "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 14,
                     "axes.titlecolor": INK, "axes.titlelocation": "left"})

R = json.load(open("results/results.json"))
RULES = pickle.load(open("results/rules.pkl", "rb"))
LEARNED = RULES[-1]
COST = CostModel()
NAMES = {"Explore until no frontiers": "Explore until no frontiers",
         "Fixed cycle budget (tuned)": "Fixed cycle budget",
         "Coverage threshold (tuned)": "Coverage threshold",
         "One-step look-ahead": "One-step look-ahead",
         "Info-gain vs cost heuristic (tuned)": "Info-gain vs cost rule",
         "Learned value-aware stopping": "Learned value-aware stop"}


def save(fig, name):
    fig.savefig(f"{OUT}/{name}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def map_rgb(known):
    img = np.empty(known.shape + (3,))
    img[known == UNKNOWN] = matplotlib.colors.to_rgb("#DDE0E7")
    img[known == FREE] = (1, 1, 1)
    img[known == OBST] = matplotlib.colors.to_rgb("#3C3F48")
    return img


def example_run(n=3, size=40, seed=50018):
    rng = np.random.default_rng(seed)
    return run_exhaustive(make_map(size, rng), n, seed=seed + 7, record_frames=True)


# --------------------------------------------------------------------- 1. trade-off
def fig_tradeoff(tr):
    r = rewards(tr, COST)
    gain = np.r_[0, np.cumsum([o["gain"] for o in tr["outcomes"]])]
    net = np.r_[0, np.cumsum(r)]
    cost = gain - net
    t_l, t_o, T = LEARNED.stop_time(tr, COST), oracle_stop(tr, COST), len(r)
    x = np.arange(T + 1)
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.plot(x, gain, color=BLUE, lw=2.4)
    ax.plot(x, cost, color=AMBER, lw=2.4)
    ax.plot(x, net, color=TEAL, lw=2.4)
    ax.text(T + 0.4, gain[-1], "Map cells revealed", color=INK, va="center", fontsize=12)
    ax.text(T + 0.4, cost[-1], "Cost (motion + comm\n+ coordination)", color=INK, va="center", fontsize=12)
    ax.text(T + 0.4, net[-1], "Net value", color=INK, va="center", fontsize=12)
    ax.axvline(t_l, color=TEAL, lw=1.6)
    ax.plot(t_l, net[t_l], "o", color=TEAL, ms=9, mec="white", mew=1.8)
    ax.text(t_l - 0.4, gain[-1] * 1.04, f"Learned stop: cycle {t_l}, "
            f"{100 * tr['obs'][t_l]['free_coverage']:.0f}% mapped", ha="right", fontsize=11.5, color=INK)
    ax.text(t_l + 0.6, gain[-1] * 1.04, f"Next {T - t_l} cycles: +{100 * (1 - tr['obs'][t_l]['free_coverage']):.0f}% "
            f"map, net value {net[t_l]:.0f} to {net[T]:.0f}", ha="left", fontsize=11.5, color=MUTED)
    ax.set_xlabel("Exploration cycle")
    ax.set_ylabel("Cells (cumulative)")
    ax.set_xlim(0, T)
    ax.set_ylim(min(0, net.min()) - 20, gain[-1] * 1.12)
    save(fig, "fig_tradeoff.png")
    return t_l, t_o, T


# ------------------------------------------------------------- 2. in-distribution bars
def fig_bars():
    d = R["in_distribution"]
    order = sorted(d, key=lambda k: d[k]["pct_oracle"])
    vals = [d[k]["pct_oracle"] for k in order]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    colors = [BLUE if "Learned" in k else GRAY for k in order]
    ax.barh(range(len(order)), vals, color=colors, height=0.62)
    for i, (k, v) in enumerate(zip(order, vals)):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=12.5, color=INK,
                fontweight="bold" if "Learned" in k else "normal")
    ax.set_yticks(range(len(order)), [NAMES[k] for k in order], color=INK)
    ax.set_xlim(0, 108)
    ax.set_xlabel("Net value achieved, % of the hindsight-best stop")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "fig_bars.png")


# ------------------------------------------------------------- 3. generalisation
def fig_generalisation():
    g = [x for x in R["generalisation"] if x["tuning"] == "train"]
    show = [("Learned value-aware stopping", BLUE), ("Coverage threshold (tuned)", AMBER),
            ("Info-gain vs cost heuristic (tuned)", TEAL), ("Explore until no frontiers", PURPLE)]
    dims = [("n", (2, 4, 6, 8), "Robots (trained on 2)"), ("size", (32, 48, 64), "Map side, cells (trained on 32)"),
            ("comm", ("low", "medium", "high"), "Communication cost (trained on medium)")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
    summary = {}
    for ax, (key, levels, label) in zip(axes, dims):
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for name, col in show:
            # mean over the other two dimensions; a result worse than "don't explore"
            # (negative) is clipped to 0 so a single collapse cannot dominate the average
            ys = [float(np.mean([max(0.0, x["pct_oracle"]) for x in g
                                 if x["rule"] == name and x[key] == lv])) for lv in levels]
            summary.setdefault(name, {})[key] = ys
            ax.plot(range(len(levels)), np.clip(ys, 0, None), color=col, lw=2.2, marker="o", ms=7,
                    markeredgecolor="white", markeredgewidth=1.5)
        ax.set_xticks(range(len(levels)), [str(v) for v in levels])
        ax.set_xlabel(label)
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("Mean % of hindsight-best value")
    handles = [plt.Line2D([], [], color=c, lw=2.4, marker="o") for _, c in show]
    fig.legend(handles, [NAMES[n] for n, _ in show], loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.06), fontsize=12)
    fig.tight_layout()
    save(fig, "fig_generalisation.png")
    return summary


# ------------------------------------------------------------- 4. is Q meaningful?
def fig_value_check():
    v = R["value_check"]
    p, t = np.array(v["pred"]), np.array(v["true"])
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.scatter(t, p, s=9, color=BLUE, alpha=0.25, lw=0)
    m = max(t.max(), p.max())
    ax.plot([0, m], [0, m], color=MUTED, lw=1.2, ls="--")
    ax.text(0.04 * m, 0.9 * m, f"Pearson r = {v['pearson']:.2f}", fontsize=13, color=INK)
    ax.set_xlabel("True remaining value (hindsight)")
    ax.set_ylabel("Learned estimate Q(s)")
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    save(fig, "fig_value_check.png")


# ------------------------------------------------------------- 5. maps at stop time
def fig_maps(tr):
    t_l, T = LEARNED.stop_time(tr, COST), len(tr["outcomes"])
    def snap(t):   # map state after t cycles (walk back if a cycle recorded no motion)
        while not tr["frames"][t]:
            t -= 1
        return tr["frames"][t][-1]
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    for ax, t, title in [(axes[0], t_l, "Learned policy stops"), (axes[1], T, "Explore until no frontiers")]:
        known, pos, trails = snap(t)
        ev = evaluate_stop(tr, COST, t)
        ax.imshow(map_rgb(known), interpolation="nearest")
        for i, trail in enumerate(trails):
            ys, xs = zip(*trail)
            ax.plot(xs, ys, color=ROBOT[i % 4], lw=1.4, alpha=0.75)
            ax.plot(pos[i][1], pos[i][0], "o", color=ROBOT[i % 4], ms=9, mec="white", mew=1.6)
        ax.set_title(f"{title}\ncycle {t}  ·  {100 * ev['coverage']:.0f}% mapped  ·  net value {ev['value']:.0f}",
                     fontsize=12.5)
        ax.axis("off")
    fig.tight_layout()
    save(fig, "fig_maps.png")


# ------------------------------------------------------------- 6. animation
def make_gif(tr):
    r = rewards(tr, COST)
    net = np.r_[0, np.cumsum(r)]
    t_l, T = LEARNED.stop_time(tr, COST), len(r)
    q = LEARNED.q_values(tr, COST)
    frames = []
    for cyc, cycle_frames in enumerate(tr["frames"]):
        for known, pos, trails in cycle_frames[::2] or cycle_frames:
            fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw=dict(width_ratios=[1, 1.25]))
            a1.imshow(map_rgb(known), interpolation="nearest")
            for i, trail in enumerate(trails):
                ys, xs = zip(*trail)
                a1.plot(xs, ys, color=ROBOT[i % 4], lw=1.2, alpha=0.7)
                a1.plot(pos[i][1], pos[i][0], "o", color=ROBOT[i % 4], ms=8, mec="white", mew=1.4)
            a1.axis("off")
            past = cyc > t_l
            a1.set_title("After the learned STOP (cost the team would still pay)" if past
                         else f"Cycle {cyc}: team continues (Q = {q[min(cyc, T)]:.0f} > 0)",
                         fontsize=11.5, color=AMBER if past else INK)
            a2.plot(range(min(cyc, t_l) + 1), net[:min(cyc, t_l) + 1], color=TEAL, lw=2.4)
            if cyc > t_l:
                a2.plot(range(t_l, cyc + 1), net[t_l:cyc + 1], color=AMBER, lw=2.4, ls="--")
            if cyc >= t_l:
                a2.axvline(t_l, color=TEAL, lw=1.4)
                a2.text(t_l + 0.4, net.min() + 0.05 * (net.max() - net.min()), "learned STOP",
                        color=TEAL, fontsize=11)
            a2.set_xlim(0, T)
            a2.set_ylim(net.min() - 20, net.max() * 1.1)
            a2.set_xlabel("Exploration cycle")
            a2.set_ylabel("Net value so far (cells)")
            a2.grid(axis="y", color=GRID, lw=0.8)
            fig.tight_layout()
            fig.canvas.draw()
            frames.append(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())
            plt.close(fig)
    frames += [frames[-1]] * 20
    imageio.mimsave(f"{OUT}/exploration.gif", frames, duration=0.08, loop=0)
    return len(frames)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    tr = example_run()
    print("trade-off example (learned stop, oracle stop, total cycles):", fig_tradeoff(tr))
    fig_bars()
    s = fig_generalisation()
    print(json.dumps({k: {kk: [round(x, 1) for x in vv] for kk, vv in v.items()} for k, v in s.items()}, indent=1))
    fig_value_check()
    fig_maps(tr)
    print("gif frames:", make_gif(tr))
