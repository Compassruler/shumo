"""静态二维四邻域风险最短路；不是具有飞行动力学约束的航路规划器。"""
import heapq
import numpy as np


def shortest_path(risk, start, goal):
    risk = np.asarray(risk, dtype=float)
    if risk.ndim != 2 or np.any(np.isnan(risk)) or np.any(risk < 0):
        raise ValueError('需要非负二维风险矩阵，正无穷表示障碍')
    for point in (start, goal):
        if not (0 <= point[0] < risk.shape[0] and 0 <= point[1] < risk.shape[1]):
            raise ValueError('端点越界')
        if not np.isfinite(risk[point]):
            raise ValueError('端点位于障碍')
    distances, parent, queue = {start: 0.}, {}, [(0., start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > distances[node]:
            continue
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parent[path[-1]])
            return path[::-1], cost
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (node[0]+dr, node[1]+dc)
            if not (0 <= nxt[0] < risk.shape[0] and 0 <= nxt[1] < risk.shape[1]):
                continue
            if not np.isfinite(risk[nxt]):
                continue
            candidate = cost + 1 + .5*(risk[node]+risk[nxt])
            if candidate < distances.get(nxt, np.inf):
                distances[nxt], parent[nxt] = candidate, node
                heapq.heappush(queue, (candidate, nxt))
    return [], np.inf


def demo():
    grid = np.zeros((5, 5))
    grid[2, :4] = np.inf
    path, cost = shortest_path(grid, (0, 0), (4, 4))
    assert cost == 8 and all(np.isfinite(grid[p]) for p in path)
    grid[2, 4] = np.inf
    no_path, no_cost = shortest_path(grid, (0, 0), (4, 4))
    assert no_path == [] and np.isinf(no_cost)
    return {'path': path, 'cost': cost, 'unreachable_case_checked': True}


if __name__ == '__main__':
    print(demo())
