"""
self_check.py
검증 노드 — 생성된 카피를 내보내기 전 마지막으로 게이트한다.
룰 기반 점검(추가 LLM 호출 없음). 파트3 self_check.py와 동일한 '최후 안전망' 역할.

점검 항목:
  ① banned_expression : 근거 없이 쓰면 위험한 최상급·단정 표현이 카피에 남아 있음
  ② source_missing    : 규제 근거(docs)가 없는데 '규제 참고'를 단 것처럼 답한 경우

①은 답변을 통째로 버리지 않고 '경고를 덧붙인다'. 카피 자체는 사용자에게 가치가 있고,
어떤 표현이 위험한지 알려주는 것이 소상공인에게 더 유용하기 때문이다
(파트3은 통째 교체였지만, 광고 도메인에서는 경고형이 맞다 — 도메인에 맞춘 의도적 차이).
"""
import re

from utils.logger import get_logger

logger = get_logger(__name__)

# 표시·광고 규제에서 반복적으로 문제되는 표현. 근거 없이 쓰면 위험하다.
_BANNED_PATTERNS = [
    r"최고(?!급)", r"최상", r"1위", r"유일", r"완벽", r"무조건",
    r"완치", r"치료", r"부작용\s*없", r"100%\s*보장", r"절대",
]

_WARN_TEMPLATE = (
    "\n\n---\n⚠️ 표현 점검: 아래 표현은 표시·광고 규제상 객관적 근거 없이 쓰면 "
    "부당 광고로 볼 수 있습니다. 근거가 없다면 순화하세요.\n{items}"
)


def _find_banned(answer: str) -> list[str]:
    """카피에 남은 위험 표현을 찾는다."""
    found = []
    for pat in _BANNED_PATTERNS:
        m = re.search(pat, answer)
        if m:
            found.append(m.group(0))
    return found


def self_check_node(state) -> dict:
    """
    카피를 룰 기반으로 점검하고, 위험 표현이 있으면 경고를 덧붙인다.

    Returns:
        dict: check_passed, check_flags (+ 플래그 시 answer 보정분)
    """
    answer = state.get("answer", "")
    flags = []

    banned = _find_banned(answer)
    if banned:
        flags.append("banned_expression")

    if "규제 참고" in answer and not state.get("docs"):
        flags.append("source_missing")

    if not flags:
        logger.info("검증 | 통과")
        return {"check_passed": True, "check_flags": []}

    patched = answer
    if banned:
        items = "\n".join(f"- {b}" for b in dict.fromkeys(banned))
        patched = answer + _WARN_TEMPLATE.format(items=items)

    logger.info(f"검증 | 플래그={flags} (위험표현 {len(banned)}건)")
    return {"check_passed": False, "check_flags": flags, "answer": patched}
