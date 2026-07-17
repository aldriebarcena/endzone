import pytest

from src.adapters import fetch_game_state


def test_fetch_game_state_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        fetch_game_state("game-1")
