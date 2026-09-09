"""Rendering layer: window setup, tile scaling and every blit to the screen.

Only pygame calls with a direct MLX equivalent are used here: window
creation, image blitting and text rendering.
"""
from typing import ClassVar

import pygame

from ..entitys.entity import Entity
from ..maze.maze import Maze

FONT_PATH = "font/press_start_2p.ttf"


def collide_point(rect: pygame.Rect, x: int, y: int) -> bool:
    """Return True if the point ``(x, y)`` lies inside *rect*."""
    return (rect.x <= x <= rect.x + rect.width and
            rect.y <= y <= rect.y + rect.height)


class Info:
    """Plain holder for the current window width and height."""

    def __init__(self, w: int, h: int) -> None:
        """Store the window size."""
        self.current_w = w
        self.current_h = h


class Render:
    """Draws the maze, the entities and the HUD onto the shared window.

    The window and a few size invariants are class attributes so every
    ``Render`` instance (one is rebuilt per level) shares the same screen.
    """

    info: ClassVar[Info]
    screen: ClassVar[pygame.Surface]
    screen_rect: ClassVar[pygame.Rect]
    base_tile_size: ClassVar[int]

    @classmethod
    def init_invariant(cls, scinder: bool) -> None:
        """Create the window once. ``scinder`` uses a half-size window."""
        pg_info = pygame.display.Info()
        cls.info = Info(pg_info.current_w, pg_info.current_h)

        pygame.display.set_caption("Pac-Man")
        if scinder:
            cls.info.current_h //= 2
            cls.info.current_w //= 2
            cls.screen = pygame.display.set_mode(
                (cls.info.current_w, cls.info.current_h))
        else:
            cls.screen = pygame.display.set_mode(
                (cls.info.current_w, cls.info.current_h), pygame.FULLSCREEN)
        cls.screen_rect = cls.screen.get_rect()
        cls.base_tile_size = 8

    def __init__(self, maze: Maze, first: bool, scinder: bool) -> None:
        """Build the render surfaces and pre-scale every tile for *maze*."""
        if first:
            self.init_invariant(scinder)
        self.maze = maze
        ratio = min(Render.info.current_h // (maze.height + 4),
                    Render.info.current_w // (maze.width + 4))
        self.scale = max(1, ratio // Render.base_tile_size)
        self.tile_size = Render.base_tile_size * self.scale
        self.half_size = self.tile_size // 2

        self.font = pygame.font.Font(FONT_PATH, self.tile_size)
        maze_surf = pygame.Surface((maze.width * self.tile_size,
                                    maze.height * self.tile_size))
        self.maze.surf = maze_surf
        self.score = pygame.Surface((maze_surf.get_width(),
                                     self.tile_size))
        self.lvl = pygame.Surface((maze_surf.get_width(),
                                   self.tile_size))
        self.fruits = [
            pygame.Surface((self.tile_size, self.tile_size))
            for _ in range(2)]

        self.maze.tiles = [
            pygame.transform.scale(
                pygame.image.load(f"images/maze/{i}.png").convert_alpha(),
                (self.tile_size, self.tile_size)) for i in range(32)]
        self.maze.fruit_tiles = [
            pygame.transform.scale(
                pygame.image.load(
                    f"images/sprites/{str(i).zfill(3)}.png").convert_alpha(),
                (self.tile_size, self.tile_size)) for i in range(33, 41)]

        self.maze_rect = maze_surf.get_rect(
            center=Render.screen.get_rect().center)
        self.lives_img = pygame.transform.scale(
            pygame.image.load("images/sprites/015.png").convert_alpha(),
            (self.tile_size * 2, self.tile_size * 2))
        self.lives_rect = self.lives_img.get_rect(
            topleft=self.maze_rect.bottomleft)
        self.build_maze()

    def build_maze(self) -> None:
        """Blit every maze tile onto the off-screen maze surface."""
        game_map = self.maze.map
        tiles = self.maze.tiles
        assert game_map is not None
        assert tiles is not None
        for i, row in enumerate(game_map):
            for j, col in enumerate(row):
                self.draw_on_maze(tiles[col], i, j)

    def draw_on_maze(self, surf: pygame.Surface, y: int, x: int) -> None:
        """Blit *surf* at maze cell ``(x, y)`` on the maze surface."""
        maze_surf = self.maze.surf
        assert maze_surf is not None
        maze_surf.blit(surf, (x * self.tile_size, y * self.tile_size))

    def draw_maze_on_surf_screen(self) -> None:
        """Blit the whole maze surface onto the window."""
        maze_surf = self.maze.surf
        assert maze_surf is not None
        Render.screen.blit(maze_surf, self.maze_rect)

    def blit_at(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        """Blit *surf* at *rect*, offset by the maze's top-left corner."""
        Render.screen.blit(surf, rect.move(self.maze_rect.topleft))

    def draw_entity(self, entity: Entity) -> None:
        """Blit *entity* at its current sub-tile position."""
        surf = entity.surf
        assert surf is not None
        col, row = entity.position
        x = col * self.tile_size + entity.offset_xy[0] * self.scale
        y = row * self.tile_size + entity.offset_xy[1] * self.scale
        entity.rect = surf.get_rect(
            topleft=(x - self.half_size, y - self.half_size))
        self.blit_at(surf, entity.rect)

    def draw_obj(self, objs: list[pygame.Surface],
                 objs_rect: list[pygame.Rect]) -> None:
        """Blit a list of surfaces at their matching rects."""
        for obj, rect in zip(objs, objs_rect):
            Render.screen.blit(obj, rect)

    def hoover_opacity70(self, buttons: list[pygame.Surface],
                         rects: list[pygame.Rect]) -> None:
        """Dim every button, and clear the one currently hovered."""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        for rect, btn in zip(rects, buttons):
            btn.set_alpha(180)
            if collide_point(rect, mouse_x, mouse_y):
                Render.screen.fill(0, rect)

    def erase(self, rects: list[pygame.Rect]) -> None:
        """Fill every rect in *rects* with black."""
        for rect in rects:
            Render.screen.fill(0, rect)

    def putstr(self, string: str, surf: pygame.Surface,
               line: int) -> None:
        """Draw *string* near the top of the screen, *line* rows down."""
        text = self.font.render(string, False, "#dedeff")
        surf.fill(0)
        surf.blit(text, (0, 0))
        target_rect = surf.get_rect(
            midtop=(Render.screen_rect.centerx,
                    10 + text.get_height() * line))
        Render.screen.blit(surf, target_rect)

    def putstr_center(self, string: str, surf: pygame.Surface,
                      line: int) -> None:
        """Draw *string* centred on the screen, offset by *line* rows."""
        text = self.font.render(string, False, "#dedeff")
        surf.fill(0)
        surf.blit(text, (0, 0))
        target_rect = text.get_rect(
            center=(Render.screen_rect.centerx,
                    Render.screen_rect.centery +
                    10 + text.get_height() * line))
        Render.screen.blit(surf, target_rect)

    def draw_text(self, string: str, font: pygame.font.Font,
                  line: int, center: bool = False) -> None:
        """Blit *string* with an arbitrary *font*.

        With ``center=False`` the text is placed *line* rows below the top of
        the screen; with ``center=True`` it is centred on the screen.
        """
        text = font.render(string, False, "#dedeff")
        if center:
            target_rect = text.get_rect(center=Render.screen_rect.center)
        else:
            target_rect = text.get_rect(
                midtop=(Render.screen_rect.centerx,
                        text.get_height() * line))
        Render.screen.blit(text, target_rect)
