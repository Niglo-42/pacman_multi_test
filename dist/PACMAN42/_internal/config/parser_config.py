"""Configuration file loading and validation.

The game is launched with a single argument: the path to a JSON configuration
file.  On top of standard JSON the loader also accepts comments (``#`` and
``//`` line comments, ``/* ... */`` blocks) and trailing commas.

Every problem -- unreadable file, malformed JSON, wrong type, out-of-range
number, unknown key -- is reported on stdout and replaced by a safe default.
The game never crashes because of the configuration.
"""
from __future__ import annotations

import json
import re
from typing import Any

# Integer keys: name -> (minimum, maximum, default).
_INT_RANGES: dict[str, tuple[int, int, int]] = {
    "width": (6, 33, 8),
    "height": (6, 33, 7),
    "lives": (1, 3, 3),
    "seed": (0, 0xFFFF, 42),
    "points_per_pacgum": (1, 100, 10),
    "points_per_super_pacgum": (1, 500, 50),
    "points_per_ghost": (1, 1600, 200),
    "fps": (30, 60, 60),
    "nb_player": (1, 2, 1),
}
# Boolean keys: name -> default.
_BOOL_KEYS: dict[str, bool] = {
    "cheat_mode": False,
    "audio_enable": False,
}
# String keys: name -> default.
_STR_KEYS: dict[str, str] = {
    "highscore_filename": "highscore.json",
}

# Matches a full string literal (kept as-is) OR a comment (captured, stripped).
_COMMENT_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'
    r'|(/\*.*?\*/|//[^\n]*|#[^\n]*)',
    re.DOTALL,
)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def defaults() -> dict[str, Any]:
    """Return a fresh dict with every configuration key at its default."""
    cfg: dict[str, Any] = dict(_STR_KEYS)
    cfg.update({key: rng[2] for key, rng in _INT_RANGES.items()})
    cfg.update(_BOOL_KEYS)
    return cfg


def print_obj(args: dict[str, Any]) -> None:
    """Pretty-print a configuration dictionary as indented JSON."""
    print(json.dumps(args, indent=4))


def _strip_comments(text: str) -> str:
    """Strip ``#``, ``//`` and ``/* */`` comments and trailing commas.

    String literals are left untouched.
    """
    def replace(match: "re.Match[str]") -> str:
        """Drop the match if it is a comment, keep it if it is a string."""
        return "" if match.group(1) is not None else match.group(0)

    text = _COMMENT_RE.sub(replace, text)
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def _load_raw(path: str) -> dict[str, Any]:
    """Read *path*, strip comments and return the JSON object it holds.

    The file may contain a single object or a one-element array wrapping it.

    Raises:
        ValueError: the path is not a ``.json`` file or the content is not
            a JSON object.
        OSError: the file cannot be read.
        json.JSONDecodeError: the content is not valid JSON.
    """
    if not path.endswith(".json"):
        raise ValueError(f"{path}: not a .json file")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.loads(_strip_comments(handle.read()))
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level value must be a JSON object")
    return data


class Parser:
    """Loads and validates the game configuration file."""

    @staticmethod
    def parse_config(argv: list[str]) -> dict[str, Any]:
        """Return a fully populated, validated configuration dictionary.

        With no argument the defaults are returned.  Otherwise ``argv[0]`` is
        loaded and each entry validated; anything invalid is reported and left
        at its default value.
        """
        cfg = defaults()
        if not argv:
            return cfg
        try:
            raw = _load_raw(argv[0])
        except (OSError, ValueError, json.JSONDecodeError) as err:
            print(f"config: {err} -- using defaults")
            return cfg
        for key, value in raw.items():
            Parser._apply(cfg, key, value)
        return cfg

    @staticmethod
    def _apply(cfg: dict[str, Any], key: str, value: Any) -> None:
        """Validate a single ``key: value`` pair and store it into *cfg*."""
        if key in _STR_KEYS:
            if isinstance(value, str) and value.endswith(".json"):
                cfg[key] = value
            else:
                print(f"config: '{key}' must be a .json filename"
                      f" -- keeping {cfg[key]!r}")
        elif key in _BOOL_KEYS:
            if isinstance(value, bool):
                cfg[key] = value
            else:
                print(f"config: '{key}' must be true or false"
                      f" -- keeping {cfg[key]}")
        elif key in _INT_RANGES:
            low, high, _ = _INT_RANGES[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                print(f"config: '{key}' must be a number"
                      f" -- keeping {cfg[key]}")
                return
            clamped = max(low, min(high, int(value)))
            if clamped != value:
                print(f"config: '{key}'={value} clamped to {clamped}")
            cfg[key] = clamped
        else:
            print(f"config: unknown key '{key}' ignored")
