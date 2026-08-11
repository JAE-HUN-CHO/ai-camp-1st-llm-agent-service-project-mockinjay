#!/usr/bin/env python3
"""
Papers Dataset Kidney Filtering Script
필터링 기준:
1. 키워드 매칭: title, abstract, keywords에서 신장 관련 용어 검색
2. Claude의 판단: 키워드가 없거나 애매한 경우 문맥 이해
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# 파일 경로
BASE_DIR = Path(__file__).parent.parent
TERMINOLOGY_FILE = BASE_DIR / "data/preprocess/kidney_terminology.json"
INPUT_FILE = BASE_DIR / "data/preprocess/unified_output/paper_dataset_enriched_s2_checkpoint_4850.jsonl"
OUTPUT_FILE = BASE_DIR / "data/preprocess/kidney_filtered/papers_kidney.jsonl"
PROGRESS_FILE = BASE_DIR / "data/preprocess/kidney_filtered/FILTERING_PROGRESS.md"

class KidneyTerminologyMatcher:
    """신장 용어 매칭 클래스"""

    def __init__(self, terminology_file: Path):
        """용어집 로드"""
        with open(terminology_file, 'r', encoding='utf-8') as f:
            self.terminology = json.load(f)

        # 핵심 신장 용어 (반드시 하나는 포함되어야 함)
        self.core_kidney_terms = {
            'kidney', 'kidneys', 'renal', 'nephro', 'nephrology', 'nephrologist',
            'nephron', 'glomerulus', 'glomeruli', 'glomerular',
            '신장', '콩팥', '사구체', '신장학'
        }

        # 고특이도 신장 용어 (이것만 있어도 신장 관련으로 판단)
        self.high_specificity_terms = {
            # 영어
            'dialysis', 'hemodialysis', 'haemodialysis', 'peritoneal dialysis',
            'nephrotic syndrome', 'nephritic syndrome', 'glomerulonephritis',
            'nephropathy', 'nephritis', 'nephrosis',
            'kidney transplant', 'kidney transplantation', 'renal transplant', 'renal transplantation',
            'acute kidney injury', 'chronic kidney disease', 'end-stage renal disease', 'renal failure',
            'proteinuria', 'albuminuria', 'hematuria',
            'IgA nephropathy', 'membranous nephropathy', 'focal segmental glomerulosclerosis',
            'diabetic nephropathy', 'diabetic kidney disease',
            'polycystic kidney disease', 'kidney stone', 'nephrolithiasis',
            'pyelonephritis', 'interstitial nephritis',
            'renal artery stenosis', 'hydronephrosis',
            'renal cell carcinoma', 'kidney cancer',
            # 약어
            'CKD', 'ESRD', 'ESKD', 'AKI', 'ARF', 'FSGS', 'CAPD', 'APD', 'CRRT',
            'PKD', 'ADPKD', 'RCC', 'GFR', 'eGFR',
            # 한국어
            '투석', '혈액투석', '복막투석', '신증후군', '신염증후군', '사구체신염',
            '신병증', '신염', '신이식', '신장이식', '콩팥이식',
            '급성신손상', '만성콩팥병', '말기신부전', '신부전',
            '단백뇨', '알부민뇨', '혈뇨',
            'IgA신병증', '막성신병증', '국소분절사구체경화증',
            '당뇨병성신병증', '당뇨콩팥병',
            '다낭콩팥병', '신결석', '신우신염', '간질신염',
            '신동맥협착', '수신증', '신세포암', '콩팥암'
        }

        # 일반 용어 (핵심 용어와 함께 있어야 의미 있음)
        self.general_terms = {
            'diabetes', 'diabetic', 'hypertension', 'cardiovascular',
            'anemia', 'edema', 'transplant', 'graft',
            '당뇨', '당뇨병', '고혈압', '심혈관', '빈혈', '부종', '이식'
        }

        # 모든 영어 용어를 소문자로 변환하여 세트로 저장
        self.english_terms = set(term.lower() for term in self.terminology.get('all_english_terms', []))

        # 모든 한국어 용어를 세트로 저장
        self.korean_terms = set(self.terminology.get('all_korean_terms', []))

        # 모든 약어를 대소문자 구분하여 세트로 저장
        self.abbreviations = set(self.terminology.get('all_abbreviations', []))

        print("✅ Loaded terminology:")
        print(f"   - Core kidney terms: {len(self.core_kidney_terms)}")
        print(f"   - High specificity terms: {len(self.high_specificity_terms)}")
        print(f"   - General terms: {len(self.general_terms)}")
        print(f"   - Total English terms: {len(self.english_terms)}")
        print(f"   - Total Korean terms: {len(self.korean_terms)}")
        print(f"   - Total Abbreviations: {len(self.abbreviations)}")

    def contains_kidney_term(self, text: str) -> Tuple[bool, List[str]]:
        """
        텍스트에 신장 관련 용어가 포함되어 있는지 확인

        Returns:
            (포함 여부, 매칭된 용어 리스트)
        """
        if not text:
            return False, []

        matched_terms = []
        text_lower = text.lower()

        # 1. 영어 용어 매칭 (부분 문자열 매칭)
        for term in self.english_terms:
            # 단어 경계를 고려한 정규식 패턴
            # 예: "kidney"는 매칭하지만 "kidneybean"은 매칭하지 않음
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                matched_terms.append(term)

        # 2. 한국어 용어 매칭 (정확한 매칭)
        for term in self.korean_terms:
            if term in text:
                matched_terms.append(term)

        # 3. 약어 매칭 (대소문자 구분, 단어 경계 고려)
        for abbr in self.abbreviations:
            pattern = r'\b' + re.escape(abbr) + r'\b'
            if re.search(pattern, text):
                matched_terms.append(abbr)

        return len(matched_terms) > 0, matched_terms

    def check_paper(self, paper: Dict) -> Tuple[bool, Dict]:
        """
        논문이 신장 관련인지 확인

        필터링 기준:
        1. 고특이도 용어가 있으면 무조건 포함
        2. 핵심 신장 용어가 있으면 포함
        3. 일반 용어만 있으면 제외

        Returns:
            (신장 관련 여부, 매칭 정보 딕셔너리)
        """
        match_info = {
            'title_match': False,
            'abstract_match': False,
            'keywords_match': False,
            'matched_terms': [],
            'has_core_term': False,
            'has_high_specificity_term': False,
            'has_general_term_only': False
        }

        # 전체 텍스트 결합 (title + abstract + keywords)
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        keywords = paper.get('metadata', {}).get('keywords', [])
        keywords_text = ' '.join(keywords) if keywords else ''

        full_text = f"{title} {abstract} {keywords_text}"
        full_text_lower = full_text.lower()

        # 매칭된 용어 수집
        matched_terms = []
        has_core = False
        has_high_spec = False
        has_general_only = False

        # 1. 고특이도 용어 확인
        for term in self.high_specificity_terms:
            term_lower = term.lower() if term.isascii() else term
            if term.isascii():
                # 영어: 단어 경계 고려
                pattern = r'\b' + re.escape(term_lower) + r'\b'
                if re.search(pattern, full_text_lower):
                    matched_terms.append(term)
                    has_high_spec = True
            else:
                # 한국어: 정확한 매칭
                if term in full_text:
                    matched_terms.append(term)
                    has_high_spec = True

        # 2. 핵심 신장 용어 확인
        for term in self.core_kidney_terms:
            term_lower = term.lower() if term.isascii() else term
            if term.isascii():
                pattern = r'\b' + re.escape(term_lower) + r'\b'
                if re.search(pattern, full_text_lower):
                    matched_terms.append(term)
                    has_core = True
            else:
                if term in full_text:
                    matched_terms.append(term)
                    has_core = True

        # 3. 일반 용어 확인 (진단용)
        general_matched = []
        for term in self.general_terms:
            term_lower = term.lower() if term.isascii() else term
            if term.isascii():
                pattern = r'\b' + re.escape(term_lower) + r'\b'
                if re.search(pattern, full_text_lower):
                    general_matched.append(term)
            else:
                if term in full_text:
                    general_matched.append(term)

        # 일반 용어만 있는 경우 체크
        if general_matched and not has_core and not has_high_spec:
            has_general_only = True

        # 매칭 정보 업데이트
        match_info['matched_terms'] = list(set(matched_terms))
        match_info['has_core_term'] = has_core
        match_info['has_high_specificity_term'] = has_high_spec
        match_info['has_general_term_only'] = has_general_only

        # Title, Abstract, Keywords 각각 확인 (정보용)
        if any(term.lower() in title.lower() or term in title for term in matched_terms):
            match_info['title_match'] = True
        if any(term.lower() in abstract.lower() or term in abstract for term in matched_terms):
            match_info['abstract_match'] = True
        if any(term.lower() in keywords_text.lower() or term in keywords_text for term in matched_terms):
            match_info['keywords_match'] = True

        # 최종 판단: 고특이도 용어가 있거나, 핵심 용어가 있으면 신장 관련
        is_kidney_related = has_high_spec or has_core

        return is_kidney_related, match_info


def filter_papers():
    """Papers 데이터셋 필터링 메인 함수"""

    print("=" * 80)
    print("Papers Dataset Kidney Filtering")
    print("=" * 80)
    print()

    # 용어집 로드
    print("📖 Loading terminology...")
    matcher = KidneyTerminologyMatcher(TERMINOLOGY_FILE)
    print()

    # 출력 파일 초기화
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 통계 변수
    total_count = 0
    filtered_count = 0
    excluded_count = 0

    # 필터링 진행
    print(f"🔍 Filtering papers from: {INPUT_FILE.name}")
    print(f"📝 Output file: {OUTPUT_FILE.name}")
    print()

    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            total_count += 1

            # 진행 상황 표시 (100개마다)
            if total_count % 100 == 0:
                print(f"Progress: {total_count} / 4,850 papers processed "
                      f"({total_count/4850*100:.1f}%) | "
                      f"Filtered: {filtered_count} ({filtered_count/total_count*100:.1f}%)")

            try:
                paper = json.loads(line.strip())

                # 신장 관련 여부 확인
                is_kidney_related, match_info = matcher.check_paper(paper)

                if is_kidney_related:
                    # 매칭 정보 추가
                    paper['_filtering_info'] = match_info

                    # 필터링된 논문 저장
                    outfile.write(json.dumps(paper, ensure_ascii=False) + '\n')
                    filtered_count += 1
                else:
                    excluded_count += 1

            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error at line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"⚠️  Error processing line {line_num}: {e}")
                continue

    print()
    print("=" * 80)
    print("✅ Filtering Complete!")
    print("=" * 80)
    print(f"Total papers processed: {total_count}")
    print(f"Kidney-related papers: {filtered_count} ({filtered_count/total_count*100:.1f}%)")
    print(f"Excluded papers: {excluded_count} ({excluded_count/total_count*100:.1f}%)")
    print()
    print(f"Output saved to: {OUTPUT_FILE}")
    print("=" * 80)

    return {
        'total': total_count,
        'filtered': filtered_count,
        'excluded': excluded_count
    }


if __name__ == "__main__":
    stats = filter_papers()
