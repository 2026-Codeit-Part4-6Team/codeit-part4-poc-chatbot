"""
routing.py
라우팅 노드 — 상권 조회가 필요한지 룰 기반으로 판단한다.
이 노드는 route 문자열만 기록하고, 실제 분기는 build.py의 조건부 엣지가 수행한다
(파트3 routing.py와 동일한 책임 분리).

  with_market : 지역 정보가 있어 상권 API를 부를 가치가 있음
  copy_only   : 지역이 없거나 상권이 무의미한 요청 → 도구 호출 생략(비용·지연 절약)
"""
from utils.logger import get_logger

logger = get_logger(__name__)

# 상권 맥락이 도움 되는 요청 신호(오프라인 매장 홍보 성격)
_LOCAL_SIGNALS = ["근처", "동네", "주변", "상권", "매장", "가게", "오픈", "손님", "방문"]


def routing_node(state) -> dict:
    """
    지역 슬롯 + 요청 성격으로 상권 조회 필요 여부를 정한다.

    Returns:
        dict: route("with_market" | "copy_only")
    """
    region = state.get("region")
    q = state.get("rewritten_question") or state["question"]

    if region:
        route = "with_market"
    elif any(sig in q for sig in _LOCAL_SIGNALS):
        # 지역이 명시되지 않았지만 오프라인 매장 맥락이면, 지역을 되묻는 대신
        # 상권 없이 진행한다(POC는 흐름 완주가 우선. 되묻기는 본 프로젝트 HITL에서).
        route = "copy_only"
    else:
        route = "copy_only"

    logger.info(f"라우팅 | route={route} (region={region})")
    return {"route": route}
