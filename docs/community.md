
게이미피케이션 - 레벨 시스템1. 레벨 체계 및 승급 조건레벨 레벨명 아이콘 필요 XP 누적 XP 승급 조건 일일 퀴즈 주요 혜택 개발 시 체크사항우선순위
Lv.1 초보자 🌱 0 0 가입 즉시 3개 기본 기능만 사용 DB: level=1, xp=0P1
Lv.2 배움이 🐣 100 100 퀴즈 10개 정답 5개 커뮤니티 좋아요 해제XP 100 달성 시 레벨업 트리거 P3
Lv.3 지식인 📘 300 400 퀴즈 30개 + 글 5개 무제한 Q&A 질문, 레벨 뱃지 표시XP 400 + 활동 조건 체크 P3
Lv.4 전문가 🎓 600 1000 퀴즈 60개 + 논문검색 10회 무제한 PubMed 50개, 월간 랭킹XP 1000 + 논문검색 카운트P3
Lv.5 마스터 1000 2000 퀴즈 100개 + 챌린지 5회무제한 프리미엄 7일 무료, 답변 상단 고정 XP 2000 + 챌린지 완료 체크P4
2. 경험치(XP) 획득 방법활동명 획득 XP 일일 제한 일일 최대 XP API 엔드포인트 예시 트리거 조건 개발 시 체크사항 우선순위
퀴즈 정답 +10 XP 무제한 무제한 /api/quiz/answer정답 제출 성공 quiz_answer 이벤트 시 XP 적립 P3
연속 정답 (3개↑) +5 XP 보너스 +5 - 연속 3개 정답 Redis로 연속 카운트 관리 P3커뮤니티 글 작성 +20 XP 무제한 무제한 /api/community/post글 작성 완료 post_created 이벤트 P3댓글 작성 +5 XP 무제한 무제한 /api/community/comment댓글 작성 완료 comment_created 이벤트 P3챌린지 완료 +50 XP 챌린지당 1회 제한 /api/challenge/complete챌린지 목표 달성 challenge_completed 체크 P3논문 검색 +15 XP 무제한 무제한 /api/pubmed/search검색 결과 반환 search_completed 이벤트 P37일 연속 접속 +100 XP 주1회 +100 - 7일 연속 로그인 login_streak 체크 P3
3. 온보딩 - 1분 퀴즈단계 화면 액션 결과 API 프론트엔드 구현 백엔드 구현 우선순위1 회원가입 완료메인 화면 진입 - - 회원가입 후 리다이렉트signup_complete 체크 P3
2 1분 퀴즈 배너팝업 표시 민트색 배너 (#00D4AA)- Modal/Banner 컴포넌트first_login 플래그 확인 P3
3 퀴즈 시작 [지금 시작하기] 버튼퀴즈 화면 전환/api/quiz/onboardingButton onClick 5문제 랜덤 출제 P3
4 5문제 출제 각 12초 제한, 난이도 혼합 답변 제출 /api/quiz/submitTimer 컴포넌트 정답 체크 + 점수 계산 P3
5 결과 표시 정답 개수 → 레벨 배정레벨 애니메이션/api/user/level/initConfetti 효과 레벨 자동 배정 (0~1: Lv.1, 2~3: Lv.2, 4~5: Lv.3) P3
스킵 나중에 버튼기본 레벨 Lv.1 프로필에 재측정 버튼 - Skip 버튼 level=1 기본값 설정 P3
게이미피케이션 - 포인트 시스템1. 포인트 적립 규칙 (⚠ 플랫폼 인터렉션 필수)활동명 적립 포인트 일일 제한 일일 최대 API 엔드포인트 트리거 조건 개발 시 체크사항 비고 우선순위퀴즈 정답 +10P 무제한 무제한/api/point/earnquiz_answer_correct정답 시에만 적립 학습 동기 부여 P3연속 정답 3개↑ +5P 1일 1회 +5P /api/point/earnconsecutive_3_correctRedis 연속 카운트 보너스 P3식사 기록 +5P 1일 3회 +15P /api/point/earnmeal_recorded 사진/텍스트 입력 완료 NutriCoach P3커뮤니티 글 +20P 1일 5회 +100P /api/point/earnpost_created 글 작성 완료 커뮤니티 활성화 P3커뮤니티 댓글 +5P 1일 10회 +50P /api/point/earncomment_created댓글 작성 완료 참여 유도 P3챌린지 완료 +100P 챌린지당 1회 제한 /api/point/earnchallenge_completed목표 달성 체크 건강 챌린지 P3논문 검색 +10P 1일 5회 +50P /api/point/earnpubmed_search검색 결과 반환 PubMed P3논문 북마크 +5P 무제한 무제한/api/point/earnpaper_bookmarked북마크 저장 완료 관심 논문 P37일 연속 접속 +200P 주1회 +200P /api/point/earnlogin_streak_7 login_streak 체크 재방문 유도 P3친구 초대 +500P 무제한 무제한/api/point/earnreferral_signup초대 가입 완료 바이럴 P4첫 프리미엄 결제 +1000P 1회 +1000P/api/point/earnfirst_premium_purchase결제 완료 후 지급 첫 구매 보너스 P4
2. 포인트 사용처항목 필요 포인트 효과/혜택 API 엔드포인트 처리 로직 개발 시 체크사항 비고 우선순위

프리미엄 1일권 100P 논문 심화 검색 1일/api/premium/purchase/point 포인트 차감 → 프리미엄 활성화 (24시간) 포인트 부족 시 에러 핵심 사용처 P3
프리미엄 7일권 500P 논문 심화 검색 7일 (약 30% 할인) /api/premium/purchase/point 포인트 차감 → 프리미엄 활성화 (7일) 할인율 표시 추천 P3
프리미엄 30일권 1500P 논문 심화 검색 30일 (약 50% 할인) /api/premium/purchase/point 포인트 차감 → 프리미엄 활성화 (30일) 할인율 표시 가장 효율적 P3
닉네임 변경 50P 닉네임 1회 변경/api/user/nickname/change 중복 체크 → 포인트 차감 → 닉네임 변경 중복 검증 기타 P4
프로필 테마 100P 프로필 배경/색상 변경 /api/user/theme/change포인트 차감 → 테마 적용 테마 리스트 관리 기타 P4
게시글 상단 고정 200P 24시간 상단 고정/api/community/pin포인트 차감 → 24시간 후 자동 해제 스케줄러 필요 기타 P4
특별 아이콘 300P 프로필 전용 아이콘/api/user/icon/purchase포인트 차감 → 아이콘 활성화아이콘 리스트 기타 P4
3. 포인트 유효기간 정책포인트 유형 유효기간 정책 알림 개발 시 체크사항 우선순위
활동 적립 포인트1년 적립일로부터 1년간 유효 만료 30일 전 푸시 알림 DB: earned_at, expires_at 필드 관리 P3
결제 적립 포인트영구 유효기간 없음 (영구 보존) - DB: is_permanent = true 플래그 P4
사용 시 차감 순서- FIFO (먼저 소멸되는 포인트부터 자동 차감) - ORDER BY expires_at ASC 쿼리 P3
4. 적립 불가 활동 (🚫 개발 시 필터링 필요)불가 활동 이유 개발 시 체크사항
단순 로그인만인터렉션 없음login_only 플래그 체크, 최소 1개 액션 필요
동일 글 반복 조회스팸 방지 view_count > 3 → 포인트 지급 차단부정 행위 (봇/매크로) 어뷰징 방지IP/디바이스 체크, 짧은 시간 반복 액션 탐지
게이미피케이션 - 프리미엄 전환 시스템1. 프리미엄 기능 (Premium Only)기능 무료 프리미엄 API 체크 개발 시 체크사항 우선순위PubMed 검색 결과 20개 100개 user.is_premiumDB 쿼리 LIMIT 분기 P2RAG 분석 횟수 1일 3회 무제한user.rag_count < 3Redis 카운터 체크 P2
논문 전문 번역 불가 AI 번역 (영→한) user.is_premium번역 API 호출 (DeepL/Papago) P3
논문 요약 길이 300자 1000자 user.is_premiumLLM max_length 파라미터 P2
키워드 알림 불가 신규 논문 푸시user.is_premium크론잡 + FCM 푸시 P4논문 비교 분석 불가 최대 5개 동시user.is_premium멀티 논문 RAG P4인용 네트워크불가 인용 관계 시각화user.is_premiumD3.js/Cytoscape.js P4
2. 프리미엄 구매 방법플랜 포인트 가격 현금 가격 1일당 비용 API 처리 로직 보너스 우선순위
1일권 100P 990원 100P / 990원 /api/premium/purchase포인트 차감 OR PG 결제 → premium_until 설정 - P3
7일권 500P 4,900원 71P / 700원 /api/premium/purchase포인트 차감 OR PG 결제 → premium_until 설정 약 30% 할인 P3
30일권 1500P 14,900원 50P / 497원 /api/premium/purchase포인트 차감 OR PG 결제 → premium_until 설정 약 50% 할인 (추천) P3

1년권 - 149,000원 408원 /api/premium/purchasePG 결제만 가능 → premium_until 설정 약 50% 할인 P4
3. 전환 전략 (개발 시 UI/UX 반영)전략 타이밍 UI 메시지개발 시 체크사항우선순위
포인트 부족 팝업프리미엄 구매 시도 시 포인트 부족
"50P 부족해요! 990원에 1일권 구매하시겠어요?"
포인트 체크 → 모달 표시 → 결제 유도 P3
검색 제한 알림무료 사용자 PubMed 검색 20개 도달
"검색 결과가 더 있어요! 프리미엄으로 100개 확인하기"
search_count == 20 → 배너 표시 P2
RAG 제한 알림무료 사용자 RAG 분석 3회 소진
"오늘 분석 횟수를 모두 사용했어요. 내일 다시 만나요!"
rag_count == 3 → 알림 + 프리미엄 CTA P2
첫 구매 보너스첫 결제 완료 시"첫 구매 감사합니다! 1000P 보너스 지급 🎉"first_purchase == true → 포인트 지급 P4
무료 체험 쿠폰이메일 인증 완료 시 "7일 무료 체험 쿠폰이 발급되었어요!" email_verified == true → 쿠폰 지급 P4
DB 스키마 참고 (개발자용)users 테이블컬럼명 타입 설명 기본값 비고id BIGINT 사용자 PK AUTO_INCREMENTPRIMARY KEYlevel INT 현재 레벨 (1~5) 1 NOT NULLxp INT 경험치 0 NOT NULLpoints INT 보유 포인트 0 NOT NULLis_premiumBOOLEAN프리미엄 여부 false NOT NULLpremium_untilDATETIME프리미엄 만료일NULL NULL 가능login_streakINT 연속 접속 일수 0 NOT NULLlast_login_dateDATE 마지막 로그인 날짜NULL NULL 가능first_purchaseBOOLEAN첫 구매 여부 false 보너스 지급 플래그
point_history 테이블컬럼명 타입 설명 기본값 비고id BIGINT 이력 PK AUTO_INCREMENTPRIMARY KEYuser_id BIGINT 사용자 FK NOT NULLFOREIGN KEY → users(id)amount INT 포인트 증감량NOT NULL양수: 적립, 음수: 차감
type VARCHAR(50)적립/사용 타입 NOT NULLENUM: quiz, post, premium 등earned_atDATETIME적립일시 NOW() NOT NULLexpires_atDATETIME만료일시 earned_at + 1년 활동 포인트만is_permanentBOOLEAN영구 포인트 여부false 결제 포인트는 truedescriptionTEXT 설명 NULL 사용 내역 표시용
xp_history 테이블컬럼명 타입 설명 기본값 비고id BIGINT 이력 PK AUTO_INCREMENTPRIMARY KEYuser_id BIGINT 사용자 FK NOT NULLFOREIGN KEY → users(id)amount INT XP 증가량 NOT NULL항상 양수
activity VARCHAR(50)활동 타입 NOT NULLENUM: quiz, post, comment 등created_atDATETIME획득일시 NOW() NOT NULL

박철희 아이디어 추가목적 환자의 건강한 습관 형성에 도움
방식 연속 식단/학습 일수 계산 + 리그제 운영- 만성질환이므로, 꾸준히 건강하게 식단이나 학습해온 걸 자랑으로 여길 수 있도록, 사용자의 건전한 경쟁 유도
레퍼런스 듀오링고 모델 (가능하다면 수익화 모델도 모방)
사용자 경험 환대 받는 느낌 추가 / 귀여운 캐릭터 2개 이상 반겨주기(ex 콩콩이 팥팥이
포인트 / 보상마스터(최고레벨) 달성 시 한국신장학회에 가입 특별회원 기회 부여, 
한국신장학회 연회원 회비 80프로 할인 (10만원 -> 2만원) 
-> e-learning platform 이용 등 학회원들만의 혜택을 환자들도 누릴 수 있도록

