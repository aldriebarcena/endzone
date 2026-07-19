# Endzone

Fantasy football live-feed iOS app — real NFL scoring plays turned into personalized fantasy-point push notifications. A portfolio project: full-stack (SwiftUI + AWS serverless).

<p float="left">
  <img src="docs/screenshots/sign-in.png" width="220" alt="Sign in with Apple screen" />
  <img src="docs/screenshots/live-feed.png" width="220" alt="Live feed with real scoring plays and computed fantasy points" />
  <img src="docs/screenshots/import-league.png" width="220" alt="League import form" />
</p>

## What it does

A user signs in with Apple, imports their Sleeper fantasy league, and watches their tracked NFL game as a live feed — every scoring play shown with real per-player fantasy points, computed against their league's actual scoring settings, not a generic estimate. Push notifications carry the same personalized points for when the app isn't open.

## Architecture, briefly

```
checker Lambda (EventBridge, ~15min)
  → detects a live game via Tank01
  → starts a Step Functions execution
      → poller Lambda loops every 90s (Step Functions Wait state)
          → diffs new scoring plays, enriches via ESPN, persists to DynamoDB, publishes to SQS
              → push Lambda computes personalized points per subscriber, calls APNs

API Gateway (Sign in with Apple JWT auth)
  → GET /live-game: same stored, ESPN-enriched state, points computed personalized to whoever's asking
  → POST /leagues, PUT /device-token: the write side (import a league, register for push)
```

iOS: SwiftUI + SwiftData, Sign in with Apple, stubbed against fake data (no live backend deployed — see [Status](#status)). Backend: Python Lambdas behind AWS SAM, deployable but not currently running.

## Status

**Portfolio/demo project, not deployed.** The backend is real, deployable infrastructure (SAM template, scoped IAM policies, a cost guardrail) because designing it that way is itself the point — but running it live isn't required to see it work. The iOS app runs fully in Simulator against stubbed data.

## Running it

**Backend** (Python 3.13):
```
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest        # 59 tests, no AWS credentials needed
sam validate --lint && sam build  # confirms the infra is real and deployable
```

**iOS** (Xcode 16+, iOS 17+ simulator):
```
cd ios
open Endzone.xcodeproj          # or: xcodebuild -project Endzone.xcodeproj -scheme Endzone -destination 'platform=iOS Simulator,name=iPhone 17' build
```
Real Sign in with Apple in Simulator needs an Apple ID signed into the Simulator itself (Settings → Sign in to your iPhone) and can hang mid-flow regardless — a known Simulator limitation, not an app bug. To skip straight to the live feed, tap **Continue as Demo User** on the sign-in screen (DEBUG builds only; see `AuthManager.swift`).

## Path to production

This is a portfolio project by design (see [Status](#status)) — nothing below is required for it to be "done." Here's what actually stands between this and real people using it.

**Backend: deploy to AWS**
1. `aws configure` with a real account, then `sam deploy --guided` from `backend/` — supplies `AlertEmail` (billing alarm) and the `Apns*` parameters (`ApnsTeamId`, `ApnsKeyId`, `ApnsPrivateKey`, `ApnsBundleId`, `ApnsSandbox=false`), which need a real Apple Developer account (see below).
2. Move off Tank01's free tier: 1,000 requests/month supports ~7 tracked games/month at the current 90s poll interval. Real usage across many users needs at least the $10/month paid tier (1,000 req/day).
3. ESPN's play-enrichment API is unofficial and undocumented — no SLA, and it could change or get rate-limited without notice. `poller.py` already degrades gracefully to un-enriched events if it fails; a real launch should treat that as the expected steady state for this dependency, not an edge case.

**iOS: ship to the App Store**
1. A real Apple Developer Program membership, a real Team ID replacing the placeholder `com.endzone.app` bundle ID, and the Sign In with Apple capability registered against that team.
2. Swap `FakeEndzoneAPI` for `URLSessionEndzoneAPI` at the `EndzoneApp.swift` injection point (already a one-line change) once the backend above has a real URL.
3. Flip the `aps-environment` entitlement from development to production for release builds, using the same `.p8` key referenced in the backend's `ApnsPrivateKey` parameter.
4. App Store Connect: create the app record, fill in App Privacy details (this app handles a Sign in with Apple identity, a Sleeper league ID, and a push token — all disclosable), host a privacy policy, and capture real screenshots on a physical device.
5. TestFlight first, then submit for review.

**The bigger gap: this only tracks one game, globally.** `checker.py`'s `_pick_game_to_track` picks a single live game for the entire app — every user sees the same tracked game regardless of their own league. That's fine for a demo but not for real usage: different users caring about different games needs per-user (or per-league) game tracking — its own poller execution per tracked game instead of one global loop — plus the per-user roster import that was deliberately skipped as speculative work. That's the real architectural lift between "deployable" and "usable by an actual audience," well beyond AWS/App Store logistics.
