"""
Client réseau (unicast) à intégrer dans le menu + la boucle de jeu, sur
chaque iMac. Envoie ta position au téléphone (serveur relais) et reçoit
l'état de tous les joueurs en retour, en unicast direct (pas de broadcast).

Utilisation :

    # Dans le menu, quand le joueur choisit le mode LAN :
    server_ip = input("IP du téléphone : ")
    player_id = input("Ton id (imac1 / imac2) : ")
    net = LanClient(server_ip, player_id)

    # Dans la boucle de jeu, à chaque frame :
    net.send_position(tile_x, tile_y, offset_x, offset_y)
    all_players = net.get_players()  # dict {id: {tile_x, tile_y, offset_x, offset_y, ...}}
    for pid, pdata in all_players.items():
        if pid == net.player_id:
            continue  # c'est moi, pas la peine de me redessiner via le réseau
        # dessiner l'autre joueur à pdata["tile_x"], pdata["tile_y"], etc.
"""
import socket
import json

PORT = 5005


class LanClient:
    def __init__(self, server_ip, player_id):
        self.server_ip = server_ip
        self.player_id = player_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.latest_state = {}  # dernier état complet reçu du serveur

    def send_position(self, tile_x, tile_y, offset_x, offset_y):
        payload = {
            "id": self.player_id,
            "tile_x": tile_x,
            "tile_y": tile_y,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }
        message = json.dumps(payload).encode("utf-8")
        try:
            self.sock.sendto(message, (self.server_ip, PORT))
        except OSError:
            pass  # réseau indisponible, on ignore pour ce frame

    def get_players(self):
        """À appeler une fois par frame : lit tous les paquets en attente
        et retourne le dernier état connu de tous les joueurs."""
        try:
            while True:
                data, addr = self.sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode("utf-8"))
                    if "players" in payload:
                        self.latest_state = payload["players"]
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        except BlockingIOError:
            pass
        return self.latest_state