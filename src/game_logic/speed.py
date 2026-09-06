from __future__ import annotations
from typing import TYPE_CHECKING
from .ghosts_state import GhostState

if TYPE_CHECKING:
    from ..entitys.ghosts import Ghost
    from ..entitys.player import Player


BASE_SPEED = 1.26
#  original a 75.75px/s soit 1.26px/frame le calcul est bon?

#  normal / normal dots / fright / fright dots
PAC_MAN_SPEED = [[0.8, 0.71, 0.9, 0.79],  # 1
                 [0.9, 0.79, 0.95, 0.83],  # 2-4
                 [1, 0.87, 1, 0.87],  # 5 -20
                 [0.9, 0.79, 1, 1]]  # 21+

#  normal / fright / tunnel / elroy1 / elroy 2
GHOST_SPEED = [[0.75, 0.5, 0.4, 0.8, 0.85],  # 1
               [0.85, 0.55, 0.4, 0.9, 0.95],  # 2-4
               [0.95, 0.6, 0.5, 1, 1.05],  # 5-20
               [0.95, 1, 0.5, 1, 1.05]]  # 21+


def update_speeds(level: int, ghosts: list[Ghost], player: Player,
                  ghoststate: GhostState) -> None:
    for ghost in ghosts:
        update_ghost_speed(level, ghost)
    update_player_speed(level, player, ghoststate)


def update_ghost_speed(level: int, ghost: Ghost) -> None:
    if level == 1:
        speeds = GHOST_SPEED[0]
    elif level <= 4:
        speeds = GHOST_SPEED[1]
    elif level <= 20:
        speeds = GHOST_SPEED[2]
    else:
        speeds = GHOST_SPEED[3]

    if ghost.state == GhostState.EYES:
        ghost.speed = BASE_SPEED * 1.25
    elif ghost.state == GhostState.FRIGHTENED:
        ghost.speed = speeds[1] * BASE_SPEED
    elif ghost.state == GhostState.ELROY1:
        ghost.speed = speeds[3] * BASE_SPEED
    elif ghost.state == GhostState.ELROY2:
        ghost.speed = speeds[4] * BASE_SPEED
    else:
        ghost.speed = speeds[0] * BASE_SPEED


def update_player_speed(level: int, player: Player, ghoststate: GhostState):
    if level == 1:
        speeds = PAC_MAN_SPEED[0]
    elif level <= 4:
        speeds = PAC_MAN_SPEED[1]
    elif level <= 20:
        speeds = PAC_MAN_SPEED[2]
    else:
        speeds = PAC_MAN_SPEED[3]

    if ghoststate == GhostState.FRIGHTENED:
        player.speed = speeds[2] * BASE_SPEED
    else:
        player.speed = speeds[0] * BASE_SPEED
