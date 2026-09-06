from enum import Enum


class Dir(Enum):
    # work in (x y)
    N = (0, -1, 1, 0, 2, 2)
    E = (1,  0, 2, 1, 3, 0)
    S = (0,  1, 4, 2, 0, 3)
    W = (-1, 0, 8, 3, 1, 1)
    X = (0, 0, 0, 0, 0, 0)

    @property
    def delta(self) -> tuple[int, int]:
        return (self.value[0], self.value[1])

    def add_delta(self, x, y) -> tuple[int, int]:
        dx, dy = self.delta
        return (dx + x, dy + y)

    def add_delta_speed(self, xy, speed) -> tuple[int, int]:
        x, y = xy
        dx, dy = self.delta
        return dx * speed + x, dy * speed + y

    def add_delta_speed_f(self, xy, speed) -> tuple[float, float]:
        x, y = xy
        dx, dy = self.delta
        return dx * speed + x, dy * speed + y

    @property
    def bit(self) -> int:
        return self.value[2]

    @property
    def get_idx(self) -> int:
        return self.value[3]

    @classmethod
    def from_index(cls, index: int) -> "Dir":
        return (cls.N, cls.E, cls.S, cls.W)[index]

    @property
    def opposite(self) -> "Dir":
        return Dir.from_index(self.value[4])
