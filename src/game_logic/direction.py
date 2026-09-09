"""The four cardinal directions (plus ``X`` for "no direction")."""
from enum import Enum


class Dir(Enum):
    """A direction, encoded as a 6-tuple used across the movement code.

    The fields are: ``(dx, dy, wall_bit, anim_index, opposite_index,
    eyes_sprite_index)``. Coordinates are ``(x, y)`` with ``y`` growing down.
    """

    N = (0, -1, 1, 0, 2, 2)
    E = (1, 0, 2, 1, 3, 0)
    S = (0, 1, 4, 2, 0, 3)
    W = (-1, 0, 8, 3, 1, 1)
    X = (0, 0, 0, 0, 0, 0)

    @property
    def delta(self) -> tuple[int, int]:
        """The ``(dx, dy)`` step for this direction."""
        return (self.value[0], self.value[1])

    def add_delta(self, x: int, y: int) -> tuple[int, int]:
        """Return ``(x, y)`` moved one tile in this direction."""
        dx, dy = self.delta
        return (dx + x, dy + y)

    def add_delta_speed(self, xy: tuple[int, int],
                        speed: int) -> tuple[int, int]:
        """Return ``xy`` moved *speed* tiles in this direction (ints)."""
        x, y = xy
        dx, dy = self.delta
        return dx * speed + x, dy * speed + y

    def add_delta_speed_f(self, xy: tuple[float, float],
                          speed: float) -> tuple[float, float]:
        """Return ``xy`` moved *speed* units in this direction (floats)."""
        x, y = xy
        dx, dy = self.delta
        return dx * speed + x, dy * speed + y

    @property
    def bit(self) -> int:
        """The wall bit for this direction in the maze connectivity mask."""
        return self.value[2]

    @property
    def get_idx(self) -> int:
        """The row index of this direction in an entity's ``anim`` table."""
        return self.value[3]

    @classmethod
    def from_index(cls, index: int) -> "Dir":
        """Map ``0..3`` to ``N, E, S, W``."""
        return (cls.N, cls.E, cls.S, cls.W)[index]

    @property
    def opposite(self) -> "Dir":
        """The direction facing the other way."""
        return Dir.from_index(self.value[4])
