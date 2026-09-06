my name is Jeff

pygame functions    |	Équivalent MLX
---------------------------------------
display.set_mode	|	mlx_new_window
Surface				|	mlx_new_image
blit				|	mlx_put_image_to_window
font.render + blit	|	mlx_string_put
event.get / boucle	|	mlx_hook / mlx_loop


<b>FIX : </b>
- le maze a des couilles / killcaves
- parser: AttributeError: 'Parser' object has no attribute 'seed' si pas de seed dans la config

<b>IMPLEMENTATION :</b>
<u>- mode cheat :</u>
° pas de collision / pas de perte de vie
° skip level (eaten_pellet = total_pellet)
° ghost freeze (plus d'update) if not gostr.freeze
° extra lives
° increased speed (parametres -> if pyagme.key speed += 1)

<b>- victory screen </b>

<b>- main menu: </b>
1) new game
2) parameters
3) highscore
4) game_mode : 42 mode, 2 players mode, (real 1980 mode), multiplayer mode

<b>package steam ?!</b>

<b>multiplayer</b>

juju:
collision entre fantomes ? -> les faire partir opp dir ?
toujours bug de collision sur fast turn
