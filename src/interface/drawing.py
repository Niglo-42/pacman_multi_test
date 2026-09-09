"""HUD helpers (lives, fruits, entities) and the between-level intermission."""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame
from pygame import KEYDOWN, K_ESCAPE

from ..exceptions import GameExit
from ..game_logic.direction import Dir
from .render import Render

if TYPE_CHECKING:
    from ..game import Game


def draw_lives(self: Game) -> None:
    """Draw one Pac-Man icon per remaining life, below the maze."""
    x, y = self.render.lives_rect.topleft
    for i in range(self.max_lives):
        rect = self.render.lives_img.get_rect(
            topleft=(x + i * self.render.tile_size * 2, y))
        if i < self.player.lives:
            self.render.draw_obj([self.render.lives_img], [rect])
        else:
            Render.screen.fill((0, 0, 0), rect)


def draw_fruits(self: Game) -> None:
    """Draw the collected bonus fruits next to the lives."""
    x, y = self.render.lives_rect.topleft
    x += (self.maze.width // 2) * self.render.tile_size
    for i, fruit in enumerate(self.render.fruits):
        rect = fruit.get_rect(topleft=(x + i * self.render.tile_size, y))
        self.render.draw_obj([fruit], [rect])


def draw_entitys(self: Game) -> None:
    """Draw the second player (if any), the player and every ghost."""
    if self.player2:
        self.render.draw_entity(self.player2)
    self.render.draw_entity(self.player)
    for g in self.ghosts:
        self.render.draw_entity(g)


def play_intermission(self: Game) -> None:
    """Play the short "next level" cutscene (Escape skips it)."""
    duration_frames = self.fps * 3
    screen_w, screen_h = Render.screen.get_size()
    y_pos = screen_h // 2
    pacman_x = -60.0
    ghost_x = -180.0
    speed = (screen_w + 240) / duration_frames
    rndm_ghost = random.randint(0, len(self.ghosts) - 1)

    for _ in range(duration_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise GameExit
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                return

        pacman_x += speed
        ghost_x += speed

        Render.screen.fill((0, 0, 0))
        self.render.putstr("READY FOR NEXT LEVEL?", self.render.score, 0)

        self.player.update_tile(facing=Dir.E)
        player_surf = self.player.surf
        assert player_surf is not None
        Render.screen.blit(player_surf, (int(pacman_x), y_pos))

        if self.ghosts:
            ghost = self.ghosts[rndm_ghost]
            ghost.update_tile(facing=Dir.E)
            assert ghost.surf is not None
            Render.screen.blit(ghost.surf, (int(ghost_x), y_pos))
        pygame.display.flip()
        self.clock.tick(self.fps)
