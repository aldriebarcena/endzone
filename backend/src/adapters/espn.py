from __future__ import annotations

from dataclasses import dataclass

import requests

HOST = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


@dataclass(frozen=True)
class EspnScoringPlay:
    """Structured supplement to Tank01's scoring plays — real yardage and
    an explicit pass/rush play-type classification, neither of which
    Tank01 exposes as structured fields (see fantasy_points.py). This is
    ESPN's unofficial, undocumented site API — no key, could change or
    get blocked without notice. Matched against a Tank01 ScoringEvent by
    (team, period, clock), which was verified to be a clean 1:1 match
    with zero collisions on a real 6-scoring-play game.
    """

    play_type: str
    text: str
    yardage: int
    team: str
    period: int
    clock: str


def to_dict(espn_play: EspnScoringPlay) -> dict:
    """Plain-dict form for storage.py/SQS messages — those boundaries
    intentionally don't import EspnScoringPlay directly (keeps models.py
    free of an adapters dependency), so this is the shared conversion
    point rather than each caller reimplementing it.
    """
    return {
        "play_type": espn_play.play_type,
        "text": espn_play.text,
        "yardage": espn_play.yardage,
        "team": espn_play.team,
        "period": espn_play.period,
        "clock": espn_play.clock,
    }


def from_dict(data: dict) -> EspnScoringPlay:
    return EspnScoringPlay(
        play_type=data["play_type"],
        text=data["text"],
        yardage=data["yardage"],
        team=data["team"],
        period=data["period"],
        clock=data["clock"],
    )


def fetch_scoring_plays(espn_game_id: str) -> tuple[EspnScoringPlay, ...]:
    response = requests.get(
        f"{HOST}/summary", params={"event": espn_game_id}, timeout=10
    )
    response.raise_for_status()
    return parse_scoring_plays(response.json())


def parse_scoring_plays(summary: dict) -> tuple[EspnScoringPlay, ...]:
    team_lookup = {
        play["team"]["id"]: play["team"]["abbreviation"] for play in summary.get("scoringPlays", [])
    }

    plays = []
    for drive in summary.get("drives", {}).get("previous", []):
        for play in drive.get("plays", []):
            if not play.get("scoringPlay"):
                continue
            offense_team_id = next(
                (tp["id"] for tp in play.get("teamParticipants", []) if tp.get("type") == "offense"),
                None,
            )
            plays.append(
                EspnScoringPlay(
                    play_type=play["type"]["text"],
                    text=play["text"],
                    yardage=int(play.get("statYardage", 0)),
                    team=team_lookup.get(offense_team_id, offense_team_id),
                    period=int(play["period"]["number"]),
                    clock=play["clock"]["displayValue"],
                )
            )
    return tuple(plays)
