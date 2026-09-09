"""Entry point.

Usage:
    python3 pac-man.py config.json

Parses the configuration, optionally sets up a LAN game through a small
console prompt, then hands control to :class:`src.game.Game`.
"""
import os
import sys
from typing import Any

from config.parser_config import Parser, print_obj
from src.game import Game
from src.network.netcode import NetHost, NetGuest, can_reach_host


def _bootstrap_frozen() -> None:
    """PyInstaller bundle setup (no-op when running from source).

    Assets are loaded through paths relative to the working directory, so we
    chdir() into the bundle where they were shipped. A windowed build has no
    real console, so guard sys.stdout / sys.stderr to keep print() harmless.
    """
    if not getattr(sys, "frozen", False):
        return
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.chdir(bundle_dir)
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


_bootstrap_frozen()


def setup_network(args: dict[str, Any]) -> dict[str, Any]:
    """Ask (on the console) for solo / host / guest before opening the window.

    The choice only adds keys to *args*; it could later move into the
    graphical menu without touching the rest of the game.
    """
    # No interactive console (packaged windowed build, or piped stdin):
    # skip the prompt and start a normal solo game.
    if sys.stdin is None or not sys.stdin.isatty():
        args["role"] = "solo"
        return args
    print("Game mode: [1] Solo/local  [2] Host (LAN)  "
          "[3] Join (LAN)  [4] Join + split-screen  [5] Host + split-screen")
    choice = input("> ").strip()
    net: NetHost | NetGuest

    if choice in ("2", "5"):
        args["role"] = "host"
        args["nb_player"] = 2
        net = NetHost()
        print("Waiting for a guest (Ctrl+C to cancel)...")
        if not net.wait_for_guest(args, args.get("seed", 1)):
            print("Nobody connected, falling back to solo.")
            args["role"] = "solo"
        else:
            args["net"] = net
            print(f"Guest connected from {net.guest_addr}.")
            args["scinder"] = choice == "5"

    elif choice in ("3", "4"):
        host_ip = input("Host IP: ").strip()
        if not can_reach_host(host_ip):
            print("Cannot reach the host directly. On the 42 VM network this "
                  "can be normal if the machines are isolated from each "
                  "other. Check you are on the same network / test with "
                  "`nc -u`, then retry.")
            return args
        net = NetGuest(host_ip)
        print("Connecting to the host...")
        if net.say_hello_and_wait_init() is None:
            print("No answer from the host, falling back to solo.")
        else:
            args["role"] = "guest"
            args["net"] = net
            args["scinder"] = choice == "4"

    return args


def main(argv: list[str]) -> int:
    """Parse the config, wire the network, and run the game."""
    args = Parser.parse_config(argv)
    print_obj(args)
    if getattr(sys, "frozen", False):
        # Keep the highscore file next to the executable: a writable spot
        # that is not wiped when the bundle is replaced on the next update.
        args["highscore_filename"] = os.path.join(
            os.path.dirname(sys.executable), "highscore.json")
    args = setup_network(args)
    game = Game(args)
    game.monitor()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:2]))
