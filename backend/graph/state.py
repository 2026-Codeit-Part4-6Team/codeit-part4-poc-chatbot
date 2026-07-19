"""
state.py
LangGraph 오케스트레이션의 공유 상태(GraphState) 정의.

LangGraph는 노드 간에 단일 state dict를 흘려보낸다. 각 노드는 state를 받아
자기가 채울 필드만 dict로 반환하고, LangGraph가 그걸 기존 state에 병합한다.
total=False: 모든 필드가 처음부터 채워져 있지 않아도 됨(노드가 점진적으로 채움).

파트3(RFPilot) state.py와 동일한 설계를 따른다 → 본 프로젝트 확장 시 그대로 이식.
"""
from typing import TypedDict, Literal, Optional
from langchain_core.documents import Document


class GraphState(TypedDict, total=False):
    # --- 입력 (그래프 진입 시 주입) ---
    question: str                 # 원본 사용자 질문 (예: "강남역 카페인데 여름 신메뉴 홍보 문구 만들어줘")
    history: list[dict]           # 대화 이력 [{"role","content"}, ...]
    config: dict                  # 설정값(top_k, retriever_type, radius 등)

    # --- question_analysis_node 산출 ---
    rewritten_question: str       # 지시어 해소된 재구성 질문
    biz_type: Optional[str]       # 업종 (카페, 미용실, 정육점 ...)
    region: Optional[str]         # 지역/주소 (강남역, 서울시 강남구 ...)
    request: Optional[str]        # 요청 사항 (톤·채널·소재 등)

    # --- routing_node 산출 ---
    route: Literal["with_market", "copy_only"]   # 상권 조회 필요 여부

    # --- market_context_node 산출 (도구 노드) ---
    market: dict                  # {store_count, top_upjong, competitor_count, summary}
    market_status: str            # ok / skipped / no_coord / api_error

    # --- compliance_rag / re_retrieve 산출 ---
    docs: list[Document]          # 광고규제 검색 청크 (Document 통째 보관)
    retrieval_status: str         # ok / empty

    # --- grade_node 산출 (agentic 재검색 루프용) ---
    grade: Literal["sufficient", "insufficient", "out_of_scope"]
    #   sufficient   : 근거 충분 → 카피 생성으로
    #   insufficient : 부족하지만 재검색 여지 있음 → re_retrieve 루프로
    #   out_of_scope : 광고 콘텐츠 생성 범위 밖 → 재검색 말고 생성(거부)으로
    retry_count: int              # 재검색 시도 횟수(무한루프 방지)

    # --- copy_generation_node 산출 ---
    answer: str                   # 생성된 광고 카피(최종 답변)
    tokens_used: int              # 생성 토큰 수

    # --- self_check_node 산출 ---
    check_passed: bool            # 검증 통과 여부
    check_flags: list[str]        # 걸린 항목(banned_expression / source_missing 등)
