"""
compliance_rag.py
광고규제 RAG 검색 노드 — 생성할 카피가 지켜야 할 표시·광고 규제 근거를 검색한다.

검색 쿼리는 사용자 질문 그대로가 아니라 '업종 + 광고 표현 규제'로 재구성한다.
사용자는 "여름 신메뉴 홍보 문구"라고 묻지 규제를 묻지 않기 때문에,
질문 원문으로 규제 코퍼스를 치면 유사도가 낮게 나온다(POC 초기 실패 지점).
"""
from backend.retrieval.retriever import get_retriever
from utils.logger import get_logger

logger = get_logger(__name__)


def build_compliance_query(state) -> str:
    """규제 코퍼스에 맞는 검색 쿼리를 만든다(업종·요청을 규제 언어로 번역)."""
    biz_type = state.get("biz_type") or ""
    request = state.get("request") or ""
    base = f"{biz_type} 광고 표현 규제 금지 표현 부당 광고 과장 광고"
    return f"{base} {request}".strip()


def compliance_rag_node(state) -> dict:
    """
    광고규제 코퍼스에서 근거 청크를 검색한다.

    Returns:
        dict: docs(list[Document]), retrieval_status(ok/empty)
    """
    config = state.get("config", {})
    query = build_compliance_query(state)
    docs = get_retriever(query, k=config.get("top_k"))
    status = "ok" if docs else "empty"
    logger.info(f"규제검색 | query='{query[:40]}...' → {len(docs)}청크")
    return {"docs": docs, "retrieval_status": status}
