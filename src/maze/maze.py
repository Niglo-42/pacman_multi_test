"""Maze wrapper around the external A-Maze-ing (`mazegenerator`) package.

The generator returns a connectivity grid: each cell is a corridor whose
0..15 value encodes, bit by bit, which of its neighbours it connects to
(walls sit on the edges between cells). :func:`src.maze.convert.Convert`
then expands each cell into a 3x3 block of drawable tiles.

Public coordinates are ``(col, row)`` -- x then y.
"""
import math
import random

import mazegenerator
from pygame import Surface

from ..game_logic.direction import Dir


class MazeGenError(Exception):
    """Raised when the external maze generator fails or returns junk."""


class Maze:
    """A generated maze plus its pac-gum / super-gum / fruit placement."""

    def __init__(self, width: int, height: int, seed: int) -> None:
        """Generate the connectivity grid for a ``width`` x ``height`` maze."""
        self.height = height
        self.width = width
        self.seed = seed
        # A dedicated RNG (not the global one) so two mazes built with the
        # same seed place super pac-gums and fruits identically -- needed for
        # the host and guest to show the same maze in LAN games.
        self.rng = random.Random(seed)
        self.grid = self.maze_loader()
        self.map: list[list[int]] | None = None
        self.tiles: list[Surface] | None = None
        self.fruit_tiles: list[Surface] | None = None
        self.surf: Surface | None = None
        self.flag_fruit = 0

    def get_first_zero(self, pacman_x: int,
                       pacman_y: int) -> tuple[int, int]:
        """Return the first empty corridor tile that is not the '42' glyph."""
        assert self.map is not None
        for y, row in enumerate(self.map):
            for x, col in enumerate(row):
                if col == 0:
                    if x == pacman_x and y == pacman_y:
                        continue
                    if not self.is_in42(y, x):
                        return (x, y)
        return (1, 1)

    def add_fruit(self, pacman_pos: tuple[int, int], tile_size: int,
                  value: int) -> Surface:
        """Drop a bonus fruit on a free tile and return its sprite."""
        assert self.map is not None
        assert self.surf is not None
        assert self.fruit_tiles is not None
        fruit_idx = self.rng.randint(0, 7)
        x, y = self.get_first_zero(*pacman_pos)
        self.map[y][x] = value
        self.surf.blit(self.fruit_tiles[fruit_idx],
                       (x * tile_size, y * tile_size))
        return self.fruit_tiles[fruit_idx]

    def add_super_gum(self) -> None:
        """Place one super pac-gum in each of the four corner regions."""
        assert self.map is not None
        y_bottom = self.height * 95 // 100
        y_top = self.height * 5 // 100
        seq = [((1), (1, y_top)),
               ((self.width - 2), (1, y_top)),
               ((1), (y_bottom, self.height - 2)),
               ((self.width - 2), (y_bottom, self.height - 2))]
        for s in seq:
            x = s[0]
            low = min(s[1][0], s[1][1])
            high = max(s[1][0], s[1][1])
            y = self.rng.randint(low, high)
            if y == 0:
                y = 1
            elif y == self.height - 1:
                y -= 1
            self.map[y][x] = 2

    def is_open(self, position: tuple[int, int],
                direction: Dir) -> bool:
        """True if the next tile in *direction* from *position* is walkable."""
        assert self.map is not None
        col, row = position
        d_x, d_y = direction.delta
        cell = self.map[row + d_y][col + d_x]
        return cell <= 3

    def maze_loader(self) -> list[list[int]]:
        """Call the external generator (``perfect=False``); return its grid."""
        try:
            maze_gen = mazegenerator.MazeGenerator(
                size=(self.width, self.height),
                perfect=False, seed=self.seed)

            maze_grid: list[list[int]] = maze_gen.maze
            return maze_grid

        except Exception as e:
            raise MazeGenError(f"error while loading the maze: {e}")

    def is_in42(self, y: int, x: int) -> bool:
        """True if ``(x, y)`` is the centre of the generator's '42' glyph."""
        assert self.map is not None
        if self.map[y - 1][x] != 24:
            return False
        if self.map[y][x + 1] != 25:
            return False
        if self.map[y][x - 1] != 27:
            return False
        if self.map[y + 1][x] != 26:
            return False
        return True

    def kills_caves(self) -> None:
        """Fill in the small enclosed pockets the 3x3 expansion can leave,
        so the corridor graph stays fully connected."""
        game_map = self.map
        assert game_map is not None

        def is_pow_2(cardinal: int) -> bool:
            """True if exactly one bit is set."""
            return cardinal != 0 and not (cardinal & cardinal - 1)

        def is_four_pellets(y: int, x: int) -> bool:
            """True if all four neighbours of ``(x, y)`` are walkable."""
            if game_map[y - 1][x] > 2:
                return False
            if game_map[y][x + 1] > 2:
                return False
            if game_map[y][x - 1] > 2:
                return False
            if game_map[y + 1][x] > 2:
                return False
            return True

        old_map = [row[:] for row in game_map]
        dirs = [Dir.E, Dir.S, Dir.W, Dir.N]
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if is_four_pellets(y, x):
                    old_map[y][x] = 255

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if old_map[y][x] != 255:
                    continue
                degree = 0
                for direction in dirs:
                    nx, ny = direction.add_delta(x, y)
                    if 0 <= ny < self.height and 0 <= nx < self.width:
                        if old_map[ny][nx] <= 2:
                            degree += 1
                if degree >= 3:
                    old_map[y][x] = 1

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if old_map[y][x] != 255:
                    continue
                if old_map[y][x + 1] == 1 and old_map[y + 1][x] <= 2:
                    if old_map[y + 1][x + 1] > 2:
                        old_map[y][x] = 1
                elif old_map[y][x - 1] == 1 and old_map[y + 1][x] <= 2:
                    if old_map[y + 1][x - 1] > 2:
                        old_map[y][x] = 1
                elif old_map[y][x - 1] == 1 and old_map[y - 1][x] <= 2:
                    if old_map[y - 1][x - 1] > 2:
                        old_map[y][x] = 1
                elif old_map[y][x + 1] == 1 and old_map[y - 1][x] <= 2:
                    if old_map[y - 1][x + 1] > 2:
                        old_map[y][x] = 1

        island = set()
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if old_map[y][x] != 255:
                    continue
                queue = [(y, x)]
                old_map[y][x] = 0
                # BFS
                while queue:
                    dy, dx = queue.pop(0)
                    island.add((dy, dx))
                    for direction in dirs:
                        nx, ny = direction.add_delta(dx, dy)
                        if ny < self.height and nx < self.width:
                            if old_map[ny][nx] == 255:
                                old_map[ny][nx] = 0
                                queue.append((ny, nx))

        for y, x in island:
            cardinal = 0
            cardinal = int((y - 1, x) in island)
            cardinal |= ((y, x + 1) in island) << 1
            cardinal |= ((y + 1, x) in island) << 2
            cardinal |= ((y, x - 1) in island) << 3
            if cardinal == 15:
                if old_map[y - 1][x + 1] == 1:
                    game_map[y][x] = 19
                elif old_map[y + 1][x + 1] == 1:
                    game_map[y][x] = 16
                elif game_map[y + 1][x - 1] == 1:
                    game_map[y][x] = 17
                elif game_map[y - 1][x - 1] == 1:
                    game_map[y][x] = 18
            else:
                if is_pow_2(~cardinal & 0xf):
                    cardinal = ~cardinal & 0xf
                    if cardinal & 1:  # north
                        game_map[y][x] = 24
                    elif cardinal & 2:  # east
                        game_map[y][x] = 25
                    elif cardinal & 4:  # south
                        game_map[y][x] = 26
                    elif cardinal & 8:  # west
                        game_map[y][x] = 27
                else:
                    if cardinal & 6 == 6:  # NW
                        game_map[y][x] = 20
                    elif cardinal & 12 == 12:  # NE
                        game_map[y][x] = 21
                    elif cardinal & 9 == 9:  # SE
                        game_map[y][x] = 22
                    elif cardinal & 3 == 3:  # SW
                        game_map[y][x] = 23
                # 20 if corner, # 24 if junction

    def get_spawn(self) -> tuple[int, int]:
        """BFS from the maze centre for the player's first walkable tile."""
        assert self.map is not None
        mid_x, mid_y = self.width // 2, self.height // 2
        if mid_x == 0 and mid_y == 0:
            return (mid_x, mid_y)
        queue = [(mid_y, mid_x)]
        visited = {(mid_y, mid_x)}
        while queue:
            y, x = queue.pop(0)
            if not self.is_in42(y, x):
                if self.map[y][x] <= 3:
                    return (x, y)
            for d in Dir:
                nx, ny = d.add_delta(x, y)
                if (ny, nx) not in visited:
                    visited.add((ny, nx))
                    queue.append((ny, nx))
        raise MazeGenError("No spawn tile found in maze")

    def get_ghosts_spawns(self) -> list[tuple[int, int]]:
        """The four maze corners, one starting tile per ghost."""
        w, h = self.width, self.height
        corners = [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]
        return corners

    def get_opposite_corner(self, pos: tuple[int, int]) -> tuple[int, int]:
        """The corner farthest from *pos* (where an eaten ghost heads)."""
        best_dist = -1.0
        further_corner = pos
        for corner in self.get_ghosts_spawns():
            dist = math.dist(pos, corner)
            if dist > best_dist:
                best_dist = dist
                further_corner = corner
        return further_corner
