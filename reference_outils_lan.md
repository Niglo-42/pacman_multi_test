# Référence complète — tous les outils utilisés pour le mode LAN

Chaque élément (fonction, méthode, objet) utilisé pour construire le
mode 2 joueurs en LAN, avec entrée, sortie, et particularités
(boucle ? bloquant ? attend un event ou un délai ? effet de bord ?).

Classé du plus bas niveau (bibliothèque standard Python) au plus haut
niveau (code métier du jeu).

---

## 0. `serveur/` — confirmé inutilisé

Aucun fichier du projet ne fait `import serveur` ni
`from serveur import ...`. `phone_server.py`, `lan_client.py` et
`input.py` ne sont référencés que dans mes commentaires (comme piste
de secours si le réseau bloque l'unicast direct). Le nouveau code ne
dépend d'eux d'aucune façon.

---

## 1. Outils de la bibliothèque standard Python

Ce sont les briques de base, indépendantes du projet — celles qu'il
faut connaître pour tout reconstruire sans regarder mon code.

- **`socket.socket(family, type)`**
  Input : `family` (ex. `socket.AF_INET` = adresses IPv4),
  `type` (ex. `socket.SOCK_DGRAM` = UDP, par opposition à
  `SOCK_STREAM` = TCP).
  Output : un objet `socket` (ni connecté ni lié à un port).
  Spécificités : ne fait rien tant qu'on n'appelle pas d'autre
  méthode dessus ; UDP = pas de connexion établie, chaque envoi doit
  repréciser le destinataire.

- **`sock.bind((host, port))`**
  Input : un tuple `(adresse, port)` — `""` comme adresse = toutes
  les interfaces réseau de la machine.
  Output : `None`.
  Spécificités : **réserve** le port pour qu'on puisse recevoir
  dessus ; lève `OSError` si le port est déjà pris par un autre
  processus. Seul l'hôte en a besoin (l'invité ne bind jamais).

- **`sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)`**
  Input : niveau d'option, option, valeur.
  Output : `None`.
  Spécificités : autorise à relancer le programme immédiatement sur
  le même port (sinon l'OS garde le port "occupé" un moment après
  fermeture, erreur `Address already in use`).

- **`sock.setblocking(bool)`**
  Input : `True` ou `False`.
  Output : `None`.
  Spécificités : **True** = les appels comme `recvfrom` gèlent le
  programme jusqu'à ce qu'il y ait quelque chose à lire. **False** =
  `recvfrom` lève immédiatement `BlockingIOError` s'il n'y a rien —
  indispensable dans une boucle de jeu à 60 FPS qui ne doit jamais
  s'arrêter d'attendre le réseau.

- **`sock.settimeout(secondes)`**
  Input : un nombre de secondes (float).
  Output : `None`.
  Spécificités : variante intermédiaire entre bloquant et non
  bloquant — bloque, mais au maximum N secondes, puis lève
  `socket.timeout`. Utilisé pour les phases d'attente ponctuelles
  (connexion, ping) qui ne doivent pas durer indéfiniment.

- **`sock.sendto(bytes, (host, port))`**
  Input : des **bytes** (pas une string — d'où le `.encode("utf-8")`
  partout) et l'adresse destination.
  Output : nombre d'octets envoyés (jamais utilisé ici).
  Spécificités : ne bloque (quasiment) jamais en UDP ; ne garantit
  pas l'arrivée du paquet ; à répéter à chaque envoi puisqu'il n'y a
  pas de connexion permanente.

- **`sock.recvfrom(bufsize)`**
  Input : taille max du buffer de réception en octets (`4096` ici).
  Output : un tuple `(bytes_reçus, (adresse_expéditeur, port))`.
  Spécificités : c'est la **seule** façon d'apprendre l'adresse de
  l'autre machine dans ce protocole — jamais tapée en dur. Comportement
  (bloquant ou non, avec ou sans timeout) dépend entièrement de
  `setblocking`/`settimeout` appelés avant.

- **`sock.close()`**
  Input/Output : rien.
  Spécificités : libère le socket. Utilisé uniquement dans
  `can_reach_host` (socket jetable, un seul aller-retour).

- **`json.dumps(objet)`** / **`json.loads(string)`**
  Input : un `dict` Python (dumps) ou une string/bytes JSON (loads).
  Output : une string JSON (dumps) ou un `dict` Python (loads).
  Spécificités : `dumps` plante (`TypeError`) sur tout objet qu'il ne
  sait pas convertir nativement (int/float/str/bool/list/dict/None
  seulement) — c'est ce qui a causé le premier bug (`NetHost` dans
  `args`). `loads` plante (`JSONDecodeError`) sur du texte malformé —
  toujours entouré d'un `try/except` ici, un paquet corrompu ne doit
  pas faire planter le jeu.

- **`random.Random(seed)`**
  Input : un entier (le seed).
  Output : un **objet générateur aléatoire indépendant** de l'état
  global du module `random`.
  Spécificités : deux instances créées avec le même seed produisent
  la même séquence de tirages, à condition d'appeler ses méthodes
  (`.randint(a, b)`) exactement dans le même ordre des deux côtés.

- **`os.environ.get(clé, défaut)`**
  Input : nom de variable d'environnement, valeur par défaut.
  Output : la valeur (string) ou le défaut si absente.
  Spécificités : lecture simple, aucun effet de bord. Utilisé pour
  `PACMAN_WINDOWED` sans toucher au reste de la config du jeu.

- **`time.sleep(secondes)`**
  Spécificités : **bloque** le thread pendant N secondes, littéralement.
  Utilisé uniquement dans de petites boucles de renvoi (pas dans la
  boucle de jeu).

- **`time.time()`**
  Output : timestamp actuel (float, secondes depuis epoch).
  Spécificités : sert à calculer une échéance (`deadline = time.time() + timeout`)
  pour les boucles d'attente bornées dans le temps.

- **Exceptions utilisées** : `BlockingIOError` (rien à lire, socket non
  bloquant), `socket.timeout` (rien reçu avant l'échéance, socket avec
  `settimeout`), `OSError` (échec d'envoi, ex. réseau injoignable),
  `json.JSONDecodeError` / `UnicodeDecodeError` (paquet reçu illisible).

---

## 2. `src/network/netcode.py` — fonctions de sérialisation

- **`_make_socket() -> socket.socket`**
  Input : aucun. Output : un socket UDP configuré (`AF_INET`,
  `SOCK_DGRAM`, `SO_REUSEADDR`, non bloquant).
  Spécificités : aucune boucle, factorise la config commune à
  `NetHost` et `NetGuest`.

- **`can_reach_host(host_ip: str, port=5005, timeout=2.0) -> bool`**
  Input : IP de l'hôte à tester. Output : `True`/`False`.
  Spécificités : pas de boucle ; **bloque jusqu'à `timeout` secondes**
  en attendant un pong ; ferme toujours son socket (`finally: s.close()`).

- **`player_to_dict(p) -> dict`** / **`ghost_to_dict(g) -> dict`**
  Input : un objet `Player`/`Ghost`. Output : un `dict` JSON-safe
  (positions en `list`, direction en `.name` string).
  Spécificités : fonctions pures, aucun effet de bord, aucune boucle.

- **`build_state_packet(game) -> dict`**
  Input : l'objet `Game`. Output : le `dict` complet envoyé par
  l'hôte chaque frame.
  Spécificités : boucle **de collecte** (pas d'attente) sur
  `game.ghosts` ; **effet de bord** — vide `game.newly_eaten_tiles`
  après l'avoir lu (reset pour la frame suivante).

- **`apply_player_dict(player, data) -> None`**
  Input : l'objet `Player` à mettre à jour + le `dict` reçu.
  Output : rien (mutation directe de `player`).
  Spécificités : jamais de boucle ; appelle `player.update_tile()`
  (méthode déjà existante, gère juste le sprite/l'animation, ne
  déplace rien).

- **`apply_guest_input(player2, data) -> None`**
  Identique à `apply_player_dict` côté hôte pour l'avatar de
  l'invité ; garde l'ancienne position dans `player2.last_pos` avant
  d'écraser (utile si vous voulez ajouter de l'interpolation plus
  tard).

- **`apply_ghost_dict(ghost, data, flashing) -> None`**
  Input : un `Ghost`, son `dict` reçu, et un booléen "clignote".
  Output : rien (mutation directe).
  Spécificités : branche sur `ghost.state` pour choisir la bonne
  méthode de sprite (`update_ghost_tile` en mode yeux/apeuré, sinon
  `update_tile`) — logique de rendu recopiée du comportement normal,
  jamais la logique d'IA.

- **`apply_remote_state(game, state) -> None`**
  Input : `Game` + le `dict` complet reçu de l'hôte. Output : rien.
  Spécificités : **boucle** `for ghost, data in zip(...)` (itère sur
  une liste fixe, n'attend rien) ; **boucle** sur les tuiles mangées
  (`eaten_tiles`) avec effet de bord sur `game.maze.map` et un appel
  de rendu (`draw_on_maze`) ; fait la **réconciliation** en comparant
  la position locale à l'écho reçu (écart > 2 tuiles ou vie/mort
  différente ⇒ on écrase la position locale par celle de l'hôte).

---

## 3. `src/network/netcode.py` — classe `NetHost`

- **`__init__(self, port=5005)`**
  Crée le socket, **`bind`** immédiatement sur `port` (peut lever
  `OSError` si déjà pris). Initialise `guest_addr = None` et
  `last_guest_input = None`.

- **`wait_for_guest(self, args, seed, timeout=300.0) -> bool`**
  Input : la config à transmettre + le seed de départ.
  Output : `True` si un invité s'est connecté, `False` si timeout.
  Spécificités : **boucle bloquante** (`while True` avec
  `setblocking(True)` + `settimeout(timeout)`) qui attend
  spécifiquement un paquet `"hello"` — répond aux `"ping"` au passage
  (pour `can_reach_host`) sans sortir de la boucle. Repasse en non
  bloquant dans un `finally` avant de continuer. Une fois le hello
  reçu : **petite boucle bornée** de 5 envois du paquet `"init"`
  espacés de `time.sleep(0.05)`, pour compenser une éventuelle perte
  UDP (pas une attente d'event, un renvoi "au cas où").

- **`poll_input(self) -> dict | None`**
  Input : aucun. Output : le dernier état connu du joueur invité (ou
  `None` si rien n'a jamais été reçu).
  Spécificités : **boucle non bloquante** (`while True` jusqu'à
  `BlockingIOError`) qui **draine tout le buffer** de réception d'un
  coup — ne s'arrête jamais sur le premier paquet, prend le plus
  récent. Ne bloque jamais la frame, contrairement à
  `wait_for_guest`.

- **`send(self, packet) -> None`**
  Input : un `dict`. Output : rien.
  Spécificités : ne fait rien si `guest_addr` est encore `None`
  (personne connecté) ; `try/except OSError` pour ne pas planter si
  l'envoi échoue ponctuellement.

- **`send_new_level(self, level, seed) -> None`**
  Simple raccourci qui appelle `send()` avec un `dict` de type
  `"new_level"`.

---

## 4. `src/network/netcode.py` — classe `NetGuest`

- **`__init__(self, host_ip, port=5005)`**
  Stocke l'adresse de l'hôte, crée le socket — **pas de `bind`** :
  l'OS assignera un port éphémère tout seul au premier `sendto`.

- **`say_hello_and_wait_init(self, timeout=300.0) -> dict | None`**
  Input : aucun. Output : le `dict` d'init reçu, ou `None` si
  timeout.
  Spécificités : **boucle bloquante bornée dans le temps**
  (`while time.time() < deadline`), avec un `settimeout(1.0)` par
  itération : renvoie le hello **toutes les secondes** jusqu'à
  recevoir un paquet `"init"`. C'est ce `sendto` répété qui révèle
  l'adresse de l'invité à l'hôte (voir `recvfrom` côté `NetHost`).

- **`send_input(self, player) -> None`**
  Sérialise et envoie la position du joueur local. Aucune boucle,
  aucune attente.

- **`poll_state(self) -> dict | None`**
  Même pattern que `poll_input` côté hôte : boucle non bloquante,
  draine tout, garde le dernier `"state"` reçu ; stocke en plus tout
  paquet `"new_level"` vu au passage dans `pending_new_level`.

---

## 5. Fichiers du jeu existant — ce qui a changé, méthode par méthode

- **`config/parser_config.py :: print_obj(args) -> None`**
  Changement : `json.dumps(args, indent=4, default=str)`.
  Spécificités : `default=str` = "si un objet n'est pas sérialisable,
  affiche son `repr()` au lieu de planter". Aucune boucle.

- **`src/maze/maze.py :: Maze.__init__`**
  Ajout d'une seule ligne : `self.rng = random.Random(seed)`.
  Doit être fait **avant** tout appel à `add_super_gum`/`add_fruit`
  (ordre important).

- **`src/maze/maze.py :: add_fruit` / `add_super_gum`**
  Changement : `randint(...)` → `self.rng.randint(...)`.
  `add_super_gum` avait déjà sa propre boucle préexistante
  (`for s in seq:`, 4 itérations fixes sur les 4 coins) — je n'y ai
  pas touché, juste changé la source des nombres aléatoires.

- **`src/init.py :: init_new_level(self, seed=None) -> None`**
  Changement : `seed` devient un paramètre optionnel (`None` par
  défaut ⇒ comportement solo inchangé, tirage aléatoire). Ajout :
  réinitialisation de `player2` (score/vies conservés) — corrige un
  bug préexistant, indépendant du LAN.

- **`src/game.py :: start_new_game(self, args)`**
  Ajout : lecture de `args.get("role")`/`args.get("net")` ; si
  `role == "guest"`, les dimensions/seed du labyrinthe viennent de
  `self.net.init_data` (reçu du réseau) au lieu de `args` local.
  Spécificité/fragilité : suppose que la poignée de main réseau est
  **déjà terminée** à ce stade (pas de vérification défensive si
  `init_data` est `None`).

- **`src/game.py :: level_is_won(self) -> None`**
  Ajout d'une ligne : si `role == "host"`, appelle
  `self.net.send_new_level(...)` juste après avoir généré le nouveau
  niveau localement.

- **`src/game_logic/updates.py :: update_entitys(game) -> None`**
  Restructurée en 3 branches (`guest` / `host` / `solo`).
  Côté `guest` : simule son joueur, envoie sa position, lit et
  applique l'état reçu, détecte un changement de niveau en comparant
  `pending["level"] != game.level`. Côté `host` : remplace l'appel
  `player2.update()` par `apply_guest_input(...)`. La boucle
  `for g in game.ghosts: g.update(...)` est préexistante, seulement
  déplacée pour n'être exécutée que côté host/solo.

- **`src/game_logic/updates.py :: update_game_state(game)`**
  Ajout d'un court-circuit : côté `guest`, ne fait que
  `draw_lives(game)` et retourne — tout le reste (pac-gums, score,
  niveaux) est déjà résolu par le réseau. Côté host : réinitialise
  `game.newly_eaten_tiles = []` en début de fonction, et en fin de
  fonction (si `role == "host"`) construit et envoie l'état.

- **`src/game_logic/updates.py :: update_pellets(game, player, map)`**
  Ajout de 2 lignes qui ajoutent `(x, y)` à
  `game.newly_eaten_tiles` **avant** de mettre la case à 0, seulement
  si elle n'était pas déjà vide. Reste de la fonction inchangé.

- **`src/interface/render.py :: Render.init_invariant(cls)`**
  Ajout d'une branche sur `os.environ.get("PACMAN_WINDOWED")` :
  fenêtre de taille réduite et positionnable au lieu de
  `pygame.FULLSCREEN`. Aucune boucle.

- **`pac_man.py :: setup_network(args) -> dict`**
  Nouvelle fonction. Utilise `input()` (bloquant standard Python —
  attend une frappe clavier + Entrée, rien à voir avec les sockets)
  pour choisir le mode, puis délègue à `NetHost.wait_for_guest` ou à
  `can_reach_host` + `NetGuest.say_hello_and_wait_init` selon le
  choix.

- **`pac_man.py :: main(argv) -> int`**
  Ajout d'une seule ligne : `args = setup_network(args)` entre le
  parsing de la config et la création de `Game(args)`.
