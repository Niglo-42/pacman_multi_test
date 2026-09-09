"""Tests for the highscore storage helpers (src/interface/menu.py)."""
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.interface.menu import (  # noqa: E402
    HIGHSCORE_LIMIT, load_scores, save_score)


def test_load_missing_file_is_empty(tmp_path):
    assert load_scores(str(tmp_path / "nope.json")) == {}


def test_load_corrupt_file_is_empty(tmp_path):
    path = tmp_path / "hs.json"
    path.write_text("{ broken")
    assert load_scores(str(path)) == {}


def test_load_drops_invalid_entries(tmp_path):
    path = tmp_path / "hs.json"
    path.write_text(json.dumps({"ok": 100, "neg": -5, "text": "x", "b": True}))
    assert load_scores(str(path)) == {"ok": 100}


def test_save_keeps_best_score_per_name(tmp_path):
    path = str(tmp_path / "hs.json")
    save_score(path, "Bob", 100)
    save_score(path, "Bob", 40)
    assert load_scores(path) == {"Bob": 100}


def test_save_trims_to_top_ten(tmp_path):
    path = str(tmp_path / "hs.json")
    for i in range(15):
        save_score(path, f"p{i:02d}", i * 100)
    scores = load_scores(path)
    assert len(scores) == HIGHSCORE_LIMIT
    assert min(scores.values()) == (15 - HIGHSCORE_LIMIT) * 100
    assert "p14" in scores and "p00" not in scores
