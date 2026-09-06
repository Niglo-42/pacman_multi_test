from dataclasses import dataclass
from ..entitys.entity import Entity
from ..maze.maze import Maze
from ..game_logic.direction import Dir
import pygame


@dataclass
class Player(Entity):
    desired_direction: Dir = Dir.X
    total_pellet: int = 0
    score: int = 0
    lives: int = 0

    def _input(self) -> None:
        keys = pygame.key.get_pressed()
        if self.id == 0:
            if keys[pygame.K_UP]:
                self.desired_direction = Dir.N
            elif keys[pygame.K_DOWN]:
                self.desired_direction = Dir.S
            elif keys[pygame.K_RIGHT]:
                self.desired_direction = Dir.E
            elif keys[pygame.K_LEFT]:
                self.desired_direction = Dir.W
        else:
            if keys[pygame.K_z]:
                self.desired_direction = Dir.N
            elif keys[pygame.K_s]:
                self.desired_direction = Dir.S
            elif keys[pygame.K_d]:
                self.desired_direction = Dir.E
            elif keys[pygame.K_q]:
                self.desired_direction = Dir.W

    def update_desire(self, maze: Maze) -> None:
        if self.offset_xy != (0, 0):
            return
        if self.direction == self.desired_direction:
            return
        if maze.is_open(self.position, self.desired_direction):
            self.direction = self.desired_direction
            self.dir_anim = self.direction.get_idx

    def update(self, maze: Maze) -> None:
        self._input()
        self.update_desire(maze)
        self.update_position(maze)
        self.update_tile()
