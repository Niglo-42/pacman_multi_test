"""
Serveur relais UDP (unicast) - à lancer sur le téléphone (Termux).
Reçoit les positions envoyées par les iMacs, garde en mémoire l'IP/port de
chaque client vu récemment, et renvoie l'état complet directement à chacun
(unicast) plutôt que par broadcast — nécessaire sur les réseaux qui bloquent
le broadcast / isolent les clients entre eux (ex: VMs école 42).

Lancement dans Termux :
    pkg install python
    python phone_server.py

Pour connaître l'IP du téléphone à donner aux iMacs :
    ifconfig   (ou "ip addr" si ifconfig n'existe pas)
    -> chercher l'IP sur l'interface wlan0
"""
import socket
import json
import time

PORT = 5005
CLIENT_TIMEOUT = 10.0   # secondes sans nouvelles d'un client avant de l'oublier
TICK_RATE = 20          # nb d'envois par seconde à chaque client

# état de la partie, indexé par id de joueur (ex: "imac1")
players = {}       # {"imac1": {"tile_x": 3, "tile_y": 5, "offset_x": 4, "offset_y": 0}}
client_addrs = {}  # {"imac1": (("192.168.1.10", 5005), last_seen_timestamp)}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", PORT))
sock.setblocking(False)

print(f"Serveur relais démarré sur le port {PORT}")

last_send = time.time()

while True:
    # 1. Réception non-bloquante des mises à jour envoyées par les clients
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            try:
                payload = json.loads(data.decode("utf-8"))
                player_id = payload["id"]
                players[player_id] = payload
                client_addrs[player_id] = (addr, time.time())
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                pass  # paquet malformé, on ignore
    except BlockingIOError:
        pass  # plus rien à lire pour l'instant

    # 2. Oublier les clients silencieux depuis trop longtemps
    now = time.time()
    stale = [pid for pid, (_, ts) in client_addrs.items() if now - ts > CLIENT_TIMEOUT]
    for pid in stale:
        del client_addrs[pid]
        players.pop(pid, None)
        print(f"Client '{pid}' déconnecté (timeout)")

    # 3. Envoi périodique de l'état complet, en unicast, à chaque client connu
    if now - last_send >= 1.0 / TICK_RATE:
        message = json.dumps({"players": players}).encode("utf-8")
        for pid, (addr, _) in client_addrs.items():
            try:
                sock.sendto(message, addr)
            except OSError as e:
                print(f"Erreur d'envoi à {pid}: {e}")
        last_send = now

    time.sleep(0.005)  # petite pause pour ne pas saturer le CPU