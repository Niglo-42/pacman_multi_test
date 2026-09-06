"""
Netcode pair-à-pair pour le mode 2 joueurs en LAN.

Modèle retenu (celui que tu as décrit) :
- L'HÔTE est autoritaire sur TOUT ce qui n'est pas le déplacement brut de
  l'invité : les fantômes (IA complète), les collisions, les pac-gums, le
  score, les vies, les niveaux.
- L'INVITÉ ne fait tourner localement QUE le déplacement de son propre
  joueur contre les murs du labyrinthe (pas de collision avec les
  fantômes, pas de pac-gums) — ça lui donne une sensation réactive sans
  lag, et l'hôte est de toute façon seul juge du résultat "officiel".
- Chaque frame :
    invité  -> hôte : position/direction de SON joueur
    hôte    -> invité : position/direction des fantômes + du joueur hôte
                        (+ échos score/vies/niveau/pac-gums mangées)

Transport : UDP direct, non bloquant, même pattern que
serveur/lan_client.py (un seul socket, on lit tout ce qui est en attente
à chaque frame, on garde le dernier état connu). Pas d'ACK/retransmission :
sur un LAN à faible latence, perdre un paquet de temps en temps n'est
gênant que de façon cosmétique (une frame de retard), donc pas besoin de
la complexité de TCP ou d'un protocole fiable maison.

ATTENTION (retour d'expérience de votre propre serveur/phone_server.py) :
le réseau des VMs de l'école 42 a par le passé isolé les clients entre eux
(broadcast bloqué, et parfois même l'unicast direct selon la config du
cluster) — c'est justement pourquoi vous êtiez passés par un relai sur
téléphone. Avant de démonter ce relai, vérifiez qu'un simple aller-retour
UDP direct passe bien entre les deux VMs cibles (voir la fonction
`can_reach_host` ci-dessous, ou plus simplement `nc -u`). Si ça ne passe
pas, gardez l'idée du relai : il suffit de faire tourner ce même protocole
(host/guest) EN PASSANT par le téléphone comme un simple forwarder UDP,
sans changer une ligne de logique de jeu.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import socket
import json
import time

if TYPE_CHECKING:
    from ..game import Game
    from ..entitys.player import Player
    from ..entitys.ghosts import Ghost

DEFAULT_PORT = 5005
RECV_BUFSIZE = 4096


def _make_socket() -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setblocking(False)
    return s


def can_reach_host(host_ip: str, port: int = DEFAULT_PORT,
                   timeout: float = 2.0) -> bool:
    """Petit test de connectivité à lancer avant la partie : envoie un
    ping UDP et attend un pong. Permet de savoir en 2 secondes si le
    réseau des VMs autorise l'unicast direct entre les deux postes."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(b'{"type":"ping"}', (host_ip, port))
        data, _ = s.recvfrom(RECV_BUFSIZE)
        return json.loads(data.decode("utf-8")).get("type") == "pong"
    except (socket.timeout, OSError, json.JSONDecodeError,
            UnicodeDecodeError):
        return False
    finally:
        s.close()


# --------------------------------------------------------------------- #
#  Sérialisation des entités
# --------------------------------------------------------------------- #

def player_to_dict(p: Player) -> dict:
    return {"pos": list(p.position), "offset": list(p.offset_xy),
            "dir": p.direction.name, "alive": p.alive,
            "score": p.score, "lives": p.lives}


def ghost_to_dict(g: Ghost) -> dict:
    return {"pos": list(g.position), "offset": list(g.offset_xy),
            "dir": g.direction.name, "state": g.state.name,
            "alive": g.alive}


def build_state_packet(game: Game) -> dict:
    """Construit le paquet envoyé par l'hôte à chaque frame."""
    packet = {
        "type": "state",
        "player1": player_to_dict(game.player),     # le joueur de l'hôte
        "player2": player_to_dict(game.player2),    # écho de l'invité
        "ghosts": [ghost_to_dict(g) for g in game.ghosts],
        "level": game.level,
        "eaten_pellet": game.eaten_pellet,
        "flashing": game.state_manager.is_flashing(game),
        "eaten_tiles": getattr(game, "newly_eaten_tiles", []),
    }
    game.newly_eaten_tiles = []
    return packet


def apply_player_dict(player: Player, data: dict) -> None:
    """Applique l'état reçu du réseau à un Player qui n'est PAS le
    joueur physiquement contrôlé sur cette machine (donc jamais de
    .update() dessus, juste position + tuile d'animation)."""
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


def apply_guest_input(player2: Player, data: dict) -> None:
    """Côté hôte : injecte la position envoyée par l'invité dans l'objet
    Player local qui représente l'invité, AVANT le calcul des collisions
    et des pac-gums (qui restent, eux, calculés par l'hôte)."""
    from ..game_logic.direction import Dir
    player2.last_pos = player2.position
    player2.position = tuple(data["pos"])
    player2.offset_xy = tuple(data["offset"])
    player2.direction = Dir[data["dir"]]
    player2.alive = data.get("alive", True)
    player2.update_tile()


def apply_ghost_dict(ghost: Ghost, data: dict, flashing: bool) -> None:
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


def apply_remote_state(game: Game, state: dict) -> None:
    """Côté invité : applique l'état complet reçu de l'hôte."""
    apply_player_dict(game.player2, state["player1"])
    flashing = state.get("flashing", False)
    for ghost, data in zip(game.ghosts, state["ghosts"]):
        apply_ghost_dict(ghost, data, flashing)
    for x, y in state.get("eaten_tiles", []):
        if game.maze.map[y][x] != 0:
            game.maze.map[y][x] = 0
            game.render.draw_on_maze(game.maze.tiles[0], y, x)
    game.eaten_pellet = state.get("eaten_pellet", game.eaten_pellet)

    # réconciliation : si mon perso local dérive trop de ce que l'hôte
    # a effectivement validé pour moi (typiquement après une mort, où
    # l'hôte me replace au spawn), on se resynchronise sur son écho.
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
#  Hôte
# --------------------------------------------------------------------- #

class NetHost:
    def __init__(self, port: int = DEFAULT_PORT):
        self.sock = _make_socket()
        self.sock.bind(("", port))
        self.guest_addr = None
        self.last_guest_input = None

    def wait_for_guest(self, args: dict, seed: int,
                       timeout: float = 300.0) -> bool:
        """Bloquant : attend le HELLO de l'invité puis lui envoie la
        config nécessaire pour régénérer un labyrinthe identique."""
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

        # args doit être sérialisable en JSON (c'est déjà le cas : int/
        # bool/str produits par Parser.parse_config)
        safe_args = {k: v for k, v in args.items()
                    if isinstance(v, (int, float, str, bool))}
        init_packet = json.dumps({"type": "init", "args": safe_args,
                                  "seed": seed}).encode("utf-8")
        for _ in range(5):  # renvoyé plusieurs fois, au cas où perdu
            self.sock.sendto(init_packet, self.guest_addr)
            time.sleep(0.05)
        return True

    def poll_input(self) -> dict | None:
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
                    self.guest_addr = addr  # l'invité a raté l'init
        except BlockingIOError:
            pass
        return self.last_guest_input

    def send(self, packet: dict) -> None:
        if self.guest_addr is None:
            return
        try:
            self.sock.sendto(json.dumps(packet).encode("utf-8"),
                             self.guest_addr)
        except OSError:
            pass

    def send_new_level(self, level: int, seed: int) -> None:
        self.send({"type": "new_level", "level": level, "seed": seed})


# --------------------------------------------------------------------- #
#  Invité
# --------------------------------------------------------------------- #

class NetGuest:
    def __init__(self, host_ip: str, port: int = DEFAULT_PORT):
        self.host_addr = (host_ip, port)
        self.sock = _make_socket()
        self.latest_state: dict | None = None
        self.init_data: dict | None = None
        self.pending_new_level: dict | None = None

    def say_hello_and_wait_init(self, timeout: float = 300.0) -> dict | None:
        hello = b'{"type":"hello"}'
        self.sock.setblocking(True)
        self.sock.settimeout(1.0)
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                try:
                    self.sock.sendto(hello, self.host_addr)
                    data, _ = self.sock.recvfrom(RECV_BUFSIZE)
                    payload = json.loads(data.decode("utf-8"))
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

    def poll_state(self) -> dict | None:
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
