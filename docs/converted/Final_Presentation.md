<!-- Slide number: 1 -->

	만성콩팥병(CDK) 환자와 연구자를 위한 RAG 기반 Multi-AI Agent 플랫폼 개발
Careguide Project | 2025. 12. 5 (금)
Team MockinJay
커널아카데미 | AI 심화캠프 1 기 바이오팀

### Notes:

<!-- Slide number: 2 -->

팀원 소개

![](GoogleShape40p5.jpg)

![](GoogleShape39p5.jpg)
- AI 챗봇 개발
- PubMed 논문 검색
- 대시보드  개발
- 기획 디자인 퍼블
- AI 챗봇 식이 영양
- 지식 콘텐츠 개발
조재훈
이윤주

![preencoded.png](GoogleShape29p5.jpg)

![preencoded.png](GoogleShape32p5.jpg)

![](GoogleShape42p5.jpg)

![](GoogleShape41p5.jpg)
- 커뮤니티 개발- 퀴즈 개발
- 팀장
- 공통 유틸 개발- 회원 모듈 개발
박철희
장준규

![preencoded.png](GoogleShape35p5.jpg)

![preencoded.png](GoogleShape38p5.jpg)

### Notes:

<!-- Slide number: 3 -->

기획 의도

![](GoogleShape54p6.jpg)

### Notes:

<!-- Slide number: 4 -->

프로젝트 개요

프로젝트 목표

핵심 기능
실제 만성콩팥병(CKD) 환자가 겪는 문제를 개선할 수 있는RAG 기반 멀티 에이전트 플랫폼 개발
AI 챗봇: Safety First 의료정보, 식단/영양 검색, PubMed 논문 RAG 분석, NutriCoach: 질환 단계별 맞춤형 식단 및 레시피 분석

![preencoded.png](GoogleShape65p7.jpg)

![preencoded.png](GoogleShape73p7.jpg)

활용 모델

운영 환경

![preencoded.png](GoogleShape75p7.jpg)

![preencoded.png](GoogleShape80p7.jpg)
GPT-5, GPT-5-mini, GPT-5-nano, GPT-4
FastAPI + React + Typescript + Parlant
기본 흐름

![기본 흐름도 (가로 직사각형 구조) 텍스트 입력 텍스트 관련 DB 검색 검색된 결과 바탕으로 AI 응답 생성](GoogleShape83p7.jpg)

### Notes:

<!-- Slide number: 5 -->

솔루션 요약

![](GoogleShape91p8.jpg)

### Notes:

<!-- Slide number: 6 -->

프로젝트 일정
2025.10.23 ~ 2025.12.04 (7주)
Week 6-7
Week 4
Week 1
Week 2-3
Week 5

1
2-3
4
5
6-7

FE 개발, 트렌드 페이지, 커뮤니티 퀴즈 에이전트 추가
데이터 수집 및 전처리
통합 테스트 & 발표 준비

BE : Multi-agent 개발 및 통합
기획
데이터 및 기능 기획
요구사항·페르소나 정의
사용 툴 및 기술 스택 정의, GitHub 연결

전체 기능 테스트, 버그 수정, 발표 자료 준비
BE: 멀티 에이전트(FastAPI) 개발 집중
Medical / Nutrition / Research / Quiz 에이전트 분리 및 정책 적용

FE: 챗봇, NutriCoach, 트렌드 페이지, 뉴스, 퀴즈 UI 구현
환자용/연구자용 화면 분리 및 사용자 여정 정리

공신력 있는 학회 가이드라인, PubMed, 질환 정보 수집
텍스트 요약·Q&A·식단/안전성 응답 프롬프트 설계
False Negative 체크리스트 기반 테스트 케이스 작성

일정 관리 포인트

![preencoded.png](GoogleShape102p9.jpg)
기본 기능 구현 우선
각자 맡은 에이전트 깃허브에 공유
팀원 간 슬랙, 노션 진행 상황 공유
일일 스크럼을 통해 진행 상황 및 To do 논의

### Notes:

<!-- Slide number: 7 -->

서비스 주요 기능

1순위
2순위
3순위

![preencoded.png](GoogleShape148p10.jpg)

![preencoded.png](GoogleShape158p10.jpg)

![preencoded.png](GoogleShape164p10.jpg)
AI 챗봇 에이전트
NutriCoach (영양 관리 에이전트)
의료복지 안내 에이전트
🔹 PubMed 논문 Hybrid Search
   (MongoDB + Pinecone)
🔹 의도 분류 기반 응답 생성
🔹 신뢰도 평가 및 출처 표시
🔹 컨텍스트 관리 (세션당 2만 토큰)
🔹 음식 이미지 분석 (GPT-4 Vision)
🔹 영양소 분석 (칼로리/단백질/나트륨/칼륨)
🔹 신장 질환 단계별 맞춤 식단 추천
🔹 대체 식품·조리법 추천 (저염/저칼륨 레시피)
🔹 의료비 지원 프로그램 검색
🔹 건강보험 관련 질의응답
🔹 프로필별 맞춤 복지 정보
🔹 신청 자격 및 절차 안내

커뮤니티

퀴즈 에이전트

트렌드 분석

![preencoded.png](GoogleShape169p10.jpg)

![preencoded.png](GoogleShape174p10.jpg)

![preencoded.png](GoogleShape179p10.jpg)
🔸 게시글 작성/조회/수정/삭제
🔸 임상시험 정보 조회
🔸 레벨 1~5 단계별 문제
🔸 난이도별 문제, 포인트 제도
🔸 논문 트렌드 시각화
🔸 연도별 키워드 통계

### Notes:

<!-- Slide number: 8 -->

사용자 흐름

![](GoogleShape186p11.jpg)

![preencoded.png](GoogleShape189p11.jpg)

![preencoded.png](GoogleShape190p11.jpg)

![preencoded.png](GoogleShape191p11.jpg)

### Notes:

<!-- Slide number: 9 -->

서비스 아키텍처

![](GoogleShape199p12.jpg)

### Notes:
Careguide 플랫폼의 전체적인 서비스 아키텍처에 대해 설명드리겠습니다. 저희는 의료진과의 정보 격차 문제와 같은 실제 만성콩팥병 환자가 겪는 문제를 개선하기 위해 RAG 기반의 Multi-AI Agent 플랫폼을 핵심으로 구축했습니다.

저희는 크게 AI 챗봇 에이전트인 리서치, 의료 복지와 영양 관리 에이전트와 연구 트렌드 요약 및 퀴즈 생성 등을 담당하는 별도의 에이전트를 만들었습니다. 이를 통해 사용자의 질문 의도에 따라 가장 적합한 전문 에이전트가 응답하도록 설계했습니다.

백엔드는 경량화되고 빠른 Fast AP를 사용했으며 프론트엔드는 사용자 친화적인 UI/UX를 위해 React와 Typescript를 활용했습니다. 기본적으로 에이전트는 GPT-4, GPT-5, GPT-5-mini 등 openai LLM 모델들을 적용했습니다. 의료 정보를 사용자에게 제공하고자 RAG를 이용해서 의료, 복지 및 영양 정보를 Mongo DB와 pinecone DB를 활용하였습니다.

<!-- Slide number: 10 -->

데이터 흐름도

사용자의 입력부터 결과 출력까지의 4단계 데이터 처리 흐름:

![preencoded.png](GoogleShape210p13.jpg)

![preencoded.png](GoogleShape215p13.jpg)

![preencoded.png](GoogleShape220p13.jpg)

![preencoded.png](GoogleShape225p13.jpg)

![preencoded.png](GoogleShape213p13.jpg)

![preencoded.png](GoogleShape218p13.jpg)

![preencoded.png](GoogleShape223p13.jpg)
1. 사용자 입력
2. Backend 요청
3. LLM API 호출
4. 결과 파싱 & 출력
LLM 응답 JSON 파싱
위험한 상황이면 상단에 경고 배너 + 의료진 상담 권고 고정 표기

질문, 식단 내용, 검사 수치, 논문 키워드 등 텍스트 입력
사용자 페르소나 유형(일반인/질환자/연구자) 기반으로 초기 컨텍스트 설정

선택된 에이전트가 프롬프트를 구성해 LLM API 호출
RAG: 관련 논문·자료·레시피를 검색 후, 컨텍스트와 함께 LLM에 전달
신뢰도 점수 계산 및 False Negative 체크

FastAPI 서버에서 의도 분류 + 안전성 필터 적용
의도에 따라 적절한 에이전트와 RAG 파이프라인 선택
예: “식단” → Nutrition Agent + 식단 DB
예: “논문” → Research Agent + PubMed API

출력 데이터 처리
입력 데이터 처리
• LLM API 응답 JSON 파싱
• 사용자가 업로드한 텍스트를 분석
• 응답 형식에 따라 UI 구성 요소 생성
• 문서 내용 추출 및 전처리
• 사용자 친화적 형태로 가공하여 표시
• Backend로 구조화된 데이터 전송

### Notes:
지금부터는 Careguide 플랫폼 내에서 사용자의 요청이 어떻게 처리되는지, 데이터 흐름도를 통해 자세히 설명드리겠습니다. 저희 시스템은 사용자의 입력부터 최종 결과 출력까지 총 4단계로 구성되어 있습니다.

사용자는 질문, 식단 내용, 검사 수치, 논문 키워드 등 다양한 텍스트를 입력합니다. 이때, 저희는 사용자의 페르소나 유형(일반인/질환자/연구자)을 기반으로 초기 컨텍스트를 설정하여 맞춤형 응답을 준비합니다. 입력된 데이터는 FastAPI 기반의 백엔드 서버로 전송됩니다. 여기서 가장 중요한 것은 의도 분류와 안전성 필터 적용입니다. 선택된 전문 에이전트가 프롬프트를 구성하여 LLM API를 호출하여 관련된 정보를 검색 후 답변합니다. JSON 형태로 파싱된 후 사용자에게 출력하고 상단에 경고 배너와 의료진 상담 권고 문구를 고정으로 표시합니다.

<!-- Slide number: 11 -->

데이터 흐름도

![](GoogleShape244p14.jpg)

### Notes:
다음과 같이 사용자가 챗봇에게 연구, 복지와 영양과 관련된 질문을 하게 됩니다.

<!-- Slide number: 12 -->

데이터 흐름도

![](GoogleShape252p15.jpg)

### Notes:
사용자가 입력한 질문을 바탕으로 알맞는 에이전트가 선택이 되게 됩니다. 리서치 에이전트는 pubmed api와 신장 학회의 가이드라인와 같은 데이터들을 바탕으로 key, semantic 두 가지를 결합한 하이브리드 검색을 통해 자료들을 선택해서 신뢰도 있는 답변을 하게 됩니다. 그리고 복지 에이전트의 경우 복지 프로그램들과 병원 위치 데이터를 기반으로 사용자의 질문에 맞는 답변을 드립니다. 영양 에이전트의 경우 텍스트 및 이미지 입력을 바탕으로 분석, 계산, 식단 추천과 리포트 제공하도록 기획했습니다.

<!-- Slide number: 13 -->

데이터 흐름도

![](GoogleShape260p16.jpg)

### Notes:
실제 서비스 런칭을 위해 안정적인 서비스 운영이 필요합니다. 이를 위해 세션 당 최대 컨텍스트, 시간 제한, 트래킹이 가능하도록 하는 세션 및 자원 관리 매니저를 설계를 하였습니다. 아직 이 부분은 완전히 적용이 되지는 않았지만 향후 추가할 기능입니다.

<!-- Slide number: 14 -->

주요 기능 시연 (1) - AI 챗봇 (Research Paper Agent)

![](GoogleShape268p17.jpg)

### Notes:
주요 기능을 시연하도록 하겠습니다. 첫 번째 기능은 리서치 페이퍼 에이전트 챗봇으로 연구 관련된 질문이나 의료 정보 관련 질문을 하게 되면 작동하는 에이전트입니다. ai hub, huggingface와 신장 학회에서 찾은 논문, 가이드라인, QA 데이터들로 구성된 mongodb와 pinecone verctor db로 검색을 하여 신뢰도 있는 답변을 하게됩니다. 중간 발표와 달라진 점은 기존에는 한 질문에 3 - 5 분 이후 답변을 하게 되었는데 프롬프트를 최적화해서 2 - 3 분 안에 답변이 가능하도록 해보았습니다. 또한, Parlant라는 오픈 소스 에이전트 패키지를 활용해서 구축했는데 데이터 검색과 사구열 투사체 계산 등 몇 가지 tool들이 있는데 pydantic missing error가 자주 나와서 이 로그를 확인 후 이를 방지해보았습니다.

<!-- Slide number: 15 -->

주요 기능 시연 (1) - AI 챗봇 (Nutrition Agent)

![](GoogleShape276p18.jpg)

![](GoogleShape277p18.jpg)

### Notes:

<!-- Slide number: 16 -->

주요 기능 시연 (1) - AI 챗봇 (Nutrition Agent)

![Nutrition agent developed in 2025](GoogleShape285p19.jpg)

### Notes:

<!-- Slide number: 17 -->

주요 기능 시연 (1) - AI 챗봇 (Medical Welfare Agent)

![](GoogleShape293p20.jpg)

### Notes:
다음은 복지 에이전트 ai 챗봇입니다. 복지 및 병원 관련 데이터베이스를 통해서 관련 답변을 하게 됩니다.

<!-- Slide number: 18 -->

주요 기능 시연 (3) 퀴즈

![](GoogleShape301p21.jpg)

![](GoogleShape302p21.jpg)

![](GoogleShape303p21.jpg)

![](GoogleShape304p21.jpg)

### Notes:
퀴즈 홈 화면, 퀴즈 시작, 퀴즈 모습, 완료 시 화면입니다. 퀴즈의 경우 qa와 관련 지식 데이터베이스들을 바탕으로 퀴즈 에이전트가 퀴즈를 만드는 기능이 구현이 되어 있습니다.

<!-- Slide number: 19 -->

주요 기능 시연 (4) 커뮤니티

![](GoogleShape312p22.jpg)

![](GoogleShape313p22.jpg)

![](GoogleShape314p22.jpg)

![](GoogleShape315p22.jpg)

### Notes:
커뮤니티의 경우에는 게시글을 작성할 수

<!-- Slide number: 20 -->

주요 기능 시연 (5) 트렌드

![](GoogleShape323p23.jpg)

### Notes:

<!-- Slide number: 21 -->

기대 효과

의료 안전성 및 신뢰도 확보

NutriCoach 기반 초개인화 식단 케어

![preencoded.png](GoogleShape334p24.jpg)

![preencoded.png](GoogleShape342p24.jpg)
False Negative 방지: 위험 증상(흉통, 호흡곤란 등) 감지 시 즉각적인 119 안내 및 답변 차단으로 의료 사고 예방.
검증된 정보 제공: 의도 분류(Safety Check)를 거친 신뢰도 높은 답변으로 환자의 불안감 해소 및 올바른 대처 유도

단계별 맞춤 영양 관리: 환자의 CKD 단계(투석/이식 여부)에 따라 칼륨, 인, 나트륨 등 제한 영양소를 고려한 최적의 레시피 추천.
실질적 삶의 질 개선: 복잡한 식단 고민을 덜어주고, '먹을 수 있는 즐거움'을 찾아주어 환자의 일상 만족도 증대.

복지 접근성 향상

연구 지원

![preencoded.png](GoogleShape344p24.jpg)

![preencoded.png](GoogleShape348p24.jpg)
최신 논문 트렌드 파악 용이 및 커뮤니티를 이용한 환자와의 직접 소통 가능케
복잡한 의료복지 제도 이해도 향상 및 개인 맞춤화 복지, 병원 정보 획득 가능

![preencoded.png](GoogleShape352p24.jpg)

Careguide를 통해 파편화 되어있던 병원, 의료 정보, 식단 영양 정보, 커뮤니티 및 퀴즈 등 필요한 모든 기능을 통합 제공하여 꾸준하게 건강한 일상을 지키게 도와주는 동반자로서 역할을 할 수 있습니다 .

### Notes:
다음은 Careguide 플랫폼을 통해 기대하는 효과에 대해 설명드리겠습니다. 저희 프로젝트는 크게 네 가지 핵심적인 기대 효과를 목표로 합니다.
첫째, 의료 안전성 및 신뢰도 확보입니다. 저희는 위험 증상, 예를 들어 흉통이나 호흡곤란 등이 감지될 경우 즉시 119 안내 및 답변을 차단하는 False Negative 방지 시스템을 통해 의료 사고를 예방하고자 합니다.
둘째, NutriCoach 기반의 초개인화 식단 케어입니다. NutriCoach는 환자의 만성콩팥병(CKD) 단계와 투석/이식 여부에 따라 칼륨, 인, 나트륨 등 제한해야 할 영양소를 고려한 최적의 맞춤형 레시피를 추천해 드립니다.
셋째, 복지 접근성 향상 및 연구 지원입니다. Careguide를 통해 복잡한 의료 복지 제도를 쉽게 이해하고, 개인 맞춤형 복지 및 병원 정보를 획득할 수 있습니다.

결론적으로 Careguide를 통해 파편화 되어있던 병원, 의료 정보, 식단 영양 정보, 커뮤니티 및 퀴즈 등 필요한 모든 기능을 통합 제공하여 만성 신장 환자과 보호자를 대상으로 건강한 일상을 지키게 도와주는 동반자로서 역할을 할 수 있습니다 .

<!-- Slide number: 22 -->

마무리

프로젝트 완성

![preencoded.png](GoogleShape364p25.jpg)
프로토타입 완성 (멀티 에이전트 챗봇, 영양 관리, 커뮤니티 및 트렌드)

![](GoogleShape370p25.jpg)

향후 발전 방향

![preencoded.png](GoogleShape368p25.jpg)

### Notes:
저희들이 6주 정도 되는 기간동안 멀티 에이전트 챗봇, 영양 관리, 커뮤니티 및 트렌드 기능이 구현된 프로토타입을 완성을 할 수 있었습니다.
향후 발전 방향으로는 크게 게이미피케이션, 캐릭터 추가, 디자인 개선, 개인화 추천 알고리즘 개선, 다국어 지원, 대화 히스토리 기반 컨텍스트 유지 및 개인 환자 기록을 바탕으로 개개인에 대해서 더 개선된 가이드가 있습니다.

<!-- Slide number: 23 -->

회고

![](GoogleShape390p26.jpg)

![](GoogleShape391p26.jpg)

공공데이터를 활용한 기획, 디자인, 퍼블리싱, 개발 일련의 과정 전체에 AI툴을 사용해 개발을 하고 결과물을 만들어 보고자 하였습니다. 기존에는 기획, 디자인, 퍼블리싱, 개발에 항상 많은 공수가 들어서 몇억의 비용을 필요로 했었는데 여러 AI 툴들을 사용해보니 작업의  50%는  AI 툴로 단축할 수 있었습니다.
AI api 연동은 쉬워도 필요한 대량의 데이터를 수집, 처리하고 이미지 학습하여 성능을 내는 부분은 계속 보완해 나가고자 합니다.

공익적으로 사회적 가치를 주는 서비스를 개발해 보고 싶었는데 이번 기회에 좋은 팀원들과 작업하게 되어 감사드립니다.

짧은 기간이었지만 팀원들과 협업하여 하나의 프로젝트를 완성해 가는 과정은 매우 의미 있는 경험이었습니다. 프로젝트를 진행하면서 각자가 새롭게 배운 점들이 향후에도 활용되기를 바랍니다.
기획부터 개발, 데이터 준비까지 여러 작업을 함께 수행하며 실제 신장 질환 환자를 위한 챗봇 및 서비스 구축을 시도해 본 점도 큰 보람이 있었습니다. 시간적 제약으로 실제 상용화까지 이어가지는 못했지만, AI뿐 아니라 백엔드·프런트엔드 등 다양한 요소들을 폭넓게 이해해야 한다는 점을 체감했고, 이를 기반으로 관련 개발 역량을 꾸준히 확장해 나갈 계획입니다.
조재훈
이윤주

바이브 코딩의 시작을 패캠에서 하게 되어서 좋았습니다. 팀원 모두가 너무 열정적이어서 보기 좋았습니다.

 바이브코딩 시 컨트롤 할 수 있는 부분이 제한적이어서 프로그램 입문하는 사람에게 효율적인 팀 협업이 쉽지 않았습니다. 저희 팀을 제외하고 모든 팀들이 1인 플젝을 하는 이유를 극복하고 싶었지만 바이브 코딩의 힘은 그마저 넘어서는 파워가 있는 거 같습니다.

끝까지 열심히 해 준 팀원분들께 감사합니다  :)

![](GoogleShape392p26.jpg)

![](GoogleShape393p26.jpg)
좋은 팀원분들을 만나 제가 많이 배울 수 있었던 것 같습니다. 동시에 협업에 있어서 성실하지 못한 점에 대해 너무 죄송한 마음이 듭니다. 이번 과정에서 배웠던 내용을 바탕으로 더 열심히 공부하여, 부족한 부분을 보완하고 싶습니다.

박철희
장준규

### Notes:
