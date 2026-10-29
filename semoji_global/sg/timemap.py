"""구간별 선형 시간 변환. old 시각 → new 시각."""
from bisect import bisect_right


class PiecewiseMap:
    def __init__(self, anchors):
        pts = [(float(a), float(b)) for a, b in anchors]
        if not pts:
            raise ValueError("anchors empty")
        for (o0, n0), (o1, n1) in zip(pts, pts[1:]):
            if o1 <= o0:
                raise ValueError(f"old not strictly increasing: {o0} -> {o1}")
            if n1 < n0:
                raise ValueError(f"new decreasing: {n0} -> {n1}")
        self.pts = pts
        self._old = [p[0] for p in pts]

    @classmethod
    def identity(cls):
        return cls([(0.0, 0.0)])

    def __call__(self, t):
        p = self.pts
        if t <= p[0][0]:
            return p[0][1] + (t - p[0][0])
        if t >= p[-1][0]:
            return p[-1][1] + (t - p[-1][0])
        i = bisect_right(self._old, t) - 1
        (o0, n0), (o1, n1) = p[i], p[i + 1]
        return n0 + (n1 - n0) * (t - o0) / (o1 - o0)

    def ratio(self, a, b):
        return (self(b) - self(a)) / (b - a)

    def child(self, st_old, st_new, sx):
        """프리컴프 레이어(startTime st, stretch sx[배수])의 자식 컴프 시간 변환."""
        return PiecewiseMap([((o - st_old) / sx, (n - st_new) / sx) for o, n in self.pts])

    def to_list(self):
        return [[o, n] for o, n in self.pts]
