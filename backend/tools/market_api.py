"""
market_api.py
소상공인시장진흥공단 상가(상권)정보 API 도구.

이 POC에서 쓰는 엔드포인트는 하나다.
  GET /storeListInRadius  : 좌표 + 반경(m) 내 상가업소 목록

Base URL: https://apis.data.go.kr/B553077/api/open/sdsc2
주소 → 좌표 변환(지오코딩)은 이 API가 제공하지 않으므로 카카오 로컬 API를 쓴다.

키가 없거나 API가 실패해도 파이프라인이 죽지 않게, 모든 실패는 예외 대신
status 문자열로 돌려준다(POC는 '흐름 완주'가 성공 기준이므로 도구 실패에 강건해야 함).
"""
from collections import Counter

import requests

from utils.config import get_data_go_kr_key, get_kakao_key, load_config
from utils.logger import get_logger

logger = get_logger(__name__)

_SDSC_BASE = "https://apis.data.go.kr/B553077/api/open/sdsc2"
_KAKAO_GEOCODE = "https://dapi.kakao.com/v2/local/search/keyword.json"
_TIMEOUT = 10


# 지역명에 붙어 검색을 방해하는 수식어. "강남역 근처"는 카카오에서 검색되지 않는다.
_REGION_NOISE = ["근처", "주변", "인근", "일대", "쪽", "부근", "앞", "옆"]


def normalize_region(region: str) -> list[str]:
    """
    지역 문자열을 검색 가능한 후보 목록으로 정리한다.

    질문 분석 노드가 "강남역 근처"처럼 수식어를 붙여 넘기는 경우가 많아,
    수식어를 떼어낸 형태를 우선 후보로 만들고 원문은 마지막 후보로 남긴다.

    Returns:
        중복 제거된 검색어 후보 리스트 (앞쪽이 우선순위 높음)
    """
    cleaned = region.strip()
    for noise in _REGION_NOISE:
        cleaned = cleaned.replace(noise, " ")
    cleaned = " ".join(cleaned.split())     # 공백 정리

    candidates = []
    if cleaned:
        candidates.append(cleaned)
        # "서울시 강남구 역삼동" 같이 여러 토큰이면 마지막 토큰(가장 구체적)도 후보
        tokens = cleaned.split()
        if len(tokens) > 1:
            candidates.append(tokens[-1])
    candidates.append(region.strip())       # 원문 폴백

    seen, result = set(), []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _geocode_once(query: str, key: str) -> tuple[float, float] | None:
    """카카오 키워드 검색 1회 호출."""
    r = requests.get(
        _KAKAO_GEOCODE,
        headers={"Authorization": f"KakaoAK {key}"},
        params={"query": query, "size": 1},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    docs = r.json().get("documents", [])
    if not docs:
        return None
    return float(docs[0]["x"]), float(docs[0]["y"])


def geocode(query: str) -> tuple[float, float] | None:
    """
    주소·장소명을 좌표(경도, 위도)로 바꾼다. 카카오 키워드 검색을 사용한다.
    "강남역 근처"처럼 수식어가 붙은 입력은 정규화 후보를 순서대로 시도한다.

    Args:
        query: "강남역 근처", "서울시 마포구 연남동" 등
    Returns:
        (lon, lat) 또는 실패 시 None
    """
    key = get_kakao_key()
    if not key:
        logger.warning("KAKAO_REST_API_KEY 없음 → 지오코딩 건너뜀")
        return None

    for candidate in normalize_region(query):
        try:
            coord = _geocode_once(candidate, key)
        except Exception as e:
            logger.error(f"지오코딩 호출 실패({candidate}): {type(e).__name__}: {e}")
            continue
        if coord:
            lon, lat = coord
            note = "" if candidate == query.strip() else f" (원문: '{query}')"
            logger.info(f"지오코딩 성공: '{candidate}' → ({lon:.5f}, {lat:.5f}){note}")
            return lon, lat
        logger.info(f"지오코딩 결과 없음: '{candidate}' → 다음 후보 시도")

    logger.warning(f"지오코딩 최종 실패: {query}")
    return None


def fetch_stores_in_radius(lon: float, lat: float, radius: int = None,
                           num_rows: int = None) -> list[dict]:
    """
    반경 내 상가업소 목록을 조회한다(/storeListInRadius).

    Returns:
        list[dict]: 상가업소 레코드(상호명·업종·좌표 등). 실패 시 빈 리스트.
    """
    cfg = load_config()
    radius = radius or cfg["market_radius"]
    num_rows = num_rows or cfg["market_max_stores"]

    key = get_data_go_kr_key()
    if not key:
        logger.warning("DATA_GO_KR_SERVICE_KEY 없음 → 상권 조회 건너뜀")
        return []

    params = {
        "serviceKey": key,      # 디코딩 키를 넣고 requests가 인코딩하게 둔다
        "radius": radius,
        "cx": lon,
        "cy": lat,
        "numOfRows": num_rows,
        "pageNo": 1,
        "type": "json",
    }
    try:
        r = requests.get(f"{_SDSC_BASE}/storeListInRadius", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        body = r.json().get("body", {})
        items = body.get("items", []) or []
        logger.info(f"상권 조회 성공: 반경 {radius}m 내 {len(items)}건")
        return items
    except Exception as e:
        logger.error(f"상권 조회 실패: {type(e).__name__}: {e}")
        return []


def summarize_market(items: list[dict], biz_type: str | None) -> dict:
    """
    상가업소 원본 레코드를 카피 생성에 쓸 컨텍스트로 요약한다.

    - 반경 내 총 점포 수
    - 우세 업종 상위 5개 (주변 상권 성격 파악)
    - 동일 업종 경쟁 점포 수 (biz_type이 있을 때)

    Returns:
        {store_count, top_upjong, competitor_count, summary}
    """
    if not items:
        return {"store_count": 0, "top_upjong": [], "competitor_count": 0,
                "summary": "상권 데이터를 확인하지 못했습니다."}

    # 상권업종중분류명이 상권 성격을 가장 잘 나타낸다(대분류는 너무 거칠고 소분류는 잘게 쪼개짐)
    upjong = [it.get("indsMclsNm") for it in items if it.get("indsMclsNm")]
    counter = Counter(upjong)
    top = counter.most_common(5)

    competitor_count = 0
    if biz_type:
        # 업종명이 사용자 입력과 부분 일치하는 점포를 경쟁 점포로 센다
        for it in items:
            names = f"{it.get('indsMclsNm', '')} {it.get('indsSclsNm', '')}"
            if biz_type in names:
                competitor_count += 1

    parts = [f"반경 내 점포 {len(items)}곳"]
    if top:
        parts.append("주요 업종: " + ", ".join(f"{n}({c})" for n, c in top))
    if biz_type:
        parts.append(f"'{biz_type}' 동종 점포 {competitor_count}곳")

    return {
        "store_count": len(items),
        "top_upjong": [{"name": n, "count": c} for n, c in top],
        "competitor_count": competitor_count,
        "summary": " · ".join(parts),
    }


def get_market_context(region: str, biz_type: str | None = None) -> tuple[dict, str]:
    """
    지역명 → 좌표 → 반경 상가 조회 → 요약까지 한 번에 수행하는 도구 진입점.

    Returns:
        (market dict, status)
        status: ok / no_coord / api_error
    """
    coord = geocode(region)
    if coord is None:
        return ({"store_count": 0, "top_upjong": [], "competitor_count": 0,
                 "summary": f"'{region}' 좌표를 찾지 못해 상권 정보를 생략합니다."}, "no_coord")

    lon, lat = coord
    items = fetch_stores_in_radius(lon, lat)
    if not items:
        return ({"store_count": 0, "top_upjong": [], "competitor_count": 0,
                 "summary": "상권 API 응답이 비어 상권 정보를 생략합니다."}, "api_error")

    return summarize_market(items, biz_type), "ok"


if __name__ == "__main__":
    # 단독 실행 점검: python -m backend.tools.market_api
    market, status = get_market_context("강남역", "카페")
    print("status:", status)
    print("summary:", market["summary"])
