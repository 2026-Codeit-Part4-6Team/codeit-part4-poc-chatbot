"""
FastAPI 서버와 Streamlit 앱 동시 실행.

메인 애플리케이션 실행(run.py) 명령어
python run.py

* 파이썬 공식 문서
sys.exit(1) 함수
참고: https://docs.python.org/ko/3/library/sys.html#sys.exit

* Claude AI 도구 활용
참고: https://claude.ai/chat/658340cd-271c-4cc0-8550-39c500607db3

* Gemini AI 도구 활용
참고: https://gemini.google.com/app/b27729891de22455?hl=ko

* Claude Code AI 도구 활용
참고: https://claude.ai/chat/1975d7a7-892a-470d-8251-188680018c56
참고 2: https://youtu.be/Ejl-ETc5Ojw?si=VXwPYpazRI_WmxxY
"""

import os
import sys
import time
import signal
import logging
import subprocess
from pathlib import Path
from backend.settings import PROJECT_ROOT, BACKEND_DIR, FRONTEND_DIR

# 로깅 설정 (반드시 logger 생성 전에!)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

processes = []  # 전역 프로세스 리스트

def signal_handler(signum, frame):
    """시그널 핸들러 - 프로세스 종료"""
    logger.info("시그널 핸들러 호출")
    logger.info("종료 신호 받음. 서버 종료...")
    
    for i, process in enumerate(processes):
        logger.info(f"프로세스 {i+1} 종료 시작")
        try:
            process.terminate()
            process.wait(timeout=5)
            logger.info(f"프로세스 {i+1} 정상 종료됨")
        except subprocess.TimeoutExpired:
            logger.info(f"프로세스 {i+1} 강제 종료")
            process.kill()
        except Exception as e:
            logger.error(f"프로세스 {i+1} 종료 중 오류: {e}")
    
    logger.info("모든 서버 종료 완료.")
    sys.exit(0)
    
def start_server():
    """FastAPI 서버 시작"""
    logger.info("FastAPI 서버 시작 준비")
    
    try:
        # 백엔드 디렉토리 서버 실행
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        logger.info(f"환경변수 PYTHONPATH 설정: {str(PROJECT_ROOT)}")
        logger.info(f"작업 디렉토리: {str(BACKEND_DIR)}")
        
        # stdout=subprocess.PIPE, stderr=subprocess.STDOUT 등을 쓰면 로그가 엉킬 수 있어 기본 출력 설정.
        # [설정 필수!] "--host", "0.0.0.0", : Docker 컨테이너에 환경을 묶어 올리거나, 모바일 기기(같은 Wi-Fi)에서 접속 테스트를 하거나, 클라우드 서버 배포 및 외부 트래픽 받기 위한 용도
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            # [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            cwd=BACKEND_DIR,
            env=env,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        processes.append(process)
        logger.info("FastAPI 프로세스 -> 프로세스 리스트 추가 완료")
        
        # 서버 시작 대기
        logger.info("FastAPI 서버 시작 대기 중...")
        time.sleep(3)
        
        if process.poll() is None:
            logger.info("FastAPI 서버 시작. (http://localhost:8000)")
            return True
        else:
            logger.error("[오류] FastAPI 서버 시작 실패")
            return False
            
    except Exception as e:
        logger.error(f"[오류] FastAPI 서버 시작 중 오류: {e}")
        return False
    
def start_streamlit():
    """Streamlit 앱 시작"""
    logger.info("Streamlit 앱 시작 준비")
    
    try:
        # 프론트엔드 디렉토리 앱 실행
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        logger.info(f"환경변수 PYTHONPATH 설정: {str(PROJECT_ROOT)}")
        logger.info(f"작업 디렉토리: {str(FRONTEND_DIR)}")
        
        process = subprocess.Popen(
            # [sys.executable, "-m", "streamlit", "run", "app.py", 
            #  "--server.port", "8501",
            #  "--server.address", "0.0.0.0"],
            # [sys.executable, "-m", "streamlit", "run", "app.py", 
            # "--server.port", "8501",
            # "--server.address", "127.0.0.1",
            # "--server.headless", "true"], # 헤드리스 모드(Streamlit 이메일 묻는 과정 생략) 추가
            [sys.executable, "-m", "streamlit", "run", "app.py", 
             "--server.port", "8501",
             "--server.address", "0.0.0.0",
             "--server.headless", "true"], # 헤드리스 모드(Streamlit 이메일 묻는 과정 생략) 추가
            cwd=FRONTEND_DIR,
            env=env,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.STDOUT,
            universal_newlines=True
        )
            
        processes.append(process)
        logger.info("Streamlit 프로세스 -> 프로세스 리스트 추가 완료")
        
        # 앱 시작 대기
        logger.info("Streamlit 앱 시작 대기 중...")
        time.sleep(5)
        
        if process.poll() is None:
            logger.info("Streamlit 앱 시작. (http://localhost:8501)")
            return True
        else:
            logger.error("[오류] Streamlit 앱 시작 실패")
            return False
            
    except Exception as e:
        logger.error(f"[오류] Streamlit 앱 시작 중 오류: {e}")
        return False

def main():
    logger.info("Codeit-Part3-5Team 메인 함수 시작")
    
    # logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
    # logger.info(f"BACKEND_DIR: {BACKEND_DIR}")
    # logger.info(f"FRONTEND_DIR: {FRONTEND_DIR}")
    
    # 시그널 핸들러 등록
    logger.info("시그널 핸들러 등록")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # FastAPI 서버 시작
    if not start_server():
        logger.error("[오류] FastAPI 서버 시작 실패로 인한 프로그램 종료")
        sys.exit(1)
    
    # Streamlit 앱 시작
    if not start_streamlit():
        logger.error("[오류] Streamlit 앱 시작 실패로 인한 프로그램 종료")
        sys.exit(1)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error("[오류] KeyboardInterrupt 감지")
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()