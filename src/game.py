import pygame
from pygame.locals import K_ESCAPE, KEYDOWN
from .interface.render import Render
from .interface.menu import Menu
from .interface.drawing import draw_entitys, play_intermission
# from .interface.parameters import set_parameters
from .entitys.player import Player
from .entitys.ghosts import Ghost
from .game_logic.direction import Dir
from .game_logic.ghosts_state import GhostState, GhostStateManager
from .game_logic.updates import update_entitys, update_game_state, get_fruits
from .init import init_ghosts, init_maze, init_player, init_new_level
from config.parser_config import print_obj


class Game:
    def __init__(self, args):
        pygame.display.init()
        pygame.font.init()
        self.args = args
        self.first = True
        self.start_new_game(self.args)

    def start_new_game(self, args: dict):
        self.fps = args.get("fps", 60)
        self.run = True
        self.path = args.get("highscore_filename", "highscore.json")
        self.cheat_mode = args.get("cheat_mode", False)
        self.points_per_pacgum = args.get("points_per_pacgum", 50)
        self.points_per_super_pacgum = \
            args.get("points_per_super_pacgum", 100)
        self.point_per_ghost = args.get("points_per_ghost", 100)
        self.total_pellet: int = 0

        # --- réseau : "solo" (défaut), "host" ou "guest" ---
        self.role = args.get("role", "solo")
        self.net = args.get("net")  # NetHost | NetGuest | None
        if self.role == "guest":
            # le labyrinthe doit être un clone EXACT de celui de l'hôte :
            # on reprend son seed/dimensions plutôt que la config locale.
            remote_args = self.net.init_data["args"]
            width = remote_args.get("width", 6)
            height = remote_args.get("height", 6)
            seed = self.net.init_data["seed"]
        else:
            width = args.get("width", 6)
            height = args.get("height", 6)
            seed = args.get("seed", 1)
        self.maze = init_maze(self, width, height, seed)

        self.level = 1
        self.eaten_pellet: int = 0
        self.frightened_timer: float = 0.0
        self.global_timer: int = 0
        self.state_timer: tuple[int, int] = (0, 0)
        self.render = Render(self.maze, self.first)
        self.first = False
        self.menu = Menu(self.render)
        self.ghost_state = GhostState
        self.elroy_cooldown: tuple[bool, int] = (False, 0)
        self.state_manager = GhostStateManager()
        self.audio_enabled = args.get("audio_enable", False)
        self.player = init_player(self, 0, args.get("lives", 3))
        # en LAN, les deux machines ont toujours un player2 : côté hôte
        # c'est l'avatar (réseau) de l'invité ; côté invité c'est
        # l'avatar (réseau, affichage seul) du joueur hôte.
        if self.role in ("host", "guest") or args.get("nb_player", 0) == 2:
            self.player2 = init_player(self, 1, args.get("lives", 3))
        else:
            self.player2 = None
        self.ghosts = init_ghosts(self)
        self.player.surf.blit(self.player.tiles[1], (0, 0))
        self.max_lives = args.get("lives", 3)
        self.clock = pygame.time.Clock()
        # print_obj(args)
        # les 33 premières tiles sont des pacmans

    # def set_args(self, args: dict):
    #     for k, v in args.items():
    #         setattr(self, k, v)

    def monitor(self):
        action = "start"
        while self.run:
            if action == "start":
                action = self.menu.main_menu(self.clock, self.fps)
            if action == "play":
                action = self.play()
            if action == "quit":
                self.run = False
            if action == "score":
                action = self.menu.score(self.path, self.clock, self.fps)
            if action == "pause":
                action = self.menu.pause_menu(self.clock, self.fps)
            if action == "param":
                self.start_new_game((self.menu.param_menu(self.args,
                                                          self.clock,
                                                          self.fps)))
                action = "start"
            if action == "play":
                action = self.play()
            if action == "get_input":
                action = self.menu.get_user_name(self.render.font,
                                                 self.path,
                                                 self.player.score,
                                                 self.clock, self.fps)
                self.start_new_game(self.args)
        pygame.quit()

    def play(self) -> str:
        while self.run:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run = False
                    return "quit"
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        return "pause"
            if self.player.lives <= 0:
                self.game_is_over()
                return "get_input"
            update_entitys(self)
            self.render.draw_maze_on_surf_screen()
            draw_entitys(self)
            get_fruits(self, self.maze, self.render.tile_size)
            update_game_state(self)
            self.render.putstr(f"Highscore: {self.player.score}",
                               self.render.score, 0)
            self.render.putstr(f"Level: {self.level}", self.render.lvl, 1)
            pygame.display.flip()
            self.clock.tick(self.fps)  # vaut un sleep qui sync sur fps / 1000
        pygame.quit()

    def player_died(self, player: Player, ghosts: list[Ghost]) -> None:
        self.elroy_cooldown = (True, self.global_timer)
        player.alive = False
        player.lives -= 1
        current_time = self.global_timer
        time_of_anim_in_frame = int(self.fps * 1.5)
        idx = 0
        while self.global_timer + idx - current_time < time_of_anim_in_frame:
            player.tile_death(time_of_anim_in_frame, 10, idx)
            self.render.draw_maze_on_surf_screen()
            self.render.draw_entity(player)
            pygame.display.flip()
            idx += 1
            self.clock.tick(self.fps)
        self.global_timer += idx
        self.state_timer = (0, 0)
        self.frightened_timer = 0
        player.position = player.spawn
        player.offset_xy = (0, 0)
        player.direction = Dir.X
        player.desired_direction = Dir.X
        player.alive = True
        for g in ghosts:
            g.state = GhostState.SCATTER
            g.position = g.spawn
            g.offset_xy = (0, 0)

    def game_is_over(self) -> None:
        duration_frames = int(self.fps * 1.5)
        for _ in range(duration_frames):
            Render.screen.fill((0, 0, 0))
            self.render.putstr_center("GAME OVAIRE", self.render.score, 0)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def level_is_won(self) -> None:
        play_intermission(self)
        init_new_level(self)
        if self.role == "host":
            self.net.send_new_level(self.level, self.last_level_seed)
        pygame.time.wait(500)
