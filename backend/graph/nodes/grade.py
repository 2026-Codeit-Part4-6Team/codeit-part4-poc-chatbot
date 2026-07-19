"""
grade.py
검색결과 평가 노드 — 회수한 규제 청크가 카피를 안전하게 쓰기에 충분한지 LLM이 판정한다.
agentic 재검색 루프의 '판단' 부분(루프 배선은 build.py의 조건부 엣지가 담당).

판정 3종 (state.grade):
  sufficient   : 근거 충분 → copy_generation으로
  insufficient : 부족하나 재검색 여지 있음 → re_retrieve 루프로
  out_of_scope : 이 서비스 범위 밖 요청 → 재검색 말고 생성(거부)으로

비용 설계(파트3 grade.py와 동일한 하이브리드):
  docs가 0개면 LLM을 부르지 않고 룰로 insufficient 처리(빈 검색에 LLM 낭비 방지).
"""
import json

from backend.generation.llm_client import call_gpt
from utils.logger import get_logger

logger = get_logger(__name__)

_GRADE_SYSTEM = """너는 소상공인 광고 카피 생성 서비스의 검색결과 평가자다.
사용자 요청과 검색된 '광고 규제 문서 청크'를 보고, 이 청크들로 규제를 지킨 카피를 쓸 수 있는지 판정하라.

판정값은 다음 셋 중 하나다:
- "sufficient"   : 청크에 해당 업종·표현에 적용할 규제 근거가 있다.
- "insufficient" : 광고 카피 요청은 맞는데 청크가 무관하거나 근거가 부족하다(재검색하면 나아질 수 있음).
- "out_of_scope" : 요청 자체가 이 서비스(소상공인 광고 콘텐츠 생성)로 답할 수 없다. 다음은 모두 out_of_scope이며 재검색하지 말라:
    · 경쟁사 비방·허위 사실 유포를 명시적으로 요구
    · 의약품 효능, 질병 치료 효과를 단정하는 광고 요구
    · 광고와 무관한 일반 상식·잡담·코드 작성 요구
    · 타인의 개인정보·연락처 수집 요구

반드시 아래 JSON 한 줄만 출력하라. 다른 말 금지.
{"grade": "sufficient" | "insufficient" | "out_of_scope"}"""


def _docs_to_text(docs: list, max_chars: int = 1800) -> str:
    """청크 본문을 판정용 텍스트로 합친다(길면 잘라 비용 절약)."""
    parts = [f"[청크 {i}] {d.page_content}" for i, d in enumerate(docs, 1)]
    return "\n".join(parts)[:max_chars]


def grade_node(state) -> dict:
    """
    검색결과가 충분한지 판정하고 재시도 횟수를 증가시킨다.

    - docs가 비면 LLM 없이 insufficient로 단락(재검색 기회를 준다).
    - JSON 파싱 실패 시 sufficient로 폴백(루프를 타지 않는 안전한 쪽).

    Returns:
        dict: grade, retry_count
    """
    retry_count = state.get("retry_count", 0) + 1
    docs = state.get("docs", [])

    if not docs:
        logger.info(f"판정 | docs 0개 → insufficient (retry={retry_count})")
        return {"grade": "insufficient", "retry_count": retry_count}

    question = state.get("rewritten_question") or state["question"]
    messages = [
        {"role": "system", "content": _GRADE_SYSTEM},
        {"role": "user",
         "content": f"### 요청:\n{question}\n\n### 검색된 규제 청크:\n{_docs_to_text(docs)}"},
    ]
    raw, _ = call_gpt(messages)   # 판정 토큰은 생성 토큰과 분리(누적 안 함)

    try:
        grade = json.loads(raw.strip()).get("grade", "sufficient")
        if grade not in ("sufficient", "insufficient", "out_of_scope"):
            grade = "sufficient"
    except (json.JSONDecodeError, AttributeError):
        logger.warning("판정 JSON 파싱 실패 → sufficient 폴백")
        grade = "sufficient"

    logger.info(f"판정 | grade={grade} (retry={retry_count}, docs={len(docs)})")
    return {"grade": grade, "retry_count": retry_count}
