from config.parser_config import Parser, print_obj
from src.game import Game
from src.network.netcode import NetHost, NetGuest, can_reach_host
import sys


def setup_network(args: dict) -> dict:
    """Petit prompt console (même esprit que serveur/lan_client.py) pour
    choisir solo / hôte / invité avant de lancer la fenêtre pygame.
    À terme, ce choix peut migrer dans le menu graphique (menu.py) en
    stockant simplement les mêmes clés dans `args`."""
    print("Mode de jeu : [1] Solo/local  [2] Héberger (LAN)  "
          "[3] Rejoindre (LAN) [4] Multi/scinder Rejoindre [5] Host")
    choice = input("> ").strip()

    if choice == "2":
        args["role"] = "host"
        args["nb_player"] = 2
        net = NetHost()
        print("En attente d'un invité (Ctrl+C pour annuler)...")
        if not net.wait_for_guest(args, args.get("seed", 1)):
            print("Personne ne s'est connecté, retour en solo.")
            args["role"] = "solo"
        else:
            args["net"] = net
            print(f"Invité connecté depuis {net.guest_addr}.")

    elif choice == "3":
        host_ip = input("IP de l'hôte : ").strip()
        if not can_reach_host(host_ip):
            print("Impossible de joindre l'hôte en direct — sur le "
                 "réseau des VMs 42, ça peut être normal si les postes "
                 "sont isolés entre eux. Vérifiez que vous êtes sur le "
                 "même réseau / testez `nc -u` entre les deux, ou "
                 "repassez par un relai (cf. serveur/phone_server.py).")
            return args
        net = NetGuest(host_ip)
        print("Connexion à l'hôte...")
        if net.say_hello_and_wait_init() is None:
            print("Pas de réponse de l'hôte, retour en solo.")
        else:
            args["role"] = "guest"
            args["net"] = net
    elif choice == "4":
        host_ip = input("IP de l'hôte : ").strip()
        if not can_reach_host(host_ip):
            print("Impossible de joindre l'hôte en direct — sur le "
                 "réseau des VMs 42, ça peut être normal si les postes "
                 "sont isolés entre eux. Vérifiez que vous êtes sur le "
                 "même réseau / testez `nc -u` entre les deux, ou "
                 "repassez par un relai (cf. serveur/phone_server.py).")
            return args
        net = NetGuest(host_ip)
        print("Connexion à l'hôte...")
        if net.say_hello_and_wait_init() is None:
            print("Pas de réponse de l'hôte, retour en solo.")
        else:
            args["role"] = "guest"
            args["net"] = net
            args["scinder"] = True
    elif choice == "5":
        args["role"] = "host"
        args["nb_player"] = 2
        net = NetHost()
        print("En attente d'un invité (Ctrl+C pour annuler)...")
        if not net.wait_for_guest(args, args.get("seed", 1)):
            print("Personne ne s'est connecté, retour en solo.")
            args["role"] = "solo"
        else:
            args["net"] = net
            print(f"Invité connecté depuis {net.guest_addr}.")
            args["scinder"] = True

    return args


def main(argv: list[str]) -> int:
    try:
        args = Parser.parse_config(argv)
        print_obj(args)
    except ValueError as e:
        print(e)
    args = setup_network(args)
    game = Game(args)
    game.monitor()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:2]))
