# Task: Containerize project with local compose build (port 8070)

## Context
- Goal: Add Docker build file and docker-compose for local development/deployment.
- Constraint: External port must be 8070.
- Selected approach: No application code changes; use compose runtime working directory `/data` for persistence.

## Approved Plan
1. Add `.dockerignore`, `Dockerfile`, and `docker-compose.yml`.
2. Persist runtime data in host path `./data` mounted to container `/data`.
3. Keep plugin loading stable by setting `PLUGINS_DIR=/app/plugins`.
4. Update docs (`README.md`, auto-doc files).
5. Run `docker compose up --build -d` and verify service at `http://127.0.0.1:8070/`.

## Expected Result
- One-command local container startup with build.
- Runtime files survive container restarts.
- Service reachable on host port 8070.
