# Weeks 1–2: what was done and what it showed

Both scripts reuse the saved exploration runs in `results/`, so no new simulation is needed.

```
python week1_problem_size.py    # ~1 min
python week2_models.py          # ~10 min (the random forest and neural net are the slow parts)
```

## Week 1: is the problem real? (`week1_problem_size.py`)
For each finished run, look back and find the best moment to stop (T*). Then measure what
exploring to the very end cost: value thrown away, and how much driving happened after T*.
This covers 36 settings (2/4/6/8 robots × 32/48/64 maps × low/medium/high message cost), 40 maps each.

| | average | range |
|---|---|---|
| Value thrown away by exploring to the end | 11.4% of the map | 5.0 – 44.6% |
| Driving done after the best stop | 36% of all driving | 22 – 83% |

- The loss grows with team size: 8 robots lose 16.8% of the map, against 8.0% for 4 robots.
- It grows with message cost: high cost loses 18.3%, low cost loses 6.9%.
- **Caveat:** the size of the problem depends on the price of driving. Re-scoring the same runs gives:

  | Cost per robot step | Value lost | Driving after the best stop |
  |---|---|---|
  | 0.5 | 1.0% of the map | 4.8% |
  | 1 | 2.2% | 9.6% |
  | 2 (the default) | 9.1% | 33% |
  | 3 | 27.3% | 68% |

  If driving is cheap compared with what a mapped cell is worth, just explore everything. The project
  matters when motion or communication is expensive: big teams, battery limits, costly radio.
  You must justify the cost numbers (for example, energy per step against the value of a cell), or
  present results across a range of costs. A range is also what the professor's Pareto section asks for.

Files: `results/week1_table.csv`, `results/week1_sensitivity.csv`, `figures/week1_*.png`

## Week 2: which model is enough? (`week2_models.py`)
The same 7 features with two ways of making the training target:
- **fqi** is fitted Q-iteration, the reinforcement-learning-style target. It repeatedly uses its own guess for the next state.
- **hindsight** is plain supervised learning. The target is the best remaining value seen after the run ends.

Each target is tried with 4 models. "Regret" means value lost against the best stop, as a % of the map,
over the 36 settings with no retraining.

| Rule | % of best (training setting) | Average regret | Worst setting | Settings below 50% |
|---|---|---|---|---|
| Coverage threshold (tuned baseline) | 92.1 | 4.7 | 25.3 | 5 |
| fqi + linear | 94.6 | 3.5 | 13.0 | 4 |
| fqi + random forest | 91.2 | 3.7 | 10.3 | 1 |
| **fqi + extra trees** (current) | 93.0 | 3.6 | **9.9** | 1 |
| fqi + neural net | 92.3 | 4.8 | 12.1 | 1 |
| hindsight + linear | 91.1 | 6.7 | 30.4 | 6 |
| hindsight + random forest | 82.5 | 9.0 | 35.7 | 8 |
| hindsight + extra trees | 79.6 | 9.6 | 39.0 | 8 |
| hindsight + neural net | 86.4 | 5.4 | 37.4 | 5 |

1. **How the target is built matters much more than which model you use.** Every fqi version beats every hindsight version, especially in the worst case (10–13 against 30–39).
   - Why: hindsight labels assume the team will know the future and stop perfectly later on. So they
     overestimate the value of continuing, and the team stops too late.
   - fqi's target only promises what the learned rule itself can deliver, which is the right target for a stopping rule.
   - This answers the professor's question "is RL needed?". The reinforcement-learning-style target is
     needed. A big model is not: even a linear model with fqi does well.
2. **Extra trees has the best worst case.** It stays as the default. A neural net brings no gain at this scale.
3. In typical conditions the learned rule still roughly ties the tuned coverage threshold.
   Its advantage is the worst case: 9.9 against 25.3, and 1 against 5 settings below 50%.

Files: `results/week2_table.csv`, `figures/week2_models.png`

## Open weak spots
- One map style (rooms with furniture). Mazes, warehouses and clutter still need adding. Do this before Week 6.
- One training seed per model.
- "% of best (training setting)" uses 100 test maps. The deck's 91% used 140 maps, so the numbers differ slightly.
