"""
웹 서버 전용 설정 파일

환경변수(.env)에서 설정값 읽어와서 Python 상수로 노출.
.env 파일이 없거나 값이 비어있을 경우 합리적인 기본값 사용.

주의사항: 시크릿(API 키, DB 비밀번호, JSON Web Token 등)은 여기서 노출하지 않습니다.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# === 경로 관련 (환경 무관, 코드에서 결정) ===
# 프로젝트 루트 디렉토리 설정
# __file__이 backend/settings.py에 있으므로, parent.parent를 해야 프로젝트 루트가 됩니다.
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

BACKEND_DIR  = f"{PROJECT_ROOT}/backend"
FRONTEND_DIR = f"{PROJECT_ROOT}/frontend"

# === .env 파일 로딩 (이 파일이 import되는 시점에 환경변수 채워짐) ===
_dotenv_path = Path(PROJECT_ROOT) / ".env"
if _dotenv_path.exists():
    load_dotenv(dotenv_path=_dotenv_path)
else:
    # Streamlit이 아닌 어느 환경에서든 보이도록 logger.warning 사용
    logger.warning(f"⚠️  [Settings] .env 파일이 없습니다: {_dotenv_path}")
    logger.warning("    OPENAI_API_KEY 등 일부 기능이 제한될 수 있습니다.")

# === API 엔드포인트 (환경별로 다름, .env에서 읽음) ===
# 기본값은 로컬 개발 환경 기준
CHAT_URL = os.getenv("CHAT_URL", "http://127.0.0.1:8000/chat")
# CHAT_URL = os.getenv("CHAT_URL", "http://localhost:8000/chat")
# RELOAD_URL=os.getenv("RELOAD_URL", "http://127.0.0.1:8000/reload-model")
# (확장 시) 추가 엔드포인트가 생기면 여기에 추가
# HEALTH_URL = os.getenv("HEALTH_URL", "http://127.0.0.1:8000/health")
# DOCS_URL = os.getenv("DOCS_URL", "http://127.0.0.1:8000/docs")