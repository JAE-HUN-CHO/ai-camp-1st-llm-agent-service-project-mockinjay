# Issue Tracker — CareGuide

**Tracker**: GitHub Issues
**Repository**: `KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-mockinjay`
**URL**: https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-mockinjay/issues

## Authoritative source

GitHub Issues is the **single source of truth** for all work items in CareGuide.
Local markdown TODOs and `docs/agents/*REPORT.md` files are historical / informational only — they do **not** replace GitHub Issues.

## When to open an issue

| Trigger | Open an issue? |
|---|---|
| Bug reproduced locally | **Yes** — label `bug` + scope label |
| New feature in the PRD | **Yes** — label `enhancement` + `type:feature` |
| ADR proposes a code change | **Yes** — link the ADR in the issue body |
| Refactor without observable behavior change | Yes if > 1 file or touches `backend/Agent/` |
| Cosmetic change in a single file | No — open a small PR directly |
| Discussion / question | Use GitHub Discussions if available, else `question` label |

## Issue title convention

```
<area>: <imperative summary>
```

Examples:
- `agent/quiz: 채점 로직에서 RAG 컨텍스트 누락`
- `frontend/health-records: empty state 컴포넌트 추가`
- `infra/mongo: vector_index migration script`

`<area>` should match one of the `area:*` labels in `triage-labels.md`.

## Issue body template

```markdown
## Context
<!-- Why this matters; link the PRD/REQ/ADR/file:line -->

## Acceptance criteria
- [ ] …
- [ ] …

## Out of scope
<!-- explicitly list things this issue does NOT do -->

## Verification
<!-- how a reviewer can confirm it works -->

## Links
- ADR: docs/adr/ADR-XXX-...
- File: backend/app/api/...
- Spec: docs/converted/...
```

## Linking to issues from code & docs

- In commit messages: `fix(agent/quiz): handle empty rag context (#42)`
- In ADRs: add a `Tracking` line at the top with `GH-#42`
- In `docs/agents/*REPORT.md`: cite issues inline with `#42` style references

## Closing rules

An issue may be closed only when:
1. All acceptance criteria checkboxes are checked.
2. Verification command in the issue body has been run and passes.
3. PR(s) referencing the issue are merged into the active integration branch.

For the `triage` skill state machine, see `triage-labels.md`.
