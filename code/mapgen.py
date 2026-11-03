"""Random indoor-style maps: rooms separated by walls with doors, plus clutter.

Cell values: 0 = free, 1 = obstacle.
Only the largest connected free region is kept, so every free cell is reachable
and "coverage" always means coverage of space the team could actually reach.
"""
import numpy as np
from collections import deque


def _largest_free_component(m):
    h, w = m.shape
    seen = np.zeros_like(m, dtype=bool)
    best = []
    for sy in range(h):
        for sx in range(w):
            if m[sy, sx] != 0 or seen[sy, sx]:
                continue
            comp, q = [], deque([(sy, sx)])
            seen[sy, sx] = True
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] == 0 and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(comp) > len(best):
                best = comp
    out = np.ones_like(m)
    ys, xs = zip(*best)
    out[list(ys), list(xs)] = 0
    return out


def make_map(size, rng):
    m = np.zeros((size, size), dtype=np.int8)
    m[0, :] = m[-1, :] = m[:, 0] = m[:, -1] = 1

    room = int(rng.integers(7, 11))
    xs = [x for x in range(room + int(rng.integers(-2, 3)), size - 3, room) if rng.random() > 0.2]
    ys = [y for y in range(room + int(rng.integers(-2, 3)), size - 3, room) if rng.random() > 0.2]
    for x in xs:
        m[1:-1, x] = 1
    for y in ys:
        m[y, 1:-1] = 1

    # doors: one 2-cell gap in each wall segment between crossing walls
    ybounds = [0] + ys + [size - 1]
    for x in xs:
        for a, b in zip(ybounds[:-1], ybounds[1:]):
            if b - a > 4 and rng.random() < 0.9:
                d = int(rng.integers(a + 1, b - 2))
                m[d:d + 2, x] = 0
    xbounds = [0] + xs + [size - 1]
    for y in ys:
        for a, b in zip(xbounds[:-1], xbounds[1:]):
            if b - a > 4 and rng.random() < 0.9:
                d = int(rng.integers(a + 1, b - 2))
                m[y, d:d + 2] = 0

    # clutter (furniture)
    for _ in range(size * size // 70):
        h, w = int(rng.integers(1, 4)), int(rng.integers(1, 4))
        y, x = int(rng.integers(2, size - 4)), int(rng.integers(2, size - 4))
        m[y:y + h, x:x + w] = 1

    return _largest_free_component(m)
