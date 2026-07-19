"""
re_retrieve.py
재검색 노드 — grade가 insufficient일 때 호출되는 '다시 검색' 동작.
agentic 재검색 루프의 '재시도' 부분(루프 배선은 build.py 조건부 엣지).

재검색 전략(파트3 re_retrieve.py의 recall 전략과 같은 철학):
  1차가 부실했으므로 좁히지 않고 '넓힌다'. k를 키우고 MMR로 다양성을 높여
  1차와 다른 청크가 올라오게 한다. 쿼리도 업종 특화어를 빼고 일반화한다.

결과 처리: 기존 docs를 '교체'한다(누적 아님).
  부실한 1차를 안고 가면 재판정이 또 부실로 빠져 루프가 안 끝난다.
"""
from backend.retrieval.retriever import re_retrieve_recall_fn
from utils.logger import get_logger

logger = get_logger(__name__)


def _broaden_query(state) -> str:
    """
    재검색용으로 쿼리를 일반화한다.
    1차는 업종어를 넣어 좁게 쳤으므로, 재검색은 규제 일반어 위주로 넓게 친다.
    """
    request = state.get("request") or ""
    return f"광고 금지 표현 과장 표현 소비자 오인 표시광고 위반 사례 {request}".strip()


def re_retrieve_node(state) -> dict:
    """
    쿼리를 넓혀 다시 검색하고 docs를 교체한다.

    Returns:
        dict: docs(교체), retrieval_status
    """
    query = _broaden_query(state)
    attempt = state.get("retry_count", 1)
    new_docs = re_retrieve_recall_fn(query)
    status = "ok" if new_docs else "empty"
    logger.info(f"재검색 | attempt={attempt} query='{query[:40]}...' → {len(new_docs)}청크")
    return {"docs": new_docs, "retrieval_status": status}
