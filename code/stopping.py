"""Cost model, team-level features, and the Level-1 stopping rules.

Net value of one cycle (in units of "map cells"):
    r_t = cells revealed - c_move*robot_steps - c_comm*N*(N-1) - c_coord
Stopping after cycle t earns the sum of r_0..r_{t-1}. The best achievable value on
a map is known in hindsight (the ORACLE) and is used as the reference (100%).

The learned rule is value-aware: it estimates
    Q(s) = expected total net value of continuing from team state s
with fitted Q-iteration (Ernst et al., 2005) and stops as soon as Q(s) <= 0,
i.e. when the expected marginal value of further exploration no longer covers its cost.
"""
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

COMM_LEVELS = {"low": 0.05, "medium": 0.2, "high": 0.6}   # cost per message


class CostModel:
    def __init__(self, c_move=2.0, c_comm=0.2, c_coord=2.0):
        self.c_move, self.c_comm, self.c_coord = c_move, c_comm, c_coord

    def cycle_cost(self, steps, n):
        return self.c_move * steps + self.c_comm * n * (n - 1) + self.c_coord

    def expected_cycle_cost(self, obs, n, k):
        return self.cycle_cost(obs["frac_assigned"] * n * k, n)


FEATURES = ["known_frac", "potential_ratio", "last_gain_ratio", "prev_gain_ratio",
            "target_dist", "frac_assigned", "frontier_density"]


def features(traj, cost):
    """One row per decision point t = 0..T. Every feature is a ratio or fraction,
    so the same policy can be applied to other team sizes, map sizes and costs."""
    n, k, size = traj["n"], traj["k"], traj["map_size"]
    rows = []
    for t, o in enumerate(traj["obs"]):
        c = max(cost.expected_cycle_cost(o, n, k), 1e-6)
        pot = o["potential"] / c
        last = traj["outcomes"][t - 1]["gain"] / c if t >= 1 else pot
        prev = traj["outcomes"][t - 2]["gain"] / c if t >= 2 else last
        rows.append([o["known_frac"], pot, last, prev, o["mean_target_dist"] / k,
                     o["frac_assigned"], o["n_frontier"] / size])
    return np.array(rows)


def rewards(traj, cost):
    return np.array([o["gain"] - cost.cycle_cost(o["steps"], traj["n"]) for o in traj["outcomes"]])


def evaluate_stop(traj, cost, t_stop):
    r = rewards(traj, cost)
    return dict(value=float(r[:t_stop].sum()),
                coverage=traj["obs"][t_stop]["free_coverage"],
                cycles=int(t_stop),
                steps=int(sum(o["steps"] for o in traj["outcomes"][:t_stop])))


def oracle_stop(traj, cost):
    prefix = np.concatenate([[0.0], np.cumsum(rewards(traj, cost))])
    return int(np.argmax(prefix))


# --------------------------------------------------------------------------- rules
def paired(trajs, cost):
    """Training data as (run, cost model) pairs. `cost` may be one model or a list."""
    costs = cost if isinstance(cost, list) else [cost] * len(trajs)
    return list(zip(trajs, costs))


def randomised_costs(trajs, copies, rng):
    """Cost randomisation: robot motion does not depend on the cost weights, so every
    training run can be re-scored under several random operator preferences for free."""
    runs, costs = [], []
    for tr in trajs:
        for _ in range(copies):
            runs.append(tr)
            costs.append(CostModel(c_move=rng.uniform(1.0, 3.0), c_comm=rng.uniform(0.05, 0.6),
                                   c_coord=rng.uniform(1.0, 40.0)))
    return runs, costs


class Rule:
    name = "rule"

    def fit(self, trajs, cost):
        return self

    def stop_time(self, traj, cost):
        raise NotImplementedError


class Exhaustive(Rule):
    name = "Explore until no frontiers"

    def stop_time(self, traj, cost):
        return len(traj["outcomes"])


def _first(cond, T):
    idx = np.flatnonzero(cond[:T])
    return int(idx[0]) if len(idx) else T


class _Tuned(Rule):
    """Pick the parameter that maximises total net value on the training maps."""
    grid = []

    def fit(self, trajs, cost):
        data = paired(trajs, cost)
        scores = [sum(evaluate_stop(tr, c, self._stop(tr, c, p))["value"] for tr, c in data)
                  for p in self.grid]
        self.param = self.grid[int(np.argmax(scores))]
        return self

    def stop_time(self, traj, cost):
        return self._stop(traj, cost, self.param)


class CoverageThreshold(_Tuned):
    name = "Coverage threshold (tuned)"
    grid = list(np.round(np.arange(0.50, 1.001, 0.02), 2))

    def _stop(self, traj, cost, tau):
        known = np.array([o["known_frac"] for o in traj["obs"]])
        return _first(known >= tau, len(traj["outcomes"]))


class FixedBudget(_Tuned):
    name = "Fixed cycle budget (tuned)"
    grid = list(range(1, 80))

    def _stop(self, traj, cost, b):
        return min(b, len(traj["outcomes"]))


class Myopic(Rule):
    name = "One-step look-ahead"

    def stop_time(self, traj, cost):
        r = rewards(traj, cost)
        cond = np.r_[False, r < 0]      # stop once the last cycle did not pay for itself
        return _first(cond, len(r))


class InfoGainHeuristic(_Tuned):
    name = "Info-gain vs cost heuristic (tuned)"
    grid = list(np.round(np.arange(0.05, 3.01, 0.05), 2))

    def _stop(self, traj, cost, alpha):
        pot = features(traj, cost)[:, 1]
        return _first(alpha * pot < 1.0, len(traj["outcomes"]))


class LearnedValueStop(Rule):
    """Fitted Q-iteration for optimal stopping (value-aware stopping)."""
    name = "Learned value-aware stopping"

    def __init__(self, iters=25, seed=0):
        self.iters, self.seed = iters, seed

    def fit(self, trajs, cost):
        S, R, S2, D = [], [], [], []
        for tr, c in paired(trajs, cost):
            f, r = features(tr, c), rewards(tr, c)
            T = len(r)
            S.append(f[:T]); R.append(r); S2.append(f[1:T + 1])
            D.append(np.r_[np.zeros(T - 1), 1.0])   # the state after the last cycle is terminal
        S, R, S2, D = map(np.concatenate, (S, R, S2, D))
        self.model = None
        for _ in range(self.iters):
            q_next = np.zeros(len(S2)) if self.model is None else self.model.predict(S2)
            y = R + (1 - D) * np.maximum(0.0, q_next)      # stop (0) or keep going
            self.model = ExtraTreesRegressor(n_estimators=80, min_samples_leaf=8,
                                             random_state=self.seed, n_jobs=-1).fit(S, y)
        return self

    def q_values(self, traj, cost):
        return self.model.predict(features(traj, cost))

    def stop_time(self, traj, cost):
        T = len(traj["outcomes"])
        return _first(self.q_values(traj, cost) <= 0, T)


class Oracle(Rule):
    name = "Oracle (hindsight best)"

    def stop_time(self, traj, cost):
        return oracle_stop(traj, cost)


ALL_RULES = [Exhaustive, FixedBudget, CoverageThreshold, Myopic, InfoGainHeuristic, LearnedValueStop]
