"""
logger.py
노드 실행 흐름을 콘솔에 남긴다. POC 성공 기준(재검색 루프 동작 확인)을
로그로 증명해야 하므로, 노드마다 한 줄씩 찍는 것을 규칙으로 한다.
"""
import logging
import sys

_FMT = "[%(levelname)s] %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
