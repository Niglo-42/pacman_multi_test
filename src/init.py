from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
import random

if TYPE_CHECKING:
    from .game import Game
    from .entitys.ghosts import Ghost
    from .entitys.player import Player
    from .maze.maze import Maze


def init_audio(self: Game) -> None:
    self.audio_enabled = False
    # la suite fonctionnera que sur les imac pas sur mon intel #snif
    # try:
    #     pygame.mixer.init()
    #     self.audio_enabled = True
    # except pygame.error:
    #     self.audio_enabled = False


def init_ghosts(self: Game) -> list[Ghost]:
    from .entitys.ghosts import Ghost, Blinky, Pinky, Inky, Clyde
    Ghost.load_common_tiles(self.render.tile_size)
    ghost_classes = [Blinky, Pinky, Inky, Clyde]
    ghost_spawns = self.maze.get_ghosts_spawns()
    ghosts = [cls(spawn, self.render.tile_size) for cls, spawn in
              zip(ghost_classes, ghost_spawns)]
    ghosts[2].blinky = ghosts[0]
    return ghosts


def init_maze(self: Game, width: int, height: int, seed: int) -> Maze:
    from .maze.maze import Maze
    from .maze.convert import Convert
    maze = Maze(width=width, height=height, seed=seed)
    maze.map = Convert.cell2tiles(maze)
    maze.height *= 3
    maze.width *= 3
    maze.add_super_gum()
    maze.kills_caves()

    self.total_pellet = sum(row.count(1) for row in maze.map)
    return maze


def init_player(self: Game, id: int, lives: int) -> Player:
    from .entitys.player import Player
    spawn = self.maze.get_spawn()
    player = Player(
        id=id, name=str(id), idx_anim=0,
        lives=lives,
        anim=[
                [23, 24, 2, 24],    # n
                [0, 1, 2, 1],  # e
                [31, 32, 2, 32],  # s
                [14, 15, 2, 15]  # w
            ],
        spawn=spawn,
        position=spawn,
        last_pos=spawn,
        surf=pygame.Surface((self.render.tile_size * 2,
                            self.render.tile_size * 2), pygame.SRCALPHA),
        tiles=[pygame.transform.scale
               (pygame.image.load(f"images/sprites/{str(i).zfill(3)}."
                                  "png").convert_alpha(),
                                 (self.render.tile_size * 2,
                                  self.render.tile_size * 2))
               for i in range(33)])
    return player


def init_new_level(self: Game, seed: int | None = None) -> None:
    from .game_logic.ghosts_state import GhostState
    from .interface.render import Render
    saved_lives = self.player.lives
    self.level += 1
    self.eaten_pellet = 0
    self.global_timer = 0
    self.state_timer = (0, 0)
    self.frightened_timer = 0
    self.elroy_cooldown = (False, 0)
    self.ghost_state = GhostState.SCATTER

    # en LAN, l'hôte choisit le seed et le transmet à l'invité (via le
    # paquet réseau "new_level") pour que les deux régénèrent le même
    # labyrinthe ; en solo/host on tire un seed aléatoire comme avant.
    if seed is None:
        seed = random.randint(0, 256)
    self.last_level_seed = seed
    self.maze = init_maze(self, self.maze.width // 3,
                          self.maze.height // 3,
                          seed=seed)
    score = self.player.score
    self.player = init_player(self, 0, saved_lives)
    self.player.score = score
    if self.player2:
        # préexistant : player2 n'était pas réinitialisé au changement
        # de niveau (bug indépendant du LAN) ; on le fait maintenant
        # pour que le mode 2 joueurs (local ou LAN) reste cohérent.
        saved_lives2 = self.player2.lives
        score2 = self.player2.score
        self.player2 = init_player(self, 1, saved_lives2)
        self.player2.score = score2
    self.ghosts = init_ghosts(self)
    self.render = Render(self.maze, False, self.scinder)
