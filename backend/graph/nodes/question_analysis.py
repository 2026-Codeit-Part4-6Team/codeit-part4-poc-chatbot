"""
question_analysis.py
질문 분석 노드 — history로 지시어를 해소(query rewriting)하고,
카피 생성에 필요한 슬롯(업종·지역·요청사항)을 한 번의 LLM 호출로 함께 뽑는다.

파트3은 rewrite_query()만 했지만, 광고 도메인에서는 '어느 동네 무슨 가게냐'가
이후 도구 호출(상권 API)의 입력이 되므로 슬롯 추출을 같이 한다(호출 1회로 비용 절약).
"""
import json

from backend.generation.llm_client import call_gpt
from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM = """너는 소상공인 광고 카피 생성 서비스의 질문 분석기다.
대화 이력을 참고해 사용자의 마지막 질문에서 지시어("여기","우리 가게","그거")를 구체 명칭으로 바꾸고,
카피 생성에 필요한 정보를 뽑아라.

반드시 아래 JSON 한 줄만 출력하라. 다른 말 금지.
{"rewritten": "지시어가 해소된 단독 질문",
 "biz_type": "업종(카페/미용실/정육점 등). 없으면 null",
 "region": "지역·주소·역명. 없으면 null",
 "request": "톤·채널·소재 등 요청사항 요약. 없으면 null"}"""


def _history_to_text(history: list[dict], limit: int = 4) -> str:
    """최근 대화만 간단한 텍스트로 만든다(토큰 절약)."""
    if not history:
        return "(이전 대화 없음)"
    lines = []
    for turn in history[-limit:]:
        role = "사용자" if turn.get("role") == "user" else "어시스턴트"
        lines.append(f"{role}: {turn.get('content', '')}")
    return "\n".join(lines)


def question_analysis_node(state) -> dict:
    """
    질문을 재구성하고 업종·지역·요청사항 슬롯을 채운다.

    파싱 실패 시 원문을 그대로 rewritten으로 쓰고 슬롯은 비운다(안전한 폴백).

    Returns:
        dict: rewritten_question, biz_type, region, request
    """
    question = state["question"]
    history_text = _history_to_text(state.get("history", []))

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"### 이전 대화:\n{history_text}\n\n### 질문:\n{question}"},
    ]
    raw, _ = call_gpt(messages)

    try:
        parsed = json.loads(raw.strip())
        result = {
            "rewritten_question": parsed.get("rewritten") or question,
            "biz_type": parsed.get("biz_type"),
            "region": parsed.get("region"),
            "request": parsed.get("request"),
        }
    except (json.JSONDecodeError, AttributeError):
        logger.warning("질문 분석 JSON 파싱 실패 → 원문 폴백")
        result = {"rewritten_question": question, "biz_type": None,
                  "region": None, "request": None}

    logger.info(f"질문분석 | 업종={result['biz_type']} 지역={result['region']}")
    return result
