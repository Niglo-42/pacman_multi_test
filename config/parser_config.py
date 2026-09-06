from io import TextIOWrapper
import json
import ast
from typing import Any

def print_obj(args: dict) -> None:
        print(json.dumps(args, indent=4))

class Parser:
    clamps = {
            "highscore_filename": "highscore.json",
            "width": (6, 33),
            "height": (6, 33),
            "lives": (1, 3),
            "seed": (0, 0xffff),
            "points_per_pacgum": (1, 100),
            "points_per_super_pacgum": (1, 500),
            "fps": (30, 60),
            "nb_player": (1, 2),
            "cheat_mode": (False, True),
            "audio_enable": (False, True),
            "points_per_ghost": (1, 1600)
    }

    @staticmethod
    def clean_commentary(file: TextIOWrapper) -> tuple[dict[str, Any],
                                                       list[int], bool]:
        clean = []
        lines = []
        isline = False
        for i, line in enumerate(file, 1):
            if line.startswith("[") or line.startswith("]"):
                isline = True
            elif line.lstrip().startswith("#"):
                lines.append(i)
            else:
                clean.append(line)
        clean_json = '\n'.join(clean)
        return (ast.literal_eval(clean_json), lines, isline)

    def get_line_nb_including_coms(com_lines: list[int], line: int) -> int:
        acc = 0
        for com_line in com_lines:
            if line >= com_line:
                acc += 1
        return line + acc

    @staticmethod
    def comment(path):
        with open(path, "r", encoding="utf-8") as file:
            if ".json" not in path:
                raise ValueError(f"{path} is not an accepted"
                                "format, only .json are allowed")
            return Parser.clean_commentary(file)

    @staticmethod
    def clamp_tuple(arg: dict) -> dict:
        for k, v in arg.items():
            if isinstance(v, tuple):
                arg[k] = v[0]
        return arg

    def parse_config(argv: list[str]) -> dict:
        if len(argv) != 1:
            raise ValueError(f"This program takes 1 arg, not {len(argv)}")
        params_clamp = Parser.clamps
        try:
            params, com_lines, islist = Parser.comment(argv[0])
        except Exception as e:
            print(e)
            return Parser.clamp_tuple(params_clamp)
        
        for i, (k, v) in enumerate(params.items(), 2 + 1 * (islist)):
            real_line_nb = Parser.get_line_nb_including_coms(com_lines, i)
            if k not in Parser.clamps.keys():
                print(f"{k} is not accepted, line {real_line_nb}")
                continue
            
            if k == "highscore_filename":
                if isinstance(v, str):
                    if ".json" in v and not v.isspace():
                        params_clamp[k] = v
                else:
                    print(
                    f"{v} is not an accepted path, error line: {real_line_nb}")
            elif k == "audio_enable" or k == "cheat_mode":
                if isinstance(v, bool):
                    params_clamp[k] = v
                else:
                    print(f"{v} is not accepted, error line: {real_line_nb}")
            else:
                try:
                    v = int(v)
                except ValueError as e:
                    print(e)
                    params_clamp[k] = Parser.clamps[k][0]
                    continue
                if v < params_clamp[k][0]:
                    params_clamp[k] = params_clamp[k][0]
                elif v > params_clamp[k][1]:
                    params_clamp[k] = params_clamp[k][1]
                else:
                    params_clamp[k] = v
        return Parser.clamp_tuple(params_clamp)
