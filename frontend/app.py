"""
app.py
Streamlit 챗 UI. POC의 목적이 '오케스트레이션이 도는가'를 보이는 것이므로,
답변만이 아니라 실행 trace(route / grade / 재검색 횟수)를 화면에 함께 띄운다.
이 화면이 POC 성공 기준(재검색 루프 동작 확인)의 증거가 된다.

실행: (루트에서) streamlit run frontend/app.py
"""
import requests
import streamlit as st
import sys
# Streamlit Cloud 배포 하기 위해 아래처럼 sys.path.insert 함수 호출(2026.07.22 minjae)
# Path(__file__)은 frontend/app.py이고, .parent.parent는 루트 디렉토리 의미
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.settings import PROJECT_ROOT, RELOAD_URL, CHAT_URL

# API_URL = "http://localhost:8000/chat"
TIMEOUT_SEC = 180

st.set_page_config(page_title="소상공인 광고 카피 생성", page_icon="🧾", layout="wide")
st.title("소상공인 광고 카피 생성 (POC)")
st.caption("상권 정보와 광고 규제 근거를 함께 반영해 카피를 만듭니다.")


# ===== 백엔드 호출 =====

def call_backend(prompt: str, history: list, retriever_type: str):
    """
    백엔드 /chat을 호출한다.

    에러를 화면에 바로 그리지 않고 '값'으로 돌려주는 이유:
    st.status(...) 블록 안에서 st.error를 부르면 상태 박스가 접힐 때
    메시지까지 같이 가려진다. 호출과 렌더링을 분리해 status 밖에서 그린다.

    Returns:
        (data, error_message) — 성공 시 (dict, None), 실패 시 (None, str)
    """
    try:
        res = requests.post(
            # API_URL,
            CHAT_URL,
            json={"query": prompt, "history": history, "retriever_type": retriever_type},
            timeout=TIMEOUT_SEC,
        )
    except requests.exceptions.ConnectionError:
        return None, (
            "백엔드에 연결하지 못했습니다.\n\n"
            "터미널에서 `python -m backend.main`이 실행 중인지 확인하세요."
        )
    except requests.exceptions.Timeout:
        return None, f"백엔드 응답이 {TIMEOUT_SEC}초를 넘었습니다. 잠시 후 다시 시도하세요."
    except Exception as e:
        return None, f"요청 중 오류가 발생했습니다: {type(e).__name__}: {e}"

    # 200이 아니면 서버가 담아 보낸 message를 꺼내 그대로 보여준다
    # (backend/main.py가 quota/auth 등을 구조화해 내려준다)
    if res.status_code != 200:
        try:
            body = res.json()
            detail = body.get("message") or body.get("detail") or res.text[:300]
        except ValueError:
            detail = res.text[:300] or "(응답 본문 없음)"
        return None, f"[HTTP {res.status_code}] {detail}"

    try:
        return res.json(), None
    except ValueError:
        return None, "백엔드 응답을 JSON으로 해석하지 못했습니다."


# ===== 사이드바: 실행 옵션 =====
with st.sidebar:
    st.header("실행 설정")
    retriever_type = st.radio(
        "검색 방식",
        ["agentic_rag", "naive_rag"],
        index=0,
        help="agentic_rag는 근거가 부족하면 스스로 다시 검색합니다. naive_rag는 한 번만 검색합니다.",
    )
    st.divider()
    st.markdown(
        "**시연 시나리오**\n\n"
        "1. 강남역 근처 카페인데 여름 신메뉴 홍보 문구 만들어줘\n"
        "2. 우리 미용실 최고라고 광고 문구 써줘\n"
        "3. 경쟁 가게가 별로라고 깎아내리는 광고 만들어줘"
    )
    if st.button("대화 지우기"):
        st.session_state.messages = []
        st.rerun()

# ===== 세션 상태: 대화 이력 유지 =====
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===== 입력 → 호출 → 렌더 =====
if prompt := st.chat_input("가게 업종과 홍보하고 싶은 내용을 알려주세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1) 진행 상황 표시 + 호출 (여기서는 에러를 '그리지 않고' 받기만 한다)
        with st.status("카피를 만들고 있습니다", expanded=True) as status:
            st.write("질문을 분석하고 상권을 조회합니다…")
            data, error = call_backend(
                prompt=prompt,
                history=st.session_state.messages[:-1],
                retriever_type=retriever_type,
            )
            if error:
                status.update(label="요청이 실패했습니다", state="error", expanded=False)
            else:
                st.write("광고 규제 근거를 검색하고 검증합니다…")
                status.update(label="카피를 완성했습니다", state="complete", expanded=False)

        # 2) 에러 렌더링 — status 블록 '밖'이라 접혀도 가려지지 않는다
        if error:
            st.error(error)
            # 크레딧 소진(503)일 때 해결 방법을 바로 안내
            if "503" in error or "크레딧" in error or "quota" in error.lower():
                st.info(
                    "**해결 방법**\n\n"
                    "1. `.env`의 `OPENAI_API_KEY`를 코드잇 제공 키로 교체하세요.\n"
                    "2. 백엔드 서버를 완전히 종료 후 재시작하세요. "
                    "(`.env`는 프로세스 시작 시 한 번만 읽습니다.)\n"
                    "3. `python -m backend.retrieval.build_index`로 인덱스를 다시 만드세요."
                )
            # 실패한 턴은 대화 이력에 남기지 않는다(다음 요청의 history 오염 방지)
            st.session_state.messages.pop()
            st.stop()

        # 3) 정상 응답 렌더링
        answer = data.get("answer", "")
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # --- 실행 trace: POC의 증거 화면 ---
        trace = data.get("trace", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("라우트", trace.get("route") or "-")
        c2.metric("근거 판정", trace.get("grade") or "-")
        c3.metric("재검색 횟수", trace.get("retry_count") or 0)
        c4.metric("응답 시간", f"{data.get('elapsed_sec', 0)}초")

        if (trace.get("retry_count") or 0) > 1:
            st.info("근거가 부족해 검색을 다시 수행했습니다. (Agentic 재검색 루프 동작)")

        flags = data.get("check_flags", [])
        if flags:
            st.warning(f"검증 플래그: {', '.join(flags)}")

        with st.expander("상권 정보"):
            market = data.get("market") or {}
            if market.get("store_count"):
                st.write(market.get("summary", ""))
                st.json(market.get("top_upjong", []))
            else:
                st.write(f"상권 정보를 사용하지 않았습니다. (상태: {trace.get('market_status')})")

        with st.expander(f"검색된 규제 근거 {len(data.get('sources', []))}건"):
            for i, s in enumerate(data.get("sources", []), 1):
                st.markdown(f"**[{i}] {s.get('source')}** (score: {s.get('score')})")
                st.caption(s.get("content", "")[:300])
