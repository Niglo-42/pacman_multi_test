from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum, auto

if TYPE_CHECKING:
    from ..game import Game
    from ..entitys.ghosts import Ghost

FRIGHT_TIMER = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 5, 7: 2, 8: 2, 9: 1,
                10: 5, 11: 2, 12: 1, 13: 1, 14: 3, 15: 1, 16: 1, 17: 0, 18: 1}

FRIGHT_FLASHES = {1: 5, 9: 3, 10: 5, 12: 3, 14: 5, 15: 3, 17: 0, 18: 3, 19: 0}

#  SCATTER / CHASE alternance
PHASE_DURATIONS = [[7, 20, 7, 20, 5, 20, 5],
                   [7, 20, 7, 20, 5, 1033, 1/60],
                   [5, 20, 5, 20, 5, 1037, 1/60]]

ELROY_COOLDOWN = 7

ELROY_TRIGGERS = {1: [20, 10],
                  2: [30, 15],
                  3: [40, 20],
                  6: [50, 25],
                  9: [60, 30],
                  12: [80, 40],
                  15: [100, 50],
                  19: [120, 60]}


class GhostState(Enum):
    SCATTER = auto()
    CHASE = auto()
    FRIGHTENED = auto()
    EYES = auto()
    CAGED = auto()
    EXITING = auto()
    ENTERING = auto()
    ELROY1 = auto()
    ELROY2 = auto()

    @property
    def is_lethal(self) -> bool:
        return self in (GhostState.CHASE, GhostState.SCATTER,
                        GhostState.ELROY1, GhostState.ELROY2)


class GhostStateManager:
    def __init__(self):
        self.actual_state: GhostState = GhostState.SCATTER
        self.last_state: GhostState = GhostState.SCATTER

    def is_flashing(self, game: Game) -> bool:
        if self.actual_state is not GhostState.FRIGHTENED:
            return False
        total = game.fps * self.fright_timer(game.level)
        elapsed = game.global_timer - game.frightened_timer
        window = self.fright_flashes(game.level) * 28
        return (total - elapsed) <= window

    def fright_timer(self, level: int) -> int:
        return FRIGHT_TIMER.get(level, 0)

    def fright_flashes(self, level: int) -> int:
        key = max(k for k in FRIGHT_FLASHES if k <= level)
        return FRIGHT_FLASHES[key]

    @property
    def effective_state(self) -> GhostState:
        if self.actual_state == GhostState.FRIGHTENED:
            return self.last_state
        return self.actual_state

    def get_frightened(self, game: Game):
        game.frightened_timer = game.global_timer
        self.actual_state = GhostState.FRIGHTENED
        for ghost in game.ghosts:
            if ghost.state != GhostState.EYES:
                self.modify_ghost_state(GhostState.FRIGHTENED, ghost)

    def update_ghosts_state(self, game: Game) -> None:
        for ghost in game.ghosts:
            if ghost.alive and ghost.state == GhostState.EYES:
                ghost.state = self.effective_state
        self.elroy_mode(game)
        self.last_state = self.effective_state

        if self.actual_state == GhostState.FRIGHTENED:
            self.manage_end_fright(game)
        else:
            self.switch_states(game)

    def modify_ghost_state(self, new_state: GhostState, ghost: Ghost) -> None:
        if ghost.alive and new_state != ghost.state:
            ghost.state = new_state
            if ghost.state != GhostState.EYES and \
               ghost.state != GhostState.FRIGHTENED:
                ghost.changing_side = True

    def manage_end_fright(self, game: Game) -> None:
        if (game.global_timer - game.frightened_timer) >= \
                (game.fps * self.fright_timer(game.level)):
            game.point_per_ghost = game.args.get("points_per_ghost")
            for ghost in game.ghosts:
                if not ghost.state == GhostState.EYES:
                    self.modify_ghost_state(self.last_state, ghost)
            self.actual_state = self.last_state

    def switch_states(self, game: Game) -> None:
        states = [GhostState.SCATTER, GhostState.CHASE]
        acc_state, state_timer = game.state_timer
        levels = {1: 0, 2: 1, 5: 2}
        lvl_index = levels[max(k for k in levels if k <= game.level)]
        length = len(PHASE_DURATIONS[lvl_index])

        if acc_state < length:
            phase_duration = PHASE_DURATIONS[lvl_index][acc_state]
            if (game.global_timer - state_timer) >= \
                    (phase_duration * game.fps):
                acc_state += 1
                state_timer = game.global_timer
                new_state = states[acc_state & 1]
                self.actual_state = new_state
                for ghost in game.ghosts:
                    if not (ghost.state == GhostState.ELROY1 or
                            ghost.state == GhostState.ELROY2):
                        self.modify_ghost_state(new_state, ghost)

            game.state_timer = (acc_state, state_timer)
        else:
            for ghost in game.ghosts:
                if not (ghost.state == GhostState.ELROY1 or
                        ghost.state == GhostState.ELROY2):
                    self.modify_ghost_state(GhostState.CHASE, ghost)
            self.actual_state = GhostState.CHASE

    def elroy_mode(self, game: Game) -> None:
        boolean, timer = game.elroy_cooldown
        diff = game.global_timer - timer
        if diff <= ELROY_COOLDOWN * game.fps:
            boolean = False
        elif boolean is True:
            return

        blinky = game.ghosts[0]
        if blinky.state == GhostState.EYES or \
                blinky.state == GhostState.FRIGHTENED:
            return

        target_lvl = max(lvl for lvl in ELROY_TRIGGERS if lvl <= game.level)
        dots = ELROY_TRIGGERS[target_lvl]
        remaining_pellets = game.total_pellet - game.eaten_pellet

        if remaining_pellets <= dots[1]:
            self.modify_ghost_state(GhostState.ELROY2, blinky)
        elif remaining_pellets <= dots[0]:
            self.modify_ghost_state(GhostState.ELROY1, blinky)
        game.elroy_cooldown = (boolean, 0)
