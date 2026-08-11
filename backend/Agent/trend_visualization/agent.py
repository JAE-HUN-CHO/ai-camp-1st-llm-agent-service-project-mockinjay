import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, TypedDict, Tuple
import logging
from datetime import datetime
import os
import asyncio
import json
from app.adapters.ollama.client import OllamaClient

# 프로젝트 경로 설정
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from Agent.core.local_agent import LocalAgent
from Agent.core.agent_registry import AgentRegistry
from Agent.core.contracts import AgentRequest, AgentResponse
from Agent.api.pubmed_client import PubMedClient

# LangGraph imports
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """LangGraph State for Trend Visualization Agent"""
    # 입력
    query: str
    session_id: str
    context: Dict[str, Any]
    
    # 분석 결과
    analysis_type: str  # temporal, geographic, mesh, compare, general
    keywords: List[str]
    
    # PubMed 데이터
    pubmed_data: Optional[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    
    # 시각화 데이터
    chart_config: Optional[Dict[str, Any]]
    
    # 응답
    explanation: str
    status: str
    error: Optional[str]
    
    # 메타데이터 (operator.add 제거)
    metadata: Dict[str, Any]


# ============================================================================
# LangGraph Agent
# ============================================================================

@AgentRegistry.register("trend_visualization")
class TrendVisualizationAgent(LocalAgent):
    """PubMed 기반 트렌드 분석 에이전트 (LangGraph)"""

    def __init__(self):
        super().__init__(agent_type="trend_visualization")
        self.pubmed = PubMedClient()
        self._initialized = False
        self.client = OllamaClient()
        
        # LangGraph workflow 구성
        self.workflow = self._build_workflow()
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """에이전트 메타데이터"""
        return {
            "name": "Trend Visualization Agent (LangGraph)",
            "description": "PubMed 연구 트렌드 분석 및 시각화",
            "version": "3.0",
            "capabilities": [
                "temporal_trends",
                "geographic_distribution",
                "mesh_categories",
                "keyword_comparison",
                "data_visualization",
                "pubmed_integration"
            ],
            "data_sources": ["PubMed"],
            "workflow_engine": "LangGraph"
        }
    
    def _build_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("analyze_request", self._analyze_request)
        workflow.add_node("fetch_pubmed_data", self._fetch_pubmed_data)
        workflow.add_node("generate_visualization", self._generate_visualization)
        workflow.add_node("generate_explanation", self._generate_explanation)
        
        # 엣지 설정
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "fetch_pubmed_data")
        workflow.add_edge("fetch_pubmed_data", "generate_visualization")
        workflow.add_edge("generate_visualization", "generate_explanation")
        workflow.add_edge("generate_explanation", END)
        
        return workflow.compile()

    async def _chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> str:
        response = await self.client.chat.completions.create(
            model=os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        통일된 계약 기반 처리 (LangGraph 실행)
        
        Args:
            request: AgentRequest
            
        Returns:
            AgentResponse: 통일된 응답 형식
        """
        try:
            # 초기 상태 생성
            initial_state: AgentState = {
                "query": request.query,
                "session_id": request.session_id,
                "context": request.context or {},
                "analysis_type": "",
                "keywords": [],
                "pubmed_data": None,
                "papers": [],
                "chart_config": None,
                "explanation": "",
                "status": "processing",
                "error": None,
                "metadata": {}
            }
            
            # LangGraph 실행
            logger.info(f"🚀 Starting LangGraph workflow for query: {request.query}")
            final_state = await self.workflow.ainvoke(initial_state)
            
            # 응답 생성
            if final_state.get("error"):
                return AgentResponse(
                    answer=f"트렌드 분석 중 오류가 발생했습니다: {final_state['error']}",
                    sources=[],
                    papers=[],
                    tokens_used=100,
                    status="error",
                    agent_type=self.agent_type,
                    metadata=final_state.get("metadata", {})
                )
            
            return AgentResponse(
                answer=final_state.get("explanation", ""),
                sources=[final_state.get("chart_config")] if final_state.get("chart_config") else [],
                papers=final_state.get("papers", [])[:5],
                tokens_used=200,
                status=final_state.get("status", "success"),
                agent_type=self.agent_type,
                metadata=final_state.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"❌ LangGraph workflow error: {e}", exc_info=True)
            return AgentResponse(
                answer=f"트렌드 분석 중 오류가 발생했습니다: {str(e)}",
                sources=[],
                papers=[],
                tokens_used=0,
                status="error",
                agent_type=self.agent_type,
                metadata={"error": str(e)}
            )

    # ========================================================================
    # LangGraph Nodes
    # ========================================================================

    async def _analyze_request(self, state: AgentState) -> AgentState:
        """
        Node 1: 요청 분석 및 분석 타입 결정
        """
        logger.info("📊 Node 1: Analyzing request...")

        query = state["query"]
        context = state.get("context", {})

        # 분석 타입 결정 (both analysis_type and analysisType supported)
        analysis_type = context.get("analysis_type") or context.get("analysisType", "temporal_trends")

        # Map 'temporal', 'geographic', 'mesh', 'compare' to internal format
        type_mapping = {
            "temporal": "temporal_trends",
            "geographic": "geographic_distribution",
            "mesh": "mesh_categories",
            "compare": "keyword_comparison"
        }
        analysis_type = type_mapping.get(analysis_type, analysis_type)

        # 쿼리에서 키워드 추출
        keywords = context.get("keywords", [query])
        if not keywords:
            keywords = [query]

        logger.info(f"   Analysis type: {analysis_type}")
        logger.info(f"   Keywords: {keywords}")

        state["analysis_type"] = analysis_type
        state["keywords"] = keywords
        state["metadata"]["analysis_type"] = analysis_type

        return state

    async def _fetch_pubmed_data(self, state: AgentState) -> AgentState:
        """
        Node 2: PubMed에서 데이터 가져오기
        """
        logger.info("🔍 Node 2: Fetching PubMed data...")
        
        try:
            analysis_type = state["analysis_type"]
            keywords = state["keywords"]
            context = state.get("context", {})
            
            pubmed_data = {}
            papers = []
            
            if analysis_type == "temporal_trends":
                # 시간별 트렌드 분석
                start_year = context.get("start_year", 2015)
                end_year = context.get("end_year", 2024)
                
                logger.info(f"   Fetching temporal trends ({start_year}-{end_year})...")
                
                try:
                    trends_data = await self.pubmed.searcher.get_publication_trends_parallel(
                        query=keywords[0],
                        start_year=start_year,
                        end_year=end_year,
                        normalize=True
                    )
                    
                    pubmed_data["trends"] = trends_data
                    pubmed_data["start_year"] = start_year
                    pubmed_data["end_year"] = end_year
                except Exception as e:
                    logger.error(f"   ⚠️ Trends fetch failed: {e}")
                    state["error"] = f"시간별 트렌드 데이터 가져오기 실패 (Rate Limit 가능성)"
                    state["status"] = "error"
                    return state
                
                # 최근 논문 가져오기 (Rate Limit 회피)
                try:
                    papers = await self.pubmed.search(
                        query=keywords[0],
                        max_results=5,  # 10 → 5로 줄임
                        sort="pub_date"
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Papers fetch failed (Rate Limit): {e}")
                    papers = []  # 논문 없이 진행
                
            elif analysis_type == "geographic_distribution":
                # 지역별 분포 분석
                countries = context.get("countries", None)
                
                logger.info(f"   Fetching geographic distribution...")
                
                try:
                    geo_data = await self.pubmed.searcher.get_geographic_distribution_parallel(
                        query=keywords[0],
                        countries=countries
                    )
                    
                    pubmed_data["geographic"] = geo_data
                except Exception as e:
                    logger.error(f"   ⚠️ Geographic fetch failed: {e}")
                    state["error"] = "지역별 분포 데이터 가져오기 실패"
                    state["status"] = "error"
                    return state
                
                try:
                    papers = await self.pubmed.search(
                        query=keywords[0],
                        max_results=5
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Papers fetch failed: {e}")
                    papers = []
                
            elif analysis_type == "keyword_comparison":
                # 키워드 비교 분석
                start_year = context.get("start_year", 2015)
                end_year = context.get("end_year", 2024)

                logger.info(f"   Comparing keywords: {keywords[:4]}")

                all_trends = []
                for keyword in keywords[:4]:  # 최대 4개
                    try:
                        trends = await self.pubmed.searcher.get_publication_trends_parallel(
                            query=keyword,
                            start_year=start_year,
                            end_year=end_year,
                            normalize=True
                        )
                        all_trends.append({
                            "keyword": keyword,
                            "data": trends
                        })
                    except Exception as e:
                        logger.warning(f"   ⚠️ Skipping keyword '{keyword}': {e}")
                        continue

                if not all_trends:
                    state["error"] = "키워드 비교 데이터 가져오기 실패"
                    state["status"] = "error"
                    return state

                pubmed_data["comparisons"] = all_trends
                pubmed_data["start_year"] = start_year
                pubmed_data["end_year"] = end_year

                # 첫 번째 키워드로 논문 검색
                try:
                    papers = await self.pubmed.search(
                        query=keywords[0],
                        max_results=5
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Papers fetch failed: {e}")
                    papers = []

            elif analysis_type == "mesh_categories":
                # MeSH 카테고리 분석 (subheading 사용)
                logger.info(f"   Fetching MeSH subheadings...")

                # MeSH subheadings만 사용 (categories는 PubMed API에서 직접 지원하지 않음)
                default_subheadings = [
                    "therapy",
                    "diagnosis",
                    "epidemiology",
                    "prevention and control",
                    "complications",
                    "drug therapy",
                    "etiology",
                    "pathology",
                    "physiology",
                    "mortality",
                    "genetics",
                    "metabolism"
                ]

                try:
                    # subheadings만 조회 (categories는 제거)
                    mesh_data = await self.pubmed.searcher.get_mesh_distribution_parallel(
                        query=keywords[0],
                        categories=None,  # categories 제거
                        subheadings=default_subheadings
                    )

                    # categories 필드를 subheadings 데이터로 채움 (차트 호환성을 위해)
                    if "subheadings" in mesh_data:
                        mesh_data["categories"] = mesh_data["subheadings"]
                    else:
                        mesh_data["categories"] = []

                    pubmed_data["mesh"] = mesh_data
                    logger.info(f"   ✅ Fetched {len(mesh_data.get('categories', []))} MeSH categories")
                except Exception as e:
                    logger.error(f"   ⚠️ MeSH fetch failed: {e}")
                    state["error"] = "MeSH 카테고리 데이터 가져오기 실패"
                    state["status"] = "error"
                    return state

                # 샘플 논문 가져오기
                try:
                    papers = await self.pubmed.search(
                        query=keywords[0],
                        max_results=5
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Papers fetch failed: {e}")
                    papers = []

            else:
                # 기본: 최근 논문 검색
                logger.info(f"   Fetching recent papers...")
                try:
                    papers = await self.pubmed.search(
                        query=keywords[0],
                        max_results=10
                    )
                    pubmed_data["papers_count"] = len(papers)
                except Exception as e:
                    logger.error(f"   ❌ Papers fetch failed: {e}")
                    state["error"] = "논문 검색 실패"
                    state["status"] = "error"
                    return state
            
            logger.info(f"   ✅ Fetched {len(papers)} papers")
            
            state["pubmed_data"] = pubmed_data
            state["papers"] = papers
            state["metadata"]["papers_count"] = len(papers)
            state["status"] = "data_fetched"
            
        except Exception as e:
            logger.error(f"   ❌ PubMed fetch error: {e}")
            state["error"] = f"PubMed 데이터 가져오기 실패: {str(e)}"
            state["status"] = "error"
        
        return state

    async def _generate_visualization(self, state: AgentState) -> AgentState:
        """
        Node 3: 차트 설정 생성
        """
        logger.info("📈 Node 3: Generating visualization...")
        
        # 에러 상태면 스킵
        if state.get("error"):
            logger.warning("   ⚠️ Skipping due to previous error")
            return state
        
        try:
            analysis_type = state["analysis_type"]
            pubmed_data = state.get("pubmed_data")
            
            # pubmed_data가 None이면 스킵
            if not pubmed_data:
                logger.warning("   ⚠️ No PubMed data available")
                return state
            
            chart_config = None
            
            if analysis_type == "temporal_trends" and "trends" in pubmed_data:
                # 시간별 트렌드 차트
                trends = pubmed_data["trends"]
                
                chart_config = {
                    "type": "line",
                    "data": {
                        "labels": [str(year) for year in trends["years"]],
                        "datasets": [
                            {
                                "label": "논문 수",
                                "data": trends["counts"],
                                "borderColor": "rgb(59, 130, 246)",
                                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                                "tension": 0.3
                            }
                        ]
                    },
                    "options": {
                        "responsive": True,
                        "plugins": {
                            "title": {
                                "display": True,
                                "text": "시간별 연구 트렌드"
                            }
                        }
                    }
                }
                
                # 정규화 데이터 추가
                if "normalized_counts" in trends:
                    chart_config["data"]["datasets"].append({
                        "label": "정규화된 수 (per 100K)",
                        "data": trends["normalized_counts"],
                        "borderColor": "rgb(239, 68, 68)",
                        "backgroundColor": "rgba(239, 68, 68, 0.1)",
                        "tension": 0.3,
                        "yAxisID": "y1"
                    })
                
            elif analysis_type == "geographic_distribution" and pubmed_data and "geographic" in pubmed_data:
                # 지역별 분포 차트
                geo_data = pubmed_data["geographic"]
                
                sorted_countries = sorted(
                    geo_data["countries"].items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )[:15]
                
                chart_config = {
                    "type": "bar",
                    "data": {
                        "labels": [country for country, _ in sorted_countries],
                        "datasets": [{
                            "label": "논문 수",
                            "data": [data["count"] for _, data in sorted_countries],
                            "backgroundColor": "rgba(59, 130, 246, 0.7)",
                            "borderColor": "rgb(59, 130, 246)",
                            "borderWidth": 1
                        }]
                    },
                    "options": {
                        "indexAxis": "y",
                        "responsive": True
                    }
                }
                
            elif analysis_type == "keyword_comparison" and pubmed_data and "comparisons" in pubmed_data:
                # 키워드 비교 차트
                comparisons = pubmed_data["comparisons"]

                colors = [
                    'rgb(59, 130, 246)',
                    'rgb(239, 68, 68)',
                    'rgb(34, 197, 94)',
                    'rgb(234, 179, 8)'
                ]

                datasets = []
                for i, comp in enumerate(comparisons):
                    datasets.append({
                        "label": comp["keyword"],
                        "data": comp["data"]["normalized_counts"],
                        "borderColor": colors[i % len(colors)],
                        "backgroundColor": colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.1)'),
                        "tension": 0.3
                    })

                chart_config = {
                    "type": "line",
                    "data": {
                        "labels": [str(year) for year in comparisons[0]["data"]["years"]],
                        "datasets": datasets
                    },
                    "options": {
                        "responsive": True,
                        "plugins": {
                            "title": {
                                "display": True,
                                "text": "키워드 비교 분석"
                            }
                        }
                    }
                }

            elif analysis_type == "mesh_categories" and pubmed_data and "mesh" in pubmed_data:
                # MeSH 카테고리 차트
                mesh_data = pubmed_data["mesh"]

                # Get categories - now it's a list of dicts [{name, count, proportion}, ...]
                categories_list = mesh_data.get("categories", [])

                # Filter out zero counts and sort by count
                categories_list = [c for c in categories_list if c.get("count", 0) > 0]
                sorted_categories = sorted(
                    categories_list,
                    key=lambda x: x.get("count", 0),
                    reverse=True
                )[:10]

                # Generate chart colors
                colors = [
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(34, 197, 94, 0.7)',
                    'rgba(234, 179, 8, 0.7)',
                    'rgba(168, 85, 247, 0.7)',
                    'rgba(236, 72, 153, 0.7)',
                    'rgba(20, 184, 166, 0.7)',
                    'rgba(251, 146, 60, 0.7)',
                    'rgba(100, 116, 139, 0.7)',
                    'rgba(14, 165, 233, 0.7)'
                ]

                chart_config = {
                    "type": "doughnut",
                    "data": {
                        "labels": [cat.get("name", "") for cat in sorted_categories],
                        "datasets": [{
                            "label": "논문 수",
                            "data": [cat.get("count", 0) for cat in sorted_categories],
                            "backgroundColor": colors[:len(sorted_categories)],
                            "borderColor": [color.replace('0.7', '1') for color in colors[:len(sorted_categories)]],
                            "borderWidth": 1
                        }]
                    },
                    "options": {
                        "responsive": True,
                        "plugins": {
                            "title": {
                                "display": True,
                                "text": "MeSH 카테고리 분포"
                            },
                            "legend": {
                                "position": "right"
                            }
                        }
                    }
                }

                # Store top category in metadata
                if sorted_categories:
                    state["metadata"]["top_category"] = sorted_categories[0].get("name", "")
                    state["metadata"]["top_category_count"] = sorted_categories[0].get("count", 0)

            if chart_config:
                logger.info(f"   ✅ Generated {chart_config['type']} chart")
                state["chart_config"] = chart_config
                state["metadata"]["chart_type"] = chart_config["type"]
            else:
                logger.info("   ℹ️ No chart generated")
            
        except Exception as e:
            logger.error(f"   ❌ Visualization error: {e}")
            # 차트 생성 실패는 치명적이지 않으므로 계속 진행
        
        return state



    async def _generate_explanation(self, state: AgentState) -> AgentState:
        """
        Node 4: 분석 결과 설명 생성
        """
        logger.info("💬 Node 4: Generating explanation...")
        
        try:
            analysis_type = state["analysis_type"]
            pubmed_data = state.get("pubmed_data") or {}
            papers = state.get("papers", [])
            query = state["query"]

            explanation = ""
            summary_payload: Dict[str, Any] = {
                "analysis_type": analysis_type,
                "query": query,
                "papers_count": len(papers)
            }

            if analysis_type == "temporal_trends" and pubmed_data and "trends" in pubmed_data:
                trends = pubmed_data["trends"]
                total_papers = sum(trends["counts"])
                max_idx = trends["counts"].index(max(trends["counts"]))
                peak_year = trends["years"][max_idx]
                peak_count = trends["counts"][max_idx]
                start_year = pubmed_data["start_year"]
                end_year = pubmed_data["end_year"]
                summary_payload["temporal"] = {
                    "total_papers": total_papers,
                    "peak_year": peak_year,
                    "peak_count": peak_count,
                    "start_year": start_year,
                    "end_year": end_year,
                    "trend_points": list(zip(trends["years"], trends["counts"]))
                }
                summary_payload["recent_titles"] = [
                    paper.get("title") for paper in papers[:3]
                ]
                
                explanation = f"""📊 시간별 연구 트렌드 분석 ({start_year}-{end_year})

🔍 **분석 주제**: "{query}"

📈 **주요 통계**:
• 전체 논문 수: {total_papers:,}개
• 최고 발행 연도: {peak_year}년 ({peak_count:,}개)
• 분석 기간: {end_year - start_year + 1}년

💡 **트렌드 요약**:
최근 {end_year - start_year + 1}년간 "{query}" 주제의 연구는 꾸준한 관심을 받고 있으며,
{peak_year}년에 가장 많은 논문이 발표되었습니다.

📄 최근 주요 논문 {len(papers)}개가 검색되었습니다."""

            elif analysis_type == "geographic_distribution" and pubmed_data and "geographic" in pubmed_data:
                geo_data = pubmed_data["geographic"]
                sorted_countries = sorted(
                    geo_data["countries"].items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )
                top_country = sorted_countries[0][0] if sorted_countries else "N/A"
                top_count = sorted_countries[0][1]["count"] if sorted_countries else 0
                total_results = geo_data["total_results"]
                summary_payload["geographic"] = {
                    "top_country": top_country,
                    "top_count": top_count,
                    "total_results": total_results,
                    "countries": [
                        {"country": country, "count": data["count"]}
                        for country, data in sorted_countries[:5]
                    ]
                }
                
                explanation = f"""🌍 지역별 연구 분포 분석

🔍 **분석 주제**: "{query}"

📈 **주요 통계**:
• 총 논문 수: {total_results:,}개
• 최다 연구 국가: {top_country} ({top_count:,}개, {top_count/total_results*100:.1f}%)
• 분석 국가 수: {len(sorted_countries)}개

💡 **분포 요약**:
"{query}" 주제는 전 세계적으로 연구되고 있으며,
{top_country}에서 가장 활발한 연구가 진행되고 있습니다."""

            elif analysis_type == "keyword_comparison" and pubmed_data and "comparisons" in pubmed_data:
                comparisons = pubmed_data["comparisons"]
                keyword_summaries = []
                comparison_payload = []
                for comp in comparisons:
                    total = sum(comp["data"]["counts"])
                    keyword_summaries.append(f"• {comp['keyword']}: {total:,}개")
                    comparison_payload.append({
                        "keyword": comp["keyword"],
                        "total": total,
                        "trend_points": list(zip(comp["data"]["years"], comp["data"]["counts"]))
                    })

                start_year = pubmed_data["start_year"]
                end_year = pubmed_data["end_year"]
                summary_payload["comparisons"] = {
                    "period": {"start": start_year, "end": end_year},
                    "keywords": comparison_payload
                }

                explanation = f"""📊 키워드 비교 분석 ({start_year}-{end_year})

🔍 **비교 키워드**: {len(comparisons)}개

📈 **키워드별 총 논문 수**:
{chr(10).join(keyword_summaries)}

💡 **분석 요약**:
선택한 키워드들의 연구 트렌드를 시간에 따라 비교하여
각 주제의 관심도 변화를 확인할 수 있습니다."""

            elif analysis_type == "mesh_categories" and pubmed_data and "mesh" in pubmed_data:
                mesh_data = pubmed_data["mesh"]
                categories_list = mesh_data.get("categories", [])

                # Filter and sort categories
                categories_list = [c for c in categories_list if c.get("count", 0) > 0]
                sorted_categories = sorted(
                    categories_list,
                    key=lambda x: x.get("count", 0),
                    reverse=True
                )[:10]

                top_category = sorted_categories[0].get("name", "N/A") if sorted_categories else "N/A"
                top_count = sorted_categories[0].get("count", 0) if sorted_categories else 0
                total_categories = len(categories_list)

                category_summaries = [
                    f"{i+1}. {cat.get('name', '')}: {cat.get('count', 0):,}개"
                    for i, cat in enumerate(sorted_categories[:5])
                ]

                summary_payload["mesh"] = {
                    "top_category": top_category,
                    "top_count": top_count,
                    "total_categories": total_categories,
                    "top_categories": [
                        {"category": cat.get("name", ""), "count": cat.get("count", 0)}
                        for cat in sorted_categories[:10]
                    ]
                }

                explanation = f"""🏷️ MeSH 카테고리 분석

🔍 **분석 주제**: "{query}"

📈 **주요 통계**:
• 발견된 카테고리 수: {total_categories}개
• 최다 카테고리: {top_category} ({top_count:,}개)
• 분석 논문 수: {len(papers)}개

📊 **주요 카테고리 (Top 5)**:
{chr(10).join(category_summaries)}

💡 **분석 요약**:
"{query}" 주제의 연구는 주로 {top_category} 카테고리에 집중되어 있으며,
다양한 MeSH 카테고리에 걸쳐 폭넓게 연구되고 있습니다."""

            else:
                # 기본 설명
                papers_count = pubmed_data.get("papers_count", len(papers))
                summary_payload["papers_count"] = papers_count
                summary_payload["recent_titles"] = [
                    paper.get("title") for paper in papers[:5]
                ]
                explanation = f"""🔍 연구 트렌드 분석

**분석 주제**: "{query}"

📄 총 {papers_count}개의 관련 논문이 검색되었습니다.

PubMed 검색 결과를 바탕으로 최신 연구 동향을 확인하세요."""
            
            logger.info(f"   ✅ Generated explanation ({len(explanation)} chars)")
            
            explanation = await self._generate_llm_explanation(
                query=query,
                analysis_type=analysis_type,
                summary_payload=summary_payload,
                fallback=explanation
            )

            state["explanation"] = explanation
            state["status"] = "success"
            state["metadata"]["explanation_length"] = len(explanation)
            
        except Exception as e:
            logger.error(f"   ❌ Explanation generation error: {e}")
            state["error"] = f"설명 생성 실패: {str(e)}"
            state["status"] = "error"
        
        return state

    async def _generate_llm_explanation(
        self,
        query: str,
        analysis_type: str,
        summary_payload: Dict[str, Any],
        fallback: str
    ) -> str:
        """
        Use OpenAI-compatible client to create a natural-language explanation.
        Falls back to the templated explanation if the LLM call fails.
        """
        try:
            payload_json = json.dumps(summary_payload, ensure_ascii=False, indent=2)
            system_prompt = (
                "당신은 의학 데이터 분석가입니다. "
                "주어진 PubMed 통계 정보를 한국어로 명확하고 친절하게 요약하세요. "
                "숫자 해석과 의미를 함께 설명하고 환자/연구자 모두 이해할 수 있게 작성합니다."
            )
            user_content = (
                f"사용자 질문: {query}\n"
                f"분석 유형: {analysis_type}\n"
                f"데이터 요약(JSON):\n{payload_json}\n\n"
                "위 데이터를 활용해 3~4개의 단락으로 결과를 설명하고, "
                "핵심 통계와 시사점을 포함해주세요."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            return await self._chat_completion(messages=messages, temperature=0.2, max_tokens=700)
        except Exception as exc:
            logger.warning(f"LLM explanation failed, using fallback: {exc}")
            return fallback

    def estimate_context_usage(self, user_input: str) -> int:
        """컨텍스트 사용량 추정"""
        return int(len(user_input) * 1.5) + 500 + 800

    async def close(self):
        """리소스 정리"""
        self.pubmed.close()
