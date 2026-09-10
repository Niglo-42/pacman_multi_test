import sys
from typing import Any
import pygame
from pygame.locals import K_ESCAPE, KEYDOWN, K_SPACE
from .interface.render import Render, FONT_PATH
from .interface.menu import Menu
from .interface.drawing import draw_entitys, play_intermission
from .entitys.player import Player
from .entitys.ghosts import Ghost
from .game_logic.direction import Dir
from .game_logic.ghosts_state import GhostState, GhostStateManager
from .game_logic.updates import update_entitys, update_game_state, get_fruits
from .init import init_ghosts, init_maze, init_player, init_new_level
from .init import init_audio
from .exceptions import GameExit
from .constants import LAST_LEVEL


class Game:
    """Owns the whole game: window, maze, entities, and the screen router."""

    def __init__(self, args: dict[str, Any]) -> None:
        """Initialise pygame and start the first game from *args*."""
        pygame.display.init()
        pygame.font.init()
        self.args = args
        self.first = True
        self.audio = init_audio(self)
        self.start_new_game(self.args)

    def start_new_game(self, args: dict[str, Any]) -> None:
        """(Re)build every game object from *args* for a brand new game."""
        self.time: float = 90
        self.fps: int = args.get("fps", 60)
        self.run = True
        self.path: str = args.get("highscore_filename", "highscore.json")
        self.btn = None

        self.cheat_mode: bool = args.get("cheat_mode", False)
        self.points_per_pacgum: int = args.get("points_per_pacgum", 50)
        self.points_per_super_pacgum: int = \
            args.get("points_per_super_pacgum", 100)
        self.point_per_ghost: int = args.get("points_per_ghost", 100)
        self.total_pellet: int = 0
        self.newly_eaten_tiles: list[tuple[int, int]] = []
        self.last_level_seed: int = 0

        # Network role: "solo" (default), "host" or "guest".
        self.role: str = args.get("role", "solo")
        self.net = args.get("net")  # NetHost | NetGuest | None
        if self.role == "guest":
            # The maze must be an exact clone of the host's, so take its
            # seed and dimensions instead of the local configuration.
            assert self.net is not None
            remote_args = self.net.init_data["args"]
            width = remote_args.get("width", 6)
            height = remote_args.get("height", 6)
            seed = self.net.init_data["seed"]
        else:
            width = args.get("width", 6)
            height = args.get("height", 6)
            seed = args.get("seed", 1)
        try:
            self.maze = init_maze(self, width, height, seed)
        except Exception as err:
            print(f"maze generation failed: {err}")
            pygame.quit()
            sys.exit(1)
        self.level = 1
        self.pending_ready = True  # show the countdown before the level starts
        self.eaten_pellet: int = 0
        self.frightened_timer: float = 0.0
        self.global_timer: int = 0
        self.scinder: bool = args.get("scinder", False)
        self.state_timer: tuple[int, int] = (0, 0)
        self.render = Render(self.maze, self.first, self.scinder)
        self.first = False
        self.menu = Menu(self.render)
        self.ghost_state = GhostState.SCATTER
        self.elroy_cooldown: tuple[bool, int] = (False, 0)
        self.state_manager = GhostStateManager()
        self.player = init_player(self, 0, args.get("lives", 3))
        # In LAN both machines always have a player2: on the host it is the
        # networked avatar of the guest, on the guest it is the display-only
        # avatar of the host player.
        if self.role in ("host", "guest") or args.get("nb_player", 0) == 2:
            self.player2: Player | None = init_player(
                self, 1, args.get("lives", 3))
        else:
            self.player2 = None
        self.ghosts = init_ghosts(self)
        player_surf = self.player.surf
        assert player_surf is not None
        player_surf.blit(self.player.tiles[1], (0, 0))
        self.max_lives: int = args.get("lives", 3)
        self.clock = pygame.time.Clock()

    def monitor(self) -> None:
        """Top-level loop: route between the menu, gameplay and end screens.

        Closing the window raises :class:`GameExit` from whatever screen is
        active; it is caught here so pygame always shuts down cleanly.
        """
        action = "start"
        try:
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
                    self.start_new_game(self.menu.param_menu(
                        self.args, self.clock, self.fps))
                    action = "start"
                if action == "instructions":
                    action = self.menu.instructions(
                        self.args, self.clock, self.fps)
                if action == "play":
                    action = self.play()
                if action == "get_input" or action == "won":
                    self.menu.get_user_name(
                        self.render.font, self.path, self.player.score,
                        self.clock, self.fps)
                    self.start_new_game(self.args)
                    action = "start"
        except GameExit:
            pass
        pygame.quit()

    def play(self) -> str:
        # self.audio.chan.play(self.audio.sound_dic["eyes"], -1)
        """Run one game (all levels) and return the next router action."""
        while self.run or self.time <= 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        return "pause"
                    if event.key == K_SPACE and self.cheat_mode:
                        self.eaten_pellet = self.total_pellet
            if self.pending_ready:
                self.pending_ready = False
                self.get_ready(self.level == 1)
            if self.player.lives <= 0 or self.time <= 0:
                self.game_is_over()
                return "get_input"
            update_entitys(self)
            self.render.draw_maze_on_surf_screen()
            draw_entitys(self)
            get_fruits(self, self.maze, self.render.tile_size)
            state = update_game_state(self)
            if state == 1:
                return "won"
            if state == 2:
                # level cleared; get_ready() runs on the next iteration
                continue

            self.render.putstr(f"Score: {self.player.score}",
                               self.render.score, 0)
            self.render.putstr(f"Level: {self.level} Time: {self.time:.2f}",
                               self.render.lvl, 1)
            pygame.display.flip()
            self.time -= 1 / self.fps
            self.clock.tick(self.fps)  # caps the loop at fps iterations / s
        return "quit"

    def get_ready(self, first_lvl: bool) -> None:
        """Freeze the board and run a 3-2-1 countdown before the level starts.

        The level timer is not touched during the countdown. Escape skips it;
        closing the window raises :class:`GameExit`.
        """
        self.render.draw_maze_on_surf_screen()
        self.render.putstr(f"Score: {self.player.score}",
                           self.render.score, 0)
        self.render.putstr(f"Level: {self.level} Time: {self.time:.2f}",
                           self.render.lvl, 1)
        background = Render.screen.copy()
        scrim = pygame.Surface(Render.screen.get_size(), pygame.SRCALPHA)
        scrim.fill((0, 0, 0, 160))
        font = pygame.font.Font(FONT_PATH, self.render.tile_size * 6)

        countdown = (3, 2, 1)
        first_lvl_countdown = (5, 4, 3, 2, 1)
        timer = first_lvl_countdown if first_lvl else countdown
        # if first_lvl:
        #     self.audio.play_sound('ready')

        for count in timer:
            digit = font.render(str(count), False, "#ffd24a")
            rect = digit.get_rect(center=Render.screen_rect.center)
            for _ in range(self.fps):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise GameExit
                    if event.type == KEYDOWN and event.key == K_ESCAPE:
                        return
                Render.screen.blit(background, (0, 0))
                Render.screen.blit(scrim, (0, 0))
                Render.screen.blit(digit, rect)
                pygame.display.flip()
                self.clock.tick(self.fps)

    def player_died(self, player: Player, ghosts: list[Ghost]) -> None:
        """Play the death animation, then respawn *player* and the ghosts."""
        # print("keepalive busy:", pygame.mixer.Channel(0).get_busy())
        # self.audio.play_sound('death')
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
        # if self.player.lives == 1:
        #     self.audio.play_sound('life')

    def game_is_over(self) -> None:
        """Show the "game over" screen with the final score for ~2 seconds."""
        duration_frames = int(self.fps * 2)
        for _ in range(duration_frames):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
            Render.screen.fill((0, 0, 0))
            self.render.putstr_center("GAME OVER", self.render.score, 0)
            self.render.putstr_center(
                f"FINAL SCORE  {self.player.score}", self.render.lvl, 1)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def level_is_won(self) -> None:
        """Go to the next level, or show the victory screen after the last."""
        self.level += 1
        if self.level > LAST_LEVEL:
            self.play_victory()
            return
        play_intermission(self)
        init_new_level(self)
        if self.role == "host":
            assert self.net is not None
            self.net.send_new_level(self.level, self.last_level_seed)
        pygame.time.wait(500)

    def play_victory(self) -> None:
        """Play the end-of-game victory animation with the final score."""
        duration_frames = self.fps * 5
        screen_w, screen_h = Render.screen.get_size()
        y_pos = screen_h // 2
        trail = self.render.tile_size * 3
        pacman_x = -60.0
        travel = screen_w + trail * (len(self.ghosts) + 1) + 60
        speed = travel / duration_frames
        colors = ("#ffd24a", "#ff5bd6", "#5bd0ff", "#5bffb0")

        for frame in range(duration_frames):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    return

            pacman_x += speed

            Render.screen.fill((0, 0, 0))
            self.render.putstr("YOU WIN!", self.render.score, 0)
            self.render.putstr(f"FINAL SCORE  {self.player.score}",
                               self.render.lvl, 1)

            color = colors[(frame // 6) % len(colors)]
            banner = self.render.font.render("*  VICTORY  *", False, color)
            Render.screen.blit(banner, banner.get_rect(
                center=(screen_w // 2, y_pos - trail)))

            for i, ghost in enumerate(self.ghosts):
                ghost_tile = ghost.afraid[(frame // 6) % 4]
                bob = ((frame // 5 + i) % 2) * self.render.scale * 3
                gx = int(pacman_x) - (i + 1) * trail
                Render.screen.blit(ghost_tile, (gx, y_pos - bob))

            anim_tile = self.player.tiles[(frame // 6) % 4]
            Render.screen.blit(anim_tile, (int(pacman_x), y_pos))

            pygame.display.flip()
            self.clock.tick(self.fps)
