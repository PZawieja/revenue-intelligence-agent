# Runtime Capability Matrix

| Capability | Status | Notes |
|---|---|---|
| Repo read access | YES | Full |
| Repo write access | YES | Full |
| Shell access | YES | bash, zsh |
| Filesystem search | YES | find, rg, fd |
| File editing | YES | Read/Edit/Write tools |
| Git access | YES | git CLI |
| Network access | YES | curl, httpx |
| Package install | YES | pip in .venv |
| Local database | YES | DuckDB (data), SQLite (AOS task store) |
| Browser control | NO | Defer M5; can add Playwright |
| Screenshot/vision | PARTIAL | Claude vision via API |
| Desktop input | NO | Defer |
| Tool-calling support | YES | Claude tool_use API |
| Sub-agent support | YES | Claude Code Agent tool |
| Long-running background | PARTIAL | Background flag in Claude Code |
| Cron/scheduled execution | NO | Defer M4; can add APScheduler |
| Webhook/event triggers | NO | Defer |
| Persistent storage | YES | SQLite + files |
| UI/dashboard rendering | YES | FastAPI + existing SPA |
| Secret management | PARTIAL | .env file (local); no vault |
| Approval/interruption | PARTIAL | Manual via API calls |
| Multi-machine support | NO | Defer |

## Capability Gaps and Resolutions
- **Browser**: defer to M5; scope M1-M4 to shell + API work
- **Scheduling**: defer to M4; use APScheduler then
- **Secrets vault**: use .env for now; flag as risk for multi-user deployment
- **Approval UI**: AOS control plane exposes `/api/aos/approvals` — human approves via API or UI panel
