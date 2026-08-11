#!/usr/bin/env python3
"""
QA Dataset Kidney Filtering Script
필터링 기준: Papers와 동일한 강화된 필터링 로직 사용
특별 처리: source_dataset가 "대한신장학회"인 경우 자동 포함
"""

import json
import re
from pathlib import Path
from typing import Dict, Tuple

# 파일 경로
BASE_DIR = Path(__file__).parent.parent
TERMINOLOGY_FILE = BASE_DIR / "data/preprocess/kidney_terminology.json"
INPUT_FILE = BASE_DIR / "data/preprocess/unified_output/qa_enhanced.jsonl"
OUTPUT_FILE = BASE_DIR / "data/preprocess/kidney_filtered/qa_kidney.jsonl"

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

        # 신장 관련 source_dataset
        self.kidney_sources = {
            '대한신장학회'
        }

        # 신장 관련 카테고리 키워드
        self.kidney_category_keywords = {
            '콩팥', '신장', '투석', '신부전', '신증후군'
        }

        print("✅ Loaded terminology:")
        print(f"   - Core kidney terms: {len(self.core_kidney_terms)}")
        print(f"   - High specificity terms: {len(self.high_specificity_terms)}")
        print(f"   - Kidney sources: {len(self.kidney_sources)}")
        print(f"   - Kidney category keywords: {len(self.kidney_category_keywords)}")

    def check_qa_data(self, data: Dict) -> Tuple[bool, Dict]:
        """
        QA 데이터가 신장 관련인지 확인

        필터링 기준:
        1. source_dataset가 대한신장학회면 자동 포함
        2. category에 신장 관련 키워드가 있으면 자동 포함
        3. 고특이도 용어가 있으면 포함
        4. 핵심 신장 용어가 있으면 포함

        Returns:
            (신장 관련 여부, 매칭 정보 딕셔너리)
        """
        match_info = {
            'question_match': False,
            'answer_match': False,
            'category_match': False,
            'source_match': False,
            'matched_terms': [],
            'has_core_term': False,
            'has_high_specificity_term': False,
            'auto_included_by_source': False,
            'auto_included_by_category': False
        }

        # 1. Source dataset 확인
        source_dataset = data.get('source_dataset', '')
        if source_dataset in self.kidney_sources:
            match_info['auto_included_by_source'] = True
            match_info['source_match'] = True
            match_info['matched_terms'].append(f'[source:{source_dataset}]')
            return True, match_info

        # 2. Category 확인
        category = data.get('category', '')
        for keyword in self.kidney_category_keywords:
            if keyword in category:
                match_info['auto_included_by_category'] = True
                match_info['category_match'] = True
                match_info['matched_terms'].append(f'[category:{keyword}]')
                return True, match_info

        # 3. 질문과 답변 텍스트 확인
        question = data.get('question', '')
        answer = data.get('answer', '')

        full_text = f"{question} {answer}"
        full_text_lower = full_text.lower()

        # 매칭된 용어 수집
        matched_terms = []
        has_core = False
        has_high_spec = False

        # 고특이도 용어 확인
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

        # 핵심 신장 용어 확인
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

        # 매칭 정보 업데이트
        match_info['matched_terms'] = list(set(matched_terms))
        match_info['has_core_term'] = has_core
        match_info['has_high_specificity_term'] = has_high_spec

        # Question, Answer 각각 확인 (정보용)
        if any(term.lower() in question.lower() or term in question for term in matched_terms):
            match_info['question_match'] = True
        if any(term.lower() in answer.lower() or term in answer for term in matched_terms):
            match_info['answer_match'] = True

        # 최종 판단: 고특이도 용어가 있거나, 핵심 용어가 있으면 신장 관련
        is_kidney_related = has_high_spec or has_core

        return is_kidney_related, match_info


def filter_qa_data():
    """QA 데이터셋 필터링 메인 함수"""

    print("=" * 80)
    print("QA Dataset Kidney Filtering")
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
    auto_included_by_source = 0
    auto_included_by_category = 0

    # 필터링 진행
    print(f"🔍 Filtering QA data from: {INPUT_FILE.name}")
    print(f"📝 Output file: {OUTPUT_FILE.name}")
    print("⚠️  WARNING: This will process 2,224,451 QA pairs. Expected time: ~10-15 hours")
    print()

    with open(INPUT_FILE, 'r', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            total_count += 1

            # 진행 상황 표시 (10000개마다)
            if total_count % 10000 == 0:
                print(f"Progress: {total_count:,} / 2,224,451 QA pairs processed "
                      f"({total_count/2224451*100:.1f}%) | "
                      f"Filtered: {filtered_count:,} ({filtered_count/total_count*100:.1f}%) | "
                      f"Auto-source: {auto_included_by_source:,} | "
                      f"Auto-category: {auto_included_by_category:,}")

            try:
                data = json.loads(line.strip())

                # 신장 관련 여부 확인
                is_kidney_related, match_info = matcher.check_qa_data(data)

                if is_kidney_related:
                    # 통계 업데이트
                    if match_info['auto_included_by_source']:
                        auto_included_by_source += 1
                    if match_info['auto_included_by_category']:
                        auto_included_by_category += 1

                    # 매칭 정보 추가
                    data['_filtering_info'] = match_info

                    # 필터링된 데이터 저장
                    outfile.write(json.dumps(data, ensure_ascii=False) + '\n')
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
    print(f"Total QA pairs processed: {total_count:,}")
    print(f"Kidney-related QA pairs: {filtered_count:,} ({filtered_count/total_count*100:.1f}%)")
    print(f"  - Auto-included by source (대한신장학회): {auto_included_by_source:,}")
    print(f"  - Auto-included by category: {auto_included_by_category:,}")
    print(f"  - Included by term matching: {filtered_count - auto_included_by_source - auto_included_by_category:,}")
    print(f"Excluded QA pairs: {excluded_count:,} ({excluded_count/total_count*100:.1f}%)")
    print()
    print(f"Output saved to: {OUTPUT_FILE}")
    print("=" * 80)

    return {
        'total': total_count,
        'filtered': filtered_count,
        'excluded': excluded_count,
        'auto_source': auto_included_by_source,
        'auto_category': auto_included_by_category
    }


if __name__ == "__main__":
    stats = filter_qa_data()
