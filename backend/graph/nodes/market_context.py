"""
market_context.py
상권·타겟 분석 노드 — 소상공인 상권정보 REST API를 호출하는 '도구 노드'.
POC가 증명할 것 중 하나: 실제 소상공인 도구가 파이프라인에 물린다.

도구 실패(키 없음·좌표 실패·API 오류)는 예외로 던지지 않고 status로 흘려보낸다.
카피 생성 노드는 market이 비어도 동작하도록 작성돼 있다(강건성).
"""
from backend.tools.market_api import get_market_context
from utils.logger import get_logger

logger = get_logger(__name__)


def market_context_node(state) -> dict:
    """
    지역·업종으로 반경 내 상권을 조회해 요약 컨텍스트를 만든다.

    Returns:
        dict: market(요약 dict), market_status(ok/no_coord/api_error/skipped)
    """
    region = state.get("region")
    biz_type = state.get("biz_type")

    if not region:
        logger.info("상권조회 | region 없음 → skipped")
        return {"market": {}, "market_status": "skipped"}

    market, status = get_market_context(region, biz_type)
    logger.info(f"상권조회 | status={status} | {market.get('summary', '')}")
    return {"market": market, "market_status": status}
