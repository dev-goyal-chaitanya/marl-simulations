# Value-aware team stopping: week-1 prototype

A small, runnable prototype of **Phase 1–2** of the proposal: can a team of robots
learn *when further exploration is no longer worth its cost*?

Everything runs on a laptop CPU in about 15 minutes. It uses only numpy,
scikit-learn, matplotlib and imageio.

```
pip install -r requirements.txt
python demo.py                      # live demo on a new random map (starts instantly)
python run_experiments.py           # full evaluation; uses the cached runs in results/ (~5 min)
python make_figures.py              # figures/ and figures/exploration.gif
```

## Live demo

`demo.py` generates a brand-new random map, lets the robots explore it in a
window, prints one line per cycle (map mapped, new cells, cost, net value, the
learned value Q, and the decision), and marks the moment the learned policy
says STOP. It then keeps animating in amber to show what continuing would
have cost, and ends with a comparison: learned stop vs explore until done vs
best in hindsight.

```
python demo.py                          # 3 robots, 40x40 map, medium comm cost
python demo.py --robots 6 --size 48     # bigger team and map
python demo.py --comm high              # expensive communication
python demo.py --seed 50018             # a specific map (this one is the example in the slides)
python demo.py --fast                   # one frame per cycle
```

The stop decision at each cycle uses only what the team knows at that moment.
The exploration is simulated to the end in advance so the "what if it kept
going" part can be shown.

On fresh random maps with 3 robots on 40×40 maps (two informal checks of 30
maps), the learned stop reached ≥90% of the hindsight-best value on 23–24 of
30 maps, with a median of 97%. On roughly 1 map in 8–10 it stops noticeably
too early or too late (<70%).

## What the prototype does

**World.** Random indoor maps (rooms, doors, furniture) on a 2D grid. The robots
start together and see only what their sensor reaches (radius 4 cells,
line of sight, walls block view). The team does not know the map in advance,
so the problem is partially observable.

**Two-level loop (the hierarchy the professor suggested).**

| Level | Runs | Decides | In this prototype |
|---|---|---|---|
| 1 — strategic | once per cycle (6 steps) | continue or stop the whole team | **learned** |
| 2 — execution | every step, per robot | which frontier to drive to | greedy nearest-frontier allocation with spreading (a fixed substrate, not the contribution) |

**Cost model.** A cycle is worth
`cells revealed − 2·(robot steps) − c_comm·N(N−1) − 2`.
Motion, pairwise map-sharing messages and a per-cycle coordination overhead all
cost something, so at some point one more cycle stops paying for itself.

**Learned stopping rule.** Fitted Q-iteration (Ernst et al., 2005) learns
`Q(s)` = expected total net value of continuing from the team's current state.
The team stops as soon as `Q(s) ≤ 0`. The state is seven team-level
features, all expressed as ratios or fractions: map known so far, unexplored
cells near planned targets ÷ cost of a cycle, last two cycles' gain ÷ cost,
distance to targets, share of robots with work, and frontier density. Because
they are ratios, the same policy can be applied to other team sizes, map sizes
and communication costs.

**Cost randomisation.** Robot motion does not depend on the cost weights, so
each training run is re-scored under 4 random cost settings at no extra
simulation cost. Training still uses only 2 robots on 32×32 maps.

## Results (test maps never seen in training)

Metric: net value as a % of the **best stop in hindsight** (the oracle, which
knows the future), computed as a ratio of totals over the test maps. All numbers
below are reproduced by `run_experiments.py` followed by `extra_metrics.py`,
`extra_metrics2.py`, `extra_metrics3.py` and `extra_metrics4.py`
(output: `results/extra_metrics.json`).

**Training setting** (2 robots, 32×32, medium communication; 140 unseen maps,
95% bootstrap intervals)

| Stopping rule | % of hindsight-best | Map covered | Cycles |
|---|---|---|---|
| Explore until no frontiers (classical) | 74 [71–77] | 100% | 27.8 |
| Fixed cycle budget (tuned: 19) | 91 [89–92] | 88% | 18.9 |
| Coverage threshold (tuned: 0.84 of grid known) | 92 [91–94] | 90% | 19.5 |
| Myopic: stop after a losing cycle* | 68 [63–73] | 56% | 10.3 |
| Gain-vs-cost rule (tuned: α = 1.6) | 89 [86–91] | 89% | 19.8 |
| **Learned value-aware stopping** | **91 [89–93]** | 78% | 15.1 |

\*Called "One-step look-ahead" in the code; it stops after the first cycle
whose value was negative. The learned rule and the coverage threshold are
statistically tied (paired difference −3.3 to +1.6 points).

**Generalisation without retraining** (robots ∈ {2,4,6,8} × map ∈ {32,48,64}
× communication ∈ {low, medium, high} = 36 settings, 40 maps each).
Regret = value lost vs the best stop, as % of all cells revealed by full
exploration (stable when the best achievable value is small).

| Stopping rule | Mean regret | Worst-setting regret | IQM of % scores | Settings ≥ 80% | Settings < 50% |
|---|---|---|---|---|---|
| Explore until no frontiers | 11.4% | 44.6% | 69% | 5 | 9 |
| Fixed cycle budget | 9.1% | 37.1% | 72% | 13 | 8 |
| Coverage threshold | 4.7% | 25.3% | 89% | 27 | 5 |
| Myopic | 11.4% | 24.5% | 56% | 0 | 12 |
| Gain-vs-cost rule | 6.9% | 15.8% | 79% | 17 | 7 |
| **Learned value-aware stopping** | **3.6%** | **9.9%** | **89%** | **27** | **1** |
| Control: coverage re-tuned per setting (on its test maps) | 3.1% | 9.9% | 90% | 30 | 3 |
| Control: budget re-tuned per setting (on its test maps) | 3.2% | 4.1% | 87% | 30 | 3 |

Typical setting: a tie with the best tuned rule. Worst case: much safer. It
gets close to a rule re-tuned for every setting, without re-tuning. A raw mean
of % scores is **not** a good summary here: in the hardest settings the best
achievable value is only a few dozen cells, which turns small losses into
numbers like −700%.

**Value estimate.** On the 140 training-setting maps, the learned Q correlates
with the hindsight value of continuing at r = 0.88 and has the right sign
(continue vs stop) at 89% of decision points.

**Honest weak spots**
- With 2 robots on 48×48 and 64×64 maps the learned rule stops 20–33 cycles too early (≈75% vs ≈92% for the coverage threshold). Cause not yet diagnosed.
- 8 robots on a 32×32 map with high communication cost: exploring is barely worth it (on 14 of 40 maps the best choice is not to explore); every rule loses value (learned −10%, the least bad).
- One training seed so far.

## What this is, and what it is not yet

It **is**: a working Phase-1/2 testbed; a clean definition of value-aware
stopping as optimal stopping (stop when expected marginal value ≤ 0); a first
learned policy; the baselines from the ablation table; and the full
generalisation protocol (team size × map size × communication).

It is **not yet**:
- **MARL.** Level 2 is a fixed heuristic and Level 1 is a single centralised
  learner. The proposal replaces Level 2 with decentralised learned robot
  policies trained with CTDE (e.g. MAPPO).
- **Deep RL.** Fitted Q-iteration with extra-trees was chosen because it is
  fast, stable and easy to inspect for a first result.
- **Communication-constrained dynamics.** Communication only costs value here;
  it does not yet limit what robots know.
- A decision about **how many robots to activate**. The action is only stop/continue.

## Files

| File | What it contains |
|---|---|
| `mapgen.py` | random indoor maps |
| `env.py` | sensing, frontiers, Level-2 allocation, the cycle loop |
| `stopping.py` | cost model, features, every stopping rule including the learned one |
| `run_experiments.py` | data generation, training, evaluation → `results/results.json` |
| `make_figures.py` | all figures and the animation (run `run_experiments.py` first) |
| `extra_metrics*.py` | confidence intervals, regret, stop-time error, robust summaries, re-tuned controls |
| `demo.py` | the live demo |
| `results/stop_model.joblib` | the trained stopping policy used in the slides and the demo |

## Next steps (weeks 2–4)

1. Level-1 action space: stop / continue with all robots / continue with half the team.
2. Communication range limits, so each robot has its own partial map.
3. Replace the Level-2 heuristic with a shared-parameter MARL policy (PettingZoo + MAPPO).
4. Re-run the same protocol and ablation table.
