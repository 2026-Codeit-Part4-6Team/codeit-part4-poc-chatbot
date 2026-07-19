"""
main.py
FastAPI 서버. Streamlit(프론트)이 이 API를 호출한다.
실행: (루트에서) python -m backend.main   또는   uvicorn backend.main:app --reload
"""
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import RateLimitError, AuthenticationError

from backend.pipeline import get_ai_response

app = FastAPI(title="파트4 POC · 소상공인 광고 카피 Agentic-RAG")

# 프론트(8501)와 백엔드(8000) 포트가 달라 브라우저가 요청을 막으므로 CORS를 연다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 개발용. 실서비스는 특정 도메인만 허용할 것
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str
    history: list[dict] = []
    retriever_type: Optional[str] = None   # naive_rag / agentic_rag 토글


@app.post("/chat")
def chat(req: ChatRequest):
    """질문을 받아 광고 카피와 실행 trace를 반환한다."""
    try:
        return get_ai_response(
            query=req.query,
            history=req.history,
            retriever_type=req.retriever_type,
        )
    except RateLimitError:
        return JSONResponse(status_code=503, content={
            "error": "quota",
            "message": "OpenAI 크레딧이 소진되었습니다. .env의 OPENAI_API_KEY와 결제 상태를 확인하세요.",
        })
    except AuthenticationError:
        return JSONResponse(status_code=401, content={
            "error": "auth",
            "message": "OpenAI 키가 유효하지 않습니다. .env를 확인하고 서버를 재시작하세요.",
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": type(e).__name__, "message": str(e)[:300],
        })


@app.get("/")
def root():
    """서버 상태 확인용 헬스체크."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
