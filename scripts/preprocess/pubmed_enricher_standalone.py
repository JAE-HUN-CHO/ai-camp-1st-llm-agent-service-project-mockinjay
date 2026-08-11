"""
PubMed + Semantic Scholar API를 사용한 논문 메타데이터 보완 스크립트

주요 특징:
- 1차: PubMed에서 제목 완전 일치 검색 (점진적: 5개 → 10개 → 25개)
- 2차: Semantic Scholar API로 제목 완전 일치 검색 (최대 10개)
- 대소문자 및 공백 차이 무시
- 429 오류 자동 재시도 (지수 백오프)
- 두 API 모두 완전 일치만 허용 (유사도 기반 매칭 제거)

Semantic Scholar API 문서:
https://api.semanticscholar.org/api-docs/

사용 방법:
    python pubmed_with_semantic_scholar.py --max 100 --email your@email.com --s2-api-key YOUR_KEY
"""

import json
import time
import argparse
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random
from difflib import SequenceMatcher


class SemanticScholarPubMedEnricher:
    """PubMed + Semantic Scholar API 하이브리드 메타데이터 보완 클래스"""
    
    PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, email: str = "user@example.com", 
                 pubmed_api_key: Optional[str] = None,
                 s2_api_key: Optional[str] = None,
                 delay: float = 0.5, 
                 similarity_threshold: float = 0.85):
        """
        초기화
        
        Args:
            email: NCBI 이메일
            pubmed_api_key: NCBI API 키
            s2_api_key: Semantic Scholar API 키 (선택, 있으면 rate limit 증가)
            delay: 기본 대기 시간 (초)
            similarity_threshold: 제목 유사도 임계값 (0.0-1.0)
        """
        self.email = email
        self.pubmed_api_key = pubmed_api_key
        self.s2_api_key = s2_api_key
        self.delay = delay
        self.similarity_threshold = similarity_threshold
        self.max_retries = 5
        
        # S2 API 헤더
        self.s2_headers = {}
        if s2_api_key:
            self.s2_headers['x-api-key'] = s2_api_key
        
        self.stats = {
            'total': 0,
            'processed': 0,
            'pubmed_searched': 0,
            'pubmed_found': 0,
            's2_searched': 0,
            's2_found': 0,
            's2_low_similarity': 0,
            'not_found': 0,
            'already_complete': 0,
            'errors': 0,
            'rate_limit_hits': 0,
            'title_mismatch_rejected': 0,
        }
    
    @staticmethod
    def calculate_title_similarity(title1: str, title2: str) -> float:
        """두 제목 간의 유사도 계산 (0.0 ~ 1.0)"""
        norm1 = SemanticScholarPubMedEnricher.normalize_title(title1)
        norm2 = SemanticScholarPubMedEnricher.normalize_title(title2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    @staticmethod
    def titles_match(title1: str, title2: str) -> bool:
        """두 제목이 동일한지 확인 (대소문자 및 공백 무시)"""
        norm1 = SemanticScholarPubMedEnricher.normalize_title(title1)
        norm2 = SemanticScholarPubMedEnricher.normalize_title(title2)
        return norm1 == norm2
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """제목 정규화 (비교용)"""
        normalized = title.lower()
        for char in ['[', ']', '(', ')', ':', '?', '.', ',', ';', '!', '"', "'", '-']:
            normalized = normalized.replace(char, ' ')
        normalized = ' '.join(normalized.split())
        return normalized.strip()
    
    def _wait_with_backoff(self, attempt: int = 0):
        """지수 백오프로 대기"""
        if attempt == 0:
            wait_time = self.delay
        else:
            wait_time = min(2 ** attempt, 30)
            wait_time += random.uniform(0, 1)
        
        if attempt > 0:
            print(f"      ⏳ {wait_time:.1f}초 대기 중... (재시도 {attempt}/{self.max_retries})")
        
        time.sleep(wait_time)
    
    # ==================== PubMed 관련 메서드 ====================
    
    def search_pubmed(self, query: str, max_results: int = 25) -> List[str]:
        """PubMed 검색"""
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'email': self.email
        }
        
        if self.pubmed_api_key:
            params['api_key'] = self.pubmed_api_key
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._wait_with_backoff(attempt)
                
                response = requests.get(f"{self.PUBMED_BASE_URL}esearch.fcgi", 
                                       params=params, timeout=15)
                
                if response.status_code == 429:
                    self.stats['rate_limit_hits'] += 1
                    print("      ⚠️ PubMed API 호출 제한 (429) - 재시도 중...")
                    continue
                
                response.raise_for_status()
                data = response.json()
                pmids = data.get('esearchresult', {}).get('idlist', [])
                return pmids
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"      ❌ PubMed 검색 실패: {str(e)[:80]}")
                    return []
        
        return []
    
    def fetch_article_metadata(self, pmid: str) -> Optional[Dict]:
        """PubMed 메타데이터 가져오기"""
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml',
            'email': self.email
        }
        
        if self.pubmed_api_key:
            params['api_key'] = self.pubmed_api_key
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._wait_with_backoff(attempt)
                
                response = requests.get(f"{self.PUBMED_BASE_URL}efetch.fcgi", 
                                       params=params, timeout=15)
                
                if response.status_code == 429:
                    self.stats['rate_limit_hits'] += 1
                    print("      ⚠️ API 호출 제한 (429) - 재시도 중...")
                    continue
                
                response.raise_for_status()
                root = ET.fromstring(response.content)
                article_elem = root.find('.//PubmedArticle')
                
                if article_elem is None:
                    return None
                
                return self._parse_article_xml(article_elem)
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"      ❌ 메타데이터 가져오기 실패: {str(e)[:80]}")
                    return None
        
        return None
    
    def _parse_article_xml(self, article_elem) -> Optional[Dict]:
        """XML에서 메타데이터 파싱"""
        try:
            medline_citation = article_elem.find('.//MedlineCitation')
            article = medline_citation.find('.//Article')
            
            # 제목
            title_elem = article.find('.//ArticleTitle')
            title = ''.join(title_elem.itertext()) if title_elem is not None else ''
            
            # 저자
            authors = []
            for author_elem in article.findall('.//Author'):
                last_name = author_elem.findtext('LastName', '')
                fore_name = author_elem.findtext('ForeName', '')
                if last_name or fore_name:
                    authors.append(f"{fore_name} {last_name}".strip())
            
            # 저널
            journal_elem = article.find('.//Journal')
            journal = journal_elem.findtext('.//Title', '') if journal_elem is not None else ''
            
            # 출판일
            pub_date_elem = article.find('.//PubDate')
            publication_date = self._parse_pub_date(pub_date_elem)
            
            # DOI
            doi = ''
            for article_id in article_elem.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break
            
            # 키워드
            keywords = []
            for keyword_elem in medline_citation.findall('.//Keyword'):
                keyword = keyword_elem.text
                if keyword:
                    keywords.append(keyword)
            
            # MeSH 용어 추가
            mesh_count = 0
            for mesh_elem in medline_citation.findall('.//MeshHeading/DescriptorName'):
                if mesh_count >= 5:
                    break
                mesh_term = mesh_elem.text
                if mesh_term and mesh_term not in keywords:
                    keywords.append(mesh_term)
                    mesh_count += 1
            
            metadata = {
                'title': title,
                'keywords': keywords,
                'journal': journal,
                'authors': authors,
                'doi': doi,
                'publication_date': publication_date,
                'source': 'pubmed'
            }
            
            return metadata
            
        except Exception as e:
            print(f"      ⚠️ XML 파싱 오류: {e}")
            return None
    
    def _parse_pub_date(self, pub_date_elem) -> str:
        """출판일 파싱"""
        if pub_date_elem is None:
            return ''
        
        year = pub_date_elem.findtext('Year', '')
        month = pub_date_elem.findtext('Month', '01')
        day = pub_date_elem.findtext('Day', '01')
        
        month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        
        if month in month_map:
            month = month_map[month]
        elif not month.isdigit():
            month = '01'
        
        try:
            month = str(month).zfill(2)
            day = str(day).zfill(2)
            return f"{year}.{month}.{day}"
        except (TypeError, ValueError, AttributeError):
            return year if year else ''
    
    @staticmethod
    def prepare_search_query(title: str) -> str:
        """제목을 PubMed 검색 쿼리로 변환"""
        clean_title = title.replace('[', '').replace(']', '')
        query = f'{clean_title.lower()[:-1]}'
        return query
    
    def find_exact_match_progressive(self, original_title: str) -> Optional[Tuple[str, Dict]]:
        """
        점진적으로 검색 범위를 늘려가며 PubMed에서 완전 일치 찾기
        """
        query = self.prepare_search_query(original_title)
        print(f"      🔍 PubMed 검색: {original_title[:50]}...")
        
        queries = [f'"{query}[Title]"'] # + [f'"{query[:i]}[Title]"' for i in range(5, len(query), len(query)//5)]

        for query_variant in queries:
            search_limits = [50]
            
            for limit in search_limits:
                pmids = self.search_pubmed(query_variant, max_results=limit)
                
                if not pmids:
                    continue
                
                print(f"      🔎 {len(pmids)}개 후보 발견, 제목 완전 일치 확인 중...")
                
                for idx, pmid in enumerate(pmids, 1):
                    metadata = self.fetch_article_metadata(pmid)
                    
                    if not metadata or 'title' not in metadata:
                        continue
                    
                    fetched_title = metadata['title']
                    if self.titles_match(original_title, fetched_title):
                        print(f"      ✅ PubMed에서 완전 일치 발견! (PMID: {pmid})")
                        return (pmid, metadata)
                    else:
                        if idx <= 3:
                            print(f"      ❌ [{idx}] 제목 불일치: {fetched_title[:50]}...")
                        self.stats['title_mismatch_rejected'] += 1
                    
                    time.sleep(self.delay)
                
                time.sleep(self.delay)
        
        return None
    
    # ==================== Semantic Scholar 관련 메서드 ====================
    
    def search_semantic_scholar(self, title: str, limit: int = 5) -> List[Dict]:
        """
        Semantic Scholar API로 논문 검색
        
        Args:
            title: 검색할 논문 제목
            limit: 최대 결과 수
            
        Returns:
            논문 리스트
        """
        print("      🎓 Semantic Scholar 검색 중...")
        
        # Paper search endpoint
        endpoint = f"{self.S2_BASE_URL}/paper/search"
        
        params = {
            'query': title,
            'limit': limit,
            'fields': 'title,authors,year,venue,externalIds,publicationDate,citationCount,abstract'
        }
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self._wait_with_backoff(attempt)
                
                response = requests.get(
                    endpoint,
                    params=params,
                    headers=self.s2_headers,
                    timeout=15
                )
                
                if response.status_code == 429:
                    self.stats['rate_limit_hits'] += 1
                    print("      ⚠️ Semantic Scholar API 제한 (429) - 재시도 중...")
                    continue
                
                response.raise_for_status()
                data = response.json()
                papers = data.get('data', [])
                
                print(f"      📚 {len(papers)}개 논문 발견")
                return papers
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"      ❌ Semantic Scholar 검색 실패: {str(e)[:80]}")
                    return []
        
        return []
    
    def find_best_match_semantic_scholar(self, original_title: str) -> Optional[Dict]:
        """
        Semantic Scholar에서 제목 완전 일치 논문 찾기
        
        Args:
            original_title: 원본 논문 제목
            
        Returns:
            메타데이터 또는 None
        """
        papers = self.search_semantic_scholar(original_title, limit=10)
        
        if not papers:
            print("      ❌ Semantic Scholar 결과 없음")
            return None
        
        print("      🔍 제목 완전 일치 확인 중...")
        
        for idx, paper in enumerate(papers, 1):
            paper_title = paper.get('title', '')
            
            if not paper_title:
                continue
            
            # 제목 완전 일치 확인
            if self.titles_match(original_title, paper_title):
                print(f"      ✅ Semantic Scholar에서 완전 일치 발견! [{idx}/{len(papers)}]")
                
                # 메타데이터 변환
                metadata = self._convert_s2_metadata(paper)
                return metadata
            else:
                if idx <= 3:  # 상위 3개만 출력
                    similarity = self.calculate_title_similarity(original_title, paper_title)
                    print(f"      ❌ [{idx}] 제목 불일치 (유사도 {similarity:.3f}): {paper_title[:50]}...")
        
        print(f"      ⚠️ {len(papers)}개 중 완전 일치하는 논문 없음")
        self.stats['s2_low_similarity'] += 1
        return None
    
    def _convert_s2_metadata(self, paper: Dict) -> Dict:
        """
        Semantic Scholar 논문 데이터를 표준 메타데이터 형식으로 변환
        
        Args:
            paper: Semantic Scholar API 응답
            
        Returns:
            표준 메타데이터
        """
        # 저자 추출
        authors = []
        for author in paper.get('authors', []):
            author_name = author.get('name', '')
            if author_name:
                authors.append(author_name)
        
        # DOI 추출
        external_ids = paper.get('externalIds', {})
        doi = external_ids.get('DOI', '')
        
        # PubMed ID도 있으면 저장
        pmid = external_ids.get('PubMed', '')
        
        # 출판일
        pub_date = paper.get('publicationDate', '')
        if not pub_date:
            year = paper.get('year')
            pub_date = str(year) if year else ''
        
        # 저널/학회
        venue = paper.get('venue', '')
        
        # 초록에서 키워드 추출 (간단한 버전)
        keywords = self._extract_keywords_from_abstract(paper.get('abstract', ''))
        
        metadata = {
            'title': paper.get('title', ''),  # 검증용 제목 포함
            'keywords': keywords,
            'journal': venue,
            'authors': authors,
            'doi': doi,
            'publication_date': pub_date,
            'source': 'semantic_scholar',
            'citation_count': paper.get('citationCount', 0),
        }
        
        if pmid:
            metadata['pmid'] = pmid
        
        return metadata
    
    def _extract_keywords_from_abstract(self, abstract: str, max_keywords: int = 5) -> List[str]:
        """
        초록에서 간단히 키워드 추출
        (실제로는 더 정교한 NLP 기법 사용 가능)
        """
        if not abstract:
            return []
        
        # 간단한 키워드 추출 (빈도 기반)
        words = abstract.lower().split()
        
        # 불용어 제거
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                      'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are',
                      'was', 'were', 'been', 'be', 'have', 'has', 'had', 'this',
                      'that', 'these', 'those', 'we', 'our', 'their', 'which'}
        
        # 단어 빈도 계산
        word_freq = {}
        for word in words:
            word = word.strip('.,;:!?()[]{}')
            if len(word) > 4 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 상위 키워드 추출
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords]]
        
        return keywords
    
    # ==================== 메인 처리 로직 ====================
    
    def enrich_article(self, article: Dict, index: int, total: int) -> Dict:
        """
        단일 논문 메타데이터 보완
        1차: PubMed 완전 일치 검색
        2차: Semantic Scholar semantic search
        """
        self.stats['processed'] += 1
        title = article.get('title', '')
        
        # 진행 상황 출력
        if index % 10 == 0 or index == 1 or index == total:
            percentage = index / total * 100
            truncated_title = title[:40] + '...' if len(title) > 40 else title
            print(f"\n[{index:,}/{total:,}] {percentage:5.1f}% - {truncated_title:45}")
        
        # 이미 메타데이터가 완전한 경우
        if 'metadata' in article and article['metadata']:
            metadata = article['metadata']
            if all([metadata.get('doi'), metadata.get('journal'), 
                   metadata.get('authors'), metadata.get('publication_date')]):
                self.stats['already_complete'] += 1
                return article
        
        if not title:
            return article
        
        # 1차 시도: PubMed 검색
        self.stats['pubmed_searched'] += 1
        match_result = self.find_exact_match_progressive(title)
        
        if match_result:
            pmid, metadata = match_result
            metadata.pop('title', None)
            article['metadata'] = metadata
            self.stats['pubmed_found'] += 1
            return article
        
        # 2차 시도: Semantic Scholar
        print("      ⚠️ PubMed 실패, Semantic Scholar 시도...")
        self.stats['s2_searched'] += 1
        
        s2_metadata = self.find_best_match_semantic_scholar(title)
        
        if s2_metadata:
            s2_metadata.pop('title', None)  # 검증용 제목 제거
            article['metadata'] = s2_metadata
            self.stats['s2_found'] += 1
            return article
        
        # 둘 다 실패
        print("      ❌ 두 API 모두 실패")
        self.stats['not_found'] += 1
        
        return article
    
    @staticmethod
    def load_jsonl(filepath: str) -> List[Dict]:
        """JSONL 파일 로드"""
        articles = []
        errors = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    article = json.loads(line)
                    articles.append(article)
                except json.JSONDecodeError:
                    errors += 1
        
        if errors > 0:
            print(f"⚠️  {errors}개 라인 파싱 오류 (건너뜀)")
        
        return articles
    
    @staticmethod
    def save_jsonl(articles: List[Dict], filepath: str):
        """JSONL 파일로 저장"""
        output_file = Path(filepath)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for article in articles:
                json_line = json.dumps(article, ensure_ascii=False)
                f.write(json_line + '\n')
        
        return output_file
    
    def save_checkpoint(self, articles: List[Dict], filepath: str, current_index: int):
        """중간 저장"""
        checkpoint_file = filepath.replace('.jsonl', f'_checkpoint_{current_index}.jsonl')
        self.save_jsonl(articles[:current_index], checkpoint_file)
        print(f"      💾 체크포인트 저장: {checkpoint_file}")
    
    def print_statistics(self):
        """처리 통계 출력"""
        print(f"\n{'='*70}")
        print("처리 통계")
        print(f"{'='*70}")
        print(f"총 논문 수: {self.stats['total']:,}개")
        print(f"처리된 논문: {self.stats['processed']:,}개")
        print(f"이미 완전한 메타데이터: {self.stats['already_complete']:,}개")
        print()
        print("📊 API별 검색 결과:")
        print("  PubMed:")
        print(f"    - 검색 시도: {self.stats['pubmed_searched']:,}개")
        print(f"    - 성공: {self.stats['pubmed_found']:,}개")
        print(f"    - 제목 불일치로 거부: {self.stats['title_mismatch_rejected']:,}개")
        print("  Semantic Scholar:")
        print(f"    - 검색 시도: {self.stats['s2_searched']:,}개")
        print(f"    - 성공: {self.stats['s2_found']:,}개")
        print(f"    - 완전 일치 없음: {self.stats['s2_low_similarity']:,}개")
        print()
        print(f"찾지 못함: {self.stats['not_found']:,}개")
        print(f"오류: {self.stats['errors']:,}개")
        print(f"API 제한 (429) 횟수: {self.stats['rate_limit_hits']:,}개")
        
        total_searched = self.stats['pubmed_searched'] + self.stats['s2_searched']
        total_found = self.stats['pubmed_found'] + self.stats['s2_found']
        
        if total_searched > 0:
            success_rate = total_found / total_searched * 100
            print(f"\n전체 검색 성공률: {success_rate:.1f}%")
            
            if self.stats['pubmed_searched'] > 0:
                pubmed_rate = self.stats['pubmed_found'] / self.stats['pubmed_searched'] * 100
                print(f"  - PubMed 성공률: {pubmed_rate:.1f}%")
            
            if self.stats['s2_searched'] > 0:
                s2_rate = self.stats['s2_found'] / self.stats['s2_searched'] * 100
                print(f"  - Semantic Scholar 성공률: {s2_rate:.1f}%")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='PubMed + Semantic Scholar API 하이브리드 메타데이터 보완 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
특징:
  - 1차: PubMed 제목 완전 일치 검색 (점진적: 5→10→25개)
  - 2차: Semantic Scholar API 제목 완전 일치 검색 (최대 10개)
  - 대소문자 및 공백 차이 무시
  - 두 API 모두 완전 일치만 허용
  
Semantic Scholar API:
  - 무료 tier: 100 requests/5min
  - API key 사용 시: 더 높은 rate limit
  - 문서: https://api.semanticscholar.org/
        """
    )
    parser.add_argument('--max', type=int, default=None,
                       help='처리할 최대 논문 수')
    parser.add_argument('--input', type=str,
                       default='/Users/jaehuncho/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/data/preprocess/unified_output/paper_dataset_.jsonl',
                       help='입력 JSONL 파일')
    parser.add_argument('--output', type=str,
                       default='/Users/jaehuncho/Coding/ai-camp-1st-llm-agent-service-project-mockinjay/data/preprocess/unified_output/paper_dataset_final.jsonl',
                       help='출력 JSONL 파일')
    parser.add_argument('--email', type=str,
                       default='ggh5454@gmail.com',
                       help='이메일 주소 (NCBI 요구사항)')
    parser.add_argument('--pubmed-api-key', type=str, default=None,
                       help='NCBI API 키 (선택)')
    parser.add_argument('--s2-api-key', type=str, default=None,
                       help='Semantic Scholar API 키 (선택, rate limit 증가)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='API 호출 간 대기 시간(초)')
    parser.add_argument('--similarity-threshold', type=float, default=0.85,
                       help='[사용안함] 현재는 제목 완전 일치만 사용')
    parser.add_argument('--checkpoint-interval', type=int, default=50,
                       help='체크포인트 저장 간격')
    
    args = parser.parse_args()
    
    print("="*70)
    print("PubMed + Semantic Scholar API 하이브리드 메타데이터 보완 도구")
    print("="*70)
    print(f"입력 파일: {args.input}")
    print(f"출력 파일: {args.output}")
    print(f"이메일: {args.email}")
    print(f"API 호출 간격: {args.delay}초")
    print(f"S2 유사도 임계값: {args.similarity_threshold}")
    print(f"체크포인트 간격: {args.checkpoint_interval}개마다")
    print("검색 전략: PubMed (완전 일치) → Semantic Scholar (완전 일치)")
    if args.s2_api_key:
        print("Semantic Scholar API 키: 설정됨 (높은 rate limit)")
    else:
        print("Semantic Scholar API 키: 없음 (무료 tier, 100 req/5min)")
    print("⚠️  두 API 모두 제목 완전 일치만 허용 (유사 제목 제외)")
    if args.max:
        print(f"처리할 논문 수: {args.max:,}개")
    print()
    
    # 프로세서 초기화
    enricher = SemanticScholarPubMedEnricher(
        email=args.email, 
        pubmed_api_key=args.pubmed_api_key,
        s2_api_key=args.s2_api_key,
        delay=args.delay,
        similarity_threshold=args.similarity_threshold
    )
    
    # 1. 파일 로드
    print("📂 파일 로딩 중...")
    articles = enricher.load_jsonl(args.input)
    print(f"✓ {len(articles):,}개의 논문 로드 완료\n")
    
    if not articles:
        print("❌ 논문 데이터가 없습니다.")
        return
    
    if args.max:
        articles = articles[:args.max]
        print(f"ℹ️  처음 {args.max:,}개 논문만 처리합니다.\n")
    
    enricher.stats['total'] = len(articles)
    
    # 2. 메타데이터 보완
    print(f"{'='*70}")
    print("메타데이터 보완 시작 (PubMed + Semantic Scholar)")
    print(f"{'='*70}")
    print("💡 팁: Ctrl+C로 안전하게 중단 가능")
    print()
    
    enriched_articles = []
    
    try:
        for i, article in enumerate(articles, 1):
            try:
                enriched = enricher.enrich_article(article, i, len(articles))
                enriched_articles.append(enriched)
                
                # 체크포인트 저장
                if i % args.checkpoint_interval == 0:
                    enricher.save_checkpoint(enriched_articles, args.output, i)
                
                # API 호출 제한 준수
                if i < len(articles):
                    time.sleep(enricher.delay)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  사용자 중단 (Ctrl+C)")
                print(f"현재까지 처리: {i}/{len(articles)}")
                break
                
            except Exception as e:
                print(f"[{i}/{len(articles)}] ❌ 예상치 못한 오류: {e}")
                enricher.stats['errors'] += 1
                enriched_articles.append(article)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  프로그램 중단됨")
    
    # 3. 최종 저장
    print("\n💾 최종 파일 저장 중...")
    output_path = enricher.save_jsonl(enriched_articles, args.output)
    file_size = output_path.stat().st_size
    
    print("✓ 저장 완료")
    print(f"  경로: {output_path}")
    print(f"  크기: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    
    # 4. 통계 출력
    enricher.print_statistics()
    
if __name__ == "__main__":
    main()
