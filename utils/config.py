"""
config.py
config.yaml(팀 공용) + .env(개인/비밀)을 통합해 설정값을 제공한다.
비밀키는 절대 config.yaml에 두지 않는다(.env만 사용, .gitignore 대상).

⚠️ 경로 규칙
  config.yaml에는 "data/faiss_index" 같은 상대 경로를 쓰지만,
  이 파일이 전부 '프로젝트 루트 기준 절대 경로'로 변환해서 돌려준다.
  이유: run.py가 FastAPI를 backend/, Streamlit을 frontend/ 디렉토리에서 띄우기 때문에
  상대 경로를 그대로 쓰면 프로세스마다 다른 위치를 보게 된다
  (실제로 "FAISS 인덱스를 열 수 없습니다" 오류의 원인이었다).
"""
import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

# utils/config.py → 부모의 부모가 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env는 루트 기준으로 명시적으로 찾는다(실행 위치가 달라도 항상 같은 파일을 읽도록).
# override=True: 이미 설정된 시스템 환경변수보다 .env 값을 우선한다
# (옛 키가 시스템에 남아 있어 .env를 고쳐도 반영되지 않는 사고 방지).
load_dotenv(PROJECT_ROOT / ".env", override=True)

_CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# 상대 경로가 오면 루트 기준 절대 경로로 바꿔줄 키 목록
_PATH_KEYS = ("faiss_index_path", "corpus_path")

_DEFAULTS = {
    "retriever_type": "agentic_rag",   # naive_rag / agentic_rag (토글)
    "top_k": 4,
    "re_retrieve_top_k": 8,
    "max_retry": 2,
    "llm_model": "gpt-5-mini",
    "embedding_model": "text-embedding-3-small",
    "faiss_index_path": "data/faiss_index",
    "corpus_path": "data/corpus",
    "market_radius": 500,              # 상권 조회 반경(m)
    "market_max_stores": 100,
    "max_history": 10,
}


def resolve_path(p: str | Path) -> str:
    """상대 경로면 프로젝트 루트 기준 절대 경로로 바꾼다. 절대 경로면 그대로 둔다."""
    path = Path(p)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


@lru_cache(maxsize=1)
def load_config() -> dict:
    """config.yaml을 읽어 기본값과 병합하고, 경로 키를 절대 경로로 변환해 반환한다."""
    cfg = dict(_DEFAULTS)
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        cfg.update({k: v for k, v in loaded.items() if v is not None})

    # 실행 위치와 무관하게 항상 같은 파일을 가리키도록 절대 경로화
    for key in _PATH_KEYS:
        if cfg.get(key):
            cfg[key] = resolve_path(cfg[key])
    return cfg


def get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(f"OPENAI_API_KEY가 없습니다. {PROJECT_ROOT / '.env'}를 확인하세요.")
    return key


def get_data_go_kr_key() -> str:
    """공공데이터포털 상권정보 API 서비스키(디코딩 키)."""
    return os.getenv("DATA_GO_KR_SERVICE_KEY", "")


def get_kakao_key() -> str:
    """카카오 로컬 API 키(주소 → 좌표 지오코딩용)."""
    return os.getenv("KAKAO_REST_API_KEY", "")


if __name__ == "__main__":
    # 진단용: python -m utils.config
    cfg = load_config()
    print("PROJECT_ROOT      :", PROJECT_ROOT)
    print("faiss_index_path  :", cfg["faiss_index_path"])
    print("  → 존재 여부     :", Path(cfg["faiss_index_path"], "index.faiss").exists())
    print("corpus_path       :", cfg["corpus_path"])
    print("OPENAI_API_KEY    :", (os.getenv("OPENAI_API_KEY") or "(없음)")[:10] + "...")
    print("KAKAO_REST_API_KEY:", "설정됨" if get_kakao_key() else "(없음)")
    print("DATA_GO_KR_KEY    :", "설정됨" if get_data_go_kr_key() else "(없음)")
