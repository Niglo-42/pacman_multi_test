"""Peer-to-peer netcode for the experimental 2-player LAN mode.

Model:
- The HOST is authoritative over everything except the guest's raw movement:
  ghost AI, collisions, pac-gums, score, lives and levels.
- The GUEST only simulates its own player against the maze walls (no ghost
  collisions, no pac-gums) for a lag-free feel; the host still decides the
  official result.
- Every frame:
    guest -> host: its player's position / direction
    host  -> guest: the ghosts and the host player, plus score / lives /
                    level / eaten-tile echoes.

Transport is plain non-blocking UDP: one socket, drain everything pending
each frame, keep the last known state. No ACK or retransmission -- on a
low-latency LAN a lost packet only costs one frame of lag.

Note: the 42 VM network has in the past isolated clients from each other.
Check a direct UDP round-trip works between the two machines (see
:func:`can_reach_host`, or ``nc -u``) before relying on this.
"""
from __future__ import annotations

import json
import socket
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..game import Game
    from ..entitys.player import Player
    from ..entitys.ghosts import Ghost

DEFAULT_PORT = 5005
RECV_BUFSIZE = 4096


def _make_socket() -> socket.socket:
    """Create a reusable non-blocking UDP socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setblocking(False)
    return s


def can_reach_host(host_ip: str, port: int = DEFAULT_PORT,
                   timeout: float = 2.0) -> bool:
    """Send a UDP ping and wait for a pong.

    A 2-second check that direct unicast works between the two machines.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(b'{"type":"ping"}', (host_ip, port))
        data, _ = s.recvfrom(RECV_BUFSIZE)
        return bool(json.loads(data.decode("utf-8")).get("type") == "pong")
    except (socket.timeout, OSError, json.JSONDecodeError,
            UnicodeDecodeError):
        return False
    finally:
        s.close()


# --------------------------------------------------------------------- #
#  Entity serialisation
# --------------------------------------------------------------------- #

def player_to_dict(p: Player) -> dict[str, Any]:
    """Serialise a player to a JSON-friendly dict."""
    return {"pos": list(p.position), "offset": list(p.offset_xy),
            "dir": p.direction.name, "alive": p.alive,
            "score": p.score, "lives": p.lives}


def ghost_to_dict(g: Ghost) -> dict[str, Any]:
    """Serialise a ghost to a JSON-friendly dict."""
    return {"pos": list(g.position), "offset": list(g.offset_xy),
            "dir": g.direction.name, "state": g.state.name,
            "alive": g.alive}


def build_state_packet(game: Game) -> dict[str, Any]:
    """Build the authoritative state packet the host sends each frame."""
    assert game.player2 is not None
    packet: dict[str, Any] = {
        "type": "state",
        "player1": player_to_dict(game.player),     # the host player
        "player2": player_to_dict(game.player2),    # echo of the guest
        "ghosts": [ghost_to_dict(g) for g in game.ghosts],
        "level": game.level,
        "eaten_pellet": game.eaten_pellet,
        "flashing": game.state_manager.is_flashing(game),
        "eaten_tiles": getattr(game, "newly_eaten_tiles", []),
    }
    game.newly_eaten_tiles = []
    return packet


def apply_player_dict(player: Player, data: dict[str, Any]) -> None:
    """Apply a networked state to a player NOT controlled on this machine
    (position and animation frame only, never ``.update()``)."""
    from ..game_logic.direction import Dir
    player.position = tuple(data["pos"])
    player.offset_xy = tuple(data["offset"])
    player.direction = Dir[data["dir"]]
    player.alive = data["alive"]
    if "score" in data:
        player.score = data["score"]
    if "lives" in data:
        player.lives = data["lives"]
    player.update_tile()


def apply_guest_input(player2: Player, data: dict[str, Any]) -> None:
    """Host side: inject the guest's reported position into the local
    player-2 object, before the host computes collisions and pac-gums."""
    from ..game_logic.direction import Dir
    player2.last_pos = player2.position
    player2.position = tuple(data["pos"])
    player2.offset_xy = tuple(data["offset"])
    player2.direction = Dir[data["dir"]]
    player2.alive = data.get("alive", True)
    player2.update_tile()


def apply_ghost_dict(ghost: Ghost, data: dict[str, Any],
                     flashing: bool) -> None:
    """Apply a networked ghost state and refresh its animation frame."""
    from ..game_logic.direction import Dir
    from ..game_logic.ghosts_state import GhostState
    ghost.position = tuple(data["pos"])
    ghost.offset_xy = tuple(data["offset"])
    ghost.direction = Dir[data["dir"]]
    ghost.state = GhostState[data["state"]]
    ghost.alive = data["alive"]
    if ghost.state == GhostState.EYES:
        ghost.update_ghost_tile(ghost.eyes, True, flashing)
    elif ghost.state == GhostState.FRIGHTENED:
        ghost.update_ghost_tile(ghost.afraid, False, flashing)
    else:
        ghost.update_tile()


def apply_remote_state(game: Game, state: dict[str, Any]) -> None:
    """Guest side: apply the full authoritative state from the host."""
    assert game.player2 is not None
    apply_player_dict(game.player2, state["player1"])
    flashing = state.get("flashing", False)
    for ghost, data in zip(game.ghosts, state["ghosts"]):
        apply_ghost_dict(ghost, data, flashing)
    game_map = game.maze.map
    tiles = game.maze.tiles
    assert game_map is not None
    assert tiles is not None
    for x, y in state.get("eaten_tiles", []):
        if game_map[y][x] != 0:
            game_map[y][x] = 0
            game.render.draw_on_maze(tiles[0], y, x)
    game.eaten_pellet = state.get("eaten_pellet", game.eaten_pellet)

    # Reconcile: if the local player has drifted too far from what the host
    # validated for us (typically after a death, when the host moves us back
    # to spawn), snap to the host's echo.
    echo = state["player2"]
    ex, ey = echo["pos"]
    px, py = game.player.position
    if (abs(px - ex) + abs(py - ey) > 2 or
            game.player.alive != echo["alive"] or
            game.player.lives != echo["lives"]):
        game.player.position = (ex, ey)
        game.player.offset_xy = tuple(echo["offset"])
        game.player.alive = echo["alive"]
        game.player.lives = echo["lives"]
        game.player.score = echo["score"]


# --------------------------------------------------------------------- #
#  Host
# --------------------------------------------------------------------- #

class NetHost:
    """UDP endpoint for the authoritative host."""

    def __init__(self, port: int = DEFAULT_PORT) -> None:
        """Bind the UDP socket on *port* and wait for a guest."""
        self.sock = _make_socket()
        self.sock.bind(("", port))
        self.guest_addr: tuple[str, int] | None = None
        self.last_guest_input: dict[str, Any] | None = None

    def wait_for_guest(self, args: dict[str, Any], seed: int,
                       timeout: float = 300.0) -> bool:
        """Block until the guest says HELLO, then send it the maze config."""
        self.sock.setblocking(True)
        self.sock.settimeout(timeout)
        try:
            while True:
                data, addr = self.sock.recvfrom(RECV_BUFSIZE)
                try:
                    payload = json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if payload.get("type") == "ping":
                    self.sock.sendto(b'{"type":"pong"}', addr)
                elif payload.get("type") == "hello":
                    self.guest_addr = addr
                    break
        except socket.timeout:
            return False
        finally:
            self.sock.setblocking(False)

        # args must be JSON-serialisable (it is: Parser.parse_config only
        # ever produces int / bool / str).
        safe_args = {k: v for k, v in args.items()
                     if isinstance(v, (int, float, str, bool))}
        init_packet = json.dumps({"type": "init", "args": safe_args,
                                  "seed": seed}).encode("utf-8")
        for _ in range(5):  # sent a few times in case a packet is lost
            self.sock.sendto(init_packet, self.guest_addr)
            time.sleep(0.05)
        return True

    def poll_input(self) -> dict[str, Any] | None:
        """Drain and return the guest's most recent input packet."""
        try:
            while True:
                data, addr = self.sock.recvfrom(RECV_BUFSIZE)
                try:
                    payload = json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if payload.get("type") == "input":
                    self.guest_addr = addr
                    self.last_guest_input = payload
                elif payload.get("type") == "hello":
                    self.guest_addr = addr  # the guest missed the init
        except BlockingIOError:
            pass
        return self.last_guest_input

    def send(self, packet: dict[str, Any]) -> None:
        """Send one JSON packet to the guest (silently drops on error)."""
        if self.guest_addr is None:
            return
        try:
            self.sock.sendto(json.dumps(packet).encode("utf-8"),
                             self.guest_addr)
        except OSError:
            pass

    def send_new_level(self, level: int, seed: int) -> None:
        """Tell the guest to regenerate maze *seed* for *level*."""
        self.send({"type": "new_level", "level": level, "seed": seed})


# --------------------------------------------------------------------- #
#  Guest
# --------------------------------------------------------------------- #

class NetGuest:
    """UDP endpoint for the non-authoritative guest."""

    def __init__(self, host_ip: str, port: int = DEFAULT_PORT) -> None:
        """Target the host at ``host_ip:port``."""
        self.host_addr = (host_ip, port)
        self.sock = _make_socket()
        self.latest_state: dict[str, Any] | None = None
        self.init_data: dict[str, Any] | None = None
        self.pending_new_level: dict[str, Any] | None = None

    def say_hello_and_wait_init(
            self, timeout: float = 300.0) -> dict[str, Any] | None:
        """Ping the host until it answers with the init packet."""
        hello = b'{"type":"hello"}'
        self.sock.setblocking(True)
        self.sock.settimeout(1.0)
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                try:
                    self.sock.sendto(hello, self.host_addr)
                    data, _ = self.sock.recvfrom(RECV_BUFSIZE)
                    payload: dict[str, Any] = json.loads(data.decode("utf-8"))
                    if payload.get("type") == "init":
                        self.init_data = payload
                        return payload
                except socket.timeout:
                    continue
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        finally:
            self.sock.setblocking(False)
        return None

    def send_input(self, player: Player) -> None:
        """Send this machine's player position/direction to the host."""
        payload = {
            "type": "input",
            "pos": list(player.position),
            "offset": list(player.offset_xy),
            "dir": player.direction.name,
            "alive": player.alive,
        }
        try:
            self.sock.sendto(json.dumps(payload).encode("utf-8"),
                             self.host_addr)
        except OSError:
            pass

    def poll_state(self) -> dict[str, Any] | None:
        """Drain incoming packets and return the latest host state."""
        try:
            while True:
                data, _ = self.sock.recvfrom(RECV_BUFSIZE)
                try:
                    payload = json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if payload.get("type") == "state":
                    self.latest_state = payload
                elif payload.get("type") == "new_level":
                    self.pending_new_level = payload
        except BlockingIOError:
            pass
        return self.latest_state
