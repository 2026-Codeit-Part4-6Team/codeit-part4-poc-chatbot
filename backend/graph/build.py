"""
build.py
POC 오케스트레이션 그래프 조립부.

흐름:
  START → question_analysis → routing ─┬ with_market → market_context ┐
                                       └ copy_only ──────────────────┴→ compliance_rag
  compliance_rag →(retriever_type 토글)┬ agentic_rag → grade
                                       └ naive_rag  → copy_generation
  grade ─┬ sufficient / out_of_scope / 재시도한도 초과 → copy_generation
         └ insufficient(재시도 여유)                  → re_retrieve → grade ↺
  copy_generation → self_check → END

파트3 build.py의 배선(조건부 엣지 + 루프백 + retry 한도)을 그대로 이식했다.
naive/agentic 토글도 유지해, POC 발표에서 "루프 없음 vs 루프 있음"을 비교 시연할 수 있다.
"""
from dotenv import load_dotenv
load_dotenv()   # .env의 OPENAI_API_KEY 등 로드 (직접 실행 진입점이라 명시적으로 읽음)

from langgraph.graph import StateGraph, START, END

from backend.graph.state import GraphState
from backend.graph.nodes.question_analysis import question_analysis_node
from backend.graph.nodes.routing import routing_node
from backend.graph.nodes.market_context import market_context_node
from backend.graph.nodes.compliance_rag import compliance_rag_node
from backend.graph.nodes.grade import grade_node
from backend.graph.nodes.re_retrieve import re_retrieve_node
from backend.graph.nodes.copy_generation import copy_generation_node
from backend.graph.nodes.self_check import self_check_node
from utils.config import load_config

# 재검색 최대 횟수. grade가 insufficient여도 한도를 넘으면 생성으로 나간다(무한루프 차단).
_MAX_RETRY = load_config()["max_retry"]


# ===== 조건부 분기 선택자 =====

def _route_selector(state: GraphState) -> str:
    """routing_node가 기록한 route로 상권 조회 여부를 가른다."""
    return state.get("route", "copy_only")


def _mode_selector(state: GraphState) -> str:
    """
    retriever_type 토글로 compliance_rag 다음 행선지를 정한다.
      agentic_rag → grade(재검색 루프 수행)
      naive_rag   → grade 건너뛰고 바로 생성
    """
    config = state.get("config", {})
    if config.get("retriever_type") == "agentic_rag":
        return "grade"
    return "copy_generation"


def _grade_selector(state: GraphState) -> str:
    """
    grade 판정 + 재시도 한도로 다음 행선지를 정한다.
      insufficient & 재시도 여유 → re_retrieve(루프)
      그 외(sufficient / out_of_scope / 한도 초과) → copy_generation

    retry_count 의미: grade 노드를 지난 횟수(grade가 매번 +1).
      1회차 판정 후 retry_count=1 → 재검색 1회째
      max_retry=2면 재검색은 최대 2회 수행되고, 3회차 판정에서 생성으로 빠진다.
    (파트3 build.py는 `<`를 써서 max_retry=2일 때 재검색이 1회만 돌았다.
     설정값 이름과 실제 동작을 일치시키기 위해 `<=`로 바로잡았다.)
    """
    grade = state.get("grade", "sufficient")
    retry_count = state.get("retry_count", 0)
    if grade == "insufficient" and retry_count <= _MAX_RETRY:
        return "re_retrieve"
    return "copy_generation"


# ===== 그래프 조립 =====

def build_graph():
    """오케스트레이션 그래프를 조립해 컴파일된 앱을 반환한다."""
    g = StateGraph(GraphState)

    # 노드 등록
    g.add_node("question_analysis", question_analysis_node)
    g.add_node("routing", routing_node)
    g.add_node("market_context", market_context_node)     # 도구 노드(상권 REST API)
    g.add_node("compliance_rag", compliance_rag_node)     # 광고규제 RAG 검색
    g.add_node("grade", grade_node)                       # 근거 충분? 판정
    g.add_node("re_retrieve", re_retrieve_node)           # 재검색(루프 동작)
    g.add_node("copy_generation", copy_generation_node)
    g.add_node("self_check", self_check_node)

    # 순서 엣지
    g.add_edge(START, "question_analysis")
    g.add_edge("question_analysis", "routing")

    # 조건부 분기: 상권 조회가 필요한 요청만 도구 노드를 거친다
    g.add_conditional_edges(
        "routing",
        _route_selector,
        {"with_market": "market_context", "copy_only": "compliance_rag"},
    )
    # 상권 조회 후에는 항상 규제 검색으로 합류
    g.add_edge("market_context", "compliance_rag")

    # naive/agentic 토글: agentic이면 grade(루프), naive면 바로 생성
    g.add_conditional_edges(
        "compliance_rag",
        _mode_selector,
        {"grade": "grade", "copy_generation": "copy_generation"},
    )

    # grade 판정으로 분기: 부족하고 재시도 여유 있으면 재검색, 아니면 생성
    g.add_conditional_edges(
        "grade",
        _grade_selector,
        {"re_retrieve": "re_retrieve", "copy_generation": "copy_generation"},
    )

    # 재검색 후 다시 grade로 돌아가 재판정(루프백). retry_count 한도로 무한루프 차단.
    g.add_edge("re_retrieve", "grade")

    # 생성 → 검증 → 종료
    g.add_edge("copy_generation", "self_check")
    g.add_edge("self_check", END)

    return g.compile()


# 직접 실행 시 흐름 확인
# 실행: (루트에서) python -m backend.graph.build
if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({
        "question": "강남역 근처 카페인데 여름 신메뉴 홍보 문구 만들어줘",
        "history": [],
        "config": load_config(),
    })
    print("=" * 60)
    print("재구성 질문 :", result.get("rewritten_question"))
    print("업종/지역   :", result.get("biz_type"), "/", result.get("region"))
    print("route       :", result.get("route"), "| market:", result.get("market_status"))
    print("grade       :", result.get("grade"), "| retry_count:", result.get("retry_count"))
    print("docs 개수   :", len(result.get("docs", [])))
    print("check       :", result.get("check_passed"), result.get("check_flags"))
    print("-" * 60)
    print(result.get("answer", "")[:600])
