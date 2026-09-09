"""Per-level movement speeds, as fractions of :data:`BASE_SPEED`.

The tables reproduce the arcade brackets (level 1 / 2-4 / 5-20 / 21+).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .ghosts_state import GhostState

if TYPE_CHECKING:
    from ..entitys.ghosts import Ghost
    from ..entitys.player import Player


# Reference speed: 75.75 px/s at 60 fps == 1.26 px/frame.
BASE_SPEED = 1.26

# Columns: normal / eating pac-gums / frightened / frightened + eating.
PAC_MAN_SPEED = [[0.8, 0.71, 0.9, 0.79],    # level 1
                 [0.9, 0.79, 0.95, 0.83],   # levels 2-4
                 [1, 0.87, 1, 0.87],        # levels 5-20
                 [0.9, 0.79, 1, 1]]         # levels 21+

# Columns: normal / frightened / tunnel / Elroy 1 / Elroy 2.
GHOST_SPEED = [[0.75, 0.5, 0.4, 0.8, 0.85],    # level 1
               [0.85, 0.55, 0.4, 0.9, 0.95],   # levels 2-4
               [0.95, 0.6, 0.5, 1, 1.05],      # levels 5-20
               [0.95, 1, 0.5, 1, 1.05]]        # levels 21+


def update_speeds(level: int, ghosts: list[Ghost], player: Player,
                  ghoststate: GhostState) -> None:
    """Refresh the speed of the player and every ghost for *level*."""
    for ghost in ghosts:
        update_ghost_speed(level, ghost)
    update_player_speed(level, player, ghoststate)


def update_ghost_speed(level: int, ghost: Ghost) -> None:
    """Set ``ghost.speed`` from its state and the level bracket."""
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


def update_player_speed(level: int, player: Player,
                        ghoststate: GhostState) -> None:
    """Set ``player.speed`` from the level bracket and the ghost state."""
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
