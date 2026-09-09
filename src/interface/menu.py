"""Menu screens: main menu, pause menu, parameters, highscores, name entry.

Every screen runs its own event loop. Closing the window raises
:class:`GameExit`, which unwinds to :meth:`src.game.Game.monitor`.
"""
import json
from typing import Any

import pygame

from ..exceptions import GameExit
from .render import Render, collide_point

HIGHSCORE_LIMIT = 10
FONT_PATH = "font/press_start_2p.ttf"


def load_scores(path: str) -> dict[str, int]:
    """Load the highscore file as a clean ``{name: score}`` mapping.

    A missing or corrupt file is treated as an empty leaderboard. Entries
    whose score is not a non-negative integer are dropped.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): int(score)
        for name, score in raw.items()
        if isinstance(score, (int, float)) and not isinstance(score, bool)
        and score >= 0
    }


def save_score(path: str, name: str, score: int) -> None:
    """Insert ``name``/``score``, then keep only the top ten entries."""
    scores = load_scores(path)
    scores[name] = max(scores.get(name, 0), score)
    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    trimmed = dict(top[:HIGHSCORE_LIMIT])
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(trimmed, handle, indent=2)
    except OSError as err:
        print(f"highscore: could not save to {path}: {err}")


class ToggleBox:
    """A labelled ON/OFF switch used in the parameters screen."""

    def __init__(self, string: str, size: int, boolean: bool) -> None:
        """Render the *string* label and the initial *boolean* state."""
        self.name = string
        self.font = pygame.font.Font(FONT_PATH, size)
        self.text = self.font.render(string, False, "#dedeff")
        self.bool_val = boolean
        self.bool = self.font.render("ON" if boolean else "OFF", False,
                                     "#0ec43c" if boolean else "#ff0000")
        self.t_size_w, self.t_size_h = self.text.get_size()
        self.b_size_w, self.b_size_h = self.bool.get_size()
        self.surf = pygame.Surface((self.t_size_w + self.b_size_w + 10,
                                    self.t_size_h))
        self.draw_box()

    def flip(self) -> None:
        """Toggle the value and re-render the ON/OFF label."""
        self.bool_val = not self.bool_val
        self.bool = self.font.render(
            "ON" if self.bool_val else "OFF",
            False, "#0ec43c" if self.bool_val else "#ff0000")
        self.b_size_w, self.b_size_h = self.bool.get_size()

    def draw_box(self) -> None:
        """Redraw the label and value onto the widget surface."""
        self.surf.fill(0)
        self.surf.blit(self.text, (0, 0))
        self.surf.blit(self.bool, (self.t_size_w + 10, 0))


class ParamBox:
    """A labelled horizontal slider bound to an integer range."""

    def __init__(self, string: str, size: int, min_v: int, max_v: int,
                 range_size: int, value: int) -> None:
        """Build a *min_v*..*max_v* slider starting at *value*."""
        self.name = string
        self.font = pygame.font.Font(FONT_PATH, size)
        self.text = self.font.render(string, False, "#dedeff")
        self.font_val = self.font.render(str(value), False, "#181713")
        self.value = value
        self.t_size_w, self.t_size_h = self.text.get_size()
        self.surf = pygame.Surface((self.t_size_w + range_size + 10,
                                    self.t_size_h))
        self.range_val = max_v - min_v
        self.min = min_v
        self.max = max_v
        self.percent = (value - min_v) / self.range_val
        self.range = pygame.Surface((range_size, self.t_size_h))
        self.range.fill("#3B1D8B")
        self.range_box = pygame.Surface((range_size, self.t_size_h))
        self.range_box.fill("#dee7de")
        self.draw_box(range_size)
        self.pad_w = self.surf.get_size()[0] // 2

    def draw_box(self, range_size: int) -> None:
        """Redraw the label, the filled bar and the current value."""
        percent = self.percent
        self.range_box.fill("#dee7de")
        self.range_box.blit(self.range, (-int(range_size * (1 - percent)), 0))
        self.surf.blit(self.range_box, (self.t_size_w + 10, 0))
        self.surf.blit(self.text, (0, 0))
        rect = self.font_val.get_rect(
            midtop=(self.t_size_w + 10 + range_size // 2, 0))
        self.surf.blit(self.font_val, rect)


class RangeBox(ParamBox):
    """Alias of :class:`ParamBox` kept for readability at call sites."""

    def __init__(self, string: str, size: int, min_v: int, max_v: int,
                 range_size: int, value: int) -> None:
        """See :meth:`ParamBox.__init__`."""
        super().__init__(string, size, min_v, max_v, range_size, value)


class Menu:
    """All the out-of-game screens, sharing one :class:`Render`."""

    def __init__(self, render: Render) -> None:
        """Bind to the active :class:`Render` and cache the window size."""
        self.render = render
        self.w, self.h = Render.screen.get_size()

    def score(self, path: str, clock: pygame.time.Clock,
              fps: int) -> str:
        """Show the highscore table until Escape is pressed."""
        scores = load_scores(path)
        Render.screen.fill(0)
        max_char_len = 30
        line_spacing = 2
        n = min(max(len(scores), 1), HIGHSCORE_LIMIT)
        available_height = (Render.screen.get_height() //
                            (line_spacing * (n + 3)))
        size = min(available_height,
                   Render.screen.get_width() // max_char_len)
        size = max(size, 1)
        font = pygame.font.Font(FONT_PATH, size)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        self.render.draw_text("HIGH SCORES", font, 0)
        for i, (name, score) in enumerate(ranked[:HIGHSCORE_LIMIT], 1):
            self.render.draw_text(f"{i}. {name} - {score}", font, (i + 1) * 2)
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                if (event.type == pygame.KEYDOWN
                        and event.key == pygame.K_ESCAPE):
                    return "start"
            clock.tick(fps)

    def instructions(self, config: dict[str, Any], clock: pygame.time.Clock,
                     fps: int) -> str:
        """Show the controls and scoring rules until Escape is pressed."""
        Render.screen.fill(0)
        lines = [
            "Eat every pac-gum to clear the level",
            "Player 1   -   arrow keys",
            "Player 2   -   Z  Q  S  D",
            "Escape   -   pause / back to menu",
            "Super pac-gum makes the ghosts edible",
            "pac-gum {}   super {}   ghost {}".format(
                config.get("points_per_pacgum", 10),
                config.get("points_per_super_pacgum", 50),
                config.get("points_per_ghost", 200)),
            "You start with {} lives".format(config.get("lives", 3)),
            "Press Escape to return",
        ]
        line_spacing = 2
        n = len(lines)
        max_char_len = max(len(line) for line in lines)
        available_height = (Render.screen.get_height() //
                            (line_spacing * (n + 3)))
        size = min(available_height,
                   Render.screen.get_width() // max_char_len)
        size = max(size, 1)
        font = pygame.font.Font(FONT_PATH, size)
        self.render.draw_text("INSTRUCTIONS", font, 0)
        for i, line in enumerate(lines, 1):
            self.render.draw_text(line, font, (i + 1) * 2)
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                if (event.type == pygame.KEYDOWN
                        and event.key == pygame.K_ESCAPE):
                    return "start"
            clock.tick(fps)

    def get_user_name(self, font: pygame.font.Font, path: str, score: int,
                      clock: pygame.time.Clock, fps: int,
                      max_len: int = 10) -> str:
        """Prompt for a 1..``max_len`` char name, then store the highscore."""
        pygame.key.start_text_input()
        user_name = ""
        active = True
        pad = Render.screen.get_rect().center
        txt_surface = font.render(user_name + "|", True, (255, 255, 255))
        Render.screen.fill(0)
        error_surface: pygame.Surface | None = None
        flag_errased = False
        frame = 0
        self.render.draw_text("Enter your name...", font, 1)
        while active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                if len(user_name) > 0 and error_surface and not flag_errased:
                    flag_errased = True
                    pad_h = pad[1] + txt_surface.get_height()
                    error_surface.fill("#000000")
                    Render.screen.blit(error_surface,
                                       (error_surface.get_rect(
                                        center=(pad[0], pad_h))))
                elif event.type == pygame.TEXTINPUT:
                    if len(user_name) < max_len and (
                            event.text == ' ' or str(event.text).isalnum()):
                        user_name += event.text
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        user_name = user_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        if not len(user_name):
                            flag_errased = False
                            pad_h = pad[1] + txt_surface.get_height()
                            error_surface = font.render(
                                "enter at least 1 letter", True, "#ca1212")
                            Render.screen.blit(error_surface,
                                               (error_surface.get_rect(
                                                   center=(pad[0], pad_h))))
                        else:
                            active = False

            txt_surface.fill((0, 0, 0))
            Render.screen.blit(txt_surface,
                               (txt_surface.get_rect(center=(pad))))
            cond = (frame > fps // 2)
            txt_surface = font.render(
                user_name + ("|" if cond else " "), True, "#ffffff")
            Render.screen.blit(txt_surface,
                               (txt_surface.get_rect(center=(pad))))
            pygame.display.flip()
            frame += 1
            frame %= fps
            clock.tick(fps)

        pygame.key.stop_text_input()
        save_score(path, user_name, score)
        return "start"

    def param_menu(self, config: dict[str, Any], clock: pygame.time.Clock,
                   fps: int) -> dict[str, Any]:
        """Let the player tweak the config with sliders/toggles; return it."""
        clamps = {
            "width": (6, 33),
            "height": (6, 33),
            "lives": (1, 3),
            "seed": (0, 0xffff),
            "points_per_pacgum": (1, 100),
            "points_per_super_pacgum": (1, 500),
            "fps": (30, 60),
            "points_per_ghost": (1, 1600),
            "nb_player": (1, 2)
        }
        Render.screen.fill(0)
        toggles = ("cheat_mode", "audio_enable")
        boxes: list[RangeBox] = []
        toggle_boxes: list[ToggleBox] = []
        nb_boxes = len(clamps.keys()) + len(toggles)
        font_size = self.h // (nb_boxes * 4 + 2)
        range_size = Render.screen.get_size()[0] // 10
        for toggle in toggles:
            toggle_boxes.append(
                ToggleBox(toggle, font_size, bool(config.get(toggle, False))))
        for name, (min_v, max_v) in clamps.items():
            current = config.get(name, min_v)
            boxes.append(RangeBox(name, font_size, min_v,
                                  max_v, range_size, current))
        pad_w = Render.screen.get_rect().centerx
        pad_h = (Render.screen.get_size()[1] - font_size * nb_boxes * 2) // 2
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                if (event.type == pygame.KEYDOWN and
                        event.key == pygame.K_ESCAPE):
                    for key, val in config.items():
                        for box in boxes:
                            if box.name == key:
                                config[key] = box.value
                        for tog in toggle_boxes:
                            if tog.name == key:
                                config[key] = tog.bool_val
                    return config
                if pygame.mouse.get_pressed()[0]:
                    mx, my = pygame.mouse.get_pos()
                    j = 0
                    for box in boxes:
                        rect = box.surf.get_rect(center=((
                            pad_w, j * (font_size * 2) + pad_h)))
                        rect.x += (box.text.get_size()[0] + 10)
                        r_box = box.range_box.get_rect()
                        r_box.x += rect.x
                        r_box.y += rect.y
                        if collide_point(r_box, mx, my):
                            len2left_edge = mx - r_box.x
                            box.percent = len2left_edge / range_size
                            val = round(box.range_val * box.percent)
                            val += box.min
                            box.value = val
                            box.font_val = box.font.render(str(val),
                                                           False, "#181713")
                            box.draw_box(range_size)
                        j += 1
                    for tog in toggle_boxes:
                        rect = tog.surf.get_rect(center=((
                            pad_w, j * (font_size * 2) + pad_h)))
                        rect.x += (tog.text.get_size()[0] + 10)
                        r_bool = tog.bool.get_rect()
                        r_bool.x += rect.x
                        r_bool.y += rect.y
                        j += 1
                        if collide_point(r_bool, mx, my):
                            tog.flip()
                            tog.draw_box()
            i = 0
            for box in (boxes):
                rect = box.surf.get_rect(center=(
                    (pad_w, i * (font_size * 2) + pad_h)))
                Render.screen.blit(box.surf, rect)
                i += 1
            for tog in (toggle_boxes):
                rect = tog.surf.get_rect(center=(
                    (pad_w, i * (font_size * 2) + pad_h)))
                Render.screen.blit(tog.surf, rect)
                i += 1
            pygame.display.flip()
            clock.tick(fps)

    def main_menu(self, clock: pygame.time.Clock, fps: int) -> str:
        """Show the main menu; return the chosen action string."""
        Render.screen.fill(0)
        nb_btn = 5
        # button size: keep the source image aspect ratio (248 / 1179)
        size = (int(self.w * 0.2), int(self.w * 0.2 * 248 / 1179))
        btns = [
            pygame.transform.smoothscale(
                pygame.image.load(f"images/buttons/btn{i}.png")
                .convert_alpha(), size) for i in range(nb_btn)
        ]
        bloc_size = size[1] * nb_btn * 2
        pad_w = (self.w - 0) // 2
        pad_h = (self.h - bloc_size) // 2
        btns_rect = [
            btn.get_rect(center=(pad_w, pad_h + size[1] * i * 2))
            for i, btn in enumerate(btns)
        ]
        play, param, hg, quit, instructions = btns_rect
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if play.collidepoint(event.pos):
                            self.render.erase(btns_rect)
                            return "play"
                        elif quit.collidepoint(event.pos):
                            return "quit"
                        elif param.collidepoint(event.pos):
                            return "param"
                        elif hg.collidepoint(event.pos):
                            return "score"
                        elif instructions.collidepoint(event.pos):
                            return "instructions"
            self.render.hoover_opacity70(btns, btns_rect)
            self.render.draw_obj(btns, btns_rect)
            pygame.display.flip()
            clock.tick(fps)

    def pause_menu(self, clock: pygame.time.Clock, fps: int) -> str:
        """Show the pause menu; return "play" to resume or "start" to leave."""
        Render.screen.fill(0)
        nb_btn = 2
        # button size: keep the source image aspect ratio (248 / 1179)
        size = (int(self.w * 0.2), int(self.w * 0.2 * 248 / 1179))
        btns = [
            pygame.transform.smoothscale(
                pygame.image.load(f"images/buttons/pause_btn{i}.png")
                .convert_alpha(), size) for i in range(nb_btn)
        ]
        bloc_size = size[1] * nb_btn * 2
        pad_w = (self.w - 0) // 2
        pad_h = (self.h - bloc_size) // 2
        btns_rect = [
            btn.get_rect(center=(pad_w, pad_h + size[1] * i * 2))
            for i, btn in enumerate(btns)
        ]
        back2menu, resume = btns_rect
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise GameExit
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if resume.collidepoint(event.pos):
                            self.render.erase(btns_rect)
                            return "play"
                        elif back2menu.collidepoint(event.pos):
                            return "start"
            self.render.hoover_opacity70(btns, btns_rect)
            self.render.draw_obj(btns, btns_rect)
            pygame.display.flip()
            clock.tick(fps)
