"""Base class for the maze-moving entities (Pac-Man and the ghosts)."""
from dataclasses import dataclass, field

from pygame import Rect, Surface

from ..game_logic.direction import Dir
from ..game_logic.speed import BASE_SPEED
from ..maze.maze import Maze


@dataclass
class Entity:
    """Position, movement and animation shared by the player and the ghosts.

    Movement is tile-based with a sub-tile pixel ``offset_xy``; when the
    offset reaches one tile (8 base units) the entity snaps to the next cell.
    """

    direction: Dir = Dir.X
    id: int = 0
    accumulator: float = 0.0
    alive: bool = True
    speed: float = BASE_SPEED
    offset_xy: tuple[float, float] = (0, 0)
    spawn: tuple[int, int] = (0, 0)
    position: tuple[int, int] = (0, 0)
    last_pos: tuple[int, int] = (0, 0)
    tiles: list[Surface] = field(default_factory=list)
    surf: Surface | None = None
    rect: Rect | None = None
    anim: list[list[int]] = field(default_factory=list)
    idx_anim: int = 0
    name: str = ""

    def update_position(self, maze: Maze) -> None:
        """Advance one frame along ``direction`` if the way is open."""
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

    def update_ghost_tile(self, ghost_afraid: list[Surface], eyes: bool,
                          afraid_end: bool) -> None:
        """Pick the next frightened/eyes sprite frame for a ghost."""
        surf = self.surf
        assert surf is not None
        surf.fill(0)
        if eyes:
            surf.blit(ghost_afraid[self.direction.value[5]], (0, 0))
        else:
            surf.blit(ghost_afraid[self.idx_anim >> 3 - 1 * (afraid_end)],
                      (0, 0))
        self.idx_anim += 1
        self.idx_anim &= 0xf

    def update_tile(self, facing: Dir = Dir.X) -> None:
        """Advance the walk animation.

        With the default ``facing`` the entity's own ``direction`` is used;
        pass an explicit direction to force a frame (used by intermissions).
        """
        surf = self.surf
        assert surf is not None
        surf.fill(0)
        if facing == Dir.X:
            surf.blit(
                self.tiles[self.anim[self.direction.value[3]]
                           [self.idx_anim >> 2]],
                (0, 0))
        else:
            surf.blit(
                self.tiles[self.anim[facing.value[3]][self.idx_anim >> 2]],
                (0, 0))
        self.idx_anim += 1
        self.idx_anim &= 0xf

    def tile_death(self, nb_frames: int, tile_of_anim_nb: int,
                   idx: int) -> None:
        """Show frame *idx* of the death animation (sprites 4..13)."""
        frame_per_tile = nb_frames // tile_of_anim_nb
        surf = self.surf
        assert surf is not None
        surf.fill(0)
        surf.blit(
            self.tiles[idx // frame_per_tile + 4],
            (0, 0))
