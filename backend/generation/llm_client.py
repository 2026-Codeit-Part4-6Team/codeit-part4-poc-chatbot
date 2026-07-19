"""
llm_client.py
gpt-5-mini 호출 단일 창구. 파트3 llm_client.py의 call_gpt 인터페이스를 그대로 유지한다
(반환: (답변 텍스트, 사용 토큰 수)). 모든 노드는 이 함수만 쓴다.
"""
from openai import OpenAI
from utils.config import load_config, get_openai_key

_client = None


def _get_client() -> OpenAI:
    """OpenAI 클라이언트를 1회만 만들어 재사용한다."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_openai_key(), timeout=60.0, max_retries=2)
    return _client


def call_gpt(messages: list[dict], model: str = None) -> tuple[str, int]:
    """
    Args:
        messages: [{"role": "system"/"user"/"assistant", "content": "..."}]
        model   : 미지정 시 config의 llm_model(gpt-5-mini)
    Returns:
        (답변 텍스트, 총 토큰 수)
    """
    cfg = load_config()
    model = model or cfg["llm_model"]
    resp = _get_client().chat.completions.create(model=model, messages=messages)
    answer = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    return answer, tokens
