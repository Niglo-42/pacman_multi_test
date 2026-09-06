from .lan_client import LanClient

server_ip = input("IP du téléphone : ")
player_id = input("Ton id (imac1 / imac2) : ")
net = LanClient(server_ip, player_id)