"""
pipeline.py
외부 진입점(FastAPI·Streamlit·평가 공통). 내부 처리는 LangGraph에 위임한다.
파트3 pipeline.py의 get_ai_response 계약(반환 dict 키)을 그대로 따라,
본 프로젝트에서 프론트 수정 없이 확장할 수 있게 한다.
"""
import time

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# LangGraph 앱 캐싱 — 첫 호출 때 1회 컴파일 후 재사용
_graph_app = None


def _get_graph_app():
    """LangGraph 앱을 1회 컴파일해 캐싱한다(지연 import로 순환참조 회피)."""
    global _graph_app
    if _graph_app is None:
        from backend.graph.build import build_graph
        _graph_app = build_graph()
        logger.info("LangGraph 앱 컴파일 완료")
    return _graph_app


def get_ai_response(query: str, history: list[dict] = None, config: dict = None,
                    retriever_type: str = None) -> dict:
    """
    질문을 받아 그래프를 실행하고 결과를 표준 dict로 반환한다.

    Args:
        query         : 사용자 질문
        history       : [{"role","content"}, ...]
        config        : 미지정 시 config.yaml
        retriever_type: naive_rag / agentic_rag (UI 토글이 config보다 우선)

    Returns:
        {answer, sources, market, trace, elapsed_sec, tokens_used, check_flags}
    """
    start = time.time()
    history = history or []
    config = config or load_config()
    if retriever_type:
        config = {**config, "retriever_type": retriever_type}   # 원본 mutate 방지

    app = _get_graph_app()
    result = app.invoke({
        "question": query,
        "history": history[-config.get("max_history", 10):],
        "config": config,
    })

    docs = result.get("docs", [])
    sources = [
        {
            "source": d.metadata.get("source"),
            "score": d.metadata.get("score"),
            "content": d.page_content,
        }
        for d in docs
    ]

    elapsed = round(time.time() - start, 2)
    logger.info(f"응답 완료 | {elapsed}초 | tokens={result.get('tokens_used', 0)}")

    return {
        "answer": result.get("answer", ""),
        "sources": sources,
        "market": result.get("market", {}),
        # trace: POC 성공 기준(루프 동작)을 UI에서 눈으로 확인하기 위한 실행 정보
        "trace": {
            "rewritten_question": result.get("rewritten_question"),
            "biz_type": result.get("biz_type"),
            "region": result.get("region"),
            "route": result.get("route"),
            "market_status": result.get("market_status"),
            "grade": result.get("grade"),
            "retry_count": result.get("retry_count", 0),
            "retrieval_status": result.get("retrieval_status"),
            "check_passed": result.get("check_passed"),
        },
        "elapsed_sec": elapsed,
        "tokens_used": result.get("tokens_used", 0),
        "check_flags": result.get("check_flags", []),
    }


if __name__ == "__main__":
    # 실행: (루트에서) python -m backend.pipeline
    out = get_ai_response("강남역 근처 카페인데 여름 신메뉴 홍보 문구 만들어줘")
    print("trace:", out["trace"])
    print("answer:", out["answer"][:400])
