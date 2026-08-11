# Triage Labels — CareGuide

Canonical label vocabulary for GitHub Issues. The `triage` skill drives issues through the state machine below using **only** these labels. Do not invent new labels without an ADR.

## Label families

### 1. `type:*` — what kind of work this is

| Label | Meaning |
|---|---|
| `type:bug` | Observable defect in shipped behavior |
| `type:feature` | New capability described in PRD / REQ |
| `type:refactor` | Internal restructure, no behavior change |
| `type:docs` | Documentation only |
| `type:infra` | DevOps, Docker, CI, scripts |
| `type:adr` | An ADR is being authored or amended |
| `type:prd` | A PRD is being authored or amended |
| `type:test` | Test-only changes (new tests, fixtures) |

### 2. `area:*` — which subsystem

| Label | Path / responsibility |
|---|---|
| `area:agent` | `backend/Agent/`, Parlant integration |
| `area:agent/medical-welfare` | Medical_Welfare agent |
| `area:agent/nutrition` | Nutrition agent (incl. NutriCoach) |
| `area:agent/research` | Research_Paper / PubMed RAG |
| `area:agent/quiz` | Quiz generation & grading |
| `area:api` | `backend/app/api/` FastAPI routers |
| `area:frontend` | `new_frontend/` (canonical) |
| `area:db` | MongoDB schemas, migrations, indexes |
| `area:vector` | Vector search index, embeddings |
| `area:infra` | Docker, env, CI |
| `area:eval` | `eval/` evaluation harnesses |
| `area:clinical-trials` | ClinicalTrials.gov integration (ADR-004) |

### 3. `priority:*` — urgency

| Label | Meaning |
|---|---|
| `priority:p0` | Blocks MVP launch / data-loss / safety regression |
| `priority:p1` | Important for MVP, has workaround |
| `priority:p2` | Nice-to-have for MVP |
| `priority:p3` | Post-MVP / backlog |

### 4. `state:*` — triage state machine

| Label | Meaning | Set by |
|---|---|---|
| `state:needs-triage` | Default on new issues | issue opener |
| `state:ready` | Triaged, has acceptance criteria, ready for an agent | triager |
| `state:in-progress` | An agent / human picked it up | assignee |
| `state:blocked` | Waiting on external decision / dependency | assignee |
| `state:in-review` | PR open and awaiting review | PR author |
| `state:done` | Merged & verified | merger |

### 5. `risk:*` — for `improve-codebase-architecture` and `diagnose`

| Label | Meaning |
|---|---|
| `risk:safety` | Touches medical / emergency-response code paths |
| `risk:privacy` | Touches PII or health records |
| `risk:perf` | Performance regression possible |

### 6. Special

| Label | Meaning |
|---|---|
| `tracer-bullet` | Smallest end-to-end vertical slice; used by `to-issues` |
| `good-first-issue` | Suitable starter task |
| `wontfix` | Explicitly declined |
| `duplicate` | Closed in favor of another issue |

## State machine

```
needs-triage ──► ready ──► in-progress ──► in-review ──► done
                  │             │                │
                  └─► wontfix   └─► blocked ◄────┘
```

Rules:
- An issue MUST have exactly one `state:*` label at all times.
- Transitioning to `state:in-progress` requires at least one `area:*` and one `priority:*` label.
- Transitioning to `state:done` requires a merged PR linked in the issue.

## Required label combinations

Every triaged issue (state ≥ `state:ready`) must carry:

1. exactly **one** `type:*`
2. **one or more** `area:*`
3. exactly **one** `priority:*`
4. exactly **one** `state:*`
5. zero or more `risk:*` and special labels

Issues missing any of (1)–(4) are sent back to `state:needs-triage`.

## Bootstrap

To create these labels in the GitHub repo, run:

```bash
gh label create "type:bug" --color d73a4a --description "Observable defect"
gh label create "type:feature" --color a2eeef --description "New capability"
gh label create "type:refactor" --color 1d76db
gh label create "type:docs" --color 0075ca
gh label create "type:infra" --color 5319e7
gh label create "type:adr" --color 0052cc
gh label create "type:prd" --color 0052cc
gh label create "type:test" --color c5def5

gh label create "area:agent" --color fbca04
gh label create "area:agent/medical-welfare" --color fbca04
gh label create "area:agent/nutrition" --color fbca04
gh label create "area:agent/research" --color fbca04
gh label create "area:agent/quiz" --color fbca04
gh label create "area:api" --color fef2c0
gh label create "area:frontend" --color bfd4f2
gh label create "area:db" --color c2e0c6
gh label create "area:vector" --color c2e0c6
gh label create "area:infra" --color e99695
gh label create "area:eval" --color d4c5f9
gh label create "area:clinical-trials" --color fbca04

gh label create "priority:p0" --color b60205
gh label create "priority:p1" --color d93f0b
gh label create "priority:p2" --color fbca04
gh label create "priority:p3" --color cccccc

gh label create "state:needs-triage" --color ededed
gh label create "state:ready" --color 0e8a16
gh label create "state:in-progress" --color 1d76db
gh label create "state:blocked" --color b60205
gh label create "state:in-review" --color a2eeef
gh label create "state:done" --color 0e8a16

gh label create "risk:safety" --color b60205
gh label create "risk:privacy" --color b60205
gh label create "risk:perf" --color d93f0b

gh label create "tracer-bullet" --color 0052cc
```

(Defaults like `bug`, `enhancement`, `documentation`, `good first issue` already exist; map them as listed in the table above when triaging old issues.)
