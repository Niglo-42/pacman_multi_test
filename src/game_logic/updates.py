from __future__ import annotations
from typing import TYPE_CHECKING
from .speed import update_speeds
from .collision import check_collision
from ..constants import LAST_LEVEL
from ..interface.drawing import draw_lives, draw_fruits

if TYPE_CHECKING:
    from ..game import Game
    from ..entitys.player import Player
    from ..maze.maze import Maze


def update_entitys(game: Game) -> None:
    """Advance every entity by one frame (player, second player, ghosts)."""
    role = getattr(game, "role", "solo")

    if role == "guest":
        # The guest only simulates its own movement against the walls; the
        # host stays the sole authority on everything else.
        assert game.net is not None
        game.player.update(game.maze)
        game.net.send_input(game.player)
        state = game.net.poll_state()
        if state:
            from ..network.netcode import apply_remote_state
            apply_remote_state(game, state)
        pending = game.net.pending_new_level
        if pending and pending["level"] != game.level:
            from ..init import init_new_level
            init_new_level(game, seed=pending["seed"])
            game.level = pending["level"]
        return

    if role == "host":
        # The guest player is never simulated locally: its position comes
        # from the network and is injected before collisions / pac-gums.
        assert game.net is not None
        guest_input = game.net.poll_input()
        if guest_input:
            assert game.player2 is not None
            from ..network.netcode import apply_guest_input
            apply_guest_input(game.player2, guest_input)
    elif game.player2:
        game.player2.update(game.maze)

    game.player.update(game.maze)
    flashing = game.state_manager.is_flashing(game)
    for g in game.ghosts:
        g.update(game, flashing)


def update_game_state(game: Game) -> int:
    """Resolve one frame of game rules.

    Returns:
        ``0`` to keep playing, ``1`` when the whole game is won (last level
        cleared), ``2`` when a level was cleared and a short "ready?" pause
        should be shown.
    """
    flag = 0
    if game.time <= 0:
        game.game_is_over()
        return flag
    role = getattr(game, "role", "solo")
    if role == "guest":
        # Nothing to compute: pac-gums, score, levels and deaths are decided
        # by the host and reach us already resolved via apply_remote_state.
        draw_lives(game)
        return flag

    game.newly_eaten_tiles = []
    game.global_timer += 1
    state_manager = game.state_manager
    game_map = game.maze.map
    assert game_map is not None
    if game.eaten_pellet == game.total_pellet:
        game.level_is_won()
        flag = 2
        if game.level > LAST_LEVEL:
            flag = 1
    update_speeds(game.level, game.ghosts, game.player,
                  state_manager.actual_state)
    check_collision(game, game.player, game.ghosts)

    if game.player2:
        check_collision(game, game.player2, game.ghosts)
        if update_pellets(game, game.player2, game_map):
            state_manager.get_frightened(game)

    if update_pellets(game, game.player, game_map):
        # a super pac-gum was eaten
        state_manager.get_frightened(game)
    state_manager.update_ghosts_state(game)
    draw_lives(game)

    if role == "host":
        assert game.net is not None
        from ..network.netcode import build_state_packet
        game.net.send(build_state_packet(game))
    return flag


def update_pellets(game: Game, player: Player, map: list[list[int]]) -> bool:
    """Eat the tile *player* stands on. Return True on a super pac-gum."""
    energizer = False
    if player and (player.offset_xy) == (0, 0):
        x, y = player.position
        if map[y][x] == 1:
            player.score += game.points_per_pacgum
            game.eaten_pellet += 1
        elif map[y][x] == 2:
            player.score += game.points_per_super_pacgum
            energizer = True
        elif map[y][x] == 3:
            player.score += 100
            draw_fruits(game)
        if map[y][x] != 0 and hasattr(game, "newly_eaten_tiles"):
            game.newly_eaten_tiles.append((x, y))
        map[y][x] = 0
        tiles = game.maze.tiles
        assert tiles is not None
        game.render.draw_on_maze(tiles[0], y, x)

    return energizer


def get_fruits(game: Game, maze: Maze, tile_size: int) -> None:
    """Spawn the level's bonus fruit once enough pac-gums have been eaten."""
    if (game.eaten_pellet == 70) and maze.flag_fruit == 0:
        maze.flag_fruit = 0b1
        game.render.fruits[0].blit(maze.add_fruit(game.player.position,
                                                  tile_size, 3), (0, 0))
    elif (game.eaten_pellet == 170) and maze.flag_fruit == 1:
        maze.flag_fruit = 0b11
        game.render.fruits[1].blit(maze.add_fruit(game.player.position,
                                                  tile_size, 3), (0, 0))
