"""Tests for the configuration loader (config/parser_config.py)."""
import json

from config.parser_config import Parser, defaults


def _cfg(tmp_path, text):
    path = tmp_path / "c.json"
    path.write_text(text)
    return Parser.parse_config([str(path)])


def test_no_argument_returns_defaults():
    assert Parser.parse_config([]) == defaults()


def test_missing_file_returns_defaults(tmp_path):
    assert Parser.parse_config([str(tmp_path / "nope.json")]) == defaults()


def test_non_json_extension_returns_defaults(tmp_path):
    path = tmp_path / "c.txt"
    path.write_text("{}")
    assert Parser.parse_config([str(path)]) == defaults()


def test_standard_json_with_bool(tmp_path):
    cfg = _cfg(tmp_path, '{"width": 20, "lives": 2, "cheat_mode": true}')
    assert (cfg["width"], cfg["lives"], cfg["cheat_mode"]) == (20, 2, True)


def test_array_wrapper_and_comments(tmp_path):
    text = '[{\n  # size\n  "width": 12, // inline\n  "height": 15,\n}]'
    cfg = _cfg(tmp_path, text)
    assert (cfg["width"], cfg["height"]) == (12, 15)


def test_block_comment(tmp_path):
    cfg = _cfg(tmp_path, '{ /* a\n b */ "seed": 7 }')
    assert cfg["seed"] == 7


def test_out_of_range_is_clamped(tmp_path):
    cfg = _cfg(tmp_path, '{"width": 9999, "lives": -5, "points_per_ghost": 0}')
    assert (cfg["width"], cfg["lives"], cfg["points_per_ghost"]) == (33, 1, 1)


def test_wrong_type_keeps_default(tmp_path):
    cfg = _cfg(tmp_path, '{"width": "abc", "cheat_mode": "yes"}')
    assert (cfg["width"], cfg["cheat_mode"]) == (8, False)


def test_unknown_key_is_ignored(tmp_path):
    cfg = _cfg(tmp_path, '{"level": [1, 2], "pacgum": 42, "width": 10}')
    assert cfg["width"] == 10 and "level" not in cfg


def test_garbage_never_raises(tmp_path):
    assert _cfg(tmp_path, "not json at all !!!") == defaults()


def test_project_config_loads(tmp_path):
    cfg = Parser.parse_config(["config/config.json"])
    assert cfg["width"] == 8 and cfg["cheat_mode"] is False
    # every key round-trips through json
    json.dumps(cfg)
