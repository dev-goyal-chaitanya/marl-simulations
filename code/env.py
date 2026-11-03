"""Multi-robot exploration on a 2D grid, organised as a two-level (hierarchical) loop.

Level 2 (execution, every step): each robot is given a frontier by a greedy
    distance-based allocator and drives towards it, sensing as it moves.
    This is the "substrate" - it is NOT the contribution being studied.
Level 1 (strategic, once per cycle): the team decides CONTINUE or STOP.
    This is the decision the project wants to learn.

Because the Level-1 decision is only "stop or not", the robots' motion does not
depend on the stopping rule. So one exhaustive run of a map (explore until no
frontiers remain) records everything needed to evaluate ANY stopping rule on that
map: stopping after cycle t just means keeping the first t cycles.
"""
import numpy as np
from collections import deque

UNKNOWN, FREE, OBST = -1, 0, 1
NEIGH4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _bresenham(y0, x0, y1, x1):
    pts = []
    dy, dx = abs(y1 - y0), abs(x1 - x0)
    sy, sx = (1 if y1 > y0 else -1), (1 if x1 > x0 else -1)
    err = dx - dy
    y, x = y0, x0
    while True:
        pts.append((y, x))
        if (y, x) == (y1, x1):
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return pts


class TeamExplorationEnv:
    def __init__(self, true_map, n_robots, rng, sensor_radius=4, steps_per_cycle=6):
        self.true = true_map
        self.h, self.w = true_map.shape
        self.n = n_robots
        self.r = sensor_radius
        self.k = steps_per_cycle
        self.rng = rng
        # sensor model: a disc of radius r with line-of-sight (walls block view)
        self.rays = []
        for dy in range(-self.r, self.r + 1):
            for dx in range(-self.r, self.r + 1):
                if dy * dy + dx * dx <= self.r * self.r:
                    self.rays.append(_bresenham(0, 0, dy, dx)[1:])
        self.n_free_total = int((true_map == FREE).sum())

    # ------------------------------------------------------------------ sensing
    def _sense(self, y, x):
        new = 0
        for ray in self.rays:
            for dy, dx in ray:
                ny, nx = y + dy, x + dx
                if not (0 <= ny < self.h and 0 <= nx < self.w):
                    break
                if self.known[ny, nx] == UNKNOWN:
                    self.known[ny, nx] = self.true[ny, nx]
                    new += 1
                if self.true[ny, nx] == OBST:
                    break
        return new

    # ----------------------------------------------------------------- planning
    def frontiers(self):
        free = self.known == FREE
        unk = np.pad(self.known == UNKNOWN, 1)
        near_unk = unk[:-2, 1:-1] | unk[2:, 1:-1] | unk[1:-1, :-2] | unk[1:-1, 2:]
        return np.argwhere(free & near_unk)

    def _is_frontier(self, c):
        y, x = c
        for dy, dx in NEIGH4:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.h and 0 <= nx < self.w and self.known[ny, nx] == UNKNOWN:
                return True
        return False

    def _bfs(self, start):
        dist = np.full((self.h, self.w), np.inf)
        parent = {}
        dist[start] = 0
        q = deque([start])
        while q:
            y, x = q.popleft()
            for dy, dx in NEIGH4:
                ny, nx = y + dy, x + dx
                if 0 <= ny < self.h and 0 <= nx < self.w and self.known[ny, nx] == FREE \
                        and dist[ny, nx] == np.inf:
                    dist[ny, nx] = dist[y, x] + 1
                    parent[(ny, nx)] = (y, x)
                    q.append((ny, nx))
        return dist, parent

    def plan(self):
        """Greedy allocation: repeatedly give the closest (robot, frontier) pair,
        then block frontier cells near that target so robots spread out."""
        fr = self.frontiers()
        self.plan_targets = [None] * self.n
        self.plan_parents = [None] * self.n
        if len(fr) == 0:
            return
        bfs = [self._bfs(tuple(p)) for p in self.pos]
        cost = np.array([[bfs[i][0][tuple(f)] for f in fr] for i in range(self.n)])
        available = np.ones(len(fr), dtype=bool)
        free_robots = set(range(self.n))
        while free_robots and available.any():
            sub = cost[list(free_robots)][:, available]
            if not np.isfinite(sub).any():
                break
            ri, fj = np.unravel_index(np.argmin(sub), sub.shape)
            robot = list(free_robots)[ri]
            f_idx = np.flatnonzero(available)[fj]
            target = tuple(fr[f_idx])
            self.plan_targets[robot] = target
            self.plan_parents[robot] = bfs[robot][1]
            free_robots.discard(robot)
            near = np.abs(fr - fr[f_idx]).max(axis=1) <= 2 * self.r
            available &= ~near
        self.plan_dist = [cost[i][np.flatnonzero((fr == np.array(t)).all(1))[0]]
                          if t is not None else np.nan for i, t in enumerate(self.plan_targets)]
        self.n_frontier = len(fr)

    def _path(self, robot):
        t, par = self.plan_targets[robot], self.plan_parents[robot]
        path = [t]
        while path[-1] != tuple(self.pos[robot]):
            path.append(par[path[-1]])
        return path[::-1][1:]

    # ------------------------------------------------------------------- episode
    def reset(self):
        self.known = np.full((self.h, self.w), UNKNOWN, dtype=np.int8)
        free_cells = np.argwhere(self.true == FREE)
        start = tuple(free_cells[self.rng.integers(len(free_cells))])
        # deploy the team around one start point (BFS order from it)
        order, seen, q = [], {start}, deque([start])
        while q and len(order) < self.n:
            c = q.popleft()
            order.append(c)
            for dy, dx in NEIGH4:
                nb = (c[0] + dy, c[1] + dx)
                if self.true[nb] == FREE and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        self.pos = [list(c) for c in order]
        self.trail = [[tuple(c)] for c in order]
        for p in self.pos:
            self._sense(*p)
        self.plan()

    def observe(self):
        """Raw team-level statistics available BEFORE deciding on the next cycle."""
        assigned = [t for t in self.plan_targets if t is not None]
        # unknown cells within sensor range of planned targets = the info the next cycle could reveal
        potential = np.zeros((self.h, self.w), dtype=bool)
        for (y, x) in assigned:
            y0, y1 = max(0, y - self.r), min(self.h, y + self.r + 1)
            x0, x1 = max(0, x - self.r), min(self.w, x + self.r + 1)
            potential[y0:y1, x0:x1] = True
        potential &= self.known == UNKNOWN
        d = [v for v in self.plan_dist if not np.isnan(v)] if assigned else []
        return dict(
            known_frac=float((self.known != UNKNOWN).mean()),
            free_coverage=float((self.known == FREE).sum() / self.n_free_total),
            n_frontier=int(len(self.frontiers())),
            frac_assigned=len(assigned) / self.n,
            mean_target_dist=float(np.mean(d)) if d else 0.0,
            potential=int(potential.sum()),
        )

    def done(self):
        return all(t is None for t in self.plan_targets)

    def _replan_one(self, i, targets):
        """A robot that reached its frontier picks the nearest frontier that is not
        already close to a team-mate's target (local, per-robot decision)."""
        fr = self.frontiers()
        if len(fr) == 0:
            return []
        dist, parent = self._bfs(tuple(self.pos[i]))
        d = dist[fr[:, 0], fr[:, 1]]
        others = [t for j, t in enumerate(targets) if j != i and t is not None]
        for t in others:
            d[np.abs(fr - np.array(t)).max(axis=1) <= 2 * self.r] = np.inf
        if not np.isfinite(d).any():
            d = dist[fr[:, 0], fr[:, 1]]          # fall back to any reachable frontier
            if not np.isfinite(d).any():
                return []
        target = tuple(fr[int(np.argmin(d))])
        targets[i] = target
        path = [target]
        while path[-1] != tuple(self.pos[i]):
            path.append(parent[path[-1]])
        return path[::-1][1:]

    def step_cycle(self, record_frames=False):
        """Execute one cycle (up to k steps per robot). Returns raw outcome stats."""
        paths = [self._path(i) if self.plan_targets[i] is not None else [] for i in range(self.n)]
        targets = list(self.plan_targets)
        active = [bool(p) for p in paths]
        gain, steps, frames = 0, 0, []
        for s in range(self.k):
            moved = False
            for i in range(self.n):
                if not paths[i] and active[i]:
                    paths[i] = self._replan_one(i, targets)
                    if not paths[i]:
                        active[i] = False
                if paths[i]:
                    nxt = paths[i].pop(0)
                    self.pos[i] = list(nxt)
                    self.trail[i].append(nxt)
                    gain += self._sense(*self.pos[i])
                    steps += 1
                    moved = True
                    # drop the target if it stopped being a frontier (already explored)
                    if paths[i] and self.known[targets[i]] == FREE and not self._is_frontier(targets[i]):
                        paths[i] = []
            if record_frames and moved:
                frames.append((self.known.copy(), [tuple(p) for p in self.pos],
                               [list(t) for t in self.trail]))
        n_active = sum(active)
        self.plan()
        return dict(gain=gain, steps=steps, n_active=n_active), frames


def run_exhaustive(true_map, n_robots, seed, record_frames=False, **kw):
    """Explore until no reachable frontier is left. Returns a per-cycle log."""
    rng = np.random.default_rng(seed)
    env = TeamExplorationEnv(true_map, n_robots, rng, **kw)
    env.reset()
    obs, outcomes, all_frames = [env.observe()], [], []
    if record_frames:
        all_frames.append([(env.known.copy(), [tuple(p) for p in env.pos], [list(t) for t in env.trail])])
    while not env.done():
        out, frames = env.step_cycle(record_frames)
        outcomes.append(out)
        obs.append(env.observe())
        if record_frames:
            all_frames.append(frames)
    return dict(obs=obs, outcomes=outcomes, n=n_robots, k=env.k,
                map_size=true_map.shape[0], frames=all_frames, true_map=true_map)
