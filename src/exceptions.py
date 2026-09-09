"""Exceptions used to steer the top-level game flow."""


class GameExit(Exception):
    """Raised from any event loop when the player closes the window.

    It unwinds straight to :meth:`src.game.Game.monitor`, which shuts pygame
    down cleanly -- so closing the window is never an unhandled crash,
    whatever screen is currently active.
    """
