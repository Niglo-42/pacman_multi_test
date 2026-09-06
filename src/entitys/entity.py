from dataclasses import dataclass, field
from ..game_logic.direction import Dir
from pygame import Surface
from ..maze.maze import Maze
from ..game_logic.speed import BASE_SPEED


@dataclass
class Entity:
    direction: Dir = Dir.X
    id: int = 0
    accumulator: float = 0.0
    alive: bool = True
    speed: float = BASE_SPEED
    offset_xy: tuple[int, int] = (0, 0)
    spawn: tuple[int, int] = (0, 0)
    position: tuple[int, int] = (0, 0)
    last_pos: tuple[int, int] = (0, 0)
    tiles: list[Surface] = field(default_factory=list)
    surf: Surface = None
    anim: list[int] = field(default_factory=list)
    idx_anim: int = 0
    name: str = ""

    def update_position(self, maze: Maze) -> None:
        if not maze.is_open(self.position, self.direction):
            return
        x, y = self.position
        self.last_pos = self.position
        d_x, d_y = self.direction.add_delta_speed_f(self.offset_xy, self.speed)
        if d_x >= 8:
            d_x = 0
            x += 1
        elif d_x <= -8:
            d_x = 0
            x -= 1
        elif d_y >= 8:
            d_y = 0
            y += 1
        elif d_y <= -8:
            d_y = 0
            y -= 1
        self.position = (x, y)
        self.offset_xy = (d_x, d_y)

    def update_ghost_tile(self, ghost_afraid, eyes, afraid_end):
        self.surf.fill(0)
        if eyes:
            self.surf.blit(ghost_afraid[self.direction.value[5]], (0, 0))
        else:
            self.surf.blit(ghost_afraid[self.idx_anim >> 3 - 1 * (afraid_end)],
                           (0, 0))
        self.idx_anim += 1
        self.idx_anim &= 0xf

    def update_tile(self) -> None:
        self.surf.fill(0)
        self.surf.blit(
            self.tiles[self.anim[self.direction.value[3]][self.idx_anim >> 2]],
            (0, 0))
        self.idx_anim += 1
        self.idx_anim &= 0xf

    def tile_death(self, nb_frames, tile_of_anim_nb, idx): #4-13
        # for 60 fps, time_in_frame = 240, anim = 10 tiles
        # so we need 24 frames of the same tile before changing
        frame_per_tile = nb_frames // tile_of_anim_nb
        self.surf.fill(0)
        self.surf.blit(
            self.tiles[idx // frame_per_tile + 4],
            (0, 0))
