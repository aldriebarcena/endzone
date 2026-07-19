# backend/

Python AWS Lambda backend, deployed via SAM. Not currently running — see the root [README](../README.md) for scope.

- `src/adapters/` — Tank01 (live scoring), ESPN (play enrichment), Sleeper (league import)
- `src/checker/`, `src/poller/`, `src/push/` — the three pipeline Lambdas (checker finds a live game, poller diffs scoring plays every 90s, push computes personalized fantasy points and calls APNs)
- `src/api/` — API Gateway handlers: `import_league`, `register_device_token`, `get_live_game`
- `template.yaml` — SAM template (Lambdas, DynamoDB tables, SQS + DLQ, API Gateway with Sign in with Apple JWT auth, billing alarm)
- `tests/` — 59 pytest tests, no AWS credentials needed

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
sam validate --lint && sam build
```
