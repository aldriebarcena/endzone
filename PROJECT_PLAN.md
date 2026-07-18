# Project Plan

Task checklist tracking progress against [DESIGN.md](DESIGN.md)'s Build order. Phases are sequenced deliberately (see DESIGN.md) — do them roughly in order except Phase 5, which is explicitly parallelizable.

## Phase 1 — Data model + adapter interface
- [x] Define `GameState` type
- [x] Define `ScoringEvent` type
- [x] Define `fetchGameState(gameId) -> GameState` adapter function signature (stub, no real provider yet)
- [x] Unit test scaffolding for model construction

## Phase 2 — Tank01 NFL integration (local validation) — done
- [x] Get a RapidAPI key, subscribed to **Tank01 NFL Live In-Game Real-Time Statistics** (`tank01`) — https://rapidapi.com/tank01/api/tank01-nfl-live-in-game-real-time-statistics-nfl (free tier: 1,000 req/month, confirmed). Providers tried and rejected first: API-Football (soccer-only), API-American-Football (dead RapidAPI link), SportAPI7 (50 req/**month**, unusably low).
- [x] Plain local script (not Lambda) to hit the provider and dump raw JSON for inspection — `backend/scripts/explore_api.py`
- [x] Ran the script against a real game (`getNFLGamesForDate`, `getNFLBoxScore`) — host and both endpoints confirmed working
- [x] Implemented the Tank01 adapter (`backend/src/adapters/tank01.py`) conforming to `fetch_game_state()`, against the real response shape. `getNFLBoxScore` returns a `scoringPlays` list (period, clock, team, description, cumulative score) — exactly what's needed, no play-by-play guessing required.
- [x] Diffing validated in `backend/tests/test_diffing.py` against a real (trimmed, git-tracked) fixture: comparing two synthetic snapshots of the same completed game correctly detects the plays added in between.
- [x] Findings: data is solid — real scoring plays with clean fields, not just aggregate stats. One real gap: **no single "the scorer" per play** — a passing TD's `playerIDs` lists passer, receiver, and kicker with no consistent primary-scorer ordering (see Open questions below). Also no per-play fantasy point value (expected — DESIGN.md wants that computed from each league's custom settings, not provider-supplied).

## Phase 3 — DynamoDB + Lambda poller (SAM)
- [ ] `template.yaml`
- [ ] `LeagueConfig` table (PK `userId`)
- [ ] `LiveGameState` table (PK `gameId`, TTL ~24hrs post-game)
- [ ] Checker Lambda — runs every ~15 min, determines if a game is currently live
- [ ] Poller Lambda — 90s cadence, only while checker says a game is live
- [ ] Local testing via `sam local invoke`
- [ ] `sam deploy --guided`

## Phase 4 — SQS + push Lambda + APNs fan-out
- [ ] SQS queue for "new scoring event detected"
- [ ] Poller Lambda publishes diffed events to SQS
- [ ] Push Lambda (SNS or direct APNs call) triggered off the queue
- [ ] APNs certs/keys, sandbox testing
- [ ] CloudWatch billing alarm at $5

## Phase 5 — Sleeper import (parallelizable with 1–4)
- [ ] Sleeper API adapter (read-only, no auth)
- [ ] League import flow: league ID in → roster/settings fetched → stored in `LeagueConfig`
- [ ] Custom point-value config

## Phase 6 — iOS app
- [ ] Xcode project (SwiftUI)
- [ ] Sign in with Apple
- [ ] SwiftData models mirroring `GameState` / `ScoringEvent` / `LeagueConfig`
- [ ] URLSession networking layer
- [ ] APNs push handling (UserNotifications framework)
- [ ] Can be stubbed against fake data early to parallelize with backend work

---

## Open questions
Gaps noticed in DESIGN.md's architecture — not blocking, but need a decision before the phase that hits them:

- **No API surface for the iOS client to write `LeagueConfig`.** DESIGN.md's backend section covers the poll → diff → push path but never specifies how a user's league import / custom point values get from the phone to DynamoDB. Likely needs an API Gateway + Lambda (or Lambda Function URL) for this CRUD path. Resolve by Phase 5.
- **No device-token registration path.** Push delivery (Phase 4) needs to know each user's APNs device token, but nothing in DESIGN.md's architecture describes how that gets registered/stored. Likely lives on the same API surface as the point above. Resolve by Phase 4.
- **Fantasy point computation and per-player scoring attribution isn't designed yet.** `ScoringEvent` carries the raw play (all `player_ids` involved, `scoring_type`, `description`) but Tank01 doesn't reliably mark which one is "the" scorer for fantasy purposes (a passing TD's `playerIDs` order is `[passer, receiver, kicker]`, a rushing TD's is `[rusher, kicker]` — inconsistent). Computing actual per-user point values against `LeagueConfig`'s custom settings, and deciding how to attribute points across multiple players on one play, needs its own design pass. Resolve by Phase 3/4 (poller needs this before it has anything meaningful to push).
