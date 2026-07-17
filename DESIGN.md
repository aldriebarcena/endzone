# Fantasy Football Live Feed App — Design Doc

## Goal
A full-stack iPhone app (like theRealApp, but fantasy-football-flavored): live game feed re-displayed as fantasy scoring events ("___ scored a TD, +7 pts"), with user-configurable league point settings and league import.

Purpose: new-grad portfolio project. Fills resume gaps (client-facing app, real-time systems, cloud infra) and builds Swift/iOS familiarity. Secondary goal: usable as a real production app later, but that decision is deferred — architecture should support it without committing to its costs now.

---

## Scope decisions (v1)

- **One live game tracked at a time** (user-selected, or auto-selected as the highest-scoring active game in their league). Multi-game concurrent tracking is explicit future work, not an oversight.
- **League import: Sleeper only** (public, read-only, no auth). Yahoo/ESPN are future work — not built symmetrically now.
- **Data provider: API-Football (RapidAPI free tier)**. Free tier ceiling: 100 requests/day. This is a hard constraint driving the poll-interval math below.
- **Poll interval: 90 seconds, only during live windows.** Roughly 140 requests per 3.5hr game at 90s — already near/over the daily cap for more than one game, hence the single-game constraint.
- Build against the free tier **behind an adapter interface** so switching to a paid provider later (if this goes to production) is a config change, not a rewrite.

---

## Architecture

### iOS Client
- Swift + SwiftUI
- async/await for concurrency (not Combine)
- SwiftData for local persistence (cached league config, cached feed)
- URLSession for networking
- APNs (UserNotifications framework) for push — not raw WebSockets. Better battery/OS-level delivery behavior for a backgrounded app; no reconnect logic needed on your end.
- Sign in with Apple for user auth (not Firebase Auth, not custom login) — aligns with Apple platform conventions, relevant to the Apple-adjacent goal.

### Backend (AWS, serverless)
- **Compute:** AWS Lambda + EventBridge scheduled rule.
  - Rationale over Fargate: workload is bursty/short/stateless (fetch → diff → push), not benefiting from a persistent warm process. Fargate would just be a third rendition of "I can run a container" on your resume; Lambda diversifies it instead. Cheaper (near-$0 given actual usage volume) and gives a real, defensible "why not always-on compute" interview answer.
  - **Two-tier scheduling:** a lightweight checker Lambda runs every ~15 min to determine "is a game currently live." Only when true does it enable/trigger the tight 90s polling rule. Avoids running an idle poller 90%+ of the week.
- **Fan-out:** SQS decouples "new scoring event detected" from "push notifications to subscribed users."
- **Push delivery:** SNS (or a Lambda calling APNs directly) triggered off the SQS queue.
- **Storage:** DynamoDB, two tables:
  - `LeagueConfig` — partition key `userId`; holds imported Sleeper league ID + custom point values (JSON blob acceptable, don't over-normalize).
  - `LiveGameState` — partition key `gameId`; holds last-known score/event snapshot for diffing. TTL ~24hrs post-game to auto-expire stale state.
- **IaC:** AWS SAM (not raw console clicks, not full CDK — SAM fits this exact stack and has a lower learning curve; pragmatic choice over the more resume-flashy CDK).
- **Cost guardrail:** one CloudWatch billing alarm at $5. Legitimate, cheap, interview-worthy ("so a polling bug couldn't silently rack up cost"). Don't build more observability than this for v1.

### Data provider abstraction
- Internal types: `GameState`, `ScoringEvent` (your own model, not the provider's JSON shape).
- One adapter function: `fetchGameState(gameId) -> GameState`, currently backed by API-Football.
- If you later pay for a provider (e.g., SportsDataIO) for production use, you add a second adapter and swap one line — nothing downstream (SQS, DynamoDB schema, push logic, iOS app) changes.

### League import
- Sleeper API only, hardcoded adapter (don't build a generic OAuth-any-provider abstraction for v1 — that's solving for Yahoo/ESPN before shipping the one integration you need).

---

## Cost reality (portfolio-scale, ~season-long usage)

- **AWS infra (Lambda, EventBridge, SQS, DynamoDB, SNS):** effectively $0–5/month at this scale (comfortably within free tiers). Not the actual cost driver — don't over-index on "optimizing AWS costs" in writeups at this scale.
- **Sports data API is the real cost variable long-term:**
  - Free tier (API-Football): ~100 req/day cap — workable for one tracked game at 90s intervals, not more.
  - Paid live-data tiers: roughly $25–100+/month for broader coverage/frequency; full enterprise feeds (SportRadar) run much higher and aren't meant for solo projects.
- **Decision for now:** stay on free tier. Defer any spend decision until you've decided whether this becomes a real production app vs. an on-demand portfolio demo.

---

## Build order (sequence matters)

1. **Data model + adapter interface** (`GameState`, `ScoringEvent`, `fetchGameState()` stub) — before touching AWS or Swift.
2. **API-Football integration**, validated locally (plain script, not yet Lambda) against a live/recent game — confirm you can diff two snapshots and detect a scoring event. **Verify this first, before building any AWS architecture around it** — this is the step most likely to reveal the free tier doesn't actually give usable in-play NFL data (delay, incompleteness, etc.).
3. **DynamoDB tables + Lambda poller**, deployed via SAM.
4. **SQS + push Lambda + APNs** fan-out.
5. **Sleeper import** (independent track, parallelizable with 1–4).
6. **iOS app** — can be stubbed against fake data earlier to parallelize, but backend correctness is the higher-risk piece, so it's front-loaded in this sequence.

---

## Explicit non-goals for v1 (don't build these yet)
- Multi-game concurrent tracking
- Yahoo/ESPN league import
- Multi-provider data fallback/failover
- Full observability suite (beyond the single billing alarm)
- Persistent WebSocket connections (only reconsider if adding a foreground "live ticker" beyond APNs push)
- Paying for any tier "just in case" — only commit to paid infra if/when you decide this goes to production
