# AGENTS.md — CareGuide Repository Guide

CareGuide는 만성 신장질환(CKD) 환자 대상 의료/복지 LLM Agent 서비스입니다.
이 문서는 AI 에이전트(Verdent, Claude Code, Codex 등)가 이 저장소에서 작업할 때 참고하는 진입점입니다.

## Project Snapshot

- **Backend**: FastAPI + Parlant SDK (port 8800), 4개 Agent (Medical_Welfare, Nutrition, Research_Paper, Quiz)
- **Frontend (canonical)**: `new_frontend/` (Vite + React + TypeScript + Tailwind) — see ADR-001
- **DB**: MongoDB (**local Docker** for development) — see ADR-005
- **Vector**: MongoDB Vector Search (1536d, cosine, text-embedding-3-small)
- **Architecture decisions**: `docs/adr/`
- **Domain language**: `docs/agents/domain.md`
- **Recent reports**: `docs/agents/FINAL_COMPLETE_REPORT.md`, `docs/agents/PARLANT_INTEGRATION.md`

## Quick Start (Agent)

1. Read `docs/agents/domain.md` to learn the bounded context and ubiquitous language.
2. Skim `docs/adr/` index — every ADR with status `Accepted` is binding.
3. For any new architectural change, propose a new ADR rather than editing an Accepted one.
4. Use the GitHub issue tracker (see `docs/agents/issue-tracker.md`) for all new work items.
5. Use the canonical triage labels from `docs/agents/triage-labels.md` — do not invent new labels without ADR.

## Agent skills

This project is configured for the Matt Pocock engineering skill suite (`to-issues`, `to-prd`, `triage`, `diagnose`, `tdd`, `improve-codebase-architecture`, `zoom-out`).

| Concern | Source of truth |
|---|---|
| Issue tracker | **GitHub Issues** — see `docs/agents/issue-tracker.md` |
| Triage label vocabulary | `docs/agents/triage-labels.md` |
| Domain documentation layout | `docs/agents/domain.md` (single bounded context) |
| Architecture decisions | `docs/adr/` (`ADR-NNN-<slug>.md`, statuses: Proposed / Accepted / Superseded) |
| PRD / requirements | `docs/converted/` (e.g. `KidneyWise_TechSpec.md`, `Requirements_v0.96.md`) |

### Skill behavior contracts

- **`to-issues`**: produce vertical-slice GitHub issues using labels from `docs/agents/triage-labels.md`. Default repo: `KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-mockinjay`.
- **`to-prd`**: append PRDs as `docs/converted/PRD_<topic>.md` and open a GitHub issue tagged `type:prd`.
- **`triage`**: drive issue state via the canonical state machine in `docs/agents/triage-labels.md`. Never assign a label not listed there.
- **`diagnose`**: when investigating runtime issues, start from `docs/agents/BUG_FIX_REPORT.md` and `docs/agents/FINAL_COMPLETE_REPORT.md` for prior diagnoses.
- **`tdd`**: respect existing test layout under `backend/tests/` and `new_frontend/src/__tests__/`. Use `pytest` for backend and `vitest` for frontend.
- **`improve-codebase-architecture`**: read all `docs/adr/*.md` first; refactors must reference at least one ADR or open a new one.
- **`zoom-out`**: anchor on `docs/agents/domain.md` and `docs/adr/ADR-002-parlant-orchestration.md` for architectural posture.

## Hard constraints

- **No payment integration** — see ADR-006 (Accepted). Do not add Stripe / KCP / Toss / Kakao Pay code, even as mock buttons.
- **Clinical trials feature is in scope** — see ADR-004 (Accepted, Option B). Surface ClinicalTrials.gov data in UI; treat as part of MVP.
- **MongoDB is local Docker only** for development — see ADR-005 (Accepted, revised). Atlas is **not** the default; production deployment is out of MVP scope.
- **No new frontend frameworks** — `new_frontend/` is canonical (ADR-001). `frontend/` and `stitch_frontend/` are deprecated; do not add features there.

## Verification before closing a task

After code edits, run lightweight verification on changed files:

- Backend: `pytest -q backend/tests/<changed-area>` + `ruff check backend/app/`
- Frontend: `cd new_frontend && npm run build` + `npm run lint`
- Integration: `docker compose up mongodb` then a smoke test against `backend/app/main.py`

## Where to add new docs

| What | Where |
|---|---|
| New ADR | `docs/adr/ADR-NNN-<slug>.md` (next number after current max) |
| Agent / orchestration design | `docs/agents/<TOPIC>.md` |
| Source-of-truth PRD or spec | `docs/converted/<NAME>.md` |
| Per-feature implementation report | `docs/agents/<FEATURE>_REPORT.md` |
