# Repository Guidelines

## Project Structure & Module Organization
- `backend/app`: FastAPI entry (`main.py`), routers in `api/`, logic in `services/`, models in `models/`, Mongo helpers in `db/`; static uploads mount to `backend/uploads`.
- `backend/Agent`: Multi-agent stack (research_paper, medical_welfare, nutrition, trend_visualization, quiz) with `agent_manager.py`, shared `core/`, and smoke tests under `Agent/test`. Utilities sit in `backend/scripts/` (e.g., `init_quiz_pool.py`).
- Frontend: `frontend/` is the canonical Vite + React + Tailwind app. Feature pages live under `src/features`, shared seams under `src/shared`, and rollback copies live under `logs/rollback/`.
- Data & docs: `data/` holds datasets/vectors; avoid committing regenerated artifacts. All project documentation and plans live under `docs/`, with runtime/test logs under `logs/`.

## Build, Test, and Development Commands
- Backend API: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` (needs `.env` and Mongo).
- Agent checks: `cd backend && python -m Agent.test_agents`; targeted runs via `python test_quiz_agent.py` or `python test_uti_apis.py`.
- Frontend: `cd frontend && npm install && npm run dev`. Build with `npm run build`; preview via `npm run preview`; lint via `npm run lint`. `new_frontend` and `stitch_frontend` are retained only under `logs/rollback/` for parity/recovery.

## Coding Style & Naming Conventions
- Python: PEP8, 4-space indent, snake_case; add type hints and short docstrings on public functions. Keep routers scoped per domain (`api/diet.py`, `api/trends.py`) and use `logging` in FastAPI handlers.
- TypeScript/React: PascalCase components, camelCase hooks/vars, shared types in `src/types`. Prefer Tailwind utilities over ad-hoc CSS; run `npm run lint` before pushing. Route agent work through `AgentManager` unless direct calls are required.

## Testing Guidelines
- Extend Python checks under `backend/Agent/test` or `backend/test_*.py`; use `pytest`-style assertions for new suites while preserving existing async/print probes for E2E coverage.
- Add frontend tests alongside features (e.g., `src/__tests__/` with Vitest/RTL if introduced). At minimum, keep lint clean and ensure `npm run build` passes for new UI flows.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`) with imperative subjects (e.g., `feat: add quiz splash animation`).
- PRs should summarize scope, list test commands run, link issues/docs, and attach screenshots or API samples for UI/API changes. Flag schema or environment variable impacts.

## Security & Configuration Tips
- Backend loads `.env` via `python-dotenv`; set `MONGODB_URI`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PUBMED_EMAIL`, and optional `NCBI_API_KEY`. Never commit secrets; use local `.env` and sanitized examples.
- Ensure MongoDB is running locally before `uvicorn`. Keep generated uploads and caches out of PRs unless debugging storage issues.
