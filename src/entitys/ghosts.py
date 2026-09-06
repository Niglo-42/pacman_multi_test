from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..game import Game

from dataclasses import dataclass
from ..entitys.entity import Entity
from ..entitys.player import Player
from ..game_logic.direction import Dir
from ..game_logic.ghosts_state import GhostState
from ..maze.maze import Maze
from collections import deque
import numpy as np
import pygame
import random
import math


@dataclass
class Ghost(Entity):
    state: GhostState = GhostState.SCATTER
    spawn: tuple[int, int] = (0, 0)
    target: tuple[int, int] = (0, 0)
    changing_side: bool = False
    last_pos = spawn

    _afraid: list[pygame.Surface] | None = None
    _eyes: list[pygame.Surface] | None = None

    @staticmethod
    def _load_tiles(start: int, end: int, size: int) -> list[pygame.Surface]:
        return [
            pygame.transform.scale(
                pygame.image.load(f"images/sprites/"
                                  f"{str(i).zfill(3)}.png").convert_alpha(),
                                 (size * 2, size * 2)) for i in range(start,
                                                                      end)
                                  ]

    @classmethod
    def load_common_tiles(cls, size: int) -> None:
        cls._afraid = cls._load_tiles(49, 53, size)
        cls._eyes = cls._load_tiles(61, 65, size)

    @property
    def afraid(self) -> list[pygame.Surface]:
        return Ghost._afraid

    @property
    def eyes(self) -> list[pygame.Surface]:
        return Ghost._eyes

    def update(self, game: Game, is_flashing: bool) -> None:
        if self.state == GhostState.EYES and self.position == self.target:
            self.alive = True
        if self.offset_xy == (0, 0):
            if not self.changing_side:
                self.target = self.get_target(game.player, game.maze)
                self.update_dir(self.target, game.maze)
            else:
                self.direction = self.direction.opposite
                self.changing_side = False
        self.update_position(game.maze)
        if self.state == GhostState.EYES:
            self.update_ghost_tile(Ghost._eyes, True, is_flashing)
        elif self.state == GhostState.FRIGHTENED:
            self.update_ghost_tile(Ghost._afraid, False, is_flashing)
        else:
            self.update_tile()

    def update_dir(self, target: tuple[int, int], maze: Maze) -> Dir:
        if self.state == GhostState.EYES:
            self.direction = self.eyed_bfs(maze)
            return
        banned = [self.direction.opposite, Dir.X]
        candidates = [d for d in Dir if maze.is_open(self.position, d)
                      and d not in banned]
        if not candidates:
            self.direction = self.direction.opposite
            return

        #  add randomness to the choices to avoid loops
        rnd, direction = self.add_randomness(candidates)
        if rnd is True:
            self.direction = direction
            return

        best_c = None
        best_dist = float("inf")
        for c in candidates:
            tried_pos = c.add_delta_speed(self.position, 1)
            distance = np.linalg.norm(np.subtract(target, tried_pos))
            if distance < best_dist:
                best_dist = distance
                best_c = c
            continue
        self.direction = best_c

    def add_randomness(self, candidates: list[Dir]) -> tuple[bool, Dir]:
        dice = random.randint(1, 6)
        if dice == 6:
            direction = random.randint(0, len(candidates) - 1)
            return (True, candidates[direction])
        return (False, Dir.X)

    def get_target(self, player: Player, maze: Maze) -> tuple[int, int]:
        if self.state == GhostState.SCATTER:
            return self.spawn
        elif self.state == GhostState.EYES:
            return self.target
        elif self.state == GhostState.FRIGHTENED:
            return self.frightened_pos(self.position, player.position)
        raise NotImplementedError

    def frightened_pos(self, ghost_pos: tuple[int, int],
                       player_pos: tuple[int, int]) -> tuple[int, int]:
        diff_x = ghost_pos[0] - player_pos[0]
        diff_y = ghost_pos[1] - player_pos[1]
        target = (ghost_pos[0] + diff_x, ghost_pos[1] + diff_y)
        return target

    def eyed_bfs(self, maze: Maze) -> Dir:
        map = maze.map
        start = self.position
        target = self.target
        if start == target:
            return Dir.X

        cardinals = (Dir.N, Dir.E, Dir.S, Dir.W)
        queue = deque()
        visited = {start}

        for d in cardinals:
            nx, ny = d.add_delta(*start)
            if 0 <= nx < maze.width and 0 <= ny < maze.height and \
                    map[ny][nx] <= 2:
                if (nx, ny) == target:
                    return d
                visited.add((nx, ny))
                queue.append((nx, ny, d))

        while queue:
            cx, cy, first_dir = queue.popleft()
            for d in cardinals:
                nx, ny = d.add_delta(cx, cy)
                if 0 <= nx < maze.width and 0 <= ny < maze.height and \
                        map[ny][nx] <= 2:
                    if (nx, ny) not in visited:
                        if (nx, ny) == target:
                            return first_dir

                        visited.add((nx, ny))
                        queue.append((nx, ny, first_dir))
        return Dir.X


class Blinky(Ghost):
    def __init__(self, spawn: tuple[int, int], size):
        super().__init__()
        self.name = "Blinky"
        self.spawn = spawn
        self.position = spawn
        self.anim = [
                    [4, 5, 4, 5],  # n
                    [0, 1, 0, 1],  # e
                    [6, 7, 6, 7],  # s
                    [2, 3, 2, 3]   # w
                ]
        self.surf = pygame.Surface((size * 2,
                                    size * 2),
                                   pygame.SRCALPHA)

        self.tiles = [
            pygame.transform.scale(
                pygame.image.load(
                    f"images/sprites/{str(i).zfill(3)}."
                    "png").convert_alpha(),
                (size * 2,
                 size * 2)) for i in range(41, 49, 1)]

    def get_target(self, player: Player, maze: Maze) -> tuple[int, int]:
        if self.state == GhostState.CHASE or self.state == GhostState.ELROY1 \
                or self.state == GhostState.ELROY2:
            return player.position
        return super().get_target(player, maze)


class Pinky(Ghost):
    def __init__(self, spawn: tuple[int, int], size):
        super().__init__()
        self.name = "Pinky"
        self.spawn = spawn
        self.position = spawn
        self.anim = [
                    [4, 5, 4, 5],  # n
                    [0, 1, 0, 1],  # e
                    [6, 7, 6, 7],  # s
                    [2, 3, 2, 3]   # w
                ]
        self.surf = pygame.Surface((size * 2,
                                    size * 2),
                                   pygame.SRCALPHA)
        self.tiles = [
            pygame.transform.scale(
                pygame.image.load(
                    f"images/sprites/{str(i).zfill(3)}.png").convert_alpha(), (
                        size * 2, size * 2)) for i in range(53, 61, 1)]

    def get_target(self, player: Player, maze: Maze) -> tuple[int, int]:
        if self.state == GhostState.CHASE:
            return player.direction.add_delta_speed(player.position, 4)
        return super().get_target(player, maze)


class Inky(Ghost):
    def __init__(self, spawn: tuple[int, int], size):
        super().__init__()
        self.name = "Inky"
        self.spawn = spawn
        self.blinky = Blinky
        self.position = spawn
        self.anim = [
                    [4, 5, 4, 5],  # n
                    [0, 1, 0, 1],  # e
                    [6, 7, 6, 7],  # s
                    [2, 3, 2, 3]   # w
                ]
        self.surf = pygame.Surface((size * 2,
                                    size * 2),
                                   pygame.SRCALPHA)
        self.tiles = [
            pygame.transform.scale(
                pygame.image.load(
                    f"images/sprites/{str(i).zfill(3)}.png").convert_alpha(),
                (size * 2,
                 size * 2)) for i in range(65, 73, 1)]

    def get_target(self, player: Player, maze: Maze):
        if self.state == GhostState.CHASE:
            player_x, player_y = player.position
            d_x, d_y = player.direction.delta
            pivot = (player_x + 2 * d_x, player_y + 2 * d_y)
            blinky_x, blinky_y = self.blinky.position
            target = (2 * pivot[0] - blinky_x, 2 * pivot[1] - blinky_y)
            return target
        return super().get_target(player, maze)


class Clyde(Ghost):
    def __init__(self, spawn: tuple[int, int], size):
        super().__init__()
        self.name = "Clyde"
        self.spawn = spawn
        self.position = spawn
        self.anim = [
                    [4, 5, 4, 5],  # n
                    [0, 1, 0, 1],  # e
                    [6, 7, 6, 7],  # s
                    [2, 3, 2, 3]   # w
                ]
        self.surf = pygame.Surface((size * 2,
                                    size * 2),
                                   pygame.SRCALPHA)
        self.tiles = [
            pygame.transform.scale(
                pygame.image.load(
                    f"images/sprites/{str(i).zfill(3)}.png").convert_alpha(),
                (size * 2,
                 size * 2)) for i in range(78, 86, 1)]

    def get_target(self, player: Player, maze: Maze):
        if self.state == GhostState.CHASE:
            dist = math.dist(self.position, player.position)
            if dist < 8:
                return self.spawn
            return player.position
        return super().get_target(player, maze)
