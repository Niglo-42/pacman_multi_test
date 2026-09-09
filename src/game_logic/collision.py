"""Player <-> ghost collision detection and its consequences."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .ghosts_state import GhostState

if TYPE_CHECKING:
    from ..entitys.ghosts import Ghost
    from ..entitys.player import Player
    from ..game import Game


def check_collision(game: Game, player: Player, ghosts: list[Ghost]) -> None:
    """Resolve contact between *player* and each ghost.

    A lethal ghost costs a life (unless cheat mode is on); a frightened ghost
    is eaten -- it turns to eyes, heads home, and scores an amount that
    doubles for each ghost eaten within the same frightened phase.
    """
    for ghost in ghosts:
        if ghost.state == GhostState.EYES:
            continue
        if offset_detection(game, ghost, player) or \
                swept_check_detection(ghost, player):
            if ghost.state.is_lethal and not game.cheat_mode:
                game.player_died(player, ghosts)
            elif ghost.state == GhostState.FRIGHTENED:
                ghost.alive = False
                ghost.state = GhostState.EYES
                ghost.changing_side = False
                ghost.target = game.maze.get_opposite_corner(ghost.position)
                player.score += game.point_per_ghost * \
                    sum([not g.alive for g in ghosts])


def offset_detection(game: Game, ghost: Ghost, player: Player) -> bool:
    """True if the pixel distance between the two is within the hitbox."""
    center_tile_size = game.render.half_size
    hitbox = center_tile_size * 0.7
    px, py = player.position
    pox, poy = player.offset_xy
    p_absolute_pos = (px * center_tile_size + pox, py * center_tile_size + poy)

    gx, gy = ghost.position
    gox, goy = ghost.offset_xy
    g_absolute_pos = (gx * center_tile_size + gox, gy * center_tile_size + goy)

    dist = math.dist(p_absolute_pos, g_absolute_pos)
    if dist <= hitbox:
        return True
    return False


def swept_check_detection(ghost: Ghost, player: Player) -> bool:
    """True if ghost and player swapped tiles in one frame (head-on pass)."""
    if ghost.position == player.last_pos and ghost.last_pos == player.position:
        return True
    return False
