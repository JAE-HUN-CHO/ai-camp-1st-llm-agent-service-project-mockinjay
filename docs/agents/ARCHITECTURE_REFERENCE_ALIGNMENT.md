# CareGuide 소프트웨어 공학 근거 정렬

**작성일:** 2026-08-15
**입력 자료:** [`software_engineering_methods_pdf_collection_2026-08-15.zip`](/Users/apple/Downloads/software_engineering_methods_pdf_collection_2026-08-15.zip)
**상태:** 설계·검증 방법의 참고 기준. Accepted ADR보다 우선하지 않는다.

## 1. 검토 범위와 원칙

ZIP의 42개 PDF를 `SHA256SUMS.txt`로 전부 검증했고 모두 원본 manifest의 hash와 일치했다.
CareGuide의 현재 P0/P1 갭에 직접 연결되는 architecture, secure SDLC, API protection, testing,
code review, CI/CD, SLO, incident response 자료를 우선 읽었다.

자료의 일반 원칙을 그대로 도입하지 않고 다음 기준으로 적용했다.

1. Accepted ADR-004/005/006/011과 local-first 범위를 먼저 지킨다.
2. 방법론은 현재 팀과 MVP에 맞게 축소하되 source → decision → test → evidence 연결은 유지한다.
3. cloud/service-mesh/HA 전제는 현재 설계에 이식하지 않는다.
4. 수치가 없는 상태에서 SLA나 성능 목표를 꾸며내지 않는다. 먼저 baseline을 측정한 뒤 결정한다.

## 2. CareGuide에 채택하는 방법

### 2.1 ATAM-lite와 지속적 architecture evaluation

SEI ATAM은 stakeholder scenario, architectural view, quality-attribute analysis, sensitivity/tradeoff
검토를 연결한다. SEI의 2023년 holistic architecture 보고서는 이를 일회성 review가 아닌 지속적
governance와 자동화된 evaluation으로 확장한다.

CareGuide에서는 정식 다주간 ATAM 대신 다음 **ATAM-lite**를 ADR-013 승인 gate로 사용한다.

1. owner, backend, frontend, safety/security, operations 관점을 모은다.
2. 아래 quality-attribute scenario를 우선순위화한다.
3. 각 scenario를 목표 architecture와 현재 코드에 mapping한다.
4. sensitivity point와 tradeoff를 기록한다.
5. risk/non-risk, owner, 검증 명령, artifact를 결정한다.

주요 sensitivity point는 `legacy|hex` selector, SSE terminal semantics, owner-bound repository,
Parlant process boundary, Mongo schema owner다. 이 값의 변경은 안전성·호환성·복구성에 동시에
영향을 주므로 일반 리팩토링 세부사항으로 처리하지 않는다.

### 2.2 Secure-by-design와 API inventory

NIST SSDF의 threat modeling·software provenance 원칙과 NIST SP 800-228의 API inventory,
end-user-to-resource authorization, input validation, runtime telemetry를 Phase 0에 적용한다.

- endpoint inventory는 method/path만이 아니라 auth, actor, resource owner, request alias,
  content type, rate/quota, sensitive fields, logs, owner, lifecycle을 포함한다.
- P0 surface인 chat, health, ClinicalTrials, upload에 misuse/abuse case를 작성한다.
- dependency와 generated artifact의 provenance는 lock file, source manifest, git SHA, test artifact로
  추적한다.
- threat model은 별도 대형 보안 프로그램이 아니라 architecture risk register의 일부로 유지한다.

### 2.3 Risk-based verification와 traceability

ISTQB의 risk-based testing·test pyramid·test basis traceability를 적용한다. test 개수가 아니라
위험과 검증 층을 연결한다.

```text
Accepted ADR / quality scenario
  → characterization / unit contract
  → explicit integration path
  → real local HTTP smoke
  → browser journey 또는 operations drill
  → redacted evidence artifact
```

unit test, model eval, provider component smoke, 실제 HTTP, browser E2E는 서로 대체하지 않는다.
ClinicalTrials safety, cross-user authorization, emergency short-circuit, SSE failure는 P0 risk-based
suite로 고정한다.

### 2.4 Small change와 rationale 중심 review

Microsoft의 modern code review 연구는 defect 탐지뿐 아니라 change understanding, design rationale,
knowledge transfer가 review의 핵심 결과임을 보여준다. 따라서 각 migration PR은 한 selector 또는
한 vertical slice만 소유하고 다음을 설명한다.

- 어떤 quality scenario와 risk를 다루는가
- 어떤 contract가 유지되거나 의도적으로 바뀌는가
- 어떤 evidence가 pass/fail을 증명하는가
- rollback selector와 irreversible cleanup 시점은 무엇인가

### 2.5 CI/CD evidence와 provenance

NIST SP 800-204D의 artifact/provenance/policy-conformance 원칙을 적용한다. CI가 생기기 전에는
local 명령을 CI 완료로 부르지 않는다. CI 도입 후에는 source SHA, dependency lock, test result,
HTTP smoke, redaction 결과를 manifest로 묶고 required check가 같은 SHA를 검증해야 한다.

DORA의 small-batch/continuous-delivery 관점은 migration PR 크기와 feedback time에만 적용한다.
배포 빈도 자체를 목표로 삼거나 미검증 변경을 자동 운영 배포하지 않는다.

### 2.6 User-journey SLI/SLO와 error budget

Google SLO 자료는 user journey에서 측정할 신호를 먼저 고르고, SLO와 error budget으로 reliability
변경을 조정할 것을 권한다. CareGuide는 real HTTP가 아직 완결되지 않았으므로 지금 availability
SLO를 선언하지 않는다.

Phase 7에서 최소 2주 local/pilot baseline이 생긴 뒤 다음 후보를 결정한다.

- chat successful completion rate: `[DONE]`이 아니라 terminal success frame 기준
- emergency policy short-circuit rate와 false negative
- Mongo/Ollama 및 capability별 readiness
- Parlant customer/session/message completion latency
- outbox terminal-failed/backlog와 recovery time

### 2.7 Incident feedback와 recovery drill

NIST SP 800-61r3의 preparation → detect/respond/recover → lessons learned 순환을 로컬 운영에도
축소 적용한다. production incident 체계를 가장하지 않고 다음 drill부터 시작한다.

- Parlant child process failure → readiness degraded → cleanup → 재시도
- Mongo backup → 격리 DB restore → record/index 확인
- provider timeout → stable API/SSE error → unaffected capability smoke
- PII canary 발견 → evidence 격리 → 원인·재발 방지 action 기록

postmortem action은 owner, due condition, 검증 방법, close evidence가 없으면 완료 처리하지 않는다.

## 3. 초기 quality-attribute scenario

아래 수치는 ADR-013 승인 전 검토할 초기 target이다. baseline이 필요한 항목은 임의 목표 대신
`baseline required`로 둔다.

| ID | Source / stimulus / environment | Expected response | Measure | Gate |
|---|---|---|---|---|
| QA-SAF-01 | 인증 사용자가 어느 chat entrypoint에든 응급 문구 전송 / provider 상태 무관 | 단일 emergency policy가 119 안내 후 종료 | gold set false negative 0, model/Agent/provider call 0 | Phase 0 |
| QA-SEC-01 | User A가 User B의 room/session/health id 사용 | model·DB mutation 전에 403/404 | cross-user suite 100%, unauthorized writes 0 | Phase 0 |
| QA-PRIV-01 | token·email·건강정보 canary가 REST/SSE/provider failure 통과 | console/storage/log/artifact에 원문이 남지 않음 | canary occurrence 0 | Phase 0 |
| QA-COMP-01 | ClinicalTrials detail 요청 | 원문·충실한 번역·source·면책만 반환 | generated interpretation/recommendation 0, contract 100% | Phase 0 |
| QA-COMPAT-01 | SSE headers 후 provider 실패·취소·disconnect | terminal state와 transport 종료를 구분 | error+DONE 성공 승격 0, fixture contract 100% | Phase 2 |
| QA-MOD-01 | Chat 구현을 `legacy → hex` 전환 | wire contract 유지, 한 selector로 rollback | contract 100%, rollback drill pass, legacy-call telemetry 기록 | Phase 2 |
| QA-REL-01 | Research/Welfare process 중단 | 해당 capability만 degraded, false-ready 금지 | 200+schema+agent identity 전 ready=false, unaffected smoke 100%; RTO baseline required | Phase 1/4 |
| QA-DATA-01 | idempotent chat/outbox command 재전송 | 동일 logical effect 하나만 저장 | duplicate side effect 0, reconciliation pass | Phase 2/5 |
| QA-REC-01 | Mongo data loss 가정 후 격리 restore | backup에서 schema/index/대표 record 복구 | restore drill pass; RPO/RTO는 baseline 후 결정 | Phase 7 |
| QA-DEL-01 | PR head가 변경됨 | 동일 SHA의 required checks와 provenance artifact 재생성 | stale check 승인 0, required gate 100% | Phase 7 |

## 4. 현재 채택하지 않는 항목

| 항목 | 판정 | 이유 |
|---|---|---|
| Full formal ATAM | 보류 | 현재 팀에는 ATAM-lite가 충분하며 정식 평가 비용이 큼 |
| Microservices/service mesh | 제외 | 단일 bounded context와 local MVP에 불필요; NIST mesh 문서는 future reference |
| Cloud provider HA topology | 제외 | ADR-005가 production deployment를 범위 밖으로 둠 |
| 즉시 외부 availability SLO | 제외 | real HTTP baseline과 공개 운영 승인이 없음 |
| 대규모 platform engineering | 제외 | CI와 단일 runtime gate도 아직 없으므로 순서가 아님 |
| 모든 보안 도구 일괄 도입 | 제외 | P0 threat/API risks와 evidence chain부터 구축 |

## 5. 적용 근거

페이지는 ZIP 안 PDF의 물리 page 기준이며, source URL은 `SOURCE_MANIFEST.tsv`에서 가져왔다.

| 분야 | Source | 사용한 근거 |
|---|---|---|
| SDLC/architecture | [SWEBOK Guide V4](https://mpomianek.v.prz.edu.pl/download/5pQABQYFUjO0EmR25tQXlGFS5EQWhrR0MKWjQKBEdU%2CGKCVIaIhsaM0k2Vh03EBwSXgtITWswDU4KADoOTwMLAigAVVl1WxpyFGgT/swebok-v4.pdf) | architecture rationale·evaluation·technical debt, PDF pp. 73–77 |
| architecture | [SEI ATAM](https://www.sei.cmu.edu/documents/1186/1998_005_001_16646.pdf) | scenario→view→analysis→sensitivity/tradeoff, PDF pp. 17–19, 22–26 |
| architecture | [SEI Holistic Architecture](https://insights.sei.cmu.edu/documents/5720/2023_005_001_983542.pdf) | six-part measurable scenario, continuous governance/evaluation, PDF pp. 5, 11, 24–26 |
| secure SDLC | [NIST SP 800-218 SSDF 1.1](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf) | threat modeling, provenance, vulnerability feedback, PDF pp. 20–21 |
| security architecture | [NIST Architecture and Software Assurance](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=916027) | explicit security requirements, misuse/abuse cases, threat models, PDF pp. 5–8 |
| API protection | [NIST SP 800-228](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-228.pdf) | resource authorization, validation, inventory/runtime ownership, telemetry, PDF pp. 18, 21, 29–30, 38–39 |
| testing | [ISTQB CTFL 4.0.1](https://istqb.org/?download_id=3345&sdm_process_download=1) | test-basis traceability, pyramid, risk-based testing, PDF pp. 18, 50–51 |
| code review | [Microsoft Modern Code Review](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/ICSE202013-codereview.pdf?download=1) | change understanding, rationale, knowledge transfer, PDF pp. 1–2 |
| CI/CD security | [NIST SP 800-204D](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-204D.pdf) | artifact provenance, policy conformance, security testing, PDF pp. 18, 22, 24 |
| delivery | [DORA 2024](https://dora.dev/research/2024/dora-report/2024-dora-accelerate-state-of-devops-report.pdf) | small batches, continuous delivery, feedback, PDF pp. 40, 72 |
| reliability | [Google SLO Adoption and Usage](https://sre.google/static/pdf/SloAdoptionAndUsageInSre.pdf) | user-journey SLI, SLO, error budget, PDF pp. 9, 46, 57–60 |
| incident response | [NIST SP 800-61r3](https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-61r3.pdf) | preparation, continuous improvement, lessons learned, PDF pp. 10–14, 21 |
