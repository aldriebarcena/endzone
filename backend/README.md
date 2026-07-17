# backend/

Python AWS Lambda backend, deployed via SAM — see [DESIGN.md](../DESIGN.md#backend-aws-serverless).

Structure fills in as Build order phases land (see [PROJECT_PLAN.md](../PROJECT_PLAN.md)):

- Phase 1 — data model (`GameState`, `ScoringEvent`) and the `fetchGameState()` adapter interface in `src/`
- Phase 2 — API-Football adapter implementation, validated with a local script
- Phase 3 — `template.yaml` (SAM), DynamoDB tables, checker + poller Lambdas
- Phase 4 — SQS fan-out, push Lambda, APNs
- Phase 5 — Sleeper import adapter

`requirements.txt` starts empty and gets populated as real dependencies are needed.
