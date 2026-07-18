from __future__ import annotations

from ..models import GameState


def fetch_game_state(game_id: str) -> GameState:
    raise NotImplementedError(
        "No provider wired up yet — implemented in Phase 2 (Tank01 adapter)"
    )
